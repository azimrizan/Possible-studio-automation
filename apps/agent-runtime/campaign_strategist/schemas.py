"""Typed contracts for the Meta campaign strategist. JSON schemas are compact and strict on purpose."""
from typing import Any, Dict, List

from pydantic import BaseModel, Field

OBJECTIVES = ["OUTCOME_AWARENESS", "OUTCOME_ENGAGEMENT", "OUTCOME_TRAFFIC", "OUTCOME_LEADS", "OUTCOME_SALES"]
CTAS = ["SHOP_NOW", "LEARN_MORE", "ORDER_NOW", "BUY_NOW", "SIGN_UP", "CONTACT_US", "BOOK_NOW", "GET_OFFER", "SUBSCRIBE", "DOWNLOAD"]
SPECIAL_CATEGORIES = ["NONE", "HOUSING", "EMPLOYMENT", "FINANCIAL_PRODUCTS_SERVICES", "ISSUES_ELECTIONS_POLITICS"]


class CreativeInsight(BaseModel):
    product: str = ""
    category: str = ""
    offer: str = ""
    on_creative_text: List[str] = Field(default_factory=list)
    language: str = "en"
    price_tier: str = "mid"
    audience_guess: str = ""
    special_category: str = "NONE"
    policy_flags: List[str] = Field(default_factory=list)


class ResearchPlan(BaseModel):
    queries: List[str] = Field(default_factory=list)
    interest_keywords: List[str] = Field(default_factory=list)
    city_names: List[str] = Field(default_factory=list)
    country_code: str = ""


class AdCopy(BaseModel):
    creative_index: int
    primary_text: str
    headline: str
    description: str = ""
    cta: str = "LEARN_MORE"


class StrategyOutput(BaseModel):
    name: str
    objective: str
    objective_reason: str
    daily_budget: float
    budget_reason: str
    duration_days: int
    start_date: str
    start_hour: int
    schedule_reason: str
    countries: List[str] = Field(default_factory=list)
    city_names: List[str] = Field(default_factory=list)
    age_min: int = 18
    age_max: int = 65
    genders: str = "all"
    interest_ids: List[str] = Field(default_factory=list)
    advantage_audience: bool = True
    audience_reason: str = ""
    placements_reason: str = ""
    ads: List[AdCopy] = Field(default_factory=list)
    kpis: List[Dict[str, str]] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    research_summary: str = ""
    caption: str = ""


def _s(desc: str = "") -> Dict[str, Any]:
    return {"type": "string", "description": desc} if desc else {"type": "string"}


INSIGHT_KEYS = list(CreativeInsight.model_fields.keys())

RESEARCH_PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "queries": {"type": "array", "items": _s(), "description": "<=4 web searches"},
        "interest_keywords": {"type": "array", "items": _s(), "description": "<=6 Meta interest keywords"},
        "city_names": {"type": "array", "items": _s(), "description": "<=4 cities, empty if national"},
        "country_code": _s("ISO-2"),
    },
    "required": ["queries", "interest_keywords", "city_names", "country_code"],
    "additionalProperties": False,
}

_AD = {
    "type": "object",
    "properties": {
        "creative_index": {"type": "integer"},
        "primary_text": _s("<=125 chars"),
        "headline": _s("<=40 chars"),
        "description": _s("<=30 chars"),
        "cta": {"type": "string", "enum": CTAS},
    },
    "required": ["creative_index", "primary_text", "headline", "description", "cta"],
    "additionalProperties": False,
}

_STRATEGY_PROPS: Dict[str, Any] = {
    "name": _s("campaign name"),
    "objective": {"type": "string", "enum": OBJECTIVES},
    "objective_reason": _s("<=25 words"),
    "daily_budget": {"type": "number"},
    "budget_reason": _s("<=30 words"),
    "duration_days": {"type": "integer"},
    "start_date": _s("YYYY-MM-DD"),
    "start_hour": {"type": "integer"},
    "schedule_reason": _s("<=25 words"),
    "countries": {"type": "array", "items": _s()},
    "city_names": {"type": "array", "items": _s()},
    "age_min": {"type": "integer"},
    "age_max": {"type": "integer"},
    "genders": {"type": "string", "enum": ["all", "male", "female"]},
    "interest_ids": {"type": "array", "items": _s()},
    "advantage_audience": {"type": "boolean"},
    "audience_reason": _s("<=30 words"),
    "placements_reason": _s("<=20 words"),
    "ads": {"type": "array", "items": _AD},
    "kpis": {"type": "array", "items": {
        "type": "object",
        "properties": {"metric": _s(), "expectation": _s("decision rule, no forecasts")},
        "required": ["metric", "expectation"],
        "additionalProperties": False,
    }},
    "risks": {"type": "array", "items": _s()},
    "research_summary": _s("<=60 words"),
    "caption": _s("Instagram caption with 5-8 hashtags"),
}

STRATEGY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": _STRATEGY_PROPS,
    "required": list(_STRATEGY_PROPS.keys()),
    "additionalProperties": False,
}
