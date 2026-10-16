import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ...db.session import get_db
from ...models.models import Campaign, WorkspaceMembership
from ...schemas.schemas import CampaignCreate, CampaignOut
from ..deps import get_tenant_context, require_role

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

@router.post("/", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    data: CampaignCreate,
    membership: WorkspaceMembership = Depends(require_role("EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    now = int(time.time())
    title = data.title or f"Campaign: {data.raw_prompt[:40]}..."

    campaign = Campaign(
        tenant_id=membership.tenant_id,
        title=title,
        raw_prompt=data.raw_prompt,
        status="DRAFT",
        current_step="PROMPT_ENHANCEMENT",
        product_details=data.product_details,
        advanced_options=data.advanced_options,
        attached_files=data.attached_files,
        created_by=membership.user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    return CampaignOut(
        id=campaign.id,
        tenant_id=campaign.tenant_id,
        title=campaign.title,
        raw_prompt=campaign.raw_prompt,
        status=campaign.status,
        current_step=campaign.current_step,
        product_details=campaign.product_details,
        advanced_options=campaign.advanced_options,
        attached_files=campaign.attached_files or [],
        created_by=campaign.created_by,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )

@router.get("/", response_model=List[CampaignOut])
async def list_campaigns(
    membership: WorkspaceMembership = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Campaign)
        .where(Campaign.tenant_id == membership.tenant_id)
        .order_by(Campaign.created_at.desc())
    )
    result = await db.execute(stmt)
    campaigns = result.scalars().all()

    return [
        CampaignOut(
            id=c.id,
            tenant_id=c.tenant_id,
            title=c.title,
            raw_prompt=c.raw_prompt,
            status=c.status,
            current_step=c.current_step,
            product_details=c.product_details,
            advanced_options=c.advanced_options,
            attached_files=c.attached_files or [],
            created_by=c.created_by,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in campaigns
    ]

@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: str,
    membership: WorkspaceMembership = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.tenant_id == membership.tenant_id,
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return CampaignOut(
        id=campaign.id,
        tenant_id=campaign.tenant_id,
        title=campaign.title,
        raw_prompt=campaign.raw_prompt,
        status=campaign.status,
        current_step=campaign.current_step,
        product_details=campaign.product_details,
        advanced_options=campaign.advanced_options,
        attached_files=campaign.attached_files or [],
        created_by=campaign.created_by,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )
