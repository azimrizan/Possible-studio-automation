"""
Deterministic design rules: sizes, templates, brand enforcement, contrast fixes and render props.

Claude proposes concepts; these rules make them safe to render:
- brand colours win: if the brand kit has colours, the accent is always one of them;
- text/background and button text/accent pairs are fixed to meet WCAG AA contrast (4.5:1);
- templates that need a product photo fall back when there is none;
- every field is clamped to known values and sane lengths.
"""
import colorsys
import re
from typing import Any, Dict, List, Optional, Tuple

SIZES: Dict[str, Tuple[int, int, str]] = {
    "square": (1080, 1080, "Instagram post 1:1"),
    "portrait": (1080, 1350, "Instagram post 4:5"),
    "story": (1080, 1920, "Story / Reel cover 9:16"),
    "landscape": (1200, 628, "Ad banner / Facebook link 1.91:1"),
}
TEMPLATES = ["hero_product", "big_statement", "split_photo", "offer_burst", "testimonial", "list_steps", "event", "announcement"]
NEEDS_PHOTO = {"hero_product", "split_photo"}
FONT_PAIRS = ["modern", "editorial", "bold_condensed", "elegant"]
BG_STYLES = ["solid", "gradient", "photo", "plate"]
DECORATIONS = ["none", "circles", "grid", "burst", "waves"]
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
ICONS = ["Zap", "ShieldCheck", "Flame", "Droplet", "Thermometer", "Timer", "Leaf", "Star", "Check", "Truck", "Heart",
         "Sparkles", "Award", "Battery", "Wifi", "Sun", "Snowflake", "Wind", "Coffee", "Utensils", "Gift", "Percent", "Clock",
         "Lock", "Recycle", "Smartphone", "Home", "Users", "BadgeCheck", "Gauge", "Weight", "Ruler", "Volume2", "Plug",
         "Wrench", "Package"]
LIMITS = {"headline": 90, "subline": 140, "cta": 24, "price": 14, "old_price": 14, "badge": 16, "quote": 220,
          "author": 40, "event_date": 30, "event_place": 50}


def _rgb(h: str) -> Tuple[float, float, float]:
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))  # type: ignore


def _hex(rgb) -> str:
    return "#" + "".join(f"{round(max(0, min(1, v)) * 255):02X}" for v in rgb)


def luminance(h: str) -> float:
    def ch(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable_on(bg: str, preferred: str, minimum: float = 4.5) -> str:
    """Keep the preferred text colour if it's readable on bg; otherwise shift its lightness until it is (or use white/black)."""
    if contrast(preferred, bg) >= minimum:
        return preferred
    h, l, s = colorsys.rgb_to_hls(*_rgb(preferred))
    dark_bg = luminance(bg) < 0.4
    for step in range(1, 11):
        cand = _hex(colorsys.hls_to_rgb(h, min(1, l + step * 0.08) if dark_bg else max(0, l - step * 0.08), s))
        if contrast(cand, bg) >= minimum:
            return cand
    return "#FFFFFF" if contrast("#FFFFFF", bg) >= contrast("#111111", bg) else "#111111"


def _clean_hex(v: Any, fallback: str) -> str:
    return v.upper() if isinstance(v, str) and HEX.match(v) else fallback


def normalise_concept(c: Dict[str, Any], brand_colors: List[str], has_photo: bool, has_plate: bool) -> Dict[str, Any]:
    out = dict(c)
    out["template"] = c.get("template") if c.get("template") in TEMPLATES else "big_statement"
    if out["template"] in NEEDS_PHOTO and not has_photo:
        out["template"] = "announcement" if out["template"] == "hero_product" else "big_statement"
    out["font_pair"] = c.get("font_pair") if c.get("font_pair") in FONT_PAIRS else "modern"
    bg_style = c.get("bg_style") if c.get("bg_style") in BG_STYLES else "gradient"
    if bg_style == "plate" and not has_plate:
        bg_style = "gradient"
    if bg_style == "photo" and not has_photo:
        bg_style = "gradient"
    out["bg_style"] = bg_style
    out["decoration"] = c.get("decoration") if c.get("decoration") in DECORATIONS else "circles"

    pal = c.get("palette") or {}
    brand = [b.upper() for b in brand_colors if isinstance(b, str) and HEX.match(b)]
    bg = _clean_hex(pal.get("bg"), "#14161C")
    surface = _clean_hex(pal.get("surface"), _hex(colorsys.hls_to_rgb(*_shift(bg, 0.08))))
    accent = _clean_hex(pal.get("accent"), brand[0] if brand else "#F5C451")
    if brand and accent not in brand and bg not in brand:
        accent = brand[0]
    # The accent is used for text and graphics on bg: make it readable there (3:1 is the bar for large text/graphics).
    accent = readable_on(bg, accent, 3.0)
    text = readable_on(bg, _clean_hex(pal.get("text"), "#FFFFFF" if luminance(bg) < 0.4 else "#111111"))
    accent_text = readable_on(accent, _clean_hex(pal.get("accent_text"), "#111111"))
    out["palette"] = {"bg": bg, "surface": surface, "text": text, "accent": accent, "accent_text": accent_text}

    for key, limit in LIMITS.items():
        out[key] = str(c.get(key) or "").strip()[:limit]
    out["points"] = [str(p).strip()[:60] for p in (c.get("points") or []) if str(p).strip()][:4]
    out["features"] = [{"icon": f.get("icon") if f.get("icon") in ICONS else "Check", "label": str(f.get("label") or "").strip()[:22]}
                       for f in (c.get("features") or []) if isinstance(f, dict) and str(f.get("label") or "").strip()][:3]
    return out


def _shift(h: str, amount: float):
    hh, l, s = colorsys.rgb_to_hls(*_rgb(h))
    return hh, min(1, l + amount) if l < 0.5 else max(0, l - amount), s


def render_props(concept: Dict[str, Any], size: str, brand_name: str, photo: Optional[Dict[str, Any]],
                 plate: Optional[str], logo: Optional[str]) -> Dict[str, Any]:
    w, h, _ = SIZES[size]
    c = concept
    return {
        "width": w, "height": h, "template": c["template"], "fontPair": c["font_pair"],
        "palette": {"bg": c["palette"]["bg"], "surface": c["palette"]["surface"], "text": c["palette"]["text"],
                    "accent": c["palette"]["accent"], "accentText": c["palette"]["accent_text"]},
        "bgStyle": c["bg_style"], "decoration": c["decoration"],
        "content": {"headline": c["headline"], "subline": c["subline"], "cta": c["cta"], "price": c["price"],
                    "oldPrice": c["old_price"], "badge": c["badge"], "points": c["points"], "features": c.get("features") or [], "quote": c["quote"],
                    "author": c["author"], "eventDate": c["event_date"], "eventPlace": c["event_place"],
                    "brandName": brand_name},
        "photo": photo, "plate": plate, "logo": logo,
    }
