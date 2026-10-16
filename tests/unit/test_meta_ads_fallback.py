import json
import pytest
from mcp_common import TenantContext
from mcp_common.meta_graph import MetaGraphError, MockMetaGraph
import meta_ads_server


class DevModeGraph(MockMetaGraph):
    """Refuses to promote an Instagram post, like Meta does for apps in Development mode."""

    async def request(self, method, path, params=None, files=None):
        if method == "POST" and path.endswith("/adcreatives") and (params or {}).get("source_instagram_media_id"):
            self.calls.append((method, path, dict(params)))
            raise MetaGraphError("Meta API error 100: Ads creative post was created by an app that is in development mode.", 100)
        return await super().request(method, path, params, files)


class FailingAdsGraph(MockMetaGraph):
    async def request(self, method, path, params=None, files=None):
        if method == "POST" and path.endswith("/ads"):
            raise MetaGraphError("Meta API error 100: boom", 100)
        return await super().request(method, path, params, files)


def _args():
    plan = {"name": "Kettle launch", "objective": "OUTCOME_ENGAGEMENT", "daily_budget": 200, "duration_days": 7,
            "audience": {"countries": ["IN"], "age_min": 25, "age_max": 45, "interests": []}}
    return {"plan": plan, "ad_account_id": "act_1", "currency": "INR", "page_id": "p1", "ig_user_id": "ig1",
            "website_url": "", "pixel_id": "", "start_time_iso": "2030-01-01T10:00:00+05:30",
            "ads": [{"primary_text": "Hot tea in 3 minutes", "headline": "Kettle", "description": "", "cta": "LEARN_MORE",
                     "boost_media_id": "media_1", "image_asset_id": "img.jpg"}]}


@pytest.fixture
def wire(monkeypatch):
    async def assets(ctx, asset_id):
        return b"\xff\xd8fakejpeg"
    monkeypatch.setattr(meta_ads_server, "asset_provider", assets)

    def use(graph):
        async def provider(ctx):
            return graph
        monkeypatch.setattr(meta_ads_server, "graph_provider", provider)
        return graph
    return use


@pytest.mark.asyncio
async def test_falls_back_to_image_creative_when_boost_is_refused(wire):
    graph = wire(DevModeGraph())
    res = await meta_ads_server.handle_create_campaign(_args(), TenantContext(tenant_id="ws-test-0001"))
    assert res["used_image_fallback"] is True and len(res["ad_ids"]) == 1
    image_creative = [p for m, path, p in graph.calls if path.endswith("/adcreatives") and "object_story_spec" in p][0]
    story = json.loads(image_creative["object_story_spec"])
    assert story["photo_data"]["caption"] == "Hot tea in 3 minutes" and "link_data" not in story


@pytest.mark.asyncio
async def test_partial_campaign_is_deleted_on_failure(wire):
    graph = wire(FailingAdsGraph())
    with pytest.raises(MetaGraphError):
        await meta_ads_server.handle_create_campaign(_args(), TenantContext(tenant_id="ws-test-0001"))
    deletes = [path for m, path, p in graph.calls if m == "DELETE"]
    assert len(deletes) == 1 and deletes[0].startswith("campaign_")


@pytest.mark.asyncio
async def test_write_override_keeps_reads_on_real_graph(monkeypatch):
    real, demo = MockMetaGraph(), MockMetaGraph()

    async def real_provider(ctx):
        return real

    async def demo_provider(ctx):
        return demo

    async def assets(ctx, asset_id):
        return b"jpeg"
    monkeypatch.setattr(meta_ads_server, "graph_provider", real_provider)
    monkeypatch.setattr(meta_ads_server, "write_graph_provider", demo_provider)
    monkeypatch.setattr(meta_ads_server, "asset_provider", assets)
    ctx = TenantContext(tenant_id="ws-test-0001")
    await meta_ads_server.handle_targeting_search({"q": "cooking"}, ctx)
    await meta_ads_server.handle_create_campaign(_args(), ctx)
    assert any(path == "search" for _, path, _ in real.calls)
    assert not any(path.endswith("/campaigns") for _, path, _ in real.calls)
    assert any(path.endswith("/campaigns") for _, path, _ in demo.calls)


@pytest.mark.asyncio
async def test_engagement_adset_targets_the_post_not_a_website(wire):
    graph = wire(MockMetaGraph())
    await meta_ads_server.handle_create_campaign(_args(), TenantContext(tenant_id="ws-test-0001"))
    adset = [p for m, path, p in graph.calls if m == "POST" and path.endswith("/adsets")][0]
    assert adset["destination_type"] == "ON_POST" and adset["optimization_goal"] == "POST_ENGAGEMENT"
