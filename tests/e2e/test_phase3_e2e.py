import pytest

@pytest.mark.asyncio
async def test_phase3_creative_generation_e2e(client):
    """
    Phase 3 Acceptance Criteria:
    - Posters never contain model-rendered text errors (text is composited via SVG/media engine).
    - Logo/colors match the design system.
    - 3 distinct variants gallery generated (Dark Titanium, Lifestyle Action, Minimalist Luxury).
    - Captions and hashtags generated per variant.
    """
    # 1. Setup User and Tenant Workspace
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "creative@brand.com", "full_name": "Art Director", "password": "password1234"},
    )
    token = signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = await client.post(
        "/api/v1/workspaces/",
        json={"name": "Aura Luxury", "slug": "aura-luxury"},
        headers=headers,
    )
    tenant_id = ws.json()["id"]
    headers["X-Tenant-ID"] = tenant_id

    # 2. Configure Brand Kit
    await client.put(
        "/api/v1/brand-kit/",
        json={
            "brand_name": "AURA LUXE",
            "palette_tokens": {"primary": "#6366f1", "secondary": "#4338ca"},
            "typography_tokens": {"headline_font": "Plus Jakarta Sans"},
            "tone_of_voice": {"style": "Ultra Luxurious and Modern"},
        },
        headers=headers,
    )

    # 3. Create a campaign
    camp_payload = {
        "title": "Quantum Pro Luxury Watch Campaign",
        "raw_prompt": "Launch high-impact Instagram poster for Quantum Pro luxury watch with 20% discount CTA",
        "product_details": {
            "name": "Quantum Pro",
            "category": "Luxury Smartwatch",
            "price": "$499",
            "usp": "Titanium case and sapphire glass with 14-day battery life",
        },
        "advanced_options": {
            "tone": "Ultra Luxurious",
            "target_country": "US",
            "platform": "Instagram",
        },
    }
    c_resp = await client.post("/api/v1/campaigns/", json=camp_payload, headers=headers)
    assert c_resp.status_code == 201
    campaign = c_resp.json()
    campaign_id = campaign["id"]

    # 4. Enhance brief
    b_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/brief/enhance", headers=headers)
    assert b_resp.status_code == 200
    brief = b_resp.json()
    assert brief["is_approved"] is False

    # 5. Approve brief
    appr_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/brief/approve", headers=headers)
    assert appr_resp.status_code == 200
    assert appr_resp.json()["is_approved"] is True

    # 6. Generate Creative Assets (Phase 3)
    gen_resp = await client.post(
        f"/api/v1/campaigns/{campaign_id}/assets/generate",
        json={"aspect_ratio": "4:5", "regenerate": False},
        headers=headers,
    )
    assert gen_resp.status_code == 200
    assets = gen_resp.json()
    assert len(assets) == 3

    # Check variants
    v1 = next(a for a in assets if a["variant_index"] == 1)
    v2 = next(a for a in assets if a["variant_index"] == 2)
    v3 = next(a for a in assets if a["variant_index"] == 3)

    assert v1["asset_type"] == "POSTER"
    assert v1["aspect_ratio"] == "4:5"
    assert v1["preview_url"].startswith("data:image/svg+xml;utf8,")
    assert v1["layout_spec"]["theme"] == "dark_titanium"
    assert v1["layout_spec"]["brand_name"] == "AURA LUXE"
    assert v1["compliance_status"] == "PASSED"
    assert "hashtags" in v1["copy_captions"]

    assert v2["layout_spec"]["theme"] == "lifestyle_action"
    assert v3["layout_spec"]["theme"] == "minimalist_luxury"

    # 7. Fetch Assets via GET endpoint
    list_resp = await client.get(f"/api/v1/campaigns/{campaign_id}/assets", headers=headers)
    assert list_resp.status_code == 200
    fetched_assets = list_resp.json()
    assert len(fetched_assets) == 3
    assert fetched_assets[0]["id"] == v1["id"]

    # 8. Verify Campaign Status is updated to CREATIVE
    camp_check = await client.get(f"/api/v1/campaigns/{campaign_id}", headers=headers)
    assert camp_check.status_code == 200
    assert camp_check.json()["status"] == "CREATIVE"
    assert camp_check.json()["current_step"] == "CREATIVE"
