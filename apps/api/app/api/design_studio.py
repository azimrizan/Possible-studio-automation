"""
AI Design: brief (+ photos + brand kit) -> three art-directed concepts, rendered at every chosen size.

Modes
- basic:    Claude + code-rendered layouts; your photos (products cut out on this server). No image model.
- advanced: same, plus text-free AI backgrounds (Gemini) behind the code-rendered text.

Flow: POST /designs (starts generation) -> poll GET /designs/{id} -> edit a concept (PUT) or
      ask Claude to change it (POST .../revise) -> download the PNGs.
"""
import asyncio
import logging
import secrets
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

import design_studio as ds
import reel_studio as rs
from poster_studio import StoreError, StudioStore

from .studio import _image_backend

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/studio/designs", tags=["AI Design"])
store = StudioStore()

MODES = {"basic", "advanced"}
GOALS = {"promote", "offer", "launch", "event", "testimonial", "educate", "announce"}
PHOTO_KINDS = {"product", "photo"}
BUSY = {"generating", "rendering"}
_tasks: set = set()


def _ws(workspace: Optional[str]) -> str:
    if not workspace:
        raise HTTPException(status_code=400, detail="X-Studio-Workspace header required")
    return workspace


def _now() -> int:
    return int(time.time())


def _load(ws: str, did: str) -> Dict[str, Any]:
    try:
        return store.load_doc(ws, "designs", did)
    except StoreError:
        raise HTTPException(status_code=404, detail="Design not found")


def _save(ws: str, d: Dict[str, Any]) -> Dict[str, Any]:
    d["updated_at"] = _now()
    return store.save_doc(ws, "designs", d["id"], d)


def _progress(ws: str, d: Dict[str, Any], message: str) -> None:
    d["progress"] = message
    _save(ws, d)


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def _public(d: Dict[str, Any]) -> Dict[str, Any]:
    return {**d, "modes": {"director": rs.director_mode(), "renderer_ready": rs.renderer_ready(),
                           "cutouts": ds.cutout_available()}}


# ---- assets for rendering -------------------------------------------------------------

def _brand(ws: str, use: bool) -> Dict[str, Any]:
    return store.load_brand_kit(ws) if use else {}


def _stage(ws: str, d: Dict[str, Any], public: Path) -> Dict[str, Any]:
    """Copies photos (cut out when they're products), logo and plates into the render dir; returns their names."""
    public.mkdir(parents=True, exist_ok=True)
    staged: Dict[str, Any] = {"photos": [], "logo": None}
    for i, ph in enumerate(d["photos"]):
        raw_name = f"photo_{i}.{ph['asset_id'].rsplit('.', 1)[1]}"
        if not (public / raw_name).exists():
            shutil.copyfile(store.asset_path(ws, ph["asset_id"]), public / raw_name)
        entry = {"src": raw_name, "cutout": False}
        if ph.get("kind", "product") == "product":
            cut = public / f"photo_{i}_cut.png"
            if cut.exists() or ds.cut_out_file(public / raw_name, cut):
                entry = {"src": cut.name, "cutout": True}
        staged["photos"].append(entry)
    logo_id = (d.get("brand") or {}).get("logo_asset_id")
    if logo_id:
        name = f"logo.{logo_id.rsplit('.', 1)[1]}"
        try:
            if not (public / name).exists():
                shutil.copyfile(store.asset_path(ws, logo_id), public / name)
            staged["logo"] = name
        except StoreError:
            pass
    return staged


def _props(d: Dict[str, Any], c: Dict[str, Any], size: str, staged: Dict[str, Any]) -> Dict[str, Any]:
    photo = staged["photos"][0] if c.get("use_photo") and staged["photos"] else None
    plate = ds.plate_for(size, c.get("plates") or {}) if c["bg_style"] == "plate" else None
    return ds.render_props(c, size, (d.get("brand") or {}).get("brand_name", ""), photo, plate, staged["logo"])


