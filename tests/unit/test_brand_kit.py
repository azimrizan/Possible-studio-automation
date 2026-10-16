import pytest

@pytest.mark.asyncio
async def test_brand_kit_lifecycle(client):
    # 1. Signup & Workspace
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "designer@acme.com", "full_name": "Acme Designer", "password": "password1234"},
    )
    token = signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = await client.post(
        "/api/v1/workspaces/",
        json={"name": "Acme Brand", "slug": "acme-brand"},
        headers=headers,
    )
    workspace_id = ws.json()["id"]
    headers["X-Tenant-ID"] = workspace_id

    # 2. Get Default Brand Kit
    get_res = await client.get("/api/v1/brand-kit/", headers=headers)
    assert get_res.status_code == 200
    brand_data = get_res.json()
    assert brand_data["version"] == 1
    assert "palette_tokens" in brand_data

    # 3. Update Brand Kit with custom colors & product
    updated_payload = {
        "brand_name": "Acme Smart Tech",
        "logo_url": "https://acme.com/logo.svg",
        "palette_tokens": {
            "primary": "#4f46e5",
            "secondary": "#06b6d4",
            "accent": "#f59e0b",
            "surface": "#1e293b",
            "background": "#0f172a",
            "text_primary": "#ffffff",
            "text_secondary": "#94a3b8",
        },
        "typography_tokens": {
            "headline_font": "Outfit, sans-serif",
            "body_font": "Inter, sans-serif",
            "headline_weights": ["700", "800"],
            "body_weights": ["400"],
        },
        "tone_of_voice": {
            "keywords": ["Futuristic", "Confident", "Accessible"],
            "do_rules": ["Highlight speed and intelligence"],
            "dont_rules": ["Never use confusing jargon"],
            "sample_posts": ["Meet the future of connected lifestyle."],
        },
        "product_catalog": [
            {
                "name": "Acme Air Watch",
                "description": "Ultra-lightweight smartwatch with AI sleep tracker",
                "price": 12999,
                "currency": "INR",
                "key_features": ["Titanium Bezel", "AI Sleep Tracker", "ECG Sensor"],
                "target_audience": "Active professionals",
            }
        ],
    }

    put_res = await client.put("/api/v1/brand-kit/", json=updated_payload, headers=headers)
    assert put_res.status_code == 200
    new_data = put_res.json()
    assert new_data["brand_name"] == "Acme Smart Tech"
    assert new_data["version"] == 2
    assert len(new_data["product_catalog"]) == 1

    # 4. Compile Brand Knowledge chunks
    compile_res = await client.post("/api/v1/brand-kit/compile", headers=headers)
    assert compile_res.status_code == 200
    comp_data = compile_res.json()
    assert comp_data["status"] == "compiled"
    assert comp_data["chunks_indexed"] >= 2

@pytest.mark.asyncio
async def test_campaign_draft_persistence(client):
    # Signup & Workspace
    signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "marketer@acme.com", "full_name": "Acme Marketer", "password": "password1234"},
    )
    token = signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = await client.post(
        "/api/v1/workspaces/",
        json={"name": "Pulse Media", "slug": "pulse-media"},
        headers=headers,
    )
    headers["X-Tenant-ID"] = ws.json()["id"]

    # Prompt Bar draft submission matching flow
    campaign_payload = {
        "title": "Smartwatch Launch",
        "raw_prompt": "Promote our new AI smartwatch on Instagram. Create a poster and a reel, publish it and run a ₹10,000 ad campaign for 7 days targeting the right audience to drive sales.",
        "product_details": {"product_name": "AI Smartwatch Pro", "price": "₹10,000"},
        "advanced_options": {"budget_inr": 10000, "duration_days": 7, "channels": ["INSTAGRAM"]},
        "attached_files": [{"filename": "smartwatch_spec.pdf", "size_kb": 250}],
    }

    create_res = await client.post("/api/v1/campaigns/", json=campaign_payload, headers=headers)
    assert create_res.status_code == 201
    camp = create_res.json()
    assert camp["status"] == "DRAFT"
    assert camp["raw_prompt"] == campaign_payload["raw_prompt"]
    assert camp["advanced_options"]["budget_inr"] == 10000

    # Retrieve campaigns
    list_res = await client.get("/api/v1/campaigns/", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
