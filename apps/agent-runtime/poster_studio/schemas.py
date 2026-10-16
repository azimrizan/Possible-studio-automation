"""
Typed contracts for the poster studio agents.

The JSON schemas sent to Groq are hand-written and compact on purpose: the schema
itself costs input tokens on every call, and strict mode means no repair calls.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from . import vocab


class ProductProfile(BaseModel):
    category: str = ""
    description: str = ""
    colours: List[str] = Field(default_factory=list)
    materials: List[str] = Field(default_factory=list)
    visible_text: List[str] = Field(default_factory=list)
    price_tier: str = "mid"
    must_preserve: List[str] = Field(default_factory=list)


class LogoProfile(BaseModel):
    kind: str = "combination"  # wordmark | icon | combination
    reads_as: str = ""
    colours: List[str] = Field(default_factory=list)
    best_on: str = "any"  # light | dark | any


class DesignConcept(BaseModel):
    name: str
    big_idea: str
    scene: str
    composition: str
    camera: str
    lighting: str
    colour_strategy: str
    palette: List[str]
    type_style: str
    text_zone: str
    logo_zone: str
    headline: str
    subline: str = ""
    cta: str = ""
    mood: List[str] = Field(default_factory=list)
    caption: str = ""
    hashtags: List[str] = Field(default_factory=list)
    alt: str = ""

    def normalised(self) -> "DesignConcept":
        """Clamp enum fields to known keys so the composer never sees an unknown value."""
        data = self.model_dump()
        for field, table, default in (
            ("composition", vocab.COMPOSITION, "hero_center"),
            ("camera", vocab.CAMERA, "three_quarter_hero"),
            ("lighting", vocab.LIGHTING, "softbox_commercial"),
            ("colour_strategy", vocab.COLOUR_STRATEGY, "product_derived"),
            ("type_style", vocab.TYPE_STYLE, "geometric_sans"),
            ("text_zone", vocab.TEXT_ZONE, "upper_third"),
            ("logo_zone", vocab.LOGO_ZONE, "top_left"),
        ):
            if data.get(field) not in table:
                data[field] = default
        data["palette"] = [c for c in data.get("palette", []) if isinstance(c, str) and c.startswith("#")][:4]
        return DesignConcept(**data)


class QAResult(BaseModel):
    headline_ok: bool = True
    logo_ok: bool = True
    issue: str = ""


def _str(max_len_hint: Optional[str] = None) -> Dict[str, Any]:
    return {"type": "string", "description": max_len_hint} if max_len_hint else {"type": "string"}


def _enum(table: Dict[str, str]) -> Dict[str, Any]:
    return {"type": "string", "enum": list(table.keys())}


_CONCEPT_PROPERTIES: Dict[str, Any] = {
    "name": _str("2-4 words"),
    "big_idea": _str("<=25 words"),
    "scene": _str("<=45 words: setting, props, action"),
    "composition": _enum(vocab.COMPOSITION),
    "camera": _enum(vocab.CAMERA),
    "lighting": _enum(vocab.LIGHTING),
    "colour_strategy": _enum(vocab.COLOUR_STRATEGY),
    "palette": {"type": "array", "items": {"type": "string"}, "description": "3-4 hex colours"},
    "type_style": _enum(vocab.TYPE_STYLE),
    "text_zone": _enum(vocab.TEXT_ZONE),
    "logo_zone": _enum(vocab.LOGO_ZONE),
    "headline": _str("<=6 words"),
    "subline": _str("<=10 words or empty"),
    "cta": _str("<=4 words"),
    "mood": {"type": "array", "items": {"type": "string"}, "description": "3 words"},
    "caption": _str("<=30 words, brand voice"),
    "hashtags": {"type": "array", "items": {"type": "string"}, "description": "5"},
    "alt": _str("<=15 words"),
}

CONCEPT_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": _CONCEPT_PROPERTIES,
    "required": list(_CONCEPT_PROPERTIES.keys()),
    "additionalProperties": False,
}

CONCEPT_SET_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {"concepts": {"type": "array", "items": CONCEPT_JSON_SCHEMA}},
    "required": ["concepts"],
    "additionalProperties": False,
}

# Patch: every field optional in meaning, but strict mode needs all keys present;
# the model returns "" / [] for fields it does not change.
CONCEPT_PATCH_JSON_SCHEMA: Dict[str, Any] = CONCEPT_JSON_SCHEMA
