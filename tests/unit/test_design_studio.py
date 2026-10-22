"""AI Design: the deterministic rules that make Claude's concepts safe to render."""
import pytest

from design_studio import contrast, normalise_concept, plan_concepts, render_props
from design_studio.layout import readable_on


def _concept(**kw):
    base = {"template": "big_statement", "font_pair": "modern", "bg_style": "solid", "decoration": "none",
            "palette": {"bg": "#111111", "surface": "#222222", "text": "#FFFFFF", "accent": "#F5C451", "accent_text": "#111111"},
            "headline": "Hello *world*", "subline": "", "cta": "", "price": "", "old_price": "", "badge": "", "points": [],
            "features": [], "quote": "", "author": "", "event_date": "", "event_place": "", "use_photo": False, "plate_prompt": ""}
    return {**base, **kw}


def test_low_contrast_text_is_fixed_to_wcag_aa():
    c = normalise_concept(_concept(palette={"bg": "#801919", "surface": "#901F1F", "text": "#7A1A1A", "accent": "#801919", "accent_text": "#851B1B"}),
                          ["#801919"], has_photo=False, has_plate=False)
    p = c["palette"]
    assert contrast(p["text"], p["bg"]) >= 4.5
    assert contrast(p["accent_text"], p["accent"]) >= 4.5
    assert contrast(p["accent"], p["bg"]) >= 3.0


def test_readable_text_keeps_its_colour():
    assert readable_on("#111111", "#F5C451") == "#F5C451"


def test_brand_colour_wins_for_the_accent():
    c = normalise_concept(_concept(), ["#2266DD"], has_photo=False, has_plate=False)
    # The accent is the brand blue, lightened only as far as needed to read on the dark background.
    assert c["palette"]["accent"] != "#F5C451"
    r, g, b = (int(c["palette"]["accent"][i:i + 2], 16) for i in (1, 3, 5))
    assert b > r and b > g


def test_templates_that_need_a_photo_fall_back_without_one():
    assert normalise_concept(_concept(template="hero_product"), [], has_photo=False, has_plate=False)["template"] == "announcement"
    assert normalise_concept(_concept(template="split_photo"), [], has_photo=False, has_plate=False)["template"] == "big_statement"
    assert normalise_concept(_concept(template="hero_product"), [], has_photo=True, has_plate=False)["template"] == "hero_product"


def test_unknown_values_are_clamped_and_text_trimmed():
    c = normalise_concept(_concept(template="nope", font_pair="comic", bg_style="plate", decoration="x", headline="h" * 300,
                                   features=[{"icon": "NotAnIcon", "label": "Anti dry"}, {"icon": "Flame", "label": ""}],
                                   palette={"bg": "red", "text": "#FFF"}),
                          [], has_photo=False, has_plate=False)
    assert c["template"] == "big_statement" and c["font_pair"] == "modern"
    assert c["bg_style"] == "gradient"  # no plate available
    assert c["decoration"] == "circles"
    assert len(c["headline"]) == 90
    assert c["features"] == [{"icon": "Check", "label": "Anti dry"}]
    assert c["palette"]["bg"].startswith("#") and len(c["palette"]["bg"]) == 7


def test_render_props_per_size():
    c = normalise_concept(_concept(features=[{"icon": "Zap", "label": "Fast"}]), [], has_photo=False, has_plate=False)
    p = render_props(c, "story", "Kaapi Co", None, None, "logo.png")
    assert (p["width"], p["height"]) == (1080, 1920)
    assert p["content"]["brandName"] == "Kaapi Co" and p["logo"] == "logo.png"
    assert p["content"]["features"] == [{"icon": "Zap", "label": "Fast"}]
    assert render_props(c, "landscape", "", None, None, None)["width"] == 1200


@pytest.mark.asyncio
async def test_demo_concepts_without_key_are_valid():
    plan = await plan_concepts({"text": "Filter coffee ₹349", "goal": "offer"}, {"colors": ["#801919"]}, [], "basic")
    assert plan["mode"] == "demo" and len(plan["concepts"]) == 3
    for c in plan["concepts"]:
        n = normalise_concept(c, ["#801919"], has_photo=False, has_plate=False)
        assert contrast(n["palette"]["text"], n["palette"]["bg"]) >= 4.5
