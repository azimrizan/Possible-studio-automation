"""
Deterministic campaign rules. The LLM proposes; this module disposes.

Everything that must hold regardless of what the model says lives here: objective
prerequisites, special ad categories, budget floors and caps, schedule sanity, and
a guard that drops any interest ID / city the model did not get from Meta.
"""
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from .schemas import CTAS, OBJECTIVES, SPECIAL_CATEGORIES, StrategyOutput

# Rough floors (account currency, major units). Meta's real minimum depends on currency and
# optimisation goal; these keep plans clearly above it.
MIN_DAILY_BUDGET = {"INR": 100, "USD": 2, "EUR": 2, "GBP": 2, "AED": 8, "SGD": 3, "AUD": 3, "CAD": 3}
# Below this, conversion objectives rarely exit the learning phase (~50 results/week).
CONVERSION_DAILY_FLOOR = {"INR": 500, "USD": 10, "EUR": 10, "GBP": 8, "AED": 40, "SGD": 15, "AUD": 15, "CAD": 15}

TEXT_LIMITS = {"primary_text": 300, "headline": 60, "description": 60}
MAX_ADS = 6


def max_daily_budget() -> float:
    return float(os.getenv("META_MAX_DAILY_BUDGET", "50000"))


def _start_time(start_date: str, start_hour: int, tz_name: str, now: datetime) -> Tuple[datetime, Optional[str]]:
    tz = ZoneInfo(tz_name) if ZoneInfo else None
    earliest = (now.astimezone(tz) if tz else now) + timedelta(hours=1)
    earliest = earliest.replace(minute=0, second=0, microsecond=0)
    try:
        start = datetime.fromisoformat(f"{start_date}T{max(0, min(23, int(start_hour))):02d}:00")
        start = start.replace(tzinfo=tz) if tz else start
    except ValueError:
        return earliest, "Start date was invalid; scheduled for the next hour."
    if start < earliest:
        return earliest, "Start time was in the past; moved to the next hour."
    return start, None


def apply_rules(
    s: StrategyOutput,
    *,
    currency: str,
    timezone: str,
    has_website: bool,
    has_pixel: bool,
    has_ig_post: bool,
    creative_count: int,
    image_creatives: List[int],
    special_category: str,
    known_interests: Dict[str, Dict[str, Any]],
    known_cities: Dict[str, Dict[str, Any]],
    default_country: str,
    user_daily_budget: Optional[float] = None,
    user_duration_days: Optional[int] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    warnings: List[str] = []
    now = now or datetime.now().astimezone()
    cur = currency.upper()

    # ---- objective prerequisites ------------------------------------------------
    objective = s.objective if s.objective in OBJECTIVES else "OUTCOME_ENGAGEMENT"
    if objective in ("OUTCOME_SALES", "OUTCOME_LEADS") and not has_pixel:
        objective = "OUTCOME_TRAFFIC" if has_website else "OUTCOME_ENGAGEMENT"
        warnings.append("Sales/Leads optimisation needs a Meta Pixel; switched objective until a Pixel is connected.")
    if objective == "OUTCOME_TRAFFIC" and not has_website:
        objective = "OUTCOME_ENGAGEMENT"
        warnings.append("Traffic ads need a website link; promoting the Instagram post for engagement instead.")
    if not has_website and objective not in ("OUTCOME_ENGAGEMENT", "OUTCOME_AWARENESS"):
        objective = "OUTCOME_ENGAGEMENT"

    # ---- budget -----------------------------------------------------------------
    budget = float(user_daily_budget) if user_daily_budget else float(s.daily_budget or 0)
    floor = MIN_DAILY_BUDGET.get(cur, 2)
    if budget < floor:
        warnings.append(f"Daily budget raised to the minimum {floor} {cur}.")
        budget = float(floor)
    if budget > max_daily_budget():
        warnings.append(f"Daily budget capped at {max_daily_budget():.0f} {cur} (workspace limit).")
        budget = max_daily_budget()
    conv_floor = CONVERSION_DAILY_FLOOR.get(cur, 10)
    if objective in ("OUTCOME_SALES", "OUTCOME_LEADS", "OUTCOME_TRAFFIC") and budget < conv_floor:
        warnings.append(
            f"{budget:.0f} {cur}/day is low for this objective; results may stay in the learning phase. "
            f"Consider {conv_floor} {cur}/day or more."
        )

    # ---- schedule ---------------------------------------------------------------
    duration = int(user_duration_days or s.duration_days or 7)
    duration = max(1, min(duration, 90))
    if duration < 7:
        warnings.append("Runs shorter than 7 days often end before Meta's learning phase completes.")
    start, note = _start_time(s.start_date, s.start_hour, timezone, now)
    if note:
        warnings.append(note)

    # ---- audience -----------------------------------------------------------------
    special = special_category if special_category in SPECIAL_CATEGORIES else "NONE"
    interests = [known_interests[i] for i in s.interest_ids if i in known_interests]
    dropped = len(s.interest_ids) - len(interests)
    if dropped:
        warnings.append(f"Removed {dropped} interest(s) that were not verified with Meta.")
    cities = [known_cities[c.lower()] for c in s.city_names if c.lower() in known_cities]
    countries = [c.upper() for c in s.countries if len(c) == 2] or ([] if cities else [default_country.upper()])

    age_min, age_max = max(18, int(s.age_min)), min(65, int(s.age_max))
    if age_max < age_min:
        age_min, age_max = 18, 65
    genders = s.genders if s.genders in ("all", "male", "female") else "all"
    if special != "NONE":
        # Special ad categories restrict targeting: no age/gender narrowing or detailed interests.
        age_min, age_max, genders, interests = 18, 65, "all", []
        warnings.append(f"Special ad category {special}: age, gender and interest targeting are restricted by Meta.")

    # ---- ads ----------------------------------------------------------------------
    ads = []
    seen = set()
    for ad in s.ads:
        idx = ad.creative_index
        if idx in seen or not (0 <= idx < creative_count):
            continue
        if has_website and idx not in image_creatives and not has_ig_post:
            continue  # link ads use uploaded images; videos are promoted via the Instagram post instead
        seen.add(idx)
        ads.append({
            "creative_index": idx,
            "primary_text": ad.primary_text[: TEXT_LIMITS["primary_text"]],
            "headline": ad.headline[: TEXT_LIMITS["headline"]],
            "description": ad.description[: TEXT_LIMITS["description"]],
            "cta": ad.cta if ad.cta in CTAS else "LEARN_MORE",
        })
    if not ads and creative_count:
        ads = [{"creative_index": i, "primary_text": s.caption[:300], "headline": s.name[:60], "description": "",
                "cta": "LEARN_MORE"} for i in (image_creatives or [0])[:MAX_ADS]]
    ads = ads[:MAX_ADS]
    if not has_website:
        # Without a website, the ad promotes the published Instagram post (one ad for the post).
        ads = ads[:1]

    return {
        "plan": {
            "name": s.name[:120] or "Campaign",
            "objective": objective,
            "special_ad_categories": [] if special == "NONE" else [special],
            "daily_budget": round(budget, 2),
            "currency": cur,
            "duration_days": duration,
            "start_time_iso": start.isoformat(),
            "timezone": timezone,
            "audience": {
                "countries": countries,
                "cities": cities,
                "age_min": age_min,
                "age_max": age_max,
                "genders": genders,
                "interests": interests,
                "advantage_audience": bool(s.advantage_audience) or special != "NONE",
            },
            "placements": "advantage_plus",
            "ads": ads,
            "delivery": "link_ads" if has_website else "boost_instagram_post",
        },
        "warnings": warnings,
    }
