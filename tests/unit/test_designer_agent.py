import pytest
from mcp_common import TenantContext
from model_gateway import ModelGateway
from gateway.router import MCPGatewayRouter
from designer_agent import GraphicDesignerAgent
from gemini_server import server as gemini_mcp_server
from media_server import server as media_mcp_server

@pytest.mark.asyncio
async def test_graphic_designer_agent_generates_3_variants():
    router = MCPGatewayRouter()
    router.register_in_process_server("mcp-gemini", gemini_mcp_server)
    router.register_in_process_server("mcp-media", media_mcp_server)

    model_gateway = ModelGateway(mock_mode=True)
    agent = GraphicDesignerAgent(model_gateway=model_gateway, mcp_gateway_client=router)

    brief = {
        "objective": "CONVERSIONS",
        "product_focus": "Aura Titanium Pro Smartwatch",
        "target_audience": {"age_range": "24-40", "interests": ["Fitness", "Tech"]},
        "tone": "Bold and Modern",
        "deliverables": "POSTER",
        "call_to_action": "Order Now · Free Shipping",
    }
    brand_kit = {
        "brand_name": "AURA SMART",
        "palette_tokens": {"primary": "#6366f1"},
    }
    tenant_ctx = TenantContext(tenant_id="test-tenant-designer", workspace_role="EDITOR")

    variants = await agent.generate_variants(
        brief=brief,
        brand_kit=brand_kit,
        tenant_context=tenant_ctx,
    )

    assert len(variants) == 3
    
    # Check variant 1 (Dark Titanium)
    v1 = variants[0]
    assert v1["variant_index"] == 1
    assert v1["layout_spec"]["theme"] == "dark_titanium"
    assert "AURA SMART" in v1["layout_spec"]["brand_name"]
    assert v1["preview_url"].startswith("data:image/svg+xml;utf8,")
    assert "Order Now · Free Shipping" in v1["layout_spec"]["cta_text"]
    assert len(v1["copy_captions"]["hashtags"]) >= 4

    # Check variant 2 (Lifestyle Action)
    v2 = variants[1]
    assert v2["variant_index"] == 2
    assert v2["layout_spec"]["theme"] == "lifestyle_action"
    assert v2["layout_spec"]["accent_color"] == "#f59e0b"

    # Check variant 3 (Minimalist Luxury)
    v3 = variants[2]
    assert v3["variant_index"] == 3
    assert v3["layout_spec"]["theme"] == "minimalist_luxury"
    assert v3["compliance_status"] == "PASSED"
