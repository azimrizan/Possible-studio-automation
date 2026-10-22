// Free Google fonts (OFL) bundled with the renderer, so output never depends on what's installed.
// Malayalam glyphs fall back to Anek Malayalam / Noto Sans Malayalam; Chrome shapes them correctly.
import "@fontsource/inter/400.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/800.css";
import "@fontsource/poppins/600.css";
import "@fontsource/poppins/800.css";
import "@fontsource/playfair-display/700.css";
import "@fontsource/dm-serif-display/400.css";
import "@fontsource/bebas-neue/400.css";
import "@fontsource/anek-malayalam/500.css";
import "@fontsource/anek-malayalam/800.css";
import "@fontsource/noto-sans-malayalam/500.css";
import { FontPair } from "./types";

const ML = '"Anek Malayalam", "Noto Sans Malayalam"';

export const FONTS: Record<FontPair, { head: string; headWeight: number; body: string; upper: boolean }> = {
  modern: { head: `Poppins, ${ML}, sans-serif`, headWeight: 800, body: `Inter, ${ML}, sans-serif`, upper: false },
  editorial: { head: `"DM Serif Display", ${ML}, serif`, headWeight: 400, body: `Inter, ${ML}, sans-serif`, upper: false },
  bold_condensed: { head: `"Bebas Neue", ${ML}, sans-serif`, headWeight: 400, body: `Inter, ${ML}, sans-serif`, upper: true },
  elegant: { head: `"Playfair Display", ${ML}, serif`, headWeight: 700, body: `Inter, ${ML}, sans-serif`, upper: false },
};

// Fonts that must be loaded before text is measured (fitTextOnNLines measures with the real font).
export const FONT_LOADS = [
  "800 40px Poppins", "600 40px Poppins", "400 40px Inter", "600 40px Inter", "800 40px Inter",
  '700 40px "Playfair Display"', '400 40px "DM Serif Display"', '400 40px "Bebas Neue"',
  '500 40px "Anek Malayalam"', '800 40px "Anek Malayalam"', '500 40px "Noto Sans Malayalam"',
];
