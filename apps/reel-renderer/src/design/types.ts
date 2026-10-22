// Mirrors apps/agent-runtime/design_studio/layout.py render_props().
export type TemplateId =
  | "hero_product"
  | "big_statement"
  | "split_photo"
  | "offer_burst"
  | "testimonial"
  | "list_steps"
  | "event"
  | "announcement";

export type FontPair = "modern" | "editorial" | "bold_condensed" | "elegant";
export type BgStyle = "solid" | "gradient" | "photo" | "plate";
export type Decoration = "none" | "circles" | "grid" | "burst" | "waves";

export type Palette = { bg: string; surface: string; text: string; accent: string; accentText: string };

export type DesignContent = {
  headline: string;
  subline: string;
  cta: string;
  price: string;
  oldPrice: string;
  badge: string;
  points: string[];
  features: { icon: string; label: string }[]; // icon = lucide-react component name
  quote: string;
  author: string;
  eventDate: string;
  eventPlace: string;
  brandName: string;
};

export type DesignProps = {
  width: number;
  height: number;
  template: TemplateId;
  fontPair: FontPair;
  palette: Palette;
  bgStyle: BgStyle;
  decoration: Decoration;
  content: DesignContent;
  photo: { src: string; cutout: boolean } | null; // relative to the public dir
  plate: string | null; // AI background (advanced), relative to the public dir
  logo: string | null;
};
