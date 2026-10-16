"""
Campaigns: creatives (uploaded or made in Poster Studio) -> strategist plan -> approval ->
Instagram post -> Meta campaign built PAUSED -> explicit launch.

Governance (code, not prompts):
- Nothing public or paid happens before POST /approve; launching spend needs a second POST /launch.
- Each MCP call carries an Ed25519 approval token minted here for that exact payload.
- Publish is idempotent per campaign; a retry never posts twice.
The UI polls GET /campaigns/{id} for progress while background steps run.
"""
import asyncio
import json
import logging
import os
import re
import secrets
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

import instagram_server
import meta_ads_server
from campaign_strategist import CampaignStrategist
from campaign_strategist.rules import CONVERSION_DAILY_FLOOR, MIN_DAILY_BUDGET, max_daily_budget
from mcp_common import TenantContext, ToolCallRequest
from mcp_common.meta_graph import MetaGraphError, meta_mock_enabled, meta_mode
from model_gateway import GroqCallError
from poster_studio import StoreError, StudioStore
from poster_studio.imaging import InvalidImageError, is_mp4, normalise_upload, to_instagram_jpeg

from ..core.security import APPROVAL_PUBLIC_KEY_HEX, mint_approval_token
from .meta_connect import graph_for, mark_needs_reauth

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/studio", tags=["Campaigns"])

store = StudioStore()
strategist = CampaignStrategist(cache_get=store.cache_get, cache_set=store.cache_set)

MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024
MAX_CREATIVES = 10
_tasks: set = set()  # keep references to background tasks


async def _graph_provider(ctx: TenantContext):
    return await graph_for(ctx.tenant_id)


async def _asset_provider(ctx: TenantContext, asset_id: str) -> bytes:
    data, _ = store.read_asset(ctx.tenant_id, asset_id)
    return data


for _srv in (instagram_server, meta_ads_server):
    _srv.graph_provider = _graph_provider
    _srv.server.set_approval_public_key(APPROVAL_PUBLIC_KEY_HEX)
meta_ads_server.asset_provider = _asset_provider


def _ws(workspace: Optional[str]) -> str:
    if not workspace:
        raise HTTPException(status_code=400, detail="X-Studio-Workspace header required")
    return workspace


def _now() -> int:
    return int(time.time())


def _load(ws: str, cid: str) -> Dict[str, Any]:
    try:
        return store.load_doc(ws, "campaigns", cid)
    except StoreError:
        raise HTTPException(status_code=404, detail="Campaign not found")


def _save(ws: str, c: Dict[str, Any]) -> Dict[str, Any]:
    c["updated_at"] = _now()
    return store.save_doc(ws, "campaigns", c["id"], c)


def _event(c: Dict[str, Any], step: str, status: str, message: str = "") -> None:
    c.setdefault("timeline", []).append({"t": _now(), "step": step, "status": status, "message": message})
    c.setdefault("steps", {})[step] = status


def _selection(ws: str) -> Dict[str, Any]:
    meta = store.load_private(ws, "connections").get("meta") or {}
    if meta.get("mock") and not meta_mock_enabled():
        return {}
    return meta.get("selection") or {}


# ---- creative uploads (images + videos) ----------------------------------------

@router.post("/uploads/creative")
async def upload_creative(file: UploadFile = File(...), x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    raw = await file.read(MAX_VIDEO_BYTES + 1)
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        if is_mp4(raw):
            if len(raw) > MAX_VIDEO_BYTES:
                raise HTTPException(status_code=413, detail="Videos must be 100 MB or smaller")
            asset = store.save_asset(ws, raw, "video/mp4")
            kind = "video"
        else:
            if len(raw) > MAX_IMAGE_BYTES:
                raise HTTPException(status_code=413, detail="Images must be 15 MB or smaller")
            data, mime, _, _ = normalise_upload(raw, max_side=2160, keep_alpha=False)
            asset = store.save_asset(ws, data, mime)
            kind = "image"
    except InvalidImageError:
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG or WebP image, or an MP4 video")
    except StoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"asset_id": asset["asset_id"], "url": asset["url"], "kind": kind, "name": file.filename or ""}


# ---- campaign CRUD ----------------------------------------------------------------

class CreativeRef(BaseModel):
    asset_id: str
    name: str = ""
    insight: Optional[Dict[str, Any]] = None  # Poster Studio passes what it already knows (saves a vision call)


class Business(BaseModel):
    goal: str = Field("", max_length=500)
    product: str = Field("", max_length=200)
    notes: str = Field("", max_length=1000)
    website_url: str = Field("", max_length=500)
    pixel_id: str = Field("", max_length=40)
    daily_budget: Optional[float] = None
    duration_days: Optional[int] = None


