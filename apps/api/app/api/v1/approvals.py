import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ...db.session import get_db
from ...models.models import ApprovalRequest, ApprovalTokenRecord, WorkspaceMembership
from ...schemas.schemas import (
    ApprovalRequestCreate,
    ApprovalDecision,
    ApprovalRequestOut,
    ApprovalTokenOut,
)
from ...core.security import mint_approval_token
from ..deps import get_tenant_context, require_role
from mcp_common import compute_payload_hash

router = APIRouter(prefix="/approvals", tags=["Approvals"])

@router.post("/request", response_model=ApprovalRequestOut, status_code=status.HTTP_201_CREATED)
async def request_approval(
    data: ApprovalRequestCreate,
    membership: WorkspaceMembership = Depends(require_role("EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    payload_hash = compute_payload_hash(data.action_payload)
    expires_at = int(time.time()) + 900  # 15 minutes TTL

    req = ApprovalRequest(
        tenant_id=membership.tenant_id,
        action_type=data.action_type,
        tool_name=data.tool_name,
        action_payload_hash=payload_hash,
        action_payload=data.action_payload,
        status="PENDING",
        requested_by=membership.user_id,
        expires_at=expires_at,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    return ApprovalRequestOut(
        id=req.id,
        tenant_id=req.tenant_id,
        action_type=req.action_type,
        tool_name=req.tool_name,
        action_payload_hash=req.action_payload_hash,
        status=req.status,
        requested_by=req.requested_by,
        reviewed_by=req.reviewed_by,
        expires_at=req.expires_at,
    )

@router.post("/{request_id}/decision", response_model=ApprovalRequestOut)
async def decide_approval(
    request_id: str,
    decision: ApprovalDecision,
    membership: WorkspaceMembership = Depends(require_role("APPROVER")),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == request_id,
            ApprovalRequest.tenant_id == membership.tenant_id,
        )
    )
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Cannot decide on request with status '{req.status}'")

    req.reviewed_by = membership.user_id
    req.review_comments = decision.comments

    token_out = None
    if decision.approved:
        req.status = "APPROVED"
        # Mint Ed25519 cryptographic token bound to payload hash
        token_data = mint_approval_token(
            tenant_id=req.tenant_id,
            tool_name=req.tool_name,
            payload=req.action_payload,
        )
        token_record = ApprovalTokenRecord(
            approval_request_id=req.id,
            tenant_id=req.tenant_id,
            token_jti=token_data["token_jti"],
            payload_hash=token_data["payload_hash"],
            signature=token_data["signature"],
            expires_at=token_data["expires_at"],
        )
        db.add(token_record)
        token_out = ApprovalTokenOut(**token_data)
    else:
        req.status = "REJECTED"

    await db.commit()
    await db.refresh(req)

    return ApprovalRequestOut(
        id=req.id,
        tenant_id=req.tenant_id,
        action_type=req.action_type,
        tool_name=req.tool_name,
        action_payload_hash=req.action_payload_hash,
        status=req.status,
        requested_by=req.requested_by,
        reviewed_by=req.reviewed_by,
        expires_at=req.expires_at,
        token=token_out,
    )

@router.get("/{request_id}", response_model=ApprovalRequestOut)
async def get_approval(
    request_id: str,
    membership: WorkspaceMembership = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == request_id,
            ApprovalRequest.tenant_id == membership.tenant_id,
        )
    )
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    token_out = None
    if req.status == "APPROVED":
        tok_res = await db.execute(
            select(ApprovalTokenRecord).where(ApprovalTokenRecord.approval_request_id == req.id)
        )
        rec = tok_res.scalar_one_or_none()
        if rec:
            token_out = ApprovalTokenOut(
                token_jti=rec.token_jti,
                tenant_id=rec.tenant_id,
                tool_name=req.tool_name,
                payload_hash=rec.payload_hash,
                expires_at=rec.expires_at,
                signature=rec.signature,
            )

    return ApprovalRequestOut(
        id=req.id,
        tenant_id=req.tenant_id,
        action_type=req.action_type,
        tool_name=req.tool_name,
        action_payload_hash=req.action_payload_hash,
        status=req.status,
        requested_by=req.requested_by,
        reviewed_by=req.reviewed_by,
        expires_at=req.expires_at,
        token=token_out,
    )
