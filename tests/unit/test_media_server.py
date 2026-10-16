import pytest
from mcp_common import TenantContext
from media_server import server, mock_adapter

@pytest.mark.asyncio
async def test_media_adapter_render_poster_svg():
    spec = {
        "headline": "TITANIUM APEX WATCH",
        "subheadline": "Crafted for extreme performance",
        "cta_text": "Buy Now · 20% Off",
        "brand_name": "AURA",
        "badge_text": "LIMITED EDITION",
        "theme": "dark_titanium",
        "aspect_ratio": "4:5",
    }
    svg = mock_adapter.generate_composite_svg(spec)
    assert "<svg" in svg
    assert "TITANIUM APEX WATCH" in svg
    assert "Crafted for extreme performance" in svg
    assert "Buy Now · 20% Off" in svg
    assert "AURA" in svg
    assert "LIMITED EDITION" in svg
    assert 'viewBox="0 0 1080 1350"' in svg

@pytest.mark.asyncio
async def test_media_adapter_aspect_ratios():
    res_square = await mock_adapter.render_poster({
        "headline": "Square Post",
        "aspect_ratio": "1:1"
    })
    assert res_square["status"] == "COMPLETED"
    assert res_square["width"] == 1080
    assert res_square["height"] == 1080
    assert res_square["preview_url"].startswith("data:image/svg+xml;utf8,")

    res_story = await mock_adapter.render_poster({
        "headline": "Story Reel Cover",
        "aspect_ratio": "9:16"
    })
    assert res_story["width"] == 1080
    assert res_story["height"] == 1920

from mcp_common import TenantContext, ToolCallRequest

@pytest.mark.asyncio
async def test_mcp_media_tool_execution():
    ctx = TenantContext(tenant_id="tenant-media-123", workspace_role="EDITOR")
    res = await server.execute_tool(
        ToolCallRequest(
            tool="render_poster",
            arguments={
                "layout_spec": {
                    "headline": "NEXT GEN RUNNING SHOES",
                    "brand_name": "VELOCITY",
                    "theme": "lifestyle_action",
                }
            },
            tenant_context=ctx,
        )
    )
    assert res.success is True
    assert res.data["status"] == "COMPLETED"
    assert res.data["tenant_id"] == "tenant-media-123"
    assert "preview_url" in res.data

    status_res = await server.execute_tool(
        ToolCallRequest(
            tool="get_render_status",
            arguments={"job_id": "job-abc"},
            tenant_context=ctx,
        )
    )
    assert status_res.success is True
    assert status_res.data["status"] == "COMPLETED"

