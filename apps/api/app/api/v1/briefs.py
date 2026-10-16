import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ...db.session import get_db
from ...models.models import Campaign, CreativeBrief, WorkspaceMembership
from ...schemas.schemas import CreativeBriefCreate, CreativeBriefUpdate, CreativeBriefOut
from ..deps import get_tenant_context, require_role
from model_gateway import ModelGateway
from gateway.router import MCPGatewayRouter
from prompt_enhancer import PromptEnhancerAgent
from mcp_common import TenantContext

router = APIRouter(prefix="/campaigns/{campaign_id}/brief", tags=["Creative Brief"])

# Shared agent instance
_model_gateway = ModelGateway()
_gateway_router = MCPGatewayRouter()
_prompt_enhancer = PromptEnhancerAgent(model_gateway=_model_gateway, mcp_gateway_client=_gateway_router)


@router.post("/enhance", response_model=CreativeBriefOut, status_code=status.HTTP_200_OK)
async def enhance_campaign_prompt(
    campaign_id: str,
    membership: WorkspaceMembership = Depends(require_role("EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    # 1. Fetch Campaign
    c_res = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == membership.tenant_id,
        )
    )
    campaign = c_res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # 2. Run Prompt Enhancer Agent
    tenant_ctx = TenantContext(
        tenant_id=membership.tenant_id,
        workspace_role=membership.role,
        user_id=membership.user_id,
    )

    generated_brief: CreativeBriefCreate = await _prompt_enhancer.enhance_prompt(
        raw_prompt=campaign.raw_prompt,
        tenant_context=tenant_ctx,
        product_details=campaign.product_details,
        advanced_options=campaign.advanced_options,
    )

    # 3. Check if brief already exists
    b_res = await db.execute(
        select(CreativeBrief).where(
            CreativeBrief.campaign_id == campaign_id,
            CreativeBrief.tenant_id == membership.tenant_id,
        )
    )
    brief = b_res.scalar_one_or_none()
    now = int(time.time())

    if brief:
        brief.objective = generated_brief.objective
        brief.product_focus = generated_brief.product_focus
        brief.target_audience = generated_brief.target_audience.model_dump()
        brief.tone = generated_brief.tone
        brief.deliverables = generated_brief.deliverables
        brief.channels = generated_brief.channels
        brief.call_to_action = generated_brief.call_to_action
        brief.constraints = generated_brief.constraints
        brief.enhanced_prompt = generated_brief.enhanced_prompt
        brief.diff_summary = generated_brief.diff_summary
        brief.version += 1
        brief.updated_at = now
    else:
        brief = CreativeBrief(
            campaign_id=campaign.id,
            tenant_id=membership.tenant_id,
            objective=generated_brief.objective,
            product_focus=generated_brief.product_focus,
            target_audience=generated_brief.target_audience.model_dump(),
            tone=generated_brief.tone,
            deliverables=generated_brief.deliverables,
            channels=generated_brief.channels,
            call_to_action=generated_brief.call_to_action,
            constraints=generated_brief.constraints,
            enhanced_prompt=generated_brief.enhanced_prompt,
            diff_summary=generated_brief.diff_summary,
            version=1,
            is_approved=False,
            created_at=now,
            updated_at=now,
        )
        db.add(brief)

    campaign.current_step = "CREATIVE_BRIEF"
    await db.commit()
    await db.refresh(brief)

    return CreativeBriefOut(
        id=brief.id,
        campaign_id=brief.campaign_id,
        tenant_id=brief.tenant_id,
        objective=brief.objective,
        product_focus=brief.product_focus,
        target_audience=brief.target_audience,
        tone=brief.tone,
        deliverables=brief.deliverables,
        channels=brief.channels,
        call_to_action=brief.call_to_action,
        constraints=brief.constraints,
        enhanced_prompt=brief.enhanced_prompt,
        diff_summary=brief.diff_summary,
        version=brief.version,
        is_approved=brief.is_approved,
        created_at=brief.created_at,
        updated_at=brief.updated_at,
    )

@router.get("/", response_model=CreativeBriefOut)
async def get_creative_brief(
    campaign_id: str,
    membership: WorkspaceMembership = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    b_res = await db.execute(
        select(CreativeBrief).where(
            CreativeBrief.campaign_id == campaign_id,
            CreativeBrief.tenant_id == membership.tenant_id,
        )
    )
    brief = b_res.scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=404, detail="Creative brief not found for this campaign")

    return CreativeBriefOut(
        id=brief.id,
        campaign_id=brief.campaign_id,
        tenant_id=brief.tenant_id,
        objective=brief.objective,
        product_focus=brief.product_focus,
        target_audience=brief.target_audience,
        tone=brief.tone,
        deliverables=brief.deliverables,
        channels=brief.channels,
        call_to_action=brief.call_to_action,
        constraints=brief.constraints,
        enhanced_prompt=brief.enhanced_prompt,
        diff_summary=brief.diff_summary,
        version=brief.version,
        is_approved=brief.is_approved,
        created_at=brief.created_at,
        updated_at=brief.updated_at,
    )

@router.put("/", response_model=CreativeBriefOut)
async def update_creative_brief(
    campaign_id: str,
    data: CreativeBriefUpdate,
    membership: WorkspaceMembership = Depends(require_role("EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    b_res = await db.execute(
        select(CreativeBrief).where(
            CreativeBrief.campaign_id == campaign_id,
            CreativeBrief.tenant_id == membership.tenant_id,
        )
    )
    brief = b_res.scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=404, detail="Creative brief not found")

    now = int(time.time())
    if data.objective is not None:
        brief.objective = data.objective
    if data.product_focus is not None:
        brief.product_focus = data.product_focus
    if data.target_audience is not None:
        brief.target_audience = data.target_audience.model_dump()
    if data.tone is not None:
        brief.tone = data.tone
    if data.deliverables is not None:
        brief.deliverables = data.deliverables
    if data.channels is not None:
        brief.channels = data.channels
    if data.call_to_action is not None:
        brief.call_to_action = data.call_to_action
    if data.constraints is not None:
        brief.constraints = data.constraints
    if data.enhanced_prompt is not None:
        brief.enhanced_prompt = data.enhanced_prompt

    brief.version += 1
    brief.updated_at = now
    await db.commit()
    await db.refresh(brief)

    return CreativeBriefOut(
        id=brief.id,
        campaign_id=brief.campaign_id,
        tenant_id=brief.tenant_id,
        objective=brief.objective,
        product_focus=brief.product_focus,
        target_audience=brief.target_audience,
        tone=brief.tone,
        deliverables=brief.deliverables,
        channels=brief.channels,
        call_to_action=brief.call_to_action,
        constraints=brief.constraints,
        enhanced_prompt=brief.enhanced_prompt,
        diff_summary=brief.diff_summary,
        version=brief.version,
        is_approved=brief.is_approved,
        created_at=brief.created_at,
        updated_at=brief.updated_at,
    )

@router.post("/approve", response_model=CreativeBriefOut)
async def approve_creative_brief(
    campaign_id: str,
    membership: WorkspaceMembership = Depends(require_role("EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    b_res = await db.execute(
        select(CreativeBrief).where(
            CreativeBrief.campaign_id == campaign_id,
            CreativeBrief.tenant_id == membership.tenant_id,
        )
    )
    brief = b_res.scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=404, detail="Creative brief not found")

    c_res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = c_res.scalar_one_or_none()
    if campaign:
        campaign.status = "PLANNING"
        campaign.current_step = "CREATIVE_GENERATION"

    brief.is_approved = True
    brief.updated_at = int(time.time())
    await db.commit()
    await db.refresh(brief)

    return CreativeBriefOut(
        id=brief.id,
        campaign_id=brief.campaign_id,
        tenant_id=brief.tenant_id,
        objective=brief.objective,
        product_focus=brief.product_focus,
        target_audience=brief.target_audience,
        tone=brief.tone,
        deliverables=brief.deliverables,
        channels=brief.channels,
        call_to_action=brief.call_to_action,
        constraints=brief.constraints,
        enhanced_prompt=brief.enhanced_prompt,
        diff_summary=brief.diff_summary,
        version=brief.version,
        is_approved=brief.is_approved,
        created_at=brief.created_at,
        updated_at=brief.updated_at,
    )
