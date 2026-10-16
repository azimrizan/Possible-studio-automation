import pytest
from mcp_common import TenantContext
from model_gateway import ModelGateway
from gateway.router import MCPGatewayRouter
from video_agent import VideoAgent
from gemini_server import server as gemini_mcp_server
from media_server import server as media_mcp_server

@pytest.mark.asyncio
async def test_video_agent_storyboard_generation():
    agent = VideoAgent(model_gateway=ModelGateway(mock_mode=True))
    brief = {
        "product_focus": "Titanium Pro Watch",
        "call_to_action": "Order Now · 20% Off",
        "tone": "Bold and Modern",
    }
    storyboard = await agent.generate_reel_storyboard(brief, brand_name="PULSE")
    assert len(storyboard) == 4
    
    # Scene 1: Hook (0-3s)
    s1 = storyboard[0]
    assert s1["scene_id"] == 1
    assert s1["duration"] == 3.0
    assert "Titanium Pro Watch" in s1["visual_prompt"]
    assert "WHAT IF" in s1["caption_overlay"]

    # Scene 4: Outro CTA
    s4 = storyboard[3]
    assert s4["scene_id"] == 4
    assert "ORDER NOW" in s4["caption_overlay"]

@pytest.mark.asyncio
async def test_video_agent_generate_reel_end_to_end():
    router = MCPGatewayRouter()
    router.register_in_process_server("mcp-gemini", gemini_mcp_server)
    router.register_in_process_server("mcp-media", media_mcp_server)

    agent = VideoAgent(
        model_gateway=ModelGateway(mock_mode=True),
        mcp_gateway_client=router,
    )

    brief = {
        "product_focus": "Apex Fitness Tracker",
        "call_to_action": "Claim 30-Day Free Trial",
        "tone": "Ultra High Energy",
    }
    brand_kit = {
        "brand_name": "APEX",
        "palette_tokens": {"primary": "#6366f1"},
    }
    tenant_ctx = TenantContext(tenant_id="tenant-video-1", workspace_role="EDITOR")

    reel = await agent.generate_reel(
        brief=brief,
        brand_kit=brand_kit,
        tenant_context=tenant_ctx,
        audio_track="cyberpunk_anthem",
        caption_style="kinetic_highlight",
    )

    assert reel["asset_type"] == "REEL"
    assert reel["aspect_ratio"] == "9:16"
    assert reel["duration_seconds"] == 15.0
    assert reel["status"] == "COMPLETED"
    assert reel["progress_percent"] == 100
    assert reel["output_url"].endswith(".mp4")
    assert len(reel["storyboard"]) == 4
    assert len(reel["copy_captions"]["hashtags"]) >= 4

    # Test job resumption / status polling across worker reconnects
    job_id = reel["job_id"]
    status_data = await agent.get_job_status(job_id, tenant_ctx)
    assert status_data["job_id"] == job_id
    assert status_data["status"] == "COMPLETED"
    assert status_data["progress_percent"] == 100
