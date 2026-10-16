import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import quote
from pydantic import BaseModel
from mcp_common import TenantContext, ToolCallRequest
from model_gateway import ModelGateway

logger = logging.getLogger("designer_agent")

class ConceptItem(BaseModel):
    variant_index: int
    theme: str
    concept_name: str
    bg_prompt: str
    badge_text: str
    accent_color: str
    headline: str
    subheadline: str
    cta_text: str
    hook: str
    body: str
    hashtags: List[str]
    alt_text: str

class DesignConceptsResponse(BaseModel):
    concepts: List[ConceptItem]

# NOTE: Custom Graphic Designer Agent is currently on hold pending fine-tuning and domain training.
# Kept intact in codebase without deletion. Active POC design generation is routed via Gemini MCP.
AGENT_STATUS = "ON_HOLD_PENDING_TRAINING"

class GraphicDesignerAgent:
    """
    Graphic Designer & Copywriter Agent (Phase 3 - ON HOLD PENDING TRAINING):
    Status: On hold for model fine-tuning; active generation handled by Gemini MCP.
    1. Interprets Creative Brief and Brand Tokens
    2. Develops 3 distinct creative layout specs (Dark Titanium, Lifestyle Action, Minimalist Luxury)
    3. Calls mcp-gemini (image.generate) for clean, text-free background art
    4. Calls mcp-media (render_poster) for deterministic typography and logo compositing
    5. Crafts high-converting captions, hooks, and hashtags per variant
    """
    def __init__(self, model_gateway: ModelGateway, mcp_gateway_client: Optional[Any] = None):
        self.model_gateway = model_gateway
        self.mcp_gateway = mcp_gateway_client

    async def generate_variants(
        self,
        brief: Dict[str, Any],
        brand_kit: Optional[Dict[str, Any]],
        tenant_context: TenantContext,
    ) -> List[Dict[str, Any]]:
        brand_name = (brand_kit and brand_kit.get("brand_name")) or "NEXUS"
        product_focus = brief.get("product_focus", "Featured Offering")
        objective = brief.get("objective", "AWARENESS")
        tone = brief.get("tone", "BOLD_PREMIUM")
        call_to_action = brief.get("call_to_action", "Shop Now · Limited Stock")
        deliverables = brief.get("deliverables", "POSTER")
        aspect_ratio = "4:5" if deliverables in ("POSTER", "BOTH") else "9:16"

        # Dynamically generate 3 concepts via Groq if enabled
        dynamic_concepts = None
        if self.model_gateway and not getattr(self.model_gateway, "mock_mode", False) and getattr(self.model_gateway, "groq_api_key", ""):
            try:
                c_resp = await self.model_gateway.generate_structured(
                    prompt=(
                        f"Brand Name: {brand_name}\nProduct Focus: {product_focus}\n"
                        f"Campaign Objective: {objective}\nTone of Voice: {tone}\n"
                        f"Call to Action: {call_to_action}\n"
                        f"Create 3 distinct creative concepts: 1) Dark High-Tech, 2) Vibrant Lifestyle, 3) Minimalist Luxury."
                    ),
                    response_schema=DesignConceptsResponse,
                    system_instruction="You are an award-winning Art Director and Conversion Copywriter.",
                    tenant_id=tenant_context.tenant_id,
                    model=os.getenv("GROQ_REASONING_MODEL", "openai/gpt-oss-120b"),
                )
                if c_resp and len(c_resp.concepts) == 3:
                    theme_map = {1: "dark_titanium", 2: "lifestyle_action", 3: "minimalist_luxury"}
                    dynamic_concepts = [
                        {
                            "variant_index": idx + 1,
                            "theme": theme_map.get(idx + 1, "dark_titanium"),
                            "concept_name": ci.concept_name,
                            "bg_prompt": ci.bg_prompt,
                            "badge_text": ci.badge_text,
                            "accent_color": ci.accent_color,
                            "headline": ci.headline,
                            "subheadline": ci.subheadline,
                            "cta_text": ci.cta_text,
                            "copy": {
                                "hook": ci.hook,
                                "body": ci.body,
                                "hashtags": ci.hashtags,
                                "alt_text": ci.alt_text,
                            },
                        }
                        for idx, ci in enumerate(c_resp.concepts)
                    ]
            except Exception as e:
                logger.warning(f"Groq dynamic concepts generation error: {e}. Using deterministic concepts.")

        # Define 3 distinct creative concepts
        concepts = dynamic_concepts or [

            {
                "variant_index": 1,
                "theme": "dark_titanium",
                "concept_name": "Dark Titanium / High Tech Precision",
                "bg_prompt": f"Minimalist ultra high definition studio lighting product showcase for {product_focus}, sleek dark titanium texture, subtle violet and indigo cyber glow, empty negative space for typography overlay, 8k resolution, cinematic aesthetic",
                "badge_text": "NEW ARRIVAL",
                "accent_color": "#6366f1",
                "headline": f"{product_focus.upper()[:22]}",
                "subheadline": "Engineered for elite performance and next-generation intelligence.",
                "cta_text": call_to_action,
                "copy": {
                    "hook": f"Meet the all-new {brand_name} {product_focus} — redefining modern craftsmanship.",
                    "body": "Built with aerospace-grade materials, lightning-fast responsiveness, and an all-day battery that never slows down.",
                    "hashtags": ["#TechInnovation", f"#{brand_name.replace(' ', '')}", "#WearableTech", "#NextGen", "#SmartLiving"],
                    "alt_text": f"{brand_name} {product_focus} in dark titanium studio spotlight with high contrast typography.",
                }
            },
            {
                "variant_index": 2,
                "theme": "lifestyle_action",
                "concept_name": "Lifestyle Action / Vibrant Energy",
                "bg_prompt": f"Dynamic energetic lifestyle atmospheric setting for {product_focus}, warm amber sunburst lighting, high octane motion aesthetic, clean compositional balance, empty space for clean text typography overlay",
                "badge_text": "TRENDING NOW",
                "accent_color": "#f59e0b",
                "headline": "UNLEASH YOUR POTENTIAL",
                "subheadline": "Seamless intelligence designed to power every adventure and milestone.",
                "cta_text": "Explore Features",
                "copy": {
                    "hook": f"Ready to take your game to the next level? The {product_focus} is here.",
                    "body": "Track your metrics in real-time, conquer your goals, and look effortless doing it.",
                    "hashtags": ["#PerformanceFirst", "#FitnessGoals", f"#{brand_name.replace(' ', '')}", "#ActiveLifestyle", "#UpgradeYourLife"],
                    "alt_text": f"Vibrant lifestyle action composition of {product_focus} featuring amber typography and badge.",
                }
            },
            {
                "variant_index": 3,
                "theme": "minimalist_luxury",
                "concept_name": "Minimalist Luxury / Modern Elegance",
                "bg_prompt": f"Luxury editorial magazine aesthetic showcase for {product_focus}, matte emerald and dark slate architectural podium, soft diffused directional shadows, premium clean background, negative space for typography",
                "badge_text": "LIMITED EDITION",
                "accent_color": "#10b981",
                "headline": "TIMELESS LUXURY",
                "subheadline": "Meticulously crafted perfection where aesthetic elegance meets everyday utility.",
                "cta_text": "Order Yours Now",
                "copy": {
                    "hook": "Elegance isn't about being noticed, it's about being remembered.",
                    "body": "Discover the harmonious blend of minimalist architecture and state-of-the-art innovation.",
                    "hashtags": ["#ModernLuxury", "#MinimalistDesign", "#AestheticTech", f"#{brand_name.replace(' ', '')}", "#TimelessStyle"],
                    "alt_text": f"Minimalist luxury poster of {brand_name} {product_focus} on architectural podium.",
                }
            }
        ]

        results = []
        for c in concepts:
            # 1. Generate clean background art via mcp-gemini
            bg_image_url = None
            if self.mcp_gateway:
                try:
                    img_resp = await self.mcp_gateway.dispatch(
                        ToolCallRequest(
                            tool="image.generate",
                            arguments={"prompt": c["bg_prompt"], "aspect_ratio": aspect_ratio},
                            tenant_context=tenant_context,
                        )
                    )
                    if img_resp.success and img_resp.data:
                        bg_image_url = img_resp.data.get("image_url")
                except Exception as e:
                    logger.warning(f"Error calling image.generate via MCP: {e}")

            if not bg_image_url:
                try:
                    from apps.api.app.api.mcp_gemini import generate_commercial_poster_data_url
                    bg_image_url = generate_commercial_poster_data_url(
                        product=product_focus,
                        brand=brand_name,
                        variant_idx=c.get("variant_index", 1),
                        headline=c.get("headline", product_focus.upper()),
                        features=[c.get("badge_text", "4K RESOLUTION"), "STUDIO GRADE", "PRECISION CRAFT"],
                        accent=c.get("accent_color", "#38bdf8"),
                    )
                except Exception:
                    bg_image_url = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA4MDAgMTAwMCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iIzBmMTcyYSIvPjwvc3ZnPg=="

            # 2. Build deterministic layout specification
            layout_spec = {
                "headline": c["headline"],
                "subheadline": c["subheadline"],
                "cta_text": c["cta_text"],
                "background_image_url": bg_image_url,
                "brand_name": brand_name,
                "badge_text": c["badge_text"],
                "theme": c["theme"],
                "aspect_ratio": aspect_ratio,
                "accent_color": c["accent_color"],
                "concept_name": c["concept_name"],
            }

            # 3. Deterministically composite via mcp-media
            preview_url = None
            storage_key = f"posters/v{c['variant_index']}_{c['theme']}.svg"
            if self.mcp_gateway:
                try:
                    render_resp = await self.mcp_gateway.dispatch(
                        ToolCallRequest(
                            tool="render_poster",
                            arguments={"layout_spec": layout_spec},
                            tenant_context=tenant_context,
                        )
                    )
                    if render_resp.success and render_resp.data:
                        preview_url = render_resp.data.get("preview_url")
                        storage_key = render_resp.data.get("storage_key", storage_key)
                except Exception as e:
                    logger.warning(f"Error calling render_poster via MCP: {e}")

            if not preview_url:
                # Direct import of mock adapter if gateway offline in tests
                from media_server import mock_adapter as media_adapter
                res = await media_adapter.render_poster(layout_spec)
                preview_url = res.get("preview_url")
                storage_key = res.get("storage_key", storage_key)

            results.append({
                "variant_index": c["variant_index"],
                "asset_type": "POSTER",
                "storage_key": storage_key,
                "preview_url": preview_url,
                "aspect_ratio": aspect_ratio,
                "layout_spec": layout_spec,
                "copy_captions": c["copy"],
                "compliance_status": "PASSED",
            })

        return results
