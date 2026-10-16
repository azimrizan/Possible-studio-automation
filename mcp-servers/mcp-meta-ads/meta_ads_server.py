"""
mcp-meta-ads: Meta Marketing API wrapper.

Hard rules enforced here (not in prompts):
- Campaigns, ad sets and ads are always created PAUSED.
- Activation is a separate SPEND tool that requires an approval token.
- Daily budget is capped per tenant (META_MAX_DAILY_BUDGET, account currency major units).
Credentials come from `graph_provider`, never from tool arguments.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional

from mcp_common import MCPServer, RiskClass, TenantContext

logger = logging.getLogger("mcp_meta_ads")

GraphProvider = Callable[[TenantContext], Awaitable[Any]]
graph_provider: Optional[GraphProvider] = None
# Resolves an asset id to JPEG bytes for ad image upload (bytes never go through tool args / payload hashes).
AssetProvider = Callable[[TenantContext, str], Awaitable[bytes]]
asset_provider: Optional[AssetProvider] = None

server = MCPServer(name="mcp-meta-ads", version="0.1.0")

# Meta stores budgets in the currency's minor unit; these currencies have no minor unit (offset 1).
ZERO_DECIMAL_CURRENCIES = {"JPY", "KRW", "VND", "CLP", "ISK", "TWD", "HUF", "COP", "CRC", "IDR", "PYG"}

OPTIMIZATION = {
    "OUTCOME_AWARENESS": "REACH",
    "OUTCOME_ENGAGEMENT": "POST_ENGAGEMENT",
    "OUTCOME_TRAFFIC": "LINK_CLICKS",
    "OUTCOME_LEADS": "OFFSITE_CONVERSIONS",
    "OUTCOME_SALES": "OFFSITE_CONVERSIONS",
}


class BudgetCapError(ValueError):
    pass


def max_daily_budget() -> float:
    return float(os.getenv("META_MAX_DAILY_BUDGET", "50000"))


def to_minor_units(amount: float, currency: str) -> int:
    return int(round(amount)) if currency.upper() in ZERO_DECIMAL_CURRENCIES else int(round(amount * 100))


def _j(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def build_targeting(audience: Dict[str, Any]) -> Dict[str, Any]:
    geo: Dict[str, Any] = {"location_types": ["home", "recent"]}
    if audience.get("cities"):
        geo["cities"] = [{"key": c["key"], "radius": 25, "distance_unit": "kilometer"} for c in audience["cities"]]
    if audience.get("countries"):
        geo["countries"] = audience["countries"]
    targeting: Dict[str, Any] = {"geo_locations": geo}

    age_min, age_max = int(audience.get("age_min", 18)), int(audience.get("age_max", 65))
    if audience.get("advantage_audience", True):
        # With Advantage+ audience the age range is a suggestion; the hard floor must stay <= 25.
        targeting["age_min"] = min(age_min, 25)
        targeting["age_max"] = 65
        targeting["age_range"] = [age_min, age_max]
        targeting["targeting_automation"] = {"advantage_audience": 1}
    else:
        targeting["age_min"], targeting["age_max"] = age_min, age_max
        targeting["targeting_automation"] = {"advantage_audience": 0}

    gender = audience.get("genders", "all")
    if gender in ("male", "female"):
        targeting["genders"] = [1 if gender == "male" else 2]
    interests = [{"id": i["id"], "name": i.get("name", "")} for i in audience.get("interests", [])]
    if interests:
        targeting["flexible_spec"] = [{"interests": interests}]
    return targeting


async def _graph(ctx: TenantContext):
    if not graph_provider:
        raise RuntimeError("mcp-meta-ads has no credential provider configured")
    return await graph_provider(ctx)


# ---- read tools ------------------------------------------------------------

async def handle_targeting_search(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    graph = await _graph(ctx)
    if args.get("type") == "city":
        res = await graph.request("GET", "search", {
            "type": "adgeolocation", "q": args["q"], "location_types": _j(["city"]),
            "country_code": args.get("country_code", ""), "limit": 3,
        })
        return {"results": [
            {"key": r["key"], "name": r["name"], "region": r.get("region", ""), "country_code": r.get("country_code", "")}
            for r in res.get("data", [])
        ], "mock": bool(getattr(graph, "mock", False))}
    res = await graph.request("GET", "search", {"type": "adinterest", "q": args["q"], "limit": 3})
    return {"results": [
        {"id": r["id"], "name": r["name"], "size_lower": r.get("audience_size_lower_bound"),
         "size_upper": r.get("audience_size_upper_bound")}
        for r in res.get("data", [])
    ], "mock": bool(getattr(graph, "mock", False))}


async def handle_delivery_estimate(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    graph = await _graph(ctx)
    res = await graph.request("GET", f"{args['ad_account_id']}/delivery_estimate", {
        "targeting_spec": _j(build_targeting(args["audience"])),
        "optimization_goal": OPTIMIZATION.get(args.get("objective", ""), "REACH"),
    })
    row = (res.get("data") or [{}])[0]
    return {
        "audience_lower": row.get("estimate_mau_lower_bound"),
        "audience_upper": row.get("estimate_mau_upper_bound"),
        "daily_active": row.get("estimate_dau"),
        "mock": bool(getattr(graph, "mock", False)),
    }


# ---- write tools -------------------------------------------------------------

async def handle_create_campaign(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    """Builds campaign -> ad set -> creatives -> ads, everything PAUSED."""
    graph = await _graph(ctx)
    plan, acct = args["plan"], args["ad_account_id"]
    currency = args.get("currency", "INR")
    daily = float(plan["daily_budget"])
    if daily <= 0 or daily > max_daily_budget():
        raise BudgetCapError(f"Daily budget {daily} {currency} is outside the allowed range (cap {max_daily_budget():.0f})")

    objective = plan["objective"]
    special = plan.get("special_ad_categories") or []
    campaign_id = (await graph.request("POST", f"{acct}/campaigns", {
        "name": plan["name"][:200],
        "objective": objective,
        "status": "PAUSED",
        "buying_type": "AUCTION",
        "special_ad_categories": _j(special),
        "daily_budget": to_minor_units(daily, currency),
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
    }))["id"]

    start = datetime.fromisoformat(args["start_time_iso"])
    adset_params: Dict[str, Any] = {
        "name": f"{plan['name'][:150]} · Ad set",
        "campaign_id": campaign_id,
        "optimization_goal": OPTIMIZATION.get(objective, "REACH"),
        "billing_event": "IMPRESSIONS",
        "targeting": _j(build_targeting(plan["audience"])),
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(days=int(plan["duration_days"]))).isoformat(),
        "status": "PAUSED",
    }
    if objective in ("OUTCOME_SALES", "OUTCOME_LEADS"):
        adset_params["promoted_object"] = _j({
            "pixel_id": args["pixel_id"], "custom_event_type": "PURCHASE" if objective == "OUTCOME_SALES" else "LEAD",
        })
    if objective == "OUTCOME_TRAFFIC":
        adset_params["destination_type"] = "WEBSITE"
    elif objective == "OUTCOME_ENGAGEMENT":
        # Engagement ad sets must name where engagement happens; without it Meta assumes a website
        # destination and rejects the ad for missing a URL. ON_POST = likes/comments/shares on the ad post.
        adset_params["destination_type"] = "ON_POST"
    adset_id = (await graph.request("POST", f"{acct}/adsets", adset_params))["id"]

    ad_ids: List[str] = []
    creative_ids: List[str] = []
    fallbacks: List[str] = []

    async def image_spec(i: int, ad: Dict[str, Any]) -> Dict[str, Any]:
        if not asset_provider:
            raise RuntimeError("mcp-meta-ads has no asset provider configured")
        image_bytes = await asset_provider(ctx, ad["image_asset_id"])
        image_name = f"creative_{i + 1}.jpg"
        upload = await graph.request("POST", f"{acct}/adimages", None, files={
            image_name: (image_name, image_bytes, "image/jpeg"),
        })
        image_hash = next(iter(upload["images"].values()))["hash"]
        story: Dict[str, Any] = {"page_id": args["page_id"], "instagram_user_id": args["ig_user_id"]}
        if args.get("website_url"):
            story["link_data"] = {
                "image_hash": image_hash,
                "link": args["website_url"],
                "message": ad["primary_text"],
                "name": ad["headline"],
                "description": ad.get("description", ""),
                "call_to_action": {"type": ad["cta"], "value": {"link": args["website_url"]}},
            }
        else:
            # No website: an image post ad (engagement) built from the creative itself.
            story["photo_data"] = {"image_hash": image_hash, "caption": ad["primary_text"]}
        return {"name": f"{plan['name'][:120]} · Creative {i + 1}", "object_story_spec": _j(story)}

    try:
        for i, ad in enumerate(args["ads"]):
            creative_id = None
            if ad.get("boost_media_id"):
                try:
                    creative_id = (await graph.request("POST", f"{acct}/adcreatives", {
                        "name": f"{plan['name'][:120]} · Creative {i + 1}",
                        "object_id": args["page_id"],
                        "instagram_user_id": args["ig_user_id"],
                        "source_instagram_media_id": ad["boost_media_id"],
                    }))["id"]
                except Exception as e:
                    # Meta refuses to promote posts published by an app in Development mode.
                    if not ad.get("image_asset_id"):
                        raise
                    logger.warning(f"[mcp-meta-ads] boosting post refused ({e}); using the image creative instead")
                    fallbacks.append(str(e))
            if creative_id is None:
                creative_id = (await graph.request("POST", f"{acct}/adcreatives", await image_spec(i, ad)))["id"]
            creative_ids.append(creative_id)
            ad_ids.append((await graph.request("POST", f"{acct}/ads", {
                "name": f"{plan['name'][:120]} · Ad {i + 1}",
                "adset_id": adset_id,
                "creative": _j({"creative_id": creative_id}),
                "status": "PAUSED",
            }))["id"])
    except Exception:
        # Don't leave a half-built (paused) campaign behind; deleting the campaign removes its ad set and ads.
        try:
            await graph.request("DELETE", campaign_id)
        except Exception as cleanup_error:
            logger.warning(f"[mcp-meta-ads] could not delete partial campaign {campaign_id}: {cleanup_error}")
        raise

    logger.info(f"[mcp-meta-ads] built PAUSED campaign {campaign_id} with {len(ad_ids)} ads for {ctx.tenant_id}")
    return {
        "campaign_id": campaign_id, "adset_id": adset_id, "creative_ids": creative_ids, "ad_ids": ad_ids,
        "status": "PAUSED", "mock": bool(getattr(graph, "mock", False)),
        "used_image_fallback": bool(fallbacks),
    }


async def handle_activate(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    """Turns a PAUSED campaign live: ads, then ad set, then campaign (so nothing half-starts)."""
    graph = await _graph(ctx)
    for object_id in list(args["ad_ids"]) + [args["adset_id"], args["campaign_id"]]:
        await graph.request("POST", object_id, {"status": "ACTIVE"})
    return {"campaign_id": args["campaign_id"], "status": "ACTIVE", "mock": bool(getattr(graph, "mock", False))}


server.register_tool(
    name="ads.targeting_search",
    description="Find real Meta interest IDs (type=interest) or city location keys (type=city) with audience sizes.",
    handler=handle_targeting_search,
    parameters_schema={"type": "object", "properties": {"q": {"type": "string"}, "type": {"type": "string"},
                                                         "country_code": {"type": "string"}}, "required": ["q"]},
    risk_class=RiskClass.READ,
)
server.register_tool(
    name="ads.delivery_estimate",
    description="Meta's own audience-size estimate for a targeting spec. Values are estimates.",
    handler=handle_delivery_estimate,
    parameters_schema={"type": "object", "properties": {"ad_account_id": {"type": "string"}, "audience": {"type": "object"},
                                                         "objective": {"type": "string"}}, "required": ["ad_account_id", "audience"]},
    risk_class=RiskClass.READ,
)
server.register_tool(
    name="ads.create_campaign",
    description="Create campaign, ad set, creatives and ads in the tenant's ad account. Always PAUSED; no spend. Requires approval.",
    handler=handle_create_campaign,
    risk_class=RiskClass.WRITE,
    requires_approval=True,
    idempotent=False,
)
server.register_tool(
    name="ads.activate",
    description="Set a PAUSED campaign, its ad set and ads ACTIVE. Starts spending money. Requires approval.",
    handler=handle_activate,
    risk_class=RiskClass.SPEND,
    requires_approval=True,
    idempotent=True,
)

app = server.app
