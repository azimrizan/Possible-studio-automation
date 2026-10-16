import asyncio
import io
import json
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

import instagram_server
import meta_ads_server
from campaign_strategist.rules import apply_rules
from campaign_strategist.schemas import AdCopy, StrategyOutput
from mcp_common import TenantContext, ToolCallRequest
from mcp_common.meta_graph import MockMetaGraph
from mcp_common.vault import VaultError, decrypt_secret, encrypt_secret

WS = "workspace-campaign-01"
CTX = TenantContext(tenant_id=WS, workspace_role="APPROVER")


def _jpeg(size=(1080, 1350)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 40, 40)).save(buf, "JPEG")
    return buf.getvalue()


def _strategy(**overrides) -> StrategyOutput:
    data = dict(
        name="Diwali Air Fryer", objective="OUTCOME_SALES", objective_reason="", daily_budget=50, budget_reason="",
        duration_days=3, start_date="2020-01-01", start_hour=9, schedule_reason="", countries=["IN"],
        city_names=["Pune", "Atlantis"], age_min=16, age_max=70, genders="female",
        interest_ids=["111", "999-made-up"], advantage_audience=True,
        ads=[AdCopy(creative_index=0, primary_text="x" * 400, headline="Big sale", cta="SHOP_NOW"),
             AdCopy(creative_index=5, primary_text="bad index", headline="h", cta="SHOP_NOW")],
        caption="cap",
    )
    data.update(overrides)
    return StrategyOutput(**data)


def _rules(s, **kw):
    args = dict(
        currency="INR", timezone="Asia/Kolkata", has_website=True, has_pixel=False, has_ig_post=True,
        creative_count=2, image_creatives=[0, 1], special_category="NONE",
        known_interests={"111": {"id": "111", "name": "Air fryer"}},
        known_cities={"pune": {"key": "2295", "name": "Pune", "region": "MH"}}, default_country="IN",
        now=datetime(2026, 10, 15, 12, tzinfo=timezone.utc),
    )
    args.update(kw)
    return apply_rules(s, **args)


# ---- vault -----------------------------------------------------------------------

def test_vault_round_trip_and_binding():
    secret = encrypt_secret("EAAB-token", associated_data=WS)
    assert "EAAB" not in secret
    assert decrypt_secret(secret, associated_data=WS) == "EAAB-token"
    with pytest.raises(VaultError):
        decrypt_secret(secret, associated_data="another-workspace")


# ---- rules -------------------------------------------------------------------------

def test_rules_guard_prerequisites_budget_schedule_and_hallucinations():
    out = _rules(_strategy())
    plan, warnings = out["plan"], " ".join(out["warnings"])
    assert plan["objective"] == "OUTCOME_TRAFFIC"  # Sales without a Pixel is downgraded
    assert plan["daily_budget"] == 100  # raised to the INR floor
    assert plan["audience"]["interests"] == [{"id": "111", "name": "Air fryer"}]  # made-up id dropped
    assert [c["name"] for c in plan["audience"]["cities"]] == ["Pune"]  # unresolved city dropped
    assert (plan["audience"]["age_min"], plan["audience"]["age_max"]) == (18, 65)
    assert datetime.fromisoformat(plan["start_time_iso"]) > datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
    assert len(plan["ads"]) == 1 and len(plan["ads"][0]["primary_text"]) == 300
    assert "Pixel" in warnings and "learning phase" in warnings and "not verified" in warnings


def test_rules_without_website_promote_instagram_post():
    plan = _rules(_strategy(objective="OUTCOME_TRAFFIC"), has_website=False)["plan"]
    assert plan["objective"] == "OUTCOME_ENGAGEMENT" and plan["delivery"] == "boost_instagram_post"
    assert len(plan["ads"]) == 1


def test_rules_special_category_strips_targeting_and_user_budget_wins():
    out = _rules(_strategy(), special_category="FINANCIAL_PRODUCTS_SERVICES", user_daily_budget=1200, user_duration_days=14)
    aud = out["plan"]["audience"]
    assert out["plan"]["special_ad_categories"] == ["FINANCIAL_PRODUCTS_SERVICES"]
    assert aud["interests"] == [] and aud["genders"] == "all" and (aud["age_min"], aud["age_max"]) == (18, 65)
    assert out["plan"]["daily_budget"] == 1200 and out["plan"]["duration_days"] == 14


