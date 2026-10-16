"""
Poster pipeline:
  product photo(s) + direction + optional brand kit
  -> [vision] product profile (cached by hash)
  -> [Groq] Creative Director: 3 compact concepts
  -> [code] Prompt Composer
  -> [Gemini] multimodal image generation with product + logo references
  -> [vision] QA (headline + logo) -> one targeted retry -> optional logo lock
"""
import asyncio
import hashlib
import io
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from PIL import Image
from pydantic import BaseModel, Field

from . import vocab
from .agents import PosterAgents
from .composer import compose_prompt
from .imaging import composite_logo
from .schemas import DesignConcept, ProductProfile
from .store import StudioStore

logger = logging.getLogger("poster_studio.pipeline")

# (prompt, [(bytes, mime)], aspect_ratio) -> (image_bytes, mime, model)
ImageFn = Callable[[str, List[Tuple[bytes, str]], str], Awaitable[Tuple[bytes, str, str]]]

MAX_PRODUCT_IMAGES = 3


class PosterRequest(BaseModel):
    brief: Dict[str, Any] = Field(default_factory=dict)
    user_direction: str = ""
    product_asset_ids: List[str] = Field(default_factory=list)
    aspect_ratio: str = "4:5"
    avoid: List[str] = Field(default_factory=list)
    use_brand_kit: bool = True


class RegenerateRequest(BaseModel):
    concept: Dict[str, Any]
    index: int = 1
    change: str = ""
    brief: Dict[str, Any] = Field(default_factory=dict)
    product_asset_ids: List[str] = Field(default_factory=list)
    aspect_ratio: str = "4:5"
    use_brand_kit: bool = True


class PipelineError(Exception):
    pass


class _Context:
    def __init__(self):
        self.brand: Dict[str, Any] = {}
        self.logo: Optional[Tuple[bytes, str]] = None
        self.products: List[Tuple[bytes, str]] = []
        self.profile: Optional[ProductProfile] = None
        self.usage: List[Dict[str, Any]] = []


