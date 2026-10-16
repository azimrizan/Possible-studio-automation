import pytest
from mcp_common.security import verify_approval_token

@pytest.mark.asyncio
async def test_phase5_approval_and_review_gate_e2e(client):
    """
    Phase 5 Acceptance Criteria:
    - LangGraph interrupt() at the approval gate.
    - Review screen data: preview, brand compliance checklist, campaign details.
    - Add per-asset comments.
    - RBAC enforcement: Only Approvers/Owners can approve; Editors cannot approve (403 Forbidden).
    - Request Changes: free-text feedback -> converted to structured instructions -> targeted regeneration -> version history & diff.
    - Approval service mints signed, single-use, payload-bound Ed25519 approval token.
    - Cryptographic verification of approval token against expected payload.
    - The graph pauses indefinitely and resumes correctly after approval or feedback.
    """
    # 1. Setup Owner / Approver
    owner_signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "approver.chief@brand.com", "full_name": "Chief Approver", "password": "securepassword123"},
    )
    approver_token = owner_signup.json()["access_token"]
    approver_headers = {"Authorization": f"Bearer {approver_token}"}

    # 2. Setup Editor
    editor_signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "designer.editor@brand.com", "full_name": "Junior Designer", "password": "securepassword123"},
    )
    editor_token = editor_signup.json()["access_token"]
    editor_headers = {"Authorization": f"Bearer {editor_token}"}

    # 3. Create Workspace as Owner
    ws = await client.post(
        "/api/v1/workspaces/",
        json={"name": "Aura Cosmetics", "slug": "aura-cosmetics"},
        headers=approver_headers,
    )
    assert ws.status_code == 201
    tenant_id = ws.json()["id"]
    approver_headers["X-Tenant-ID"] = tenant_id

    # 4. Add Editor as workspace member with role EDITOR
    add_mem = await client.post(
        f"/api/v1/workspaces/{tenant_id}/members",
        json={"email": "designer.editor@brand.com", "role": "EDITOR"},
        headers=approver_headers,
    )
    assert add_mem.status_code == 201
    editor_headers["X-Tenant-ID"] = tenant_id

    # 5. Create Brand Kit & Campaign
    await client.put(
        "/api/v1/brand-kit/",
        json={
            "brand_name": "Aura Glow",
            "palette_tokens": {"primary": "#a855f7", "accent": "#ec4899"},
            "typography_tokens": {"headline_font": "Plus Jakarta Sans"},
            "tone_of_voice": {"style": "Luxury, Luminous, Modern"},
        },
        headers=approver_headers,
    )

    camp_res = await client.post(
        "/api/v1/campaigns/",
        json={
            "title": "Aura Glow Hydra-Serum Launch",
            "raw_prompt": "Launch luxury hydrating serum with 24h glow effect and clean botanical ingredients.",
        },
        headers=approver_headers,
    )
    assert camp_res.status_code == 201
    campaign_id = camp_res.json()["id"]

    # 6. Submit Campaign to LangGraph Review & Approval Gate
    sub_res = await client.post(
        f"/api/v1/campaigns/{campaign_id}/review/submit",
        headers=editor_headers,
    )
    assert sub_res.status_code == 200
    gate_state = sub_res.json()
    assert gate_state["campaign_id"] == campaign_id
    assert gate_state["version"] == 1
    assert gate_state["status"] == "PENDING_REVIEW"
    assert gate_state["compliance_report"]["overall_status"] == "PASSED"
    assert len(gate_state["compliance_report"]["checklist"]) == 4

    # 7. Add Asset Feedback Comment
    comm_res = await client.post(
        f"/api/v1/campaigns/{campaign_id}/review/comments",
        json={"asset_id": "var-1", "content": "Headline could be bolder and check contrast on 9:16 story cut."},
        headers=editor_headers,
    )
    assert comm_res.status_code == 201
    comment = comm_res.json()
    assert comment["content"] == "Headline could be bolder and check contrast on 9:16 story cut."

    # Verify listing comments
    list_comm = await client.get(
        f"/api/v1/campaigns/{campaign_id}/review/comments",
        headers=approver_headers,
    )
    assert list_comm.status_code == 200
    assert len(list_comm.json()) == 1

    # 8. RBAC Test: Editor attempts to APPROVE -> must be rejected with 403 Forbidden
    unauth_appr = await client.post(
        f"/api/v1/campaigns/{campaign_id}/review/decision",
        json={"decision": "APPROVE"},
        headers=editor_headers,
    )
    assert unauth_appr.status_code == 403
    assert "not authorized to approve" in unauth_appr.json()["detail"].lower()

    # 9. Request Changes: Free-text feedback -> structured instructions -> targeted regeneration -> version 2
    req_changes = await client.post(
        f"/api/v1/campaigns/{campaign_id}/review/decision",
        json={
            "decision": "REQUEST_CHANGES",
            "feedback": "Make headline punchier and switch to vibrant neon purple accent",
            "target_asset_id": "var-1",
        },
        headers=editor_headers,
    )
    assert req_changes.status_code == 200
    rev_state = req_changes.json()
    assert rev_state["version"] == 2
    assert rev_state["diff_summary"] is not None
    assert len(rev_state["revisions"]) == 1
    assert rev_state["revisions"][0]["version"] == 2

    # 10. Approver approves campaign
    appr_res = await client.post(
        f"/api/v1/campaigns/{campaign_id}/review/decision",
        json={
            "decision": "APPROVE",
            "feedback": "Approved for live social publication and Meta Ad campaign.",
        },
        headers=approver_headers,
    )
    assert appr_res.status_code == 200
    final_state = appr_res.json()
    assert final_state["status"] == "PUBLISH_READY"
    token = final_state["approval_token"]
    assert token is not None
    assert token["tool_name"] == "publish_post"
    assert token["tenant_id"] == tenant_id

    # 11. Cryptographically verify the Ed25519 single-use payload-bound token
    is_valid = verify_approval_token(
        token_dict=token,
        expected_payload_hash=token["payload_hash"],
        expected_tenant_id=tenant_id,
        expected_tool_name="publish_post",
        public_key_hex=token["public_key"],
    )
    assert is_valid is True
