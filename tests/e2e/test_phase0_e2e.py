import pytest
import os
import sys

from mcp_common import TenantContext
from model_gateway import ModelGateway
from gateway.router import MCPGatewayRouter
from hello_server import server as hello_server
from agent import HelloAgent
from apps.api.app.core.security import APPROVAL_PUBLIC_KEY_HEX

@pytest.mark.asyncio
async def test_phase0_full_e2e_flow(client):
    """
    Phase 0 Acceptance Criteria:
    - User can sign up and create a workspace.
    - Traced 'hello agent' call goes Agent -> Gateway -> Hello MCP server.
    - Protected tool call cannot run without a valid approval token.
    - Approval service mints signed token; server verifies and executes.
    """
    # Configure hello_server with the platform's public key
    hello_server.set_approval_public_key(APPROVAL_PUBLIC_KEY_HEX)

    # 1. User signs up
    signup_resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "operator@brand.com", "full_name": "Ops Lead", "password": "pass12345678"},
    )
    assert signup_resp.status_code == 201
    auth_data = signup_resp.json()
    user_token = auth_data["access_token"]
    user_id = auth_data["user"]["id"]
    api_headers = {"Authorization": f"Bearer {user_token}"}

    # 2. User creates workspace
    ws_resp = await client.post(
        "/api/v1/workspaces/",
        json={"name": "Studio Velocity", "slug": "studio-velocity"},
        headers=api_headers,
    )
    assert ws_resp.status_code == 201
    workspace_id = ws_resp.json()["id"]
    api_headers["X-Tenant-ID"] = workspace_id

    # 3. Setup MCP Gateway & Hello Agent
    gateway_router = MCPGatewayRouter()
    gateway_router.register_in_process_server("mcp-hello", hello_server)

    model_gw = ModelGateway(mock_mode=True)
    agent = HelloAgent(model_gateway=model_gw, mcp_gateway_client=gateway_router)

    tenant_ctx = TenantContext(
        tenant_id=workspace_id,
        workspace_role="OWNER",
        user_id=user_id,
    )

    # 4. Safe Tool Call: Traced Hello Agent -> Gateway -> mcp-hello
    echo_result = await agent.run_echo_flow(
        user_prompt="Run initial workspace diagnostics",
        tenant_context=tenant_ctx,
    )
    assert echo_result["status"] == "COMPLETED"
    assert "echo" in echo_result["tool_response"]
    assert echo_result["tool_response"]["tenant_id"] == workspace_id
    assert len(echo_result["traces"]) >= 3

    # 5. Protected Tool Call Attempt without approval token -> Must Fail
    protected_action = "publish_live_billboard"
    failed_protected = await agent.run_protected_flow(
        action=protected_action,
        tenant_context=tenant_ctx,
        approval_token=None,
    )
    assert failed_protected["success"] is False
    assert "APPROVAL_REQUIRED" in failed_protected["error"]

    # 6. Request approval through API
    req_resp = await client.post(
        "/api/v1/approvals/request",
        json={
            "action_type": "PUBLISH",
            "tool_name": "hello_protected_action",
            "action_payload": {"action": protected_action},
        },
        headers=api_headers,
    )
    assert req_resp.status_code == 201
    approval_request_id = req_resp.json()["id"]
    assert req_resp.json()["status"] == "PENDING"

    # 7. Approver reviews and APPROVES -> mints single-use Ed25519 token
    decision_resp = await client.post(
        f"/api/v1/approvals/{approval_request_id}/decision",
        json={"approved": True, "comments": "Approved after QA sign-off"},
        headers=api_headers,
    )
    assert decision_resp.status_code == 200
    approval_data = decision_resp.json()
    assert approval_data["status"] == "APPROVED"
    assert approval_data["token"] is not None
    minted_token = approval_data["token"]
    assert "signature" in minted_token
    assert len(minted_token["signature"]) == 128

    # 8. Retry protected flow WITH the cryptographic approval token -> Must Succeed
    success_protected = await agent.run_protected_flow(
        action=protected_action,
        tenant_context=tenant_ctx,
        approval_token=minted_token,
    )
    assert success_protected["success"] is True, f"Failed: {success_protected}"
    assert success_protected["data"]["status"] == "APPROVED_AND_EXECUTED"
    assert success_protected["data"]["tenant_id"] == workspace_id

    # 9. Tampered token attempt -> Must Fail
    tampered_token = minted_token.copy()
    tampered_token["tool_name"] = "unauthorized_tool"
    tampered_run = await agent.run_protected_flow(
        action=protected_action,
        tenant_context=tenant_ctx,
        approval_token=tampered_token,
    )
    assert tampered_run["success"] is False
    assert "INVALID_APPROVAL_TOKEN" in tampered_run["error"]
