"""
Advanced mode: text-free background "plates" from an image model (Gemini by default).

The image model only makes the picture. It is told where the layout will put text so it leaves that area calm,
and never to draw words or logos; the real text is rendered on top as code. One plate per aspect group
(square/portrait share 4:5, story 9:16, banner 16:9) keeps cost down.
"""
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

ImageFn = Callable[[str, List[Tuple[bytes, str]], str], Awaitable[Tuple[bytes, str, str]]]

ASPECT_GROUP = {"square": "4:5", "portrait": "4:5", "story": "9:16", "landscape": "16:9"}
TEXT_ZONE = {
    "hero_product": "the top 35% and the bottom 20%", "big_statement": "the middle and left two thirds",
    "split_photo": "the bottom half", "offer_burst": "the centre and the top quarter", "testimonial": "the centre",
    "list_steps": "almost all of it", "event": "the bottom 60%", "announcement": "the bottom half",
}


def plate_prompt(concept: Dict, aspect: str) -> str:
    zone = TEXT_ZONE.get(concept["template"], "the area where text goes") if aspect != "16:9" else "the left half"
    pal = concept["palette"]
    return (
        f"A text-free background image for a social media ad ({aspect}). Scene: {concept['plate_prompt']}\n"
        f"Colour palette to harmonise with: background {pal['bg']}, accent {pal['accent']}.\n"
        f"Composition: keep {zone} of the frame calm and uncluttered (soft, out of focus, low detail) because text "
        "will be placed there later.\n"
        "Strictly no text, letters, numbers, logos, watermarks or UI anywhere in the image. Photographic, "
        "professional commercial quality, natural light."
    )


async def make_plates(concept: Dict, sizes: List[str], image_fn: ImageFn) -> Dict[str, Tuple[bytes, str]]:
    """aspect -> (image bytes, mime). Skips silently (falls back to gradient) when the model fails."""
    out: Dict[str, Tuple[bytes, str]] = {}
    if not concept.get("plate_prompt"):
        return out
    for aspect in sorted({ASPECT_GROUP[s] for s in sizes}):
        try:
            data, mime, _ = await image_fn(plate_prompt(concept, aspect), [], aspect)
            out[aspect] = (data, mime)
        except Exception:  # noqa: BLE001 - a missing plate falls back to the gradient background
            continue
    return out


def plate_for(size: str, plates: Dict[str, str]) -> Optional[str]:
    return plates.get(ASPECT_GROUP[size])
