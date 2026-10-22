import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { fitTextOnNLines } from "@remotion/layout-utils";
import * as Icons from "lucide-react";
import { FONTS } from "./fonts";
import { DesignProps } from "./types";

export type Dims = {
  W: number;
  H: number;
  u: number; // 1 at 1080px on the short side
  landscape: boolean;
  story: boolean;
  pad: number;
  top: number; // safe top (story UI)
  bottom: number; // safe bottom (story UI / caption)
};

export function dims(W: number, H: number): Dims {
  const u = Math.min(W, H) / 1080;
  const story = H / W > 1.6;
  const landscape = W / H > 1.2;
  const pad = Math.round((landscape ? 56 : 72) * u);
  return { W, H, u, landscape, story, pad, top: story ? 250 : pad, bottom: story ? 330 : pad };
}

// "*word*" marks accent words in headlines; stripped for measuring.
const plain = (t: string) => t.replace(/\*/g, "");

export const Headline: React.FC<{
  text: string;
  width: number;
  maxLines: number;
  maxSize: number;
  p: DesignProps;
  align?: "left" | "center";
  color?: string;
  maxHeight?: number; // also fit the block's height, so tall formats never push the CTA off the canvas
}> = ({ text, width, maxLines, maxSize, p, align = "left", color, maxHeight }) => {
  const f = FONTS[p.fontPair];
  const shown = f.upper ? plain(text).toUpperCase() : plain(text);
  const accents = new Set((text.match(/\*([^*]+)\*/g) || []).flatMap((m) => m.slice(1, -1).toLowerCase().split(/\s+/)));
  const lineHeight = f.upper ? 0.95 : 1.05;
  const fitted = fitTextOnNLines({
    text: shown || " ",
    maxLines,
    maxBoxWidth: width,
    fontFamily: f.head,
    fontWeight: f.headWeight,
    maxFontSize: maxSize,
  });
  const { lines } = fitted;
  const fontSize = maxHeight ? Math.min(fitted.fontSize, maxHeight / (lines.length * lineHeight)) : fitted.fontSize;
  return (
    <div style={{ fontFamily: f.head, fontWeight: f.headWeight, fontSize, lineHeight, letterSpacing: f.upper ? 1 : -0.5, color: color || p.palette.text, textAlign: align }}>
      {lines.map((line, i) => (
        <div key={i}>
          {line.split(" ").map((w, j) => (
            <span key={j} style={{ color: accents.has(w.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "")) ? p.palette.accent : undefined }}>
              {w}
              {j < line.split(" ").length - 1 ? " " : ""}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
};

export const Body: React.FC<{ text: string; size: number; p: DesignProps; align?: "left" | "center"; opacity?: number; weight?: number; color?: string }> = ({
  text,
  size,
  p,
  align = "left",
  opacity = 0.82,
  weight = 400,
  color,
}) =>
  text ? (
    <div style={{ fontFamily: FONTS[p.fontPair].body, fontSize: size, fontWeight: weight, lineHeight: 1.35, color: color || p.palette.text, opacity, textAlign: align }}>{text}</div>
  ) : null;

export const Cta: React.FC<{ text: string; d: Dims; p: DesignProps }> = ({ text, d, p }) =>
  text ? (
    <div
      style={{
        display: "inline-flex", alignSelf: "flex-start", fontFamily: FONTS[p.fontPair].body, fontWeight: 800, fontSize: 38 * d.u,
        color: p.palette.accentText, background: p.palette.accent, borderRadius: 999, padding: `${20 * d.u}px ${44 * d.u}px`,
        boxShadow: `0 ${12 * d.u}px ${30 * d.u}px rgba(0,0,0,0.25)`,
      }}
    >
      {text} →
    </div>
  ) : null;

export const Badge: React.FC<{ text: string; d: Dims; p: DesignProps; style?: React.CSSProperties }> = ({ text, d, p, style }) => {
  if (!text) return null;
  const size = 210 * d.u;
  return (
    <div
      style={{
        position: "absolute", width: size, height: size, borderRadius: 999, background: p.palette.accent, color: p.palette.accentText,
        display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", padding: 22 * d.u, transform: "rotate(-12deg)",
        fontFamily: FONTS[p.fontPair].body, fontWeight: 800, fontSize: (text.length > 10 ? 30 : 40) * d.u, lineHeight: 1.05,
        boxShadow: `0 ${14 * d.u}px ${34 * d.u}px rgba(0,0,0,0.3)`, ...style,
      }}
    >
      {text}
    </div>
  );
};

export const Price: React.FC<{ price: string; old: string; d: Dims; p: DesignProps; size?: number }> = ({ price, old, d, p, size = 150 }) =>
  price ? (
    <div style={{ display: "flex", alignItems: "baseline", gap: 24 * d.u, fontFamily: FONTS[p.fontPair].head, fontWeight: FONTS[p.fontPair].headWeight }}>
      <span style={{ fontSize: size * d.u, color: p.palette.accent, lineHeight: 1 }}>{price}</span>
      {old && <span style={{ fontSize: size * 0.36 * d.u, color: p.palette.text, opacity: 0.55, textDecoration: "line-through", fontFamily: FONTS[p.fontPair].body }}>{old}</span>}
    </div>
  ) : null;

export const Logo: React.FC<{ d: Dims; p: DesignProps; right?: boolean }> = ({ d, p, right }) => {
  const pos: React.CSSProperties = { position: "absolute", top: d.top, [right ? "right" : "left"]: d.pad };
  if (p.logo) return <Img src={staticFile(p.logo)} style={{ ...pos, maxWidth: 220 * d.u, maxHeight: 90 * d.u, objectFit: "contain" }} />;
  if (!p.content.brandName) return null;
  return (
    <div style={{ ...pos, fontFamily: FONTS[p.fontPair].body, fontWeight: 800, fontSize: 32 * d.u, letterSpacing: 2, color: p.palette.text, textTransform: "uppercase" }}>
      {p.content.brandName}
    </div>
  );
};

export const Product: React.FC<{ p: DesignProps; box: React.CSSProperties; d: Dims }> = ({ p, box, d }) => {
  if (!p.photo) return null;
  const src = staticFile(p.photo.src);
  if (!p.photo.cutout) {
    return <Img src={src} style={{ position: "absolute", objectFit: "cover", borderRadius: 36 * d.u, boxShadow: `0 ${20 * d.u}px ${50 * d.u}px rgba(0,0,0,0.3)`, ...box }} />;
  }
  return (
    <div style={{ position: "absolute", ...box }}>
      <div style={{ position: "absolute", left: "12%", right: "12%", bottom: "2%", height: "9%", borderRadius: "50%", background: "rgba(0,0,0,0.35)", filter: `blur(${22 * d.u}px)` }} />
      <Img src={src} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain", filter: `drop-shadow(0 ${18 * d.u}px ${28 * d.u}px rgba(0,0,0,0.28))` }} />
    </div>
  );
};

// Row of up to 3 product features: icon in a ring + short label (the classic Indian product-ad "FEATURES" strip).
export const Features: React.FC<{ d: Dims; p: DesignProps; align?: "left" | "center" }> = ({ d, p, align = "left" }) => {
  const items = (p.content.features || []).slice(0, 3);
  if (!items.length) return null;
  return (
    <div style={{ display: "flex", gap: 40 * d.u, justifyContent: align === "center" ? "center" : "flex-start" }}>
      {items.map((f, i) => {
        const Icon = ((Icons as unknown as Record<string, React.FC<{ size?: number; color?: string; strokeWidth?: number }>>)[f.icon]) || Icons.Check;
        return (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 * d.u, width: 170 * d.u }}>
            <div style={{ width: 84 * d.u, height: 84 * d.u, borderRadius: 999, border: `${3 * d.u}px solid ${p.palette.accent}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Icon size={44 * d.u} color={p.palette.text} strokeWidth={1.8} />
            </div>
            <div style={{ fontFamily: FONTS[p.fontPair].body, fontWeight: 800, fontSize: 24 * d.u, letterSpacing: 1, textTransform: "uppercase", textAlign: "center", color: p.palette.text, lineHeight: 1.15 }}>
              {f.label}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export const Background: React.FC<{ p: DesignProps; d: Dims; scrim?: "left" | "bottom" | "top" | "none" }> = ({ p, d, scrim = "bottom" }) => {
  const { bg, surface, accent } = p.palette;
  const image = p.bgStyle === "plate" ? p.plate : p.bgStyle === "photo" && p.photo && !p.photo.cutout ? p.photo.src : null;
  const scrims: Record<string, string> = {
    left: `linear-gradient(90deg, ${bg}F2 0%, ${bg}CC 38%, ${bg}00 70%)`,
    bottom: `linear-gradient(0deg, ${bg}F2 0%, ${bg}B3 40%, ${bg}00 72%)`,
    top: `linear-gradient(180deg, ${bg}F2 0%, ${bg}B3 38%, ${bg}00 68%)`,
    none: "none",
  };
  return (
    <AbsoluteFill style={{ background: p.bgStyle === "gradient" ? `linear-gradient(160deg, ${bg} 0%, ${surface} 100%)` : bg }}>
      {image && (
        <>
          <Img src={staticFile(image)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }} />
          <AbsoluteFill style={{ background: scrims[scrim] }} />
        </>
      )}
      {!image && <Decoration p={p} d={d} color={accent} />}
    </AbsoluteFill>
  );
};

const Decoration: React.FC<{ p: DesignProps; d: Dims; color: string }> = ({ p, d, color }) => {
  const { W, H } = d;
  switch (p.decoration) {
    case "circles":
      return (
        <svg width={W} height={H} style={{ position: "absolute" }}>
          <circle cx={W * 0.92} cy={H * 0.12} r={Math.min(W, H) * 0.32} fill={color} opacity={0.16} />
          <circle cx={W * 0.05} cy={H * 0.95} r={Math.min(W, H) * 0.22} fill={color} opacity={0.12} />
        </svg>
      );
    case "grid": {
      const s = 44 * d.u;
      const dots = [];
      for (let x = s / 2; x < W; x += s) for (let y = s / 2; y < H; y += s) dots.push(<circle key={`${x}-${y}`} cx={x} cy={y} r={2.2 * d.u} fill={p.palette.text} opacity={0.12} />);
      return <svg width={W} height={H} style={{ position: "absolute" }}>{dots}</svg>;
    }
    case "burst": {
      const rays = Array.from({ length: 24 }, (_, i) => {
        const a = (i / 24) * Math.PI * 2;
        const R = Math.max(W, H) * 1.5;
        return <path key={i} d={`M${W * 0.8},${H * 0.25} L${W * 0.8 + R * Math.cos(a)},${H * 0.25 + R * Math.sin(a)} L${W * 0.8 + R * Math.cos(a + 0.09)},${H * 0.25 + R * Math.sin(a + 0.09)} Z`} fill={color} opacity={0.08} />;
      });
      return <svg width={W} height={H} style={{ position: "absolute" }}>{rays}</svg>;
    }
    case "waves":
      return (
        <svg width={W} height={H} style={{ position: "absolute" }} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
          <path d={`M0,${H * 0.82} C${W * 0.3},${H * 0.74} ${W * 0.6},${H * 0.9} ${W},${H * 0.8} L${W},${H} L0,${H} Z`} fill={color} opacity={0.18} />
          <path d={`M0,${H * 0.9} C${W * 0.35},${H * 0.84} ${W * 0.65},${H * 0.97} ${W},${H * 0.88} L${W},${H} L0,${H} Z`} fill={color} opacity={0.22} />
        </svg>
      );
    default:
      return null;
  }
};
