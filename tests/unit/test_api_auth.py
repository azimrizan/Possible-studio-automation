import pytest

@pytest.mark.asyncio
async def test_signup_and_login(client):
    # 1. Signup
    signup_resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "alice@example.com", "full_name": "Alice Smith", "password": "securepassword123"},
    )
    assert signup_resp.status_code == 201
    data = signup_resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alice@example.com"
    token = data["access_token"]

    # 2. Get Me
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "alice@example.com"

    # 3. Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepassword123"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

@pytest.mark.asyncio
async def test_workspace_creation_and_roles(client):
    # Create user
    signup_resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "bob@example.com", "full_name": "Bob Jones", "password": "securepassword123"},
    )
    token = signup_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create workspace
    ws_resp = await client.post(
        "/api/v1/workspaces/",
        json={"name": "Acme Marketing", "slug": "acme-mktg"},
        headers=headers,
    )
    assert ws_resp.status_code == 201
    ws_data = ws_resp.json()
    assert ws_data["role"] == "OWNER"
    assert ws_data["slug"] == "acme-mktg"

    # List workspaces
    list_resp = await client.get("/api/v1/workspaces/", headers=headers)
    assert list_resp.status_code == 200
    workspaces = list_resp.json()
    assert len(workspaces) == 1
    assert workspaces[0]["id"] == ws_data["id"]
