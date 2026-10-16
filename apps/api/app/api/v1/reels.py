import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ...db.session import get_db
from ...models.models import Campaign, CreativeBrief, CreativeAsset, BrandKit, CampaignEvent, WorkspaceMembership
from ...schemas.schemas import CreativeAssetOut, GenerateReelRequest, ReelJobStatusOut
from ..deps import require_role
from model_gateway import ModelGateway
from gateway.router import MCPGatewayRouter
from video_agent import VideoAgent
from mcp_common import TenantContext

router = APIRouter(prefix="/campaigns/{campaign_id}/reels", tags=["Reel Generation"])

_model_gateway = ModelGateway()
_gateway_router = MCPGatewayRouter()


try:
    from gemini_server import server as gemini_mcp_server
    _gateway_router.register_in_process_server("mcp-gemini", gemini_mcp_server)
except Exception:
    pass

try:
    from media_server import server as media_mcp_server
    _gateway_router.register_in_process_server("mcp-media", media_mcp_server)
except Exception:
    pass

_video_agent = VideoAgent(
    model_gateway=_model_gateway,
    mcp_gateway_client=_gateway_router,
)

@router.post("/generate", response_model=CreativeAssetOut, status_code=status.HTTP_200_OK)
async def generate_campaign_reel(
    campaign_id: str,
    req: GenerateReelRequest = GenerateReelRequest(),
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

    # 2. Fetch Brief
    b_res = await db.execute(
        select(CreativeBrief).where(
            CreativeBrief.campaign_id == campaign_id,
            CreativeBrief.tenant_id == membership.tenant_id,
        )
    )
    brief = b_res.scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=400, detail="Creative Brief must be generated before reel generation.")

    # 3. Fetch Brand Kit
    bk_res = await db.execute(
        select(BrandKit).where(
            BrandKit.tenant_id == membership.tenant_id,
            BrandKit.is_active == True,
        )
    )
    brand_kit = bk_res.scalar_one_or_none()
    brand_kit_dict = None
    if brand_kit:
        brand_kit_dict = {
            "brand_name": brand_kit.brand_name,
            "palette_tokens": brand_kit.palette_tokens,
            "typography_tokens": brand_kit.typography_tokens,
            "logo_url": brand_kit.logo_url,
        }

    # 4. Dispatch Video Agent
    tenant_ctx = TenantContext(
        tenant_id=membership.tenant_id,
        workspace_role=membership.role,
        user_id=membership.user_id,
    )

    brief_dict = {
        "objective": brief.objective,
        "product_focus": brief.product_focus,
        "target_audience": brief.target_audience,
        "tone": brief.tone,
        "deliverables": brief.deliverables,
        "call_to_action": brief.call_to_action,
        "enhanced_prompt": brief.enhanced_prompt,
    }

    reel_data = await _video_agent.generate_reel(
        brief=brief_dict,
        brand_kit=brand_kit_dict,
        tenant_context=tenant_ctx,
        audio_track=req.audio_track or "cinematic_synth_anthem",
        caption_style=req.caption_style or "kinetic_highlight",
    )

    # 5. Clear previous REEL asset for this campaign if re-generating
    await db.execute(
        delete(CreativeAsset).where(
            CreativeAsset.campaign_id == campaign_id,
            CreativeAsset.tenant_id == membership.tenant_id,
            CreativeAsset.asset_type == "REEL",
        )
    )

    # 6. Save new CreativeAsset
    now = int(time.time())
    layout_spec = {
        "storyboard": reel_data["storyboard"],
        "audio_track": reel_data["audio_track"],
        "caption_style": reel_data["caption_style"],
        "job_id": reel_data["job_id"],
        "duration_seconds": reel_data["duration_seconds"],
        "thumbnail_url": reel_data["thumbnail_url"],
    }

    asset = CreativeAsset(
        campaign_id=campaign_id,
        tenant_id=membership.tenant_id,
        asset_type="REEL",
        variant_index=1,
        storage_key=f"reels/{reel_data['job_id']}.mp4",
        preview_url=reel_data["output_url"],
        aspect_ratio="9:16",
        layout_spec=layout_spec,
        copy_captions=reel_data["copy_captions"],
        compliance_status="PASSED",
        created_at=now,
    )
    db.add(asset)

    # 7. Update Campaign Status
    campaign.status = "CREATIVE"
    campaign.updated_at = now

    # 8. Audit event
    event = CampaignEvent(
        tenant_id=membership.tenant_id,
        campaign_id=campaign_id,
        event_type="REEL_GENERATED",
        actor_type="AGENT",
        actor_id="video_agent",
        payload={"job_id": reel_data["job_id"], "duration": reel_data["duration_seconds"]},
    )
    db.add(event)

    await db.commit()
    await db.refresh(asset)
    return asset

@router.get("", response_model=List[CreativeAssetOut])
async def get_campaign_reels(
    campaign_id: str,
    membership: WorkspaceMembership = Depends(require_role("VIEWER")),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(CreativeAsset).where(
            CreativeAsset.campaign_id == campaign_id,
            CreativeAsset.tenant_id == membership.tenant_id,
            CreativeAsset.asset_type == "REEL",
        )
    )
    return res.scalars().all()

@router.get("/{asset_id}/status", response_model=ReelJobStatusOut)
async def get_reel_render_status(
    campaign_id: str,
    asset_id: str,
    membership: WorkspaceMembership = Depends(require_role("VIEWER")),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(CreativeAsset).where(
            CreativeAsset.id == asset_id,
            CreativeAsset.campaign_id == campaign_id,
            CreativeAsset.tenant_id == membership.tenant_id,
        )
    )
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Reel asset not found")

    job_id = asset.layout_spec.get("job_id", asset.id)
    tenant_ctx = TenantContext(
        tenant_id=membership.tenant_id,
        workspace_role=membership.role,
        user_id=membership.user_id,
    )
    status_data = await _video_agent.get_job_status(job_id, tenant_ctx)
    return ReelJobStatusOut(
        job_id=job_id,
        status=status_data.get("status", "COMPLETED"),
        progress_percent=status_data.get("progress_percent", 100),
        output_url=status_data.get("output_url", asset.preview_url),
        duration_seconds=status_data.get("duration_seconds", 15.0),
        scenes_count=len(asset.layout_spec.get("storyboard", [])),
    )