def test_rules_cap_budget(monkeypatch):
    monkeypatch.setenv("META_MAX_DAILY_BUDGET", "2000")
    assert _rules(_strategy(), user_daily_budget=999999)["plan"]["daily_budget"] == 2000


# ---- mcp-instagram -------------------------------------------------------------------

@pytest.fixture
def mock_graph(monkeypatch):
    graph = MockMetaGraph()

    async def provider(ctx):
        return graph

    monkeypatch.setattr(instagram_server, "graph_provider", provider)
    monkeypatch.setattr(meta_ads_server, "graph_provider", provider)
    instagram_server._published.clear()
    return graph


@pytest.mark.asyncio
async def test_instagram_publish_requires_approval(mock_graph):
    req = ToolCallRequest(tool="instagram.publish", arguments={"ig_user_id": "1", "items": [{"url": "u", "kind": "image"}]},
                          tenant_context=CTX)
    from mcp_common import ApprovalRequiredError
    with pytest.raises(ApprovalRequiredError):
        await instagram_server.server.execute_tool(req)


@pytest.mark.asyncio
async def test_instagram_carousel_and_reel(mock_graph):
    res = await instagram_server.publish(mock_graph, "1784", [{"url": "a", "kind": "image"}, {"url": "b", "kind": "video"}], "hi")
    posts = [c for c in mock_graph.calls if c[0] == "POST" and c[1].endswith("/media")]
    assert [p[2].get("is_carousel_item") for p in posts[:2]] == ["true", "true"]
    assert posts[1][2]["media_type"] == "VIDEO" and posts[2][2]["media_type"] == "CAROUSEL"
    assert res["permalink"].startswith("https://www.instagram.com/p/")

    mock_graph.calls.clear()
    await instagram_server.publish(mock_graph, "1784", [{"url": "v", "kind": "video"}], "reel")
    assert mock_graph.calls[0][2]["media_type"] == "REELS"


# ---- mcp-meta-ads ------------------------------------------------------------------------

def _approved(server, tool, args):
    from apps.api.app.core.security import APPROVAL_PUBLIC_KEY_HEX, mint_approval_token
    server.set_approval_public_key(APPROVAL_PUBLIC_KEY_HEX)
    token = mint_approval_token(tenant_id=WS, tool_name=tool, payload=args)
    return ToolCallRequest(tool=tool, arguments=args, tenant_context=CTX, approval_token=json.dumps(token))


@pytest.mark.asyncio
async def test_meta_ads_builds_everything_paused_and_caps_budget(mock_graph, monkeypatch):
    async def assets(ctx, asset_id):
        return _jpeg()

    monkeypatch.setattr(meta_ads_server, "asset_provider", assets)
    plan = _rules(_strategy())["plan"]
    args = {
        "plan": plan, "ad_account_id": "act_1", "currency": "INR", "page_id": "p", "ig_user_id": "ig",
        "website_url": "https://x.in", "pixel_id": "", "start_time_iso": plan["start_time_iso"],
        "ads": [{**plan["ads"][0], "image_asset_id": "a.jpg"}],
    }
    res = await meta_ads_server.server.execute_tool(_approved(meta_ads_server.server, "ads.create_campaign", args))
    assert res.success, res.error
    statuses = [c[2].get("status") for c in mock_graph.calls if c[0] == "POST" and c[2] and "status" in c[2]]
    assert statuses and set(statuses) == {"PAUSED"}
    campaign_call = next(c for c in mock_graph.calls if c[1].endswith("/campaigns"))
    assert campaign_call[2]["daily_budget"] == 10000  # 100 INR in paise
    adset_call = next(c for c in mock_graph.calls if c[1].endswith("/adsets"))
    targeting = json.loads(adset_call[2]["targeting"])
    assert targeting["targeting_automation"]["advantage_audience"] == 1 and targeting["age_max"] == 65

    monkeypatch.setenv("META_MAX_DAILY_BUDGET", "50")
    res = await meta_ads_server.server.execute_tool(_approved(meta_ads_server.server, "ads.create_campaign", args))
    assert not res.success and "outside the allowed range" in res.error


@pytest.mark.asyncio
async def test_meta_ads_activate_needs_its_own_token(mock_graph):
    args = {"campaign_id": "c", "adset_id": "s", "ad_ids": ["a"]}
    wrong = _approved(meta_ads_server.server, "ads.create_campaign", args)
    wrong.tool = "ads.activate"
    from mcp_common import InvalidApprovalTokenError
    with pytest.raises(InvalidApprovalTokenError):
        await meta_ads_server.server.execute_tool(wrong)
    res = await meta_ads_server.server.execute_tool(_approved(meta_ads_server.server, "ads.activate", args))
    assert res.success and mock_graph.statuses["c"] == "ACTIVE"


# ---- API flow (mock Meta, fake strategist) -------------------------------------------------

class FakeStrategist:
    async def run(self, *, creatives, business, account, meta_search, estimate=None, instruction="", known_insights=None, today=None):
        interests = await meta_search("air fryer", "interest", "IN")
        out = _rules(_strategy(interest_ids=[interests[0]["id"]]),
                     known_interests={interests[0]["id"]: {"id": interests[0]["id"], "name": interests[0]["name"]}},
                     has_website=bool(business.get("website_url")), creative_count=len(creatives),
                     image_creatives=[i for i, c in enumerate(creatives) if c["kind"] == "image"],
                     user_daily_budget=business.get("daily_budget"), now=datetime.now(timezone.utc))
        return {**out, "rationale": {}, "kpis": [], "risks": [], "research": {}, "caption": "Caption #tag",
                "estimate": await estimate(out["plan"]["audience"], out["plan"]["objective"]),
                "insights": [{} for _ in creatives], "usage": {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}}


@pytest.mark.asyncio
async def test_campaign_api_end_to_end_in_mock_mode(client, tmp_path, monkeypatch):
    from apps.api.app.api import meta_connect, studio_campaigns
    from poster_studio import StudioStore

    st = StudioStore(root=tmp_path)
    monkeypatch.setattr(meta_connect, "store", st)
    monkeypatch.setattr(studio_campaigns, "store", st)
    monkeypatch.setattr(studio_campaigns, "strategist", FakeStrategist())
    monkeypatch.setenv("MOCK_META_GRAPH", "true")
    monkeypatch.setattr(instagram_server, "graph_provider", studio_campaigns._graph_provider)
    monkeypatch.setattr(meta_ads_server, "graph_provider", studio_campaigns._graph_provider)
    monkeypatch.setattr(meta_ads_server, "asset_provider", studio_campaigns._asset_provider)
    instagram_server._published.clear()
    h = {"X-Studio-Workspace": WS}

    start = await client.get(f"/api/studio/connections/meta/start?workspace={WS}")
    assert start.status_code == 307
    cb = start.headers["location"].split("/api/studio", 1)[1]
    assert "meta_connected=1" in (await client.get("/api/studio" + cb)).headers["location"]
    conn = (await client.get("/api/studio/connections", headers=h)).json()["meta"]
    assert conn["connected"] and conn["mock"] and conn["selection"]["ig_username"] == "demo_brand_mock"
    assert "token" not in json.dumps(conn).lower().replace("needs_reauth", "")

    up = (await client.post("/api/studio/uploads/creative", headers=h, files={"file": ("ad.jpg", _jpeg(), "image/jpeg")})).json()
    vid = (await client.post("/api/studio/uploads/creative", headers=h,
                             files={"file": ("v.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64, "video/mp4")})).json()
    assert up["kind"] == "image" and vid["kind"] == "video"

    c = (await client.post("/api/studio/campaigns", headers=h, json={
        "creatives": [{"asset_id": up["asset_id"]}, {"asset_id": vid["asset_id"]}],
        "business": {"goal": "sales", "website_url": "https://crispo.in", "daily_budget": 800},
    })).json()
    assert (await client.post(f"/api/studio/campaigns/{c['id']}/approve", headers=h, json={})).status_code == 409

    planned = (await client.post(f"/api/studio/campaigns/{c['id']}/strategy", headers=h, json={})).json()
    assert planned["status"] == "planned" and planned["strategy"]["plan"]["daily_budget"] == 800

    await client.post(f"/api/studio/campaigns/{c['id']}/approve", headers=h, json={})
    for _ in range(50):
        state = (await client.get(f"/api/studio/campaigns/{c['id']}", headers=h)).json()
        if state["status"] in ("ads_ready", "failed"):
            break
        await asyncio.sleep(0.05)
    assert state["status"] == "ads_ready", state.get("error")
    assert state["instagram"]["permalink"] and state["meta"]["status"] == "PAUSED"

    live = (await client.post(f"/api/studio/campaigns/{c['id']}/launch", headers=h)).json()
    assert live["status"] == "live" and len(live["approval"]["tokens_used"]) == 3
