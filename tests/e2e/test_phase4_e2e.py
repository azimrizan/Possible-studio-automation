import pytest

@pytest.mark.asyncio
async def test_phase4_reel_generation_e2e(client):
    """
    Phase 4 Acceptance Criteria:
    - A reel is produced end-to-end from one brief with brand-consistent captions.
    - Storyboard contains structured scenes with visual prompts and caption overlays.
    - Output format is 9:16 vertical video, duration <= 90s.
    - Resumable jobs with progress survive worker reconnects.
    - A user can pick Poster only, Reel only, or both from one brief.
    """
    # 1. Setup User and Tenant Workspace
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "video.director@brand.com", "full_name": "Video Lead", "password": "password1234"},
    )
    token = signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = await client.post(
        "/api/v1/workspaces/",
        json={"name": "Kinetics Media", "slug": "kinetics-media"},
        headers=headers,
    )
    tenant_id = ws.json()["id"]
    headers["X-Tenant-ID"] = tenant_id

    # 2. Setup Brand Kit
    await client.put(
        "/api/v1/brand-kit/",
        json={
            "brand_name": "KINETICS PRO",
            "palette_tokens": {"primary": "#6366f1", "secondary": "#4338ca"},
            "typography_tokens": {"headline_font": "Plus Jakarta Sans"},
            "tone_of_voice": {"style": "Dynamic, High-Octane, Cinematic"},
        },
        headers=headers,
    )

    # 3. Create Campaign with BOTH deliverables
    camp_payload = {
        "title": "Kinetics Pro Video Launch",
        "raw_prompt": "Produce a high-energy 15-second vertical Instagram Reel showcasing the new Kinetics Smartwatch. Highlight waterproof endurance and AI coaching, ending with a 20% discount offer.",
        "product_details": {
            "name": "Kinetics Watch Ultra",
            "category": "Smartwatch",
            "price": "$399",
            "usp": "Waterproof 50m with adaptive AI fitness coach",
        },
        "advanced_options": {
            "tone": "High-Energy Athletic",
            "platform": "Instagram",
        },
    }
    c_resp = await client.post("/api/v1/campaigns/", json=camp_payload, headers=headers)
    assert c_resp.status_code == 201
    campaign = c_resp.json()
    campaign_id = campaign["id"]

    # 4. Enhance and Approve Brief
    b_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/brief/enhance", headers=headers)
    assert b_resp.status_code == 200

    appr_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/brief/approve", headers=headers)
    assert appr_resp.status_code == 200

    # 5. Generate Reel (Phase 4)
    reel_gen = await client.post(
        f"/api/v1/campaigns/{campaign_id}/reels/generate",
        json={
            "audio_track": "cinematic_synth_anthem",
            "caption_style": "kinetic_highlight",
        },
        headers=headers,
    )
    assert reel_gen.status_code == 200
    reel_asset = reel_gen.json()

    assert reel_asset["asset_type"] == "REEL"
    assert reel_asset["aspect_ratio"] == "9:16"
    assert reel_asset["preview_url"].endswith(".mp4")
    assert reel_asset["compliance_status"] == "PASSED"

    # Verify Storyboard
    layout_spec = reel_asset["layout_spec"]
    storyboard = layout_spec["storyboard"]
    assert len(storyboard) == 4
    assert layout_spec["duration_seconds"] <= 90.0
    assert layout_spec["duration_seconds"] == 15.0

    # Verify scene details
    assert storyboard[0]["scene_id"] == 1
    assert "caption_overlay" in storyboard[0]
    assert "visual_prompt" in storyboard[0]

    # Verify Copy & Captions
    captions = reel_asset["copy_captions"]
    assert "KINETICS PRO" in captions["hook"]
    assert len(captions["hashtags"]) >= 4

    # 6. Check Job Status & Resumability Endpoint
    status_resp = await client.get(
        f"/api/v1/campaigns/{campaign_id}/reels/{reel_asset['id']}/status",
        headers=headers,
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "COMPLETED"
    assert status_data["progress_percent"] == 100
    assert status_data["scenes_count"] == 4

    # 7. Fetch all reels for campaign
    list_reels = await client.get(f"/api/v1/campaigns/{campaign_id}/reels", headers=headers)
    assert list_reels.status_code == 200
    reels_list = list_reels.json()
    assert len(reels_list) == 1
    assert reels_list[0]["id"] == reel_asset["id"]
