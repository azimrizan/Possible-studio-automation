import pytest

@pytest.mark.asyncio
async def test_phase2_full_acceptance_flow(client):
    """
    Phase 2 Acceptance Criteria:
    - Same raw prompt yields schema-valid briefs.
    - User edits are respected and persist across updates.
    - Brief approval moves campaign to PLANNING status.
    """
    # 1. Signup & Workspace
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "growth@brand.com", "full_name": "Growth Lead", "password": "password1234"},
    )
    token = signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = await client.post(
        "/api/v1/workspaces/",
        json={"name": "Pulse Tech", "slug": "pulse-tech"},
        headers=headers,
    )
    tenant_id = ws.json()["id"]
    headers["X-Tenant-ID"] = tenant_id

    # 2. Start Campaign from Prompt Bar
    raw_prompt = "Promote our new AI smartwatch on Instagram. Create a poster and a reel, publish it and run a ₹10,000 ad campaign for 7 days targeting the right audience to drive sales."
    camp_resp = await client.post(
        "/api/v1/campaigns/",
        json={
            "title": "Smartwatch Launch",
            "raw_prompt": raw_prompt,
            "product_details": {"product_name": "Pulse AI Watch", "price": "₹10,000"},
            "advanced_options": {"budget_inr": 10000, "duration_days": 7},
        },
        headers=headers,
    )
    assert camp_resp.status_code == 201
    campaign_id = camp_resp.json()["id"]

    # 3. Enhance Button Triggered -> Enhancer Agent Generates Creative Brief
    enhance_resp = await client.post(
        f"/api/v1/campaigns/{campaign_id}/brief/enhance",
        headers=headers,
    )
    assert enhance_resp.status_code == 200
    brief_data = enhance_resp.json()
    assert brief_data["campaign_id"] == campaign_id
    assert brief_data["objective"] == "Drive sales"
    assert brief_data["deliverables"] == "BOTH"
    assert brief_data["call_to_action"] == "Shop Now"
    assert brief_data["version"] == 1
    assert brief_data["is_approved"] is False

    # 4. User Edits the Brief (e.g. Change Deliverables to POSTER only, update CTA)
    edit_payload = {
        "deliverables": "POSTER",
        "call_to_action": "Claim Exclusive Pre-Order",
        "tone": "Ultra-sleek, minimalist luxury",
        "constraints": ["Highlight titanium bezel", "Do not mention competitor brands"],
    }
    update_resp = await client.put(
        f"/api/v1/campaigns/{campaign_id}/brief/",
        json=edit_payload,
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated_brief = update_resp.json()
    # Verify user edits were respected!
    assert updated_brief["deliverables"] == "POSTER"
    assert updated_brief["call_to_action"] == "Claim Exclusive Pre-Order"
    assert updated_brief["tone"] == "Ultra-sleek, minimalist luxury"
    assert updated_brief["version"] == 2

    # 5. User Approves Brief
    approve_resp = await client.post(
        f"/api/v1/campaigns/{campaign_id}/brief/approve",
        headers=headers,
    )
    assert approve_resp.status_code == 200
    approved_brief = approve_resp.json()
    assert approved_brief["is_approved"] is True

    # 6. Verify Campaign Status Updated to PLANNING for Phase 3
    camp_check = await client.get(f"/api/v1/campaigns/{campaign_id}", headers=headers)
    assert camp_check.status_code == 200
    assert camp_check.json()["status"] == "PLANNING"
    assert camp_check.json()["current_step"] == "CREATIVE_GENERATION"
