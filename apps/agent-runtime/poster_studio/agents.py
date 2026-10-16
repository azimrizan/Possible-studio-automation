"""
Groq-powered agents for the poster studio.

Token discipline (see docs/poster-studio.md):
- System prompts are static strings so Groq prompt caching can apply.
- Dynamic input is a compact key=value brief, not pretty-printed JSON.
- The Creative Director outputs short fields + vocab enums; code expands them.
- Vision calls use small downscaled images and tiny JSON answers.
- Product analysis is cached by image hash; logo analysis happens once at upload.
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from model_gateway import GroqModelAdapter

from .imaging import to_data_url
from .schemas import (
    CONCEPT_JSON_SCHEMA,
    CONCEPT_SET_JSON_SCHEMA,
    DesignConcept,
    LogoProfile,
    ProductProfile,
    QAResult,
)

logger = logging.getLogger("poster_studio.agents")

Usage = Dict[str, Any]

DIRECTOR_SYSTEM = """You are the Creative Director of a top advertising agency with 15+ years of award-winning product campaigns. You art-direct finished social posters that an image model renders in one pass: photography, set design and typography together.

For each concept think in this order:
1. Insight: what the audience wants or feels that this product answers.
2. Big idea: one sharp, ownable visual idea that dramatises the insight. Never just "product on a background".
3. Craft: composition, camera, lighting and colour chosen to serve the idea; a scene built from specific, tangible props, materials and setting.
4. Type: one dominant headline, optional sub-line, short CTA, in a style that fits the brand and idea.
5. Copy: scroll-stopping headline of max 6 words; concrete benefit over adjectives; no cliches (elevate, unleash, next level, experience, redefine).

