import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any, List

from ...db.session import get_db
from ...models.models import BrandKit, BrandKnowledgeItem, WorkspaceMembership
from ...schemas.schemas import BrandKitCreate, BrandKitOut
from ..deps import get_tenant_context, require_role

router = APIRouter(prefix="/brand-kit", tags=["Brand Kit"])

def compile_design_tokens(brand_kit_data: BrandKitCreate) -> Dict[str, Any]:
    """Compiles machine-readable design tokens JSON for creative agents."""
    palette = brand_kit_data.palette_tokens.model_dump()
    typography = brand_kit_data.typography_tokens.model_dump()
    voice = brand_kit_data.tone_of_voice.model_dump()

    return {
        "brand_name": brand_kit_data.brand_name,
        "logo_url": brand_kit_data.logo_url,
        "color_palette": {
            "primary": palette.get("primary", "#6366f1"),
            "secondary": palette.get("secondary", "#4f46e5"),
            "accent": palette.get("accent", "#ec4899"),
            "surface": palette.get("surface", "#0f172a"),
            "background": palette.get("background", "#080c14"),
            "text": {
                "primary": palette.get("text_primary", "#f8fafc"),
                "secondary": palette.get("text_secondary", "#94a3b8"),
            },
        },
        "typography": {
            "headline": {
                "font_family": typography.get("headline_font", "Inter"),
                "weights": typography.get("headline_weights", ["700", "800"]),
            },
            "body": {
                "font_family": typography.get("body_font", "Inter"),
                "weights": typography.get("body_weights", ["400", "500"]),
            },
        },
        "tone_of_voice": {
            "keywords": voice.get("keywords", []),
            "do": voice.get("do_rules", []),
            "dont": voice.get("dont_rules", []),
            "samples": voice.get("sample_posts", []),
        },
        "layout_guidelines": {
            "aspect_ratios": ["1:1", "4:5", "9:16"],
            "safe_zones": {"top_percent": 15, "bottom_percent": 20, "sides_percent": 8},
            "logo_placement": "top_left",
        },
    }

@router.get("/", response_model=BrandKitOut)
async def get_brand_kit(
    membership: WorkspaceMembership = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BrandKit).where(
        BrandKit.tenant_id == membership.tenant_id,
        BrandKit.is_active == True,
    )
    result = await db.execute(stmt)
    brand_kit = result.scalar_one_or_none()

    if not brand_kit:
        # Return a sensible default brand kit for new workspaces
        default_kit = BrandKit(
            tenant_id=membership.tenant_id,
            brand_name="Possible Studio",
            logo_url=None,
            palette_tokens={
                "primary": "#6366f1",
                "secondary": "#4f46e5",
                "accent": "#ec4899",
                "surface": "#0f172a",
                "background": "#080c14",
                "text_primary": "#f8fafc",
                "text_secondary": "#94a3b8",
            },
            typography_tokens={
                "headline_font": "Inter, sans-serif",
                "body_font": "Inter, sans-serif",
                "headline_weights": ["600", "700"],
                "body_weights": ["400", "500"],
            },
            tone_of_voice={
                "keywords": ["Innovative", "Direct", "Authoritative", "Empowering"],
                "do_rules": ["Emphasize customer ROI and time saved", "Use clear, energetic verbs"],
                "dont_rules": ["Never use vague buzzwords", "Avoid generic stock imagery feel"],
                "sample_posts": [
                    "Say goodbye to manual campaign setup. Let your AI Marketing Employee handle research, creative, and ads launch in minutes."
                ],
            },
            product_catalog=[
                {
                    "name": "AI Marketing Suite",
                    "description": "Complete social media & Meta Ads automation platform",
                    "price": 9999,
                    "currency": "INR",
                    "key_features": ["1-Click Campaign Launch", "Deterministic Poster Design", "Auto Reels", "WhatsApp CRM"],
                }
            ],
            version=1,
            is_active=True,
        )
        db.add(default_kit)
        await db.commit()
        await db.refresh(default_kit)
        brand_kit = default_kit

    return BrandKitOut(
        id=brand_kit.id,
        tenant_id=brand_kit.tenant_id,
        brand_name=brand_kit.brand_name,
        logo_url=brand_kit.logo_url,
        palette_tokens=brand_kit.palette_tokens,
        typography_tokens=brand_kit.typography_tokens,
        tone_of_voice=brand_kit.tone_of_voice,
        product_catalog=brand_kit.product_catalog or [],
        version=brand_kit.version,
        is_active=brand_kit.is_active,
        created_at=brand_kit.created_at,
        updated_at=brand_kit.updated_at,
    )

