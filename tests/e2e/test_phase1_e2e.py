import pytest
from mcp_common import TenantContext, ToolCallRequest
from gateway.router import MCPGatewayRouter
from knowledge_server import server as knowledge_server, mock_adapter as knowledge_mock

@pytest.mark.asyncio
async def test_phase1_full_acceptance_flow(client):
    """
    Phase 1 Acceptance Criteria:
    - Brand kit saved, versioned, retrievable as tokens JSON via MCP.
    - The prompt bar persists draft campaigns with product & advanced options.
    - mcp-knowledge tool search_kb returns relevant brand & product context.
    """
    # 1. User signs up & creates workspace
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "alex@studio.ai", "full_name": "Alex", "password": "securepass123"},
    )
    assert signup.status_code == 201
    token = signup.json()["access_token"]
    user_id = signup.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = await client.post(
        "/api/v1/workspaces/",
        json={"name": "Alex Brand Studio", "slug": "alex-studio"},
        headers=headers,
    )
    assert ws.status_code == 201
    tenant_id = ws.json()["id"]
    headers["X-Tenant-ID"] = tenant_id

    # 2. Save Custom Brand Kit
    brand_payload = {
        "brand_name": "Apex Wearables",
        "logo_url": "https://apex.ai/logo.png",
        "palette_tokens": {
            "primary": "#4f46e5",
            "secondary": "#06b6d4",
            "accent": "#f43f5e",
            "surface": "#0f172a",
            "background": "#080c14",
            "text_primary": "#ffffff",
            "text_secondary": "#94a3b8",
        },
        "typography_tokens": {
            "headline_font": "Inter, sans-serif",
            "body_font": "Inter, sans-serif",
            "headline_weights": ["700", "800"],
            "body_weights": ["400", "500"],
        },
        "tone_of_voice": {
            "keywords": ["High-Performance", "Elite", "Futuristic"],
            "do_rules": ["Highlight battery endurance and biometric accuracy"],
            "dont_rules": ["Never promise medical diagnostics"],
            "sample_posts": ["Smarter Every Move. Experience the all-new Apex Watch."],
        },
        "product_catalog": [
            {
                "name": "Apex AI Smartwatch",
                "description": "Next-gen fitness & health smartwatch with 7-day battery",
                "price": 10000,
                "currency": "INR",
                "key_features": ["7-day battery", "AMOLED 120Hz", "AI Coach"],
                "target_audience": "Tech enthusiasts aged 22-35",
            }
        ],
    }

    put_res = await client.put("/api/v1/brand-kit/", json=brand_payload, headers=headers)
    assert put_res.status_code == 200
    brand_data = put_res.json()
    assert brand_data["brand_name"] == "Apex Wearables"
    assert brand_data["version"] >= 1

    # 3. Synchronize design tokens with mcp-knowledge server mock adapter
    knowledge_mock.set_tenant_tokens(
        tenant_id=tenant_id,
        tokens={
            "brand_name": brand_data["brand_name"],
            "logo_url": brand_data["logo_url"],
            "color_palette": brand_data["palette_tokens"],
            "typography": brand_data["typography_tokens"],
            "tone_of_voice": brand_data["tone_of_voice"],
            "product_catalog": brand_data["product_catalog"],
        },
    )

    # 4. Wire MCP Gateway with mcp-knowledge
    gateway_router = MCPGatewayRouter()
    gateway_router.register_in_process_server("mcp-knowledge", knowledge_server)

    tenant_ctx = TenantContext(
        tenant_id=tenant_id,
        workspace_role="OWNER",
        user_id=user_id,
    )

    # 5. Retrieve Brand Tokens JSON via MCP
    token_req = ToolCallRequest(
        tool="get_brand_tokens",
        arguments={},
        tenant_context=tenant_ctx,
    )
    token_res = await gateway_router.dispatch(token_req)
    assert token_res.success is True
    retrieved_tokens = token_res.data["design_tokens"]
    assert retrieved_tokens["brand_name"] == "Apex Wearables"
    assert retrieved_tokens["color_palette"]["primary"] == "#4f46e5"

    # 6. Retrieve Knowledge Search via MCP (RAG)
    search_req = ToolCallRequest(
        tool="search_kb",
        arguments={"query": "smartwatch battery life", "top_k": 2},
        tenant_context=tenant_ctx,
    )
    search_res = await gateway_router.dispatch(search_req)
    assert search_res.success is True
    assert len(search_res.data["matches"]) >= 1

    # 7. Persist Draft Campaign from Prompt Bar
    prompt_text = "Promote our new AI smartwatch on Instagram. Create a poster and a reel, publish it and run a ₹10,000 ad campaign for 7 days targeting the right audience to drive sales."
    camp_payload = {
        "title": "AI Smartwatch Launch",
        "raw_prompt": prompt_text,
        "product_details": {"product_name": "Apex AI Smartwatch", "price_inr": 10000},
        "advanced_options": {"budget_inr": 10000, "duration_days": 7, "channels": ["INSTAGRAM"]},
        "attached_files": [{"filename": "product_banner.png", "size_kb": 512}],
    }

    camp_res = await client.post("/api/v1/campaigns/", json=camp_payload, headers=headers)
    assert camp_res.status_code == 201
    camp = camp_res.json()
    assert camp["status"] == "DRAFT"
    assert camp["title"] == "AI Smartwatch Launch"
    assert camp["raw_prompt"] == prompt_text
    assert camp["advanced_options"]["budget_inr"] == 10000
    assert len(camp["attached_files"]) == 1