Rules:
- Exactly 3 concepts that differ in IDEA, not only colour: e.g. one human/lifestyle, one conceptual metaphor or surreal, one bold graphic/editorial. Vary composition, lighting and colour strategy across them.
- The product is the hero and stays recognisable. Never invent features, claims, prices, discounts or certifications that are not in the brief.
- USER_DIRECTION overrides your defaults. Any offer, discount, date or occasion it states must appear in the copy (headline, subline or cta).
- If brand colours are given, honour them in at least two concepts. palette = 3-4 hex values.
- Minimal text: no feature-icon rows, bullet lists, URLs or phone numbers unless supplied.
- scene describes what is physically in frame, not adjectives.
- text_zone, logo_zone and the product must not collide.
- Do not reuse any idea listed in AVOID.
- Write copy in the language of USER_DIRECTION.
Return JSON only."""

PATCH_SYSTEM = """You revise one poster concept for a senior art director. Apply CHANGE precisely and keep everything else unless the change requires it. Headline max 6 words; never invent product claims. Return the full revised concept as JSON only."""

PRODUCT_SYSTEM = """You analyse product photos for an advertising art director. Return JSON only:
{"category":str,"description":"<=20 words: what it is, form, finish","colours":["#hex",..max 3],"materials":[..max 3],"visible_text":["brand/label text exactly as printed"],"price_tier":"budget|mid|premium|luxury","must_preserve":["<=4 distinctive details that must stay identical"]}"""

LOGO_SYSTEM = """You analyse brand logos. Return JSON only:
{"kind":"wordmark|icon|combination","reads_as":"exact text in the logo or empty","colours":["#hex",..max 3],"best_on":"light|dark|any (background on which it stays legible)"}"""

QA_SYSTEM = """You are a strict print-production checker for advertising posters. Answer only what is asked. Return JSON only:
{"headline_ok":bool,"logo_ok":bool,"issue":"<=15 words, empty if both ok"}"""


def _fmt_list(values: List[str]) -> str:
    return ", ".join(v for v in values if v)


class PosterAgents:
    def __init__(self, groq: Optional[GroqModelAdapter] = None):
        self.groq = groq or GroqModelAdapter()
        self.director_model = self.groq.reasoning_model
        self.fast_model = self.groq.fast_model
        self.vision_model = self.groq.vision_model
        self.director_effort = os.getenv("POSTER_DIRECTOR_REASONING_EFFORT", "medium")

    # ---- vision analysis ----------------------------------------------
    async def analyse_product(self, image: bytes) -> Tuple[ProductProfile, Usage]:
        data, usage = await self.groq.complete_json(
            system=PRODUCT_SYSTEM,
            user="Analyse this product.",
            model=self.vision_model,
            images=[to_data_url(image, max_side=512)],
            max_tokens=220,
            temperature=0.2,
        )
        return ProductProfile(**{k: v for k, v in data.items() if k in ProductProfile.model_fields}), usage

    async def analyse_logo(self, logo: bytes) -> Tuple[LogoProfile, Usage]:
        data, usage = await self.groq.complete_json(
            system=LOGO_SYSTEM,
            user="Analyse this logo.",
            model=self.vision_model,
            images=[to_data_url(logo, max_side=384)],
            max_tokens=120,
            temperature=0.1,
        )
        return LogoProfile(**{k: v for k, v in data.items() if k in LogoProfile.model_fields}), usage

    # ---- creative direction -------------------------------------------
    @staticmethod
    def build_director_input(
        brief: Dict[str, Any],
        user_direction: str,
        product: Optional[ProductProfile],
        brand: Dict[str, Any],
        aspect_label: str,
        avoid: List[str],
    ) -> str:
        lines = [
            "BRIEF: " + "; ".join(
                f"{k}={brief[k]}" for k in ("product_focus", "objective", "audience", "tone", "call_to_action", "offer")
                if brief.get(k)
            ),
            f'USER_DIRECTION: "{user_direction.strip()}"' if user_direction.strip() else "USER_DIRECTION: none",
        ]
        if product:
            lines.append(
                f"PRODUCT_PHOTO: {product.category}; {product.description}; colours {_fmt_list(product.colours)}; "
                f"materials {_fmt_list(product.materials)}; label text {_fmt_list(product.visible_text) or 'none'}; tier {product.price_tier}"
            )
        else:
            lines.append("PRODUCT_PHOTO: none (product will be rendered from the brief)")
        brand_bits = []
        if brand.get("brand_name"):
            brand_bits.append(f"name={brand['brand_name']}")
        if brand.get("colors"):
            brand_bits.append("colours=" + _fmt_list(brand["colors"]))
        if brand.get("tone"):
            brand_bits.append(f"voice={brand['tone']}")
        if brand.get("tagline"):
            brand_bits.append(f"tagline={brand['tagline']}")
        logo = brand.get("logo_profile")
        if logo:
            brand_bits.append(f"logo={logo.get('kind')} '{logo.get('reads_as', '')}', legible on {logo.get('best_on', 'any')}")
        lines.append("BRAND: " + ("; ".join(brand_bits) if brand_bits else "none (no brand kit)"))
        lines.append(f"FORMAT: {aspect_label}")
        if avoid:
            lines.append("AVOID: " + " | ".join(a[:140] for a in avoid[:9]))
        return "\n".join(lines)

    async def direct(self, director_input: str) -> Tuple[List[DesignConcept], Usage]:
        try:
            data, usage = await self.groq.complete_json(
                system=DIRECTOR_SYSTEM,
                user=director_input,
                model=self.director_model,
                json_schema=CONCEPT_SET_JSON_SCHEMA,
                schema_name="concepts",
                max_tokens=5000,
                temperature=0.9,
                reasoning_effort=self.director_effort,
            )
        except Exception as e:
            # Rate-limited or unavailable: fall back to the fast model rather than failing the run.
            logger.warning(f"[Director] {self.director_model} failed ({e}); retrying with {self.fast_model}")
            data, usage = await self.groq.complete_json(
                system=DIRECTOR_SYSTEM,
                user=director_input,
                model=self.fast_model,
                json_schema=CONCEPT_SET_JSON_SCHEMA,
                schema_name="concepts",
                max_tokens=5000,
                temperature=0.9,
                reasoning_effort="medium",
            )
        concepts = [DesignConcept(**c).normalised() for c in data.get("concepts", [])][:3]
        if not concepts:
            raise ValueError("Creative Director returned no concepts")
        if len(concepts) < 3:
            logger.warning(f"[Director] returned {len(concepts)} concepts (completion {usage.get('completion_tokens')} tokens)")
        return concepts, usage

    async def revise(self, concept: DesignConcept, change: str) -> Tuple[DesignConcept, Usage]:
        user = "CONCEPT: " + json.dumps(concept.model_dump(), separators=(",", ":")) + f'\nCHANGE: "{change.strip()}"'
        data, usage = await self.groq.complete_json(
            system=PATCH_SYSTEM,
            user=user,
            model=self.fast_model,
            json_schema=CONCEPT_JSON_SCHEMA,
            schema_name="concept",
            max_tokens=900,
            temperature=0.6,
            reasoning_effort="low",
        )
        return DesignConcept(**data).normalised(), usage

    # ---- quality check --------------------------------------------------
    async def inspect(self, poster: bytes, headline: str, logo: Optional[Dict[str, Any]]) -> Tuple[QAResult, Usage]:
        if logo:
            logo_q = f"2) Is the brand logo ({logo.get('kind', 'logo')} reading '{logo.get('reads_as', '')}') present, clean and undistorted?"
        else:
            logo_q = "2) No logo expected: set logo_ok true."
        user = f'1) Does the main headline read exactly "{headline}" with correct spelling and no garbled letters?\n{logo_q}'
        data, usage = await self.groq.complete_json(
            system=QA_SYSTEM,
            user=user,
            model=self.vision_model,
            images=[to_data_url(poster, max_side=512)],
            max_tokens=80,
            temperature=0.0,
        )
        return QAResult(**{k: v for k, v in data.items() if k in QAResult.model_fields}), usage
