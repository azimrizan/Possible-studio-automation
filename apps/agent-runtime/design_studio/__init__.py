"""
AI Design: brief -> three on-brand design concepts -> every size, editable.

    Claude art-directs (director.py) -> deterministic rules (layout.py: brand colours, contrast, template
    fallbacks) -> product cut-outs (cutout.py) -> optional text-free AI backgrounds (plates.py, advanced)
    -> code-rendered designs (apps/reel-renderer, composition "Design") -> Claude reviews the renders.

Image models never draw text: text, logo and layout are rendered as code, so spelling is exact in any
language and every design stays editable.
"""
from .cutout import cut_out, cut_out_file, cutout_available
from .director import demo_concepts, plan_concepts, review_concepts, revise_concept
from .layout import SIZES, TEMPLATES, contrast, normalise_concept, render_props
from .plates import ASPECT_GROUP, make_plates, plate_for

__all__ = [
    "ASPECT_GROUP", "SIZES", "TEMPLATES", "contrast", "cut_out", "cut_out_file", "cutout_available", "demo_concepts", "make_plates",
    "normalise_concept", "plan_concepts", "plate_for", "render_props", "review_concepts", "revise_concept",
]