def summarise_usage(usage: List[Dict[str, Any]]) -> Dict[str, Any]:
    totals = {"calls": len(usage), "prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "cached_tokens": 0}
    for u in usage:
        for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "cached_tokens"):
            totals[k] += u.get(k, 0) or 0
    totals["total_tokens"] = totals["prompt_tokens"] + totals["completion_tokens"]
    totals["by_step"] = [
        {"step": u.get("step"), "model": u.get("model"), "in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0)}
        for u in usage
    ]
    return totals


class PosterPipeline:
    def __init__(self, store: StudioStore, agents: Optional[PosterAgents] = None):
        self.store = store
        self.agents = agents or PosterAgents()

    # ---- context ------------------------------------------------------
    async def _context(self, workspace: str, product_ids: List[str], use_brand_kit: bool, need_profile: bool) -> _Context:
        ctx = _Context()
        if use_brand_kit:
            ctx.brand = self.store.load_brand_kit(workspace)
            logo_id = (ctx.brand.get("logo") or {}).get("asset_id")
            if logo_id:
                try:
                    ctx.logo = self.store.read_asset(workspace, logo_id)
                except Exception:
                    logger.warning("Brand kit logo missing on disk; continuing without logo")
        for asset_id in product_ids[:MAX_PRODUCT_IMAGES]:
            ctx.products.append(self.store.read_asset(workspace, asset_id))
        if need_profile and ctx.products:
            ctx.profile = await self._product_profile(ctx.products[0][0], ctx.usage)
        return ctx

    async def _product_profile(self, image: bytes, usage: List[Dict[str, Any]]) -> Optional[ProductProfile]:
        key = "product_" + hashlib.sha256(image).hexdigest()
        cached = self.store.cache_get(key)
        if cached:
            return ProductProfile(**cached)
        try:
            profile, u = await self.agents.analyse_product(image)
        except Exception as e:
            logger.warning(f"[Pipeline] product analysis failed, continuing without profile: {e}")
            return None
        usage.append({**u, "step": "product_analysis"})
        self.store.cache_set(key, profile.model_dump())
        return profile

    # ---- rendering ----------------------------------------------------
    async def _render(
        self,
        workspace: str,
        index: int,
        concept: DesignConcept,
        ctx: _Context,
        product_focus: str,
        aspect_ratio: str,
        image_fn: ImageFn,
        run_qa: bool,
    ) -> Dict[str, Any]:
        refs = list(ctx.products) + ([ctx.logo] if ctx.logo else [])

        def prompt_for(fix_note: str = "") -> str:
            return compose_prompt(
                concept, aspect_ratio, len(ctx.products), ctx.profile, product_focus, ctx.brand, bool(ctx.logo), fix_note
            )

        prompt = prompt_for()
        try:
            image, mime, model = await image_fn(prompt, refs, aspect_ratio)
        except Exception as e:
            logger.warning(f"[Pipeline] variant {index} image generation failed: {e}")
            return self._variant(index, concept, None, prompt, status="failed", error=str(e))

        qa: Dict[str, Any] = {"checked": False}
        if run_qa:
            qa = await self._qa(image, concept, ctx)
            if qa.get("checked") and not (qa["headline_ok"] and qa["logo_ok"]):
                fix = qa.get("issue") or ""
                if not qa["headline_ok"]:
                    fix += f' The headline must read exactly "{concept.headline}".'
                if not qa["logo_ok"]:
                    fix += " The supplied logo must appear once, unaltered."
                prompt = prompt_for(fix.strip())
                try:
                    image, mime, model = await image_fn(prompt, refs, aspect_ratio)
                    qa = await self._qa(image, concept, ctx)
                    qa["retried"] = True
                except Exception as e:
                    logger.warning(f"[Pipeline] variant {index} retry failed, keeping first render: {e}")

            if qa.get("checked") and not qa["logo_ok"] and ctx.logo:
                image = composite_logo(image, ctx.logo[0], concept.logo_zone)
                mime = "image/png"
                qa["logo_locked"] = True

        if mime not in ("image/png", "image/jpeg"):
            buf = io.BytesIO()
            Image.open(io.BytesIO(image)).save(buf, "PNG")
            image, mime = buf.getvalue(), "image/png"
        asset = self.store.save_asset(workspace, image, mime)
        return self._variant(index, concept, asset, prompt, model=model, qa=qa)

    async def _qa(self, image: bytes, concept: DesignConcept, ctx: _Context) -> Dict[str, Any]:
        logo_profile = (ctx.brand.get("logo_profile") or {"kind": "logo"}) if ctx.logo else None
        try:
            result, u = await self.agents.inspect(image, concept.headline, logo_profile)
        except Exception as e:
            logger.warning(f"[Pipeline] QA skipped: {e}")
            return {"checked": False}
        ctx.usage.append({**u, "step": "qa"})
        return {"checked": True, **result.model_dump()}

    @staticmethod
    def _variant(
        index: int,
        concept: DesignConcept,
        asset: Optional[Dict[str, Any]],
        prompt: str,
        status: str = "ready",
        error: str = "",
        model: str = "",
        qa: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "index": index,
            "status": status,
            "error": error,
            "title": concept.name,
            "theme": concept.composition,
            "tag": " · ".join(m.upper() for m in concept.mood[:2]),
            "accent": concept.palette[0] if concept.palette else "#6366f1",
            "headline": concept.headline,
            "subheadline": concept.subline,
            "cta": concept.cta,
            "description": concept.big_idea,
            "visual_prompt": prompt,
            "bgUrl": asset["url"] if asset else None,
            "asset_id": asset["asset_id"] if asset else None,
            "copy": {
                "hook": concept.headline,
                "body": concept.caption,
                "hashtags": concept.hashtags,
                "alt": concept.alt,
            },
            "concept": concept.model_dump(),
            "qa": qa or {"checked": False},
            "model": model,
        }

    # ---- public API -----------------------------------------------------
    async def generate(self, workspace: str, req: PosterRequest, image_fn: ImageFn, run_qa: bool = True) -> Dict[str, Any]:
        aspect = req.aspect_ratio if req.aspect_ratio in vocab.ASPECT_LABEL else "4:5"
        ctx = await self._context(workspace, req.product_asset_ids, req.use_brand_kit, need_profile=True)
        product_focus = req.brief.get("product_focus") or (ctx.profile.description if ctx.profile else "") or "the product"

        director_input = self.agents.build_director_input(
            req.brief, req.user_direction, ctx.profile, ctx.brand, vocab.ASPECT_LABEL[aspect], req.avoid
        )
        concepts, u = await self.agents.direct(director_input)
        ctx.usage.append({**u, "step": "creative_director"})

        variants = await asyncio.gather(*[
            self._render(workspace, i + 1, c, ctx, product_focus, aspect, image_fn, run_qa)
            for i, c in enumerate(concepts)
        ])
        if all(v["status"] == "failed" for v in variants):
            raise PipelineError(variants[0]["error"] or "Image generation failed")

        usage = summarise_usage(ctx.usage)
        logger.info(f"[Pipeline] {len(variants)} posters | Groq tokens {usage['total_tokens']} over {usage['calls']} calls")
        return {"variants": list(variants), "usage": usage, "brand_kit_applied": bool(ctx.brand)}

    async def regenerate(self, workspace: str, req: RegenerateRequest, image_fn: ImageFn, run_qa: bool = True) -> Dict[str, Any]:
        aspect = req.aspect_ratio if req.aspect_ratio in vocab.ASPECT_LABEL else "4:5"
        ctx = await self._context(workspace, req.product_asset_ids, req.use_brand_kit, need_profile=True)
        concept = DesignConcept(**req.concept).normalised()
        if req.change.strip():
            concept, u = await self.agents.revise(concept, req.change)
            ctx.usage.append({**u, "step": "revise"})
        product_focus = req.brief.get("product_focus") or "the product"
        variant = await self._render(workspace, req.index, concept, ctx, product_focus, aspect, image_fn, run_qa)
        if variant["status"] == "failed":
            raise PipelineError(variant["error"])
        return {"variant": variant, "usage": summarise_usage(ctx.usage)}
