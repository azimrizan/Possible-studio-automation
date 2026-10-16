"""
Craft vocabulary library.

The Creative Director (Groq) picks short enum keys; the Prompt Composer expands
each key into the phrasing a senior art director would brief a photographer and
typographer with. Writing this once in code (instead of having the LLM write
3 x 400-word prompts every run) is where most output-token savings come from,
and it keeps the craft language consistent and tunable through evals.

The keys also become JSON-schema enums, so the model cannot invent unknown ones.
"""

COMPOSITION = {
    "hero_center": "Symmetrical, centred hero composition: the product sits on the vertical axis slightly below centre, with generous breathing room above for the headline.",
    "diagonal_dynamic": "Dynamic diagonal composition: the product angled roughly 20-30 degrees along a strong leading line from lower-left to upper-right, creating motion and energy.",
    "thirds_right": "Rule-of-thirds layout: the product anchored on the right-third power point, the left two-thirds held as calm negative space for typography.",
    "thirds_left": "Rule-of-thirds layout: the product anchored on the left-third power point, the right two-thirds held as calm negative space for typography.",
    "low_angle_monument": "Low, heroic camera position that makes the product feel monumental; low horizon line, the product towering against the backdrop.",
    "levitation": "The product levitating mid-air with a soft contact shadow beneath it, a few related elements suspended around it in balanced orbit.",
    "flat_lay": "Top-down flat-lay: the product and a curated set of props arranged on a deliberate grid with consistent spacing and intentional negative space.",
    "macro_crop": "Tight, partial macro crop filling most of the frame, the frame edge deliberately cutting the product to emphasise material, texture and craftsmanship.",
    "lifestyle_moment": "A believable real-life moment of use: a person partially in frame (hands, over-the-shoulder or mid-action), yet the product remains the unmistakable focal point.",
    "split_layout": "Bold split layout: one side is a clean flat colour field carrying the typography, the other side the photographic product scene, joined by a crisp edge.",
    "repetition_break": "Rhythmic repetition: multiple instances of the product forming a pattern, with one hero instance breaking the pattern to catch the eye.",
    "frame_in_frame": "Frame-within-a-frame: an architectural arch, doorway, window or geometric cut-out framing the product and pulling the eye inward.",
    "surreal_scale": "Surreal scale play: the product rendered oversized within a miniature world (or a tiny world on the product), treated with full photographic realism.",
    "exploded_view": "Deconstructed/exploded arrangement: key components, ingredients or materials floating apart in an orderly radial arrangement around the product.",
    "pedestal_set": "The product presented on a sculptural plinth inside an architectural set built from simple geometric forms and arches.",
    "mirror_floor": "The product standing on a glossy mirror-like surface with a clean reflection beneath it, the horizon softly dissolving into the backdrop.",
}

CAMERA = {
    "85mm_eye_level": "Shot on an 85mm lens at eye level, shallow depth of field, background softly compressed.",
    "50mm_natural": "Natural 50mm perspective, honest proportions, moderate depth of field.",
    "35mm_environment": "35mm environmental perspective showing the surrounding scene, product still dominant in the foreground.",
    "100mm_macro": "100mm macro lens, razor-thin focus plane on the key detail, creamy falloff.",
    "24mm_low_wide": "24mm wide lens from a low angle, dramatic perspective and depth, slight foreshortening.",
    "three_quarter_hero": "Classic three-quarter hero view from slightly above, 70mm, showing front and side of the product.",
    "overhead_90": "Perfect 90-degree overhead camera, orthographic feel, no perspective distortion.",
    "tilt_shift": "Tilt-shift effect with a narrow band of focus through the product, miniature-like blur above and below.",
}

LIGHTING = {
    "softbox_commercial": "Clean commercial studio lighting: large overhead softbox key, white bounce fill, soft wraparound shadows, true-to-life colour.",
    "rim_dark_premium": "Low-key premium lighting: dark environment, crisp rim lights tracing the product silhouette, a subtle top light revealing form.",
    "chiaroscuro": "Dramatic chiaroscuro: a single hard key light from the side carving deep shadows and bright highlights.",
    "golden_hour": "Warm golden-hour sunlight raking in low from the side, long soft shadows, gentle lens glow.",
    "hard_sun": "Bright midday sun with crisp, graphic hard-edged shadows and saturated summer colour.",
    "neon_gels": "Two-colour gel lighting (complementary hues) from opposite sides, glossy reflections and atmospheric colour spill.",
    "backlit_glow": "Strong backlight creating a luminous halo and translucent glow around the product, light haze in the air.",
    "window_soft": "Soft natural window light from one side, airy and calm, delicate shadow gradients.",
    "caustics": "Light passing through water or glass, throwing shimmering caustic patterns across the product and surface.",
    "volumetric_beams": "Atmospheric haze with volumetric light beams cutting through the scene toward the product.",
    "high_key": "Bright high-key lighting, nearly shadowless, luminous and optimistic.",
}

COLOUR_STRATEGY = {
    "brand_led": "Colour grade built around the brand palette, used with restraint so the product stays the hero.",
    "product_derived": "Palette derived from the product's own colours and materials for a seamless, tonal look.",
    "complementary_pop": "Complementary contrast: a backdrop hue opposite the product colour on the wheel so the product pops.",
    "analogous_harmony": "Analogous harmony: neighbouring hues on the colour wheel for a calm, cohesive mood.",
    "dark_luxe_accent": "Deep, rich darks with a single saturated accent colour reserved for the product and the call to action.",
    "pastel_soft": "Soft desaturated pastels, airy and gentle, with low-contrast shadows.",
    "bold_high_contrast": "Bold, high-contrast blocks of saturated colour with strong graphic punch.",
    "earthy_natural": "Earthy, natural tones (stone, clay, wood, linen, foliage) with organic textures.",
    "monochrome_tonal": "Monochromatic tonal palette, shades of a single hue from light to dark.",
}

TYPE_STYLE = {
    "bold_condensed_sans": "a bold condensed sans-serif, tight tracking, punchy and confident",
    "geometric_sans": "a clean geometric sans-serif, balanced weights, modern and precise",
    "editorial_serif": "an elegant high-contrast editorial serif, refined and premium",
    "modern_serif_italic": "a modern serif with an expressive italic accent word, fashionable and warm",
    "extended_heavy_sans": "a heavy extended sans-serif, wide letterforms, bold and impactful",
    "script_accent": "a clean sans-serif paired with one hand-lettered script accent word",
    "mono_tech": "a technical monospaced typeface, engineered and precise",
    "rounded_friendly": "a soft rounded sans-serif, friendly and approachable",
}

TEXT_ZONE = {
    "top": "across the top of the poster",
    "upper_third": "in the upper third, above the product",
    "lower_third": "in the lower third, below the product",
    "left_column": "stacked in a left-aligned column",
    "right_column": "stacked in a right-aligned column",
    "center_overlay": "centred over a calm area of the scene with strong contrast",
}

LOGO_ZONE = {
    "top_left": "top-left corner",
    "top_right": "top-right corner",
    "top_center": "top centre",
    "bottom_left": "bottom-left corner",
    "bottom_right": "bottom-right corner",
    "bottom_center": "bottom centre",
}

ASPECT_LABEL = {
    "4:5": "4:5 portrait Instagram feed poster",
    "1:1": "1:1 square social post",
    "9:16": "9:16 full-screen vertical story/reel cover",
}
