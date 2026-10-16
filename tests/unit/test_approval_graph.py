import pytest
try:
    from apps.agent_runtime.approval_graph import (
        ApprovalWorkflowManager,
        evaluate_compliance,
        parse_free_text_to_instructions,
        apply_targeted_regeneration,
    )
except ImportError:
    from approval_graph import (
        ApprovalWorkflowManager,
        evaluate_compliance,
        parse_free_text_to_instructions,
        apply_targeted_regeneration,
    )
from mcp_common.security import verify_approval_token


def test_compliance_evaluation_rules():
    sample_creatives = [
        {
            "id": "c1",
            "copy": {"headline": "Next-Gen Tech", "cta": "Buy Now"},
        }
    ]
    report = evaluate_compliance(sample_creatives, {"channels": ["INSTAGRAM"]})
    assert report["overall_status"] == "PASSED"
    assert report["score"] == 100
    assert len(report["checklist"]) == 4

    # Test prohibited claims failure
    violating_creatives = [
        {
            "id": "c2",
            "copy": {"headline": "Get rich quick with guaranteed 100% cure"},
        }
    ]
    bad_report = evaluate_compliance(violating_creatives, {})
    assert bad_report["overall_status"] == "FAILED"
    assert len(bad_report["blocking_reasons"]) > 0


def test_free_text_to_structured_instructions():
    feedback = "Make headline punchier and switch to purple accent with urgent CTA"
    instructions = parse_free_text_to_instructions(feedback, target_asset_id="var-1", current_creatives=[])
    
    assert instructions["target_asset_id"] == "var-1"
    fields = [m["field"] for m in instructions["modifications"]]
    assert "headline" in fields
    assert "accent_color" in fields
    assert "cta" in fields


def test_targeted_regeneration_preserves_unmodified_structure():
    creatives = [
        {
            "id": "var-1",
            "accent": "#6366f1",
            "copy": {"headline": "Base Tech", "cta": "Get Started"},
        },
        {
            "id": "var-2",
            "accent": "#6366f1",
            "copy": {"headline": "Second Variant", "cta": "Learn More"},
        },
    ]
    instructions = {
        "target_asset_id": "var-1",
        "raw_feedback": "purple accent and punchier headline",
        "modifications": [
            {"field": "headline"},
            {"field": "accent_color"},
        ],
    }
    updated, diff_summary = apply_targeted_regeneration(creatives, instructions)
    
    # var-1 was modified
    assert updated[0]["accent"] == "#a855f7"
    assert "Powered for Next-Gen Scale" in updated[0]["copy"]["headline"]
    # var-2 remains unchanged
    assert updated[1]["accent"] == "#6366f1"
    assert updated[1]["copy"]["headline"] == "Second Variant"
    assert "Variant 1" in diff_summary


def test_langgraph_workflow_interrupt_and_resume_cycle():
    manager = ApprovalWorkflowManager()
    camp_id = "test-camp-123"
    tenant_id = "tenant-xyz"

    brief = {"objective": "Brand awareness", "channels": ["INSTAGRAM"]}
    creatives = [
        {
            "id": "var-1",
            "accent": "#6366f1",
            "copy": {"headline": "Original Hook", "cta": "Join Us"},
        }
    ]

    # 1. Start workflow - should pause at approval gate
    state = manager.start_campaign_workflow(camp_id, tenant_id, brief, creatives)
    assert state["status"] == "PENDING_REVIEW"
    assert state["version"] == 1
    assert state["compliance_report"]["overall_status"] == "PASSED"

    # 2. Unauthorized approve attempt: Editor tries to approve
    with pytest.raises(PermissionError):
        manager.resume_with_decision(
            campaign_id=camp_id,
            decision="APPROVE",
            reviewer_id="editor-1",
            reviewer_role="EDITOR",
        )

    # 3. Request Changes with free-text feedback
    revised_state = manager.resume_with_decision(
        campaign_id=camp_id,
        decision="REQUEST_CHANGES",
        reviewer_id="editor-1",
        reviewer_role="EDITOR",
        feedback="Make headline punchier and change accent to neon purple",
        target_asset_id="var-1",
    )
    assert revised_state["version"] == 2
    assert len(revised_state["feedback_history"]) == 1
    assert "Headline" in revised_state["diff_summary"]

    # 4. Approver approves campaign
    approved_state = manager.resume_with_decision(
        campaign_id=camp_id,
        decision="APPROVE",
        reviewer_id="approver-1",
        reviewer_role="APPROVER",
        feedback="Looks stellar, approved for launch",
    )
    assert approved_state["status"] == "PUBLISH_READY"
    token = approved_state["approval_token"]
    assert token is not None
    assert token["tool_name"] == "publish_post"
    assert token["tenant_id"] == tenant_id

    # Verify Ed25519 signature cryptographically
    is_valid = verify_approval_token(
        token_dict=token,
        expected_payload_hash=token["payload_hash"],
        expected_tenant_id=tenant_id,
        expected_tool_name="publish_post",
        public_key_hex=token["public_key"],
    )
    assert is_valid is True