@router.put("/", response_model=BrandKitOut)
async def upsert_brand_kit(
    data: BrandKitCreate,
    membership: WorkspaceMembership = Depends(require_role("EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BrandKit).where(
        BrandKit.tenant_id == membership.tenant_id,
        BrandKit.is_active == True,
    )
    result = await db.execute(stmt)
    brand_kit = result.scalar_one_or_none()

    now = int(time.time())
    catalog_dicts = [p.model_dump() for p in data.product_catalog]

    if brand_kit:
        brand_kit.brand_name = data.brand_name
        brand_kit.logo_url = data.logo_url
        brand_kit.palette_tokens = data.palette_tokens.model_dump()
        brand_kit.typography_tokens = data.typography_tokens.model_dump()
        brand_kit.tone_of_voice = data.tone_of_voice.model_dump()
        brand_kit.product_catalog = catalog_dicts
        brand_kit.version += 1
        brand_kit.updated_at = now
    else:
        brand_kit = BrandKit(
            tenant_id=membership.tenant_id,
            brand_name=data.brand_name,
            logo_url=data.logo_url,
            palette_tokens=data.palette_tokens.model_dump(),
            typography_tokens=data.typography_tokens.model_dump(),
            tone_of_voice=data.tone_of_voice.model_dump(),
            product_catalog=catalog_dicts,
            version=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(brand_kit)

    await db.commit()
    await db.refresh(brand_kit)

    return BrandKitOut(
        id=brand_kit.id,
        tenant_id=brand_kit.tenant_id,
        brand_name=brand_kit.brand_name,
        logo_url=brand_kit.logo_url,
        palette_tokens=brand_kit.palette_tokens,
        typography_tokens=brand_kit.typography_tokens,
        tone_of_voice=brand_kit.tone_of_voice,
        product_catalog=brand_kit.product_catalog or [],
        version=brand_kit.version,
        is_active=brand_kit.is_active,
        created_at=brand_kit.created_at,
        updated_at=brand_kit.updated_at,
    )

@router.post("/compile", status_code=status.HTTP_200_OK)
async def compile_brand_knowledge(
    membership: WorkspaceMembership = Depends(require_role("EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    """
    Compiles Brand Kit and Product Catalog into chunked knowledge items for vector search / RAG.
    """
    stmt = select(BrandKit).where(
        BrandKit.tenant_id == membership.tenant_id,
        BrandKit.is_active == True,
    )
    result = await db.execute(stmt)
    brand_kit = result.scalar_one_or_none()
    if not brand_kit:
        raise HTTPException(status_code=404, detail="No active brand kit found for this workspace")

    # Clear existing items
    del_stmt = select(BrandKnowledgeItem).where(BrandKnowledgeItem.brand_kit_id == brand_kit.id)
    items_to_del = (await db.execute(del_stmt)).scalars().all()
    for item in items_to_del:
        await db.delete(item)

    new_items: List[BrandKnowledgeItem] = []

    # 1. Voice & Guidelines chunk
    voice = brand_kit.tone_of_voice
    voice_chunk = (
        f"Brand Voice for {brand_kit.brand_name}: Keywords: {', '.join(voice.get('keywords', []))}. "
        f"Do: {'; '.join(voice.get('do_rules', []))}. Don't: {'; '.join(voice.get('dont_rules', []))}."
    )
    new_items.append(
        BrandKnowledgeItem(
            tenant_id=membership.tenant_id,
            brand_kit_id=brand_kit.id,
            content_chunk=voice_chunk,
            category="voice_sample",
        )
    )

    # 2. Product Catalog chunks
    for prod in (brand_kit.product_catalog or []):
        features = ", ".join(prod.get("key_features", []))
        prod_chunk = (
            f"Product: {prod.get('name')}. Description: {prod.get('description')}. "
            f"Price: {prod.get('currency', 'INR')} {prod.get('price', 0)}. Features: {features}."
        )
        new_items.append(
            BrandKnowledgeItem(
                tenant_id=membership.tenant_id,
                brand_kit_id=brand_kit.id,
                content_chunk=prod_chunk,
                category="product_spec",
            )
        )

    for item in new_items:
        db.add(item)

    await db.commit()
    return {
        "status": "compiled",
        "tenant_id": membership.tenant_id,
        "brand_kit_id": brand_kit.id,
        "chunks_indexed": len(new_items),
    }
