"""
Prompt Composer — deterministic, zero LLM tokens.

Expands a compact DesignConcept into the full art-direction prompt for the Gemini
image model, and declares the role of each reference image in order.
"""
from typing import Any, Dict, List, Optional

from . import vocab
from .schemas import DesignConcept, ProductProfile


def compose_prompt(
    concept: DesignConcept,
    aspect_ratio: str,
    product_image_count: int,
    product: Optional[ProductProfile],
    product_focus: str,
    brand: Dict[str, Any],
    has_logo: bool,
    fix_note: str = "",
) -> str:
    c = concept
    out: List[str] = [
        f"Create a finished, publication-ready advertising poster ({vocab.ASPECT_LABEL.get(aspect_ratio, aspect_ratio)}), "
        "the calibre a senior art director at a leading agency would sign off. Photorealistic product photography, "
        "set design and professional typography integrated into one cohesive image.",
    ]

    refs: List[str] = []
    if product_image_count:
        span = "Image 1" if product_image_count == 1 else f"Images 1-{product_image_count}"
        preserve = ""
        if product and product.must_preserve:
            preserve = " Keep these details exact: " + "; ".join(product.must_preserve) + "."
        if product and product.visible_text:
            preserve += " Printed text on the product must read: " + ", ".join(f'"{t}"' for t in product.visible_text) + "."
        refs.append(
            f"- {span}: the real product. Reproduce it faithfully with identical shape, proportions, colours, "
            f"materials and labels; relight and place it in the scene but never redesign it.{preserve}"
        )
    logo_zone = vocab.LOGO_ZONE[c.logo_zone]
    if has_logo:
        idx = product_image_count + 1
        logo = brand.get("logo_profile") or {}
        contrast = ""
        if logo.get("best_on") in ("light", "dark"):
            contrast = f" Keep the area behind it {logo['best_on']} so it stays legible."
        refs.append(
            f"- Image {idx}: the brand logo. Place it exactly as provided in the {logo_zone}, modest size "
            f"(about 12-18% of the poster width), unaltered: no redrawing, recolouring, warping or added effects.{contrast}"
        )
    if refs:
        out.append("REFERENCE IMAGES:\n" + "\n".join(refs))

    if not product_image_count:
        desc = product.description if product else product_focus
        out.append(f"PRODUCT: {desc}. Render it as a real, premium, photographed product.")

    out.append(f"BIG IDEA: {c.big_idea}")
    out.append(f"SCENE: {c.scene}")
    out.append(f"COMPOSITION: {vocab.COMPOSITION[c.composition]}")
    out.append(f"CAMERA: {vocab.CAMERA[c.camera]}")
    out.append(f"LIGHTING: {vocab.LIGHTING[c.lighting]}")
    palette = (" Palette: " + ", ".join(c.palette) + ".") if c.palette else ""
    out.append(f"COLOUR: {vocab.COLOUR_STRATEGY[c.colour_strategy]}{palette}")

    type_lines = [
        "TYPOGRAPHY: render ONLY the text below, spelled exactly, nothing else:",
        f'- Headline: "{c.headline}", set in {vocab.TYPE_STYLE[c.type_style]}, the dominant element, {vocab.TEXT_ZONE[c.text_zone]}.',
    ]
    if c.subline.strip():
        type_lines.append(f'- Sub-line: "{c.subline}", smaller, same family, lighter weight, directly supporting the headline.')
    if c.cta.strip():
        type_lines.append(f'- Call to action: "{c.cta}", compact, in a refined pill, button or underline treatment.')
    if not has_logo and brand.get("brand_name"):
        type_lines.append(f'- Brand wordmark: "{brand["brand_name"]}", small and tasteful in the {logo_zone}.')
    type_lines.append(
        "Clear hierarchy, consistent alignment, generous margins (keep all text and logo inside a 6% safe area), "
        "strong contrast for legibility on a phone screen."
    )
    out.append("\n".join(type_lines))

    if c.mood:
        out.append("MOOD: " + ", ".join(c.mood) + ".")
    if fix_note:
        out.append(f"CORRECTION FROM REVIEW: {fix_note}")
    out.append(
        "AVOID: any extra or gibberish text, misspellings, watermarks, fake UI, extra logos, duplicated or distorted "
        "products, cluttered layouts, plastic CGI look, low resolution, cropped headline."
    )
    return "\n\n".join(out)