class CreateCampaign(BaseModel):
    source: str = "upload"
    creatives: List[CreativeRef]
    business: Business = Business()


def _summary(c: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": c["id"], "status": c["status"], "source": c["source"], "created_at": c["created_at"],
        "name": ((c.get("strategy") or {}).get("plan") or {}).get("name") or c["business"].get("product") or "Untitled campaign",
        "thumbnail": next((x["url"] for x in c["creatives"] if x["kind"] == "image"), None),
        "instagram": c.get("instagram"), "meta_status": (c.get("meta") or {}).get("status"),
    }


@router.get("/campaigns")
async def list_campaigns(x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    return {"campaigns": [_summary(c) for c in store.list_docs(ws, "campaigns")]}


@router.post("/campaigns")
async def create_campaign(body: CreateCampaign, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    if not body.creatives:
        raise HTTPException(status_code=400, detail="Add at least one creative")
    if len(body.creatives) > MAX_CREATIVES:
        raise HTTPException(status_code=400, detail=f"Up to {MAX_CREATIVES} creatives per campaign")
    creatives = []
    for ref in body.creatives:
        try:
            store.asset_path(ws, ref.asset_id)
        except StoreError:
            raise HTTPException(status_code=400, detail=f"Unknown creative {ref.asset_id}")
        kind = "video" if ref.asset_id.endswith(".mp4") else "image"
        creatives.append({"asset_id": ref.asset_id, "url": store.url_for(ws, ref.asset_id), "kind": kind,
                          "name": ref.name, "insight": ref.insight})
    cid = secrets.token_hex(12)
    c = {
        "id": cid, "created_at": _now(), "source": body.source if body.source in ("upload", "studio") else "upload",
        "status": "draft", "creatives": creatives, "business": body.business.model_dump(),
        "strategy": None, "instagram": None, "meta": None, "error": "", "timeline": [], "steps": {},
    }
    _event(c, "created", "done")
    return _save(ws, c)


@router.get("/campaigns/{cid}")
async def get_campaign(cid: str, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    c = _load(ws, cid)
    c["connection"] = {k: v for k, v in _selection(ws).items()}
    c["meta_mode"] = meta_mode()
    return c


# ---- strategy ---------------------------------------------------------------------

class StrategyBody(BaseModel):
    instruction: str = Field("", max_length=500)
    business: Optional[Business] = None


@router.post("/campaigns/{cid}/strategy")
async def build_strategy(cid: str, body: StrategyBody, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    c = _load(ws, cid)
    if c["status"] not in ("draft", "planned", "failed"):
        raise HTTPException(status_code=409, detail="This campaign is already approved")
    if body.business:
        c["business"] = body.business.model_dump()
    c["status"] = "planning"
    _event(c, "strategy", "running")
    _save(ws, c)

    sel = _selection(ws)
    connected = bool(sel.get("ad_account_id")) or meta_mock_enabled()

    async def meta_search(q: str, kind: str, country: str):
        if not connected:
            return []
        req = ToolCallRequest(tool="ads.targeting_search", arguments={"q": q, "type": kind, "country_code": country},
                              tenant_context=TenantContext(tenant_id=ws, workspace_role="EDITOR"))
        res = await meta_ads_server.server.execute_tool(req)
        return res.data["results"] if res.success else []

    async def estimate(audience: Dict[str, Any], objective: str):
        if not connected:
            return {}
        req = ToolCallRequest(
            tool="ads.delivery_estimate",
            arguments={"ad_account_id": sel.get("ad_account_id") or "act_mock", "audience": audience, "objective": objective},
            tenant_context=TenantContext(tenant_id=ws, workspace_role="EDITOR"),
        )
        res = await meta_ads_server.server.execute_tool(req)
        return res.data if res.success else {}

    creatives = []
    for x in c["creatives"]:
        data = store.read_asset(ws, x["asset_id"])[0] if x["kind"] == "image" else None
        creatives.append({"kind": x["kind"], "bytes": data})

    try:
        result = await strategist.run(
            creatives=creatives,
            business=c["business"],
            account={"currency": sel.get("currency", "INR"), "timezone": sel.get("timezone", "Asia/Kolkata"),
                     "country_code": os.getenv("DEFAULT_COUNTRY", "IN")},
            meta_search=meta_search,
            estimate=estimate,
            instruction=body.instruction,
            known_insights=[x.get("insight") for x in c["creatives"]],
        )
    except (GroqCallError, ValueError) as e:
        c["status"], c["error"] = "failed", f"Strategy failed: {e}"
        _event(c, "strategy", "failed", str(e))
        _save(ws, c)
        raise HTTPException(status_code=502, detail=c["error"])

    if not connected:
        result["warnings"].insert(0, "Connect Instagram & Meta to verify interests with Meta and get real reach estimates.")
    for i, ins in enumerate(result.pop("insights")):
        if ins and not c["creatives"][i].get("insight"):
            c["creatives"][i]["insight"] = ins
    c["strategy"] = result
    c["status"], c["error"] = "planned", ""
    _event(c, "strategy", "done", f"{result['usage']['prompt_tokens'] + result['usage']['completion_tokens']} Groq tokens")
    logger.info(f"[Campaign] strategy ready for {cid}: {result['usage']}")
    return _save(ws, c)


# ---- user edits to the plan ---------------------------------------------------------

class PlanEdits(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    objective: Optional[str] = None
    daily_budget: Optional[float] = None
    duration_days: Optional[int] = None
    start_time_iso: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    genders: Optional[str] = None
    remove_interest_ids: List[str] = Field(default_factory=list)
    ads: Optional[List[Dict[str, Any]]] = None
    caption: Optional[str] = Field(None, max_length=2200)
    website_url: Optional[str] = Field(None, max_length=500)


@router.put("/campaigns/{cid}/plan")
async def edit_plan(cid: str, edits: PlanEdits, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    c = _load(ws, cid)
    if c["status"] != "planned" or not c.get("strategy"):
        raise HTTPException(status_code=409, detail="The plan can only be edited before approval")
    plan, warnings = c["strategy"]["plan"], []
    cur = plan["currency"]

    if edits.name:
        plan["name"] = edits.name.strip()
    if edits.website_url is not None:
        c["business"]["website_url"] = edits.website_url.strip()
    if edits.objective:
        has_site, has_pixel = bool(c["business"].get("website_url")), bool(c["business"].get("pixel_id"))
        allowed = {"OUTCOME_AWARENESS", "OUTCOME_ENGAGEMENT"} | ({"OUTCOME_TRAFFIC"} if has_site else set()) | (
            {"OUTCOME_SALES", "OUTCOME_LEADS"} if has_pixel and has_site else set())
        if edits.objective not in allowed:
            raise HTTPException(status_code=400, detail="That objective needs a website link (and a Pixel for Sales/Leads)")
        plan["objective"] = edits.objective
        plan["delivery"] = "link_ads" if has_site else "boost_instagram_post"
    if edits.daily_budget is not None:
        lo, hi = MIN_DAILY_BUDGET.get(cur, 2), max_daily_budget()
        if not lo <= edits.daily_budget <= hi:
            raise HTTPException(status_code=400, detail=f"Daily budget must be between {lo} and {hi:.0f} {cur}")
        plan["daily_budget"] = round(edits.daily_budget, 2)
        if plan["objective"] in ("OUTCOME_SALES", "OUTCOME_LEADS", "OUTCOME_TRAFFIC") and edits.daily_budget < CONVERSION_DAILY_FLOOR.get(cur, 10):
            warnings.append(f"Below {CONVERSION_DAILY_FLOOR.get(cur, 10)} {cur}/day this objective may not exit the learning phase.")
    if edits.duration_days is not None:
        if not 1 <= edits.duration_days <= 90:
            raise HTTPException(status_code=400, detail="Duration must be 1-90 days")
        plan["duration_days"] = edits.duration_days
    if edits.start_time_iso:
        from datetime import datetime
        try:
            start = datetime.fromisoformat(edits.start_time_iso)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start time")
        if start.tzinfo and start.timestamp() < time.time():
            raise HTTPException(status_code=400, detail="Start time must be in the future")
        plan["start_time_iso"] = edits.start_time_iso
    aud = plan["audience"]
    special = bool(plan.get("special_ad_categories"))
    if edits.age_min is not None or edits.age_max is not None:
        if special:
            raise HTTPException(status_code=400, detail="Age targeting is restricted for this special ad category")
        lo, hi = edits.age_min or aud["age_min"], edits.age_max or aud["age_max"]
        if not 18 <= lo <= hi <= 65:
            raise HTTPException(status_code=400, detail="Age range must be within 18-65")
        aud["age_min"], aud["age_max"] = lo, hi
    if edits.genders:
        if special or edits.genders not in ("all", "male", "female"):
            raise HTTPException(status_code=400, detail="Invalid gender targeting")
        aud["genders"] = edits.genders
    if edits.remove_interest_ids:
        aud["interests"] = [i for i in aud["interests"] if i["id"] not in edits.remove_interest_ids]
    if edits.ads is not None:
        by_idx = {a["creative_index"]: a for a in plan["ads"]}
        for upd in edits.ads:
            ad = by_idx.get(upd.get("creative_index"))
            if ad:
                for k, limit in (("primary_text", 300), ("headline", 60), ("description", 60)):
                    if k in upd:
                        ad[k] = str(upd[k])[:limit]
    if edits.caption is not None:
        c["strategy"]["caption"] = edits.caption
    c["strategy"]["edit_warnings"] = warnings
    return _save(ws, c)


# ---- approval -> publish -> build ads (background) ------------------------------------

class ApproveBody(BaseModel):
    publish_instagram: bool = True
    create_ads: bool = True


def _public_url(ws: str, asset_id: str, graph_is_mock: bool) -> str:
    base = os.getenv("PUBLIC_ASSET_BASE_URL", "").rstrip("/")
    if not base:
        if graph_is_mock:
            return f"http://localhost{store.url_for(ws, asset_id)}"
        raise HTTPException(
            status_code=400,
            detail="Instagram downloads media from a public URL. Set PUBLIC_ASSET_BASE_URL (e.g. a Cloudflare Tunnel or ngrok URL to this app).",
        )
    return f"{base}{store.url_for(ws, asset_id)}"


async def _call(server, tool: str, ws: str, args: Dict[str, Any], c: Dict[str, Any]) -> Dict[str, Any]:
    token = mint_approval_token(tenant_id=ws, tool_name=tool, payload=args)
    c.setdefault("approval", {}).setdefault("tokens_used", []).append({"tool": tool, "jti": token["token_jti"]})
    res = await server.execute_tool(ToolCallRequest(
        tool=tool, arguments=args, tenant_context=TenantContext(tenant_id=ws, workspace_role="APPROVER"),
        approval_token=json.dumps(token), idempotency_key=f"{c['id']}:{tool}",
    ))
    if not res.success:
        raise RuntimeError(res.error or f"{tool} failed")
    return res.data


async def _execute(ws: str, cid: str, publish: bool, build_ads: bool) -> None:
    c = _load(ws, cid)
    sel = _selection(ws)
    plan = c["strategy"]["plan"]
    try:
        graph = await graph_for(ws)
        mock = bool(getattr(graph, "mock", False))

        # Instagram-ready JPEG copies of image creatives
        for x in c["creatives"]:
            if x["kind"] == "image" and not x.get("jpeg_asset_id"):
                jpeg = to_instagram_jpeg(store.read_asset(ws, x["asset_id"])[0])
                x["jpeg_asset_id"] = store.save_asset(ws, jpeg, "image/jpeg")["asset_id"]
        _save(ws, c)

        if publish and not c.get("instagram"):
            c["status"] = "publishing"
            _event(c, "publish", "running", "Posting to Instagram")
            _save(ws, c)
            items = [{"url": _public_url(ws, x.get("jpeg_asset_id") or x["asset_id"], mock), "kind": x["kind"]}
                     for x in c["creatives"]]
            result = await _call(instagram_server.server, "instagram.publish", ws, {
                "ig_user_id": sel.get("ig_user_id") or "17841400000000001",
                "items": items, "caption": c["strategy"].get("caption", ""),
                "idempotency_key": f"{cid}:publish",
            }, c)
            c["instagram"] = result
            c["status"] = "published"
            _event(c, "publish", "done", result.get("permalink", ""))
            _save(ws, c)

        if build_ads:
            c["status"] = "building_ads"
            _event(c, "build_ads", "running", "Creating campaign in Meta (paused)")
            _save(ws, c)
            ads = []
            for ad in plan["ads"]:
                x = c["creatives"][ad["creative_index"]]
                entry = {k: ad[k] for k in ("primary_text", "headline", "description", "cta")}
                if plan["delivery"] == "boost_instagram_post":
                    if not c.get("instagram"):
                        raise RuntimeError("Promoting a post needs it published on Instagram first")
                    entry["boost_media_id"] = c["instagram"]["media_id"]
                    if x["kind"] == "image":
                        entry["image_asset_id"] = x["jpeg_asset_id"]  # fallback if Meta refuses to boost the post
                else:
                    if x["kind"] != "image":
                        continue
                    entry["image_asset_id"] = x["jpeg_asset_id"]
                ads.append(entry)
            if not ads:
                raise RuntimeError("No ads could be built from the selected creatives")
            result = await _call(meta_ads_server.server, "ads.create_campaign", ws, {
                "plan": plan, "ad_account_id": sel.get("ad_account_id") or "act_300000000000001",
                "currency": plan["currency"], "page_id": sel.get("page_id") or "200000000000001",
                "ig_user_id": sel.get("ig_user_id") or "17841400000000001",
                "website_url": c["business"].get("website_url", ""), "pixel_id": c["business"].get("pixel_id", ""),
                "start_time_iso": plan["start_time_iso"], "ads": ads,
            }, c)
            c["meta"] = result
            c["status"] = "ads_ready"
            _event(c, "build_ads", "done", f"{len(result['ad_ids'])} ads created, paused" + (
                " (built from your image: Meta can't promote posts made by an app in Development mode)"
                if result.get("used_image_fallback") else ""))
        else:
            c["status"] = "done"
        _save(ws, c)
    except Exception as e:
        if isinstance(e, MetaGraphError) and e.needs_reauth:
            mark_needs_reauth(ws)
        message = e.detail if isinstance(e, HTTPException) else str(e)
        if "development mode" in message.lower():
            message += (
                " — Meta does not allow ads from an app in Development mode. Switch your Meta app to Live mode "
                "(developers.facebook.com → your app → App Mode: Live), then press Retry. Your Instagram post is not affected."
            )
        elif re.search(r"Meta API error 31:", message):
            message += (
                " — Meta put a security hold on your ad account. Open adsmanager.facebook.com, confirm it's you "
                "(login code / two-factor), then press Retry. It can take a few minutes to lift."
            )
        elif re.search(r"Meta API error (10|200|190):", message):
            message += (
                " — Your Meta connection is missing a permission or has expired. Make sure your login configuration "
                "includes instagram_basic and instagram_content_publish (plus the ads permissions), then disconnect and "
                "reconnect Instagram & Meta in Integrations and press Retry."
            )
        logger.error(f"[Campaign] execution failed for {cid}: {message}")
        c = _load(ws, cid) if not c else c
        step = "build_ads" if c["status"] == "building_ads" else "publish"
        c["status"], c["error"] = "failed", message
        _event(c, step, "failed", message)
        _save(ws, c)


@router.post("/campaigns/{cid}/approve")
async def approve_campaign(cid: str, body: ApproveBody, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    c = _load(ws, cid)
    if c["status"] not in ("planned", "failed") or not c.get("strategy"):
        raise HTTPException(status_code=409, detail="Generate and review the campaign plan first")
    sel = _selection(ws)
    if not meta_mock_enabled():
        if body.publish_instagram and not sel.get("ig_user_id"):
            raise HTTPException(status_code=400, detail="Connect Instagram and choose an account first")
        if body.create_ads and not sel.get("ad_account_id"):
            raise HTTPException(status_code=400, detail="Connect Meta and choose an ad account first")
        if body.publish_instagram and not os.getenv("PUBLIC_ASSET_BASE_URL"):
            raise HTTPException(status_code=400, detail="Set PUBLIC_ASSET_BASE_URL so Instagram can download your media")
    c["approval"] = {**(c.get("approval") or {}), "approved_at": _now(),
                     "publish_instagram": body.publish_instagram, "create_ads": body.create_ads}
    c["status"], c["error"] = "approved", ""
    _event(c, "approve", "done")
    _save(ws, c)
    task = asyncio.create_task(_execute(ws, cid, body.publish_instagram, body.create_ads))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return c


@router.post("/campaigns/{cid}/launch")
async def launch_campaign(cid: str, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    c = _load(ws, cid)
    if c["status"] != "ads_ready" or not c.get("meta"):
        raise HTTPException(status_code=409, detail="Ads must be built (paused) before launch")
    c["status"] = "launching"
    _event(c, "launch", "running")
    _save(ws, c)
    try:
        await _call(meta_ads_server.server, "ads.activate", ws, {
            "campaign_id": c["meta"]["campaign_id"], "adset_id": c["meta"]["adset_id"], "ad_ids": c["meta"]["ad_ids"],
        }, c)
    except Exception as e:
        if isinstance(e, MetaGraphError) and e.needs_reauth:
            mark_needs_reauth(ws)
        c["status"], c["error"] = "ads_ready", f"Launch failed: {e}"
        _event(c, "launch", "failed", str(e))
        _save(ws, c)
        raise HTTPException(status_code=502, detail=c["error"])
    c["meta"]["status"] = "ACTIVE"
    c["status"] = "live"
    _event(c, "launch", "done")
    return _save(ws, c)
