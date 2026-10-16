import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ...db.session import get_db
from ...models.models import Campaign, CreativeBrief, CreativeAsset, BrandKit, CampaignEvent, WorkspaceMembership
from ...schemas.schemas import CreativeAssetOut, GenerateCreativeRequest
from ..deps import require_role
from model_gateway import ModelGateway
from gateway.router import MCPGatewayRouter
from designer_agent import GraphicDesignerAgent
from mcp_common import TenantContext

router = APIRouter(prefix="/campaigns/{campaign_id}/assets", tags=["Creative Generation"])

_model_gateway = ModelGateway()
_gateway_router = MCPGatewayRouter()


# Register in-process servers for reliable fast offline execution
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

_designer_agent = GraphicDesignerAgent(
    model_gateway=_model_gateway,
    mcp_gateway_client=_gateway_router,
)

@router.post("/generate", response_model=List[CreativeAssetOut], status_code=status.HTTP_200_OK)
async def generate_creative_assets(
    campaign_id: str,
    req: GenerateCreativeRequest = GenerateCreativeRequest(),
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
        raise HTTPException(status_code=400, detail="Creative Brief must be generated before creative generation.")

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

    # 4. Run Graphic Designer Agent
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

    variants = await _designer_agent.generate_variants(
        brief=brief_dict,
        brand_kit=brand_kit_dict,
        tenant_context=tenant_ctx,
    )

    # 5. Clear old assets if any
    await db.execute(
        delete(CreativeAsset).where(
            CreativeAsset.campaign_id == campaign_id,
            CreativeAsset.tenant_id == membership.tenant_id,
        )
    )

    # 6. Save new CreativeAsset records
    asset_records = []
    now = int(time.time())
    for v in variants:
        asset = CreativeAsset(
            campaign_id=campaign_id,
            tenant_id=membership.tenant_id,
            asset_type=v.get("asset_type", "POSTER"),
            variant_index=v.get("variant_index", 1),
            storage_key=v.get("storage_key", f"posters/v{v.get('variant_index', 1)}.svg"),
            preview_url=v.get("preview_url", ""),
            aspect_ratio=v.get("aspect_ratio", req.aspect_ratio or "4:5"),
            layout_spec=v.get("layout_spec", {}),
            copy_captions=v.get("copy_captions", {}),
            compliance_status="PASSED",
            created_at=now,
        )
        db.add(asset)
        asset_records.append(asset)

    # 7. Update Campaign Status
    campaign.status = "CREATIVE"
    campaign.current_step = "CREATIVE"
    campaign.updated_at = now

    # 8. Audit event
    event = CampaignEvent(
        tenant_id=membership.tenant_id,
        campaign_id=campaign_id,
        event_type="CREATIVE_GENERATED",
        actor_type="AGENT",
        actor_id="graphic_designer_agent",
        payload={"variant_count": len(asset_records)},
    )
    db.add(event)

    await db.commit()
    for a in asset_records:
        await db.refresh(a)

    return asset_records

@router.get("", response_model=List[CreativeAssetOut])
async def get_creative_assets(
    campaign_id: str,
    membership: WorkspaceMembership = Depends(require_role("VIEWER")),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(CreativeAsset).where(
            CreativeAsset.campaign_id == campaign_id,
            CreativeAsset.tenant_id == membership.tenant_id,
        ).order_by(CreativeAsset.variant_index.asc())
    )
    return res.scalars().all()