async def _render(ws: str, d: Dict[str, Any], work: Path, public: Path, staged: Dict[str, Any],
                  which: List[int], sizes: List[str], out_dir: Path) -> Dict[int, Dict[str, Path]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks, outputs = [], {}
    for i in which:
        c = d["concepts"][i]
        for size in sizes:
            path = out_dir / f"c{i}_{size}.png"
            tasks.append({"kind": "still", "composition": "Design", "props": _props(d, c, size, staged), "out": str(path)})
            outputs.setdefault(i, {})[size] = path
    await rs.run_job(work, public, tasks)
    return outputs


def _store_renders(ws: str, d: Dict[str, Any], outputs: Dict[int, Dict[str, Path]]) -> None:
    for i, by_size in outputs.items():
        renders = d["concepts"][i].setdefault("renders", {})
        for size, path in by_size.items():
            old = renders.get(size, {}).get("asset_id")
            asset = store.save_asset(ws, path.read_bytes(), "image/png")
            renders[size] = {"asset_id": asset["asset_id"], "url": asset["url"]}
            path.unlink(missing_ok=True)
            if old:
                store.delete_asset(ws, old)


# ---- generation -----------------------------------------------------------------------

def _normalise_all(d: Dict[str, Any], plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    colors = (d.get("brand") or {}).get("colors") or []
    return [ds.normalise_concept(c, colors, bool(d["photos"]), d["mode"] == "advanced") for c in (plan.get("concepts") or [])[:3]]


async def _run_generate(ws: str, did: str, image_fn) -> None:
    d = _load(ws, did)
    try:
        work = store.work_dir(ws, "designs", did)
        public = work / "public"
        brief = {"text": d["brief"], "goal": d["goal"], "language": d["language"]}
        photos = [store.read_asset(ws, p["asset_id"])[0] for p in d["photos"]]

        _progress(ws, d, "Preparing your photos" if d["photos"] else "Starting")
        staged = await asyncio.to_thread(_stage, ws, d, public)

        _progress(ws, d, "Claude is art-directing three concepts")
        plan = await ds.plan_concepts(brief, d["brand_ctx"], photos, d["mode"])
        d["concepts"] = _normalise_all(d, plan)
        d["plan_meta"] = {k: plan.get(k) for k in ("summary", "caption", "hashtags", "notes", "mode", "model", "usage")}

        if plan.get("mode") == "claude" and d["concepts"]:
            _progress(ws, d, "Claude is checking the rendered designs")
            try:
                outs = await _render(ws, d, work, public, staged, list(range(len(d["concepts"]))), [d["sizes"][0]], work / "review")
                order = [outs[i][d["sizes"][0]] for i in sorted(outs)]
                sheet = rs.contact_sheet(order, [f"Concept {i + 1}" for i in range(len(order))], work / "review" / "sheet.jpg", cols=3, width=360)
                revised = await ds.review_concepts(brief, d["brand_ctx"], plan, sheet, len(photos), d["mode"])
                if revised and revised.get("concepts"):
                    d["concepts"] = _normalise_all(d, revised)
                    d["plan_meta"].update({k: revised.get(k) for k in ("caption", "hashtags", "notes", "usage")}, reviewed=True)
            except (rs.RenderError, rs.DirectorError) as e:  # the first concepts are still usable
                logger.warning(f"[Designs] self-check skipped for {did}: {e}")

        if d["mode"] == "advanced" and image_fn:
            for i, c in enumerate(d["concepts"]):
                if c["bg_style"] != "plate" and c.get("plate_prompt"):
                    c["bg_style"] = "plate"
                if c["bg_style"] != "plate":
                    continue
                _progress(ws, d, f"Generating the background for concept {i + 1}")
                plates = await ds.make_plates(c, d["sizes"], image_fn)
                c["plates"] = {}
                for aspect, (data, mime) in plates.items():
                    name = f"plate_{i}_{aspect.replace(':', 'x')}.{'png' if 'png' in mime else 'jpg'}"
                    (public / name).write_bytes(data)
                    c["plates"][aspect] = name
                if not c["plates"]:
                    c["bg_style"] = "gradient"

        _progress(ws, d, f"Rendering {len(d['concepts'])} designs × {len(d['sizes'])} sizes")
        outs = await _render(ws, d, work, public, staged, list(range(len(d["concepts"]))), d["sizes"], work / "out")
        _store_renders(ws, d, outs)
        d.update(status="ready", progress="", error="")
    except (rs.RenderError, rs.DirectorError, StoreError, OSError, ValueError) as e:
        logger.error(f"[Designs] generation failed for {did}: {e}")
        d.update(status="failed", progress="", error=str(e))
    _save(ws, d)


async def _run_rerender(ws: str, did: str, i: int) -> None:
    d = _load(ws, did)
    try:
        work = store.work_dir(ws, "designs", did)
        public = work / "public"
        staged = await asyncio.to_thread(_stage, ws, d, public)
        outs = await _render(ws, d, work, public, staged, [i], d["sizes"], work / "out")
        _store_renders(ws, d, outs)
        d.update(status="ready", progress="", error="")
    except (rs.RenderError, StoreError, OSError) as e:
        logger.error(f"[Designs] re-render failed for {did}: {e}")
        d.update(status="failed", progress="", error=str(e))
    _save(ws, d)


# ---- routes ---------------------------------------------------------------------------

class PhotoRef(BaseModel):
    asset_id: str
    kind: str = "product"


class CreateBody(BaseModel):
    brief: str = Field(..., min_length=3, max_length=1500)
    goal: str = "promote"
    mode: str = "basic"
    language: str = Field("en", max_length=10)
    sizes: List[str] = Field(default_factory=lambda: ["portrait", "square", "story"], min_length=1, max_length=4)
    photos: List[PhotoRef] = Field(default_factory=list, max_length=3)
    use_brand_kit: bool = True
    api_key: Optional[str] = None
    oauth_token: Optional[str] = None


@router.get("")
async def list_designs(x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    out = []
    for d in store.list_docs(ws, "designs"):
        first = next((c.get("renders", {}).get(d["sizes"][0], {}).get("url") for c in d.get("concepts") or [] if c.get("renders")), None)
        out.append({"id": d["id"], "brief": d["brief"][:80], "status": d["status"], "mode": d["mode"], "updated_at": d.get("updated_at"), "thumb": first})
    return out


@router.post("")
async def create_design(body: CreateBody, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    if body.mode not in MODES or body.goal not in GOALS:
        raise HTTPException(status_code=400, detail="Unknown mode or goal")
    sizes = [s for s in dict.fromkeys(body.sizes) if s in ds.SIZES]
    if not sizes:
        raise HTTPException(status_code=400, detail="Choose at least one size")
    for p in body.photos:
        if p.kind not in PHOTO_KINDS:
            raise HTTPException(status_code=400, detail="Photo kind must be product or photo")
        try:
            store.asset_path(ws, p.asset_id)
        except StoreError:
            raise HTTPException(status_code=400, detail="A photo could not be found; upload it again")
    image_fn = None
    if body.mode == "advanced":
        image_fn, _ = _image_backend(body.api_key, body.oauth_token)  # raises 400 when Gemini isn't connected
    if not rs.renderer_ready():
        raise HTTPException(status_code=500, detail="The renderer isn't installed. Run: npm --prefix apps/reel-renderer install")

    kit = _brand(ws, body.use_brand_kit)
    d = {
        "id": secrets.token_hex(12), "created_at": _now(), "brief": body.brief.strip(), "goal": body.goal, "mode": body.mode,
        "language": body.language, "sizes": sizes, "photos": [p.model_dump() for p in body.photos],
        "brand": {"brand_name": kit.get("brand_name", ""), "colors": kit.get("colors") or [],
                  "logo_asset_id": (kit.get("logo") or {}).get("asset_id")},
        "brand_ctx": {k: kit.get(k) for k in ("brand_name", "colors", "tone", "tagline") if kit.get(k)},
        "status": "generating", "progress": "Starting", "error": "", "concepts": [], "plan_meta": {},
    }
    _save(ws, d)
    _spawn(_run_generate(ws, d["id"], image_fn))
    return _public(d)


@router.get("/{did}")
async def get_design(did: str, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    return _public(_load(ws, did))


class ConceptEdit(BaseModel):
    template: Optional[str] = None
    font_pair: Optional[str] = None
    palette: Optional[Dict[str, str]] = None
    bg_style: Optional[str] = None
    decoration: Optional[str] = None
    headline: Optional[str] = Field(None, max_length=90)
    subline: Optional[str] = Field(None, max_length=140)
    cta: Optional[str] = Field(None, max_length=24)
    price: Optional[str] = Field(None, max_length=14)
    old_price: Optional[str] = Field(None, max_length=14)
    badge: Optional[str] = Field(None, max_length=16)
    points: Optional[List[str]] = Field(None, max_length=4)
    features: Optional[List[Dict[str, str]]] = Field(None, max_length=3)
    quote: Optional[str] = Field(None, max_length=220)
    author: Optional[str] = Field(None, max_length=40)
    event_date: Optional[str] = Field(None, max_length=30)
    event_place: Optional[str] = Field(None, max_length=50)
    use_photo: Optional[bool] = None


def _check_editable(d: Dict[str, Any], i: int) -> None:
    if d["status"] in BUSY:
        raise HTTPException(status_code=409, detail="Wait for the current step to finish")
    if not 0 <= i < len(d.get("concepts") or []):
        raise HTTPException(status_code=404, detail="Concept not found")


@router.put("/{did}/concepts/{i}")
async def edit_concept(did: str, i: int, body: ConceptEdit, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    d = _load(ws, did)
    _check_editable(d, i)
    c = d["concepts"][i]
    merged = {**c, **{k: v for k, v in body.model_dump().items() if v is not None}}
    if body.palette:
        merged["palette"] = {**c["palette"], **body.palette}
    fixed = ds.normalise_concept(merged, d["brand"]["colors"], bool(d["photos"]), bool(c.get("plates")))
    fixed["plates"], fixed["renders"] = c.get("plates") or {}, c.get("renders") or {}
    d["concepts"][i] = fixed
    d.update(status="rendering", progress=f"Updating concept {i + 1}", error="")
    _save(ws, d)
    _spawn(_run_rerender(ws, did, i))
    return _public(d)


class ReviseBody(BaseModel):
    instruction: str = Field(..., min_length=2, max_length=500)


async def _run_revise(ws: str, did: str, i: int, instruction: str) -> None:
    d = _load(ws, did)
    try:
        c = d["concepts"][i]
        brief = {"text": d["brief"], "goal": d["goal"], "language": d["language"]}
        core = {k: v for k, v in c.items() if k not in ("renders", "plates")}
        new = await ds.revise_concept(brief, d["brand_ctx"], core, instruction, d["mode"])
        fixed = ds.normalise_concept(new, d["brand"]["colors"], bool(d["photos"]), bool(c.get("plates")))
        fixed["plates"], fixed["renders"] = c.get("plates") or {}, c.get("renders") or {}
        fixed["last_change"] = {"instruction": instruction, "notes": new.get("notes", "")}
        d["concepts"][i] = fixed
        _save(ws, d)
    except rs.DirectorError as e:
        d.update(status="ready", progress="", error=str(e))
        _save(ws, d)
        return
    await _run_rerender(ws, did, i)


@router.post("/{did}/concepts/{i}/revise")
async def revise(did: str, i: int, body: ReviseBody, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    d = _load(ws, did)
    _check_editable(d, i)
    d.update(status="rendering", progress=f"Claude is changing concept {i + 1}", error="")
    _save(ws, d)
    _spawn(_run_revise(ws, did, i, body.instruction.strip()))
    return _public(d)
