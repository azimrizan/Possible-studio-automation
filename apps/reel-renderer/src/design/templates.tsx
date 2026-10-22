// Eight layout archetypes. Each one lays itself out for square, portrait, story and landscape sizes,
// keeps text inside the safe area and sizes headlines to fit (fitTextOnNLines) so text never overflows.
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { FONTS } from "./fonts";
import { Background, Badge, Body, Cta, Dims, Features, Headline, Logo, Price, Product } from "./parts";
import { DesignProps } from "./types";

type T = React.FC<{ p: DesignProps; d: Dims }>;

const Column: React.FC<{ d: Dims; style?: React.CSSProperties; children: React.ReactNode }> = ({ d, style, children }) => (
  <div style={{ position: "absolute", display: "flex", flexDirection: "column", gap: 26 * d.u, ...style }}>{children}</div>
);

const HeroProduct: T = ({ p, d }) => {
  const c = p.content;
  if (d.landscape) {
    const textW = d.W * 0.5;
    return (
      <AbsoluteFill>
        <Background p={p} d={d} scrim="left" />
        <Product p={p} d={d} box={{ right: d.pad, top: d.pad, width: d.W * 0.42, height: d.H - 2 * d.pad }} />
        <Logo d={d} p={p} />
        <Column d={d} style={{ left: d.pad, top: d.pad + 90 * d.u, width: textW, bottom: d.pad, justifyContent: "center" }}>
          <Headline text={c.headline} width={textW} maxLines={3} maxSize={110 * d.u} p={p} />
          <Body text={c.subline} size={30 * d.u} p={p} />
          <Features d={d} p={p} />
          <Price price={c.price} old={c.oldPrice} d={d} p={p} size={90} />
          <Cta text={c.cta} d={d} p={p} />
        </Column>
        <Badge text={c.badge} d={d} p={p} style={{ right: d.W * 0.38, top: d.pad }} />
      </AbsoluteFill>
    );
  }
  const textW = d.W - 2 * d.pad;
  const productTop = d.top + (d.story ? 520 : d.H > d.W ? 420 : 330) * d.u + (c.features.length ? (d.story ? 160 : 150) * d.u : 0);
  const productBottom = d.bottom + (d.story ? 300 : 180) * d.u;
  return (
    <AbsoluteFill>
      <Background p={p} d={d} scrim="top" />
      <Logo d={d} p={p} />
      <Column d={d} style={{ left: d.pad, top: d.top + 110 * d.u, width: textW }}>
        <Headline text={c.headline} width={textW} maxLines={2} maxSize={(d.story ? 130 : 112) * d.u} p={p} align={c.features.length ? "center" : "left"} />
        <Body text={c.subline} size={34 * d.u} p={p} align={c.features.length ? "center" : "left"} />
        <Features d={d} p={p} align="center" />
      </Column>
      <Product p={p} d={d} box={{ left: d.pad, right: d.pad, top: productTop, bottom: productBottom }} />
      <div style={{ position: "absolute", left: d.pad, right: d.pad, bottom: d.bottom, display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
        <Price price={c.price} old={c.oldPrice} d={d} p={p} size={96} />
        <Cta text={c.cta} d={d} p={p} />
      </div>
      <Badge text={c.badge} d={d} p={p} style={{ right: d.pad, top: productTop }} />
    </AbsoluteFill>
  );
};

const BigStatement: T = ({ p, d }) => {
  const c = p.content;
  const w = d.W - 2 * d.pad;
  return (
    <AbsoluteFill>
      <Background p={p} d={d} scrim="bottom" />
      <Logo d={d} p={p} />
      <Column d={d} style={{ left: d.pad, width: w, top: d.top + 100 * d.u, bottom: d.bottom, justifyContent: "center" }}>
        <div style={{ width: 120 * d.u, height: 14 * d.u, borderRadius: 14, background: p.palette.accent }} />
        <Headline text={c.headline} width={w} maxLines={d.landscape ? 3 : 5} maxSize={(d.landscape ? 120 : 190) * d.u} p={p}
          maxHeight={(d.H - d.top - d.bottom) * 0.62} />
        <Body text={c.subline} size={(d.landscape ? 30 : 38) * d.u} p={p} />
        <div style={{ height: 10 * d.u }} />
        <Cta text={c.cta} d={d} p={p} />
      </Column>
    </AbsoluteFill>
  );
};

const SplitPhoto: T = ({ p, d }) => {
  const c = p.content;
  if (d.landscape) {
    const textW = d.W * 0.44;
    return (
      <AbsoluteFill>
        <Background p={{ ...p, bgStyle: p.bgStyle === "plate" ? "plate" : "solid" }} d={d} scrim="left" />
        {p.photo && <Img src={staticFile(p.photo.src)} style={{ position: "absolute", right: 0, top: 0, width: d.W * 0.48, height: d.H, objectFit: p.photo.cutout ? "contain" : "cover", background: p.palette.surface }} />}
        <Logo d={d} p={p} />
        <Column d={d} style={{ left: d.pad, top: d.pad + 80 * d.u, width: textW, bottom: d.pad, justifyContent: "center" }}>
          <Headline text={c.headline} width={textW} maxLines={3} maxSize={100 * d.u} p={p} />
          <Body text={c.subline} size={30 * d.u} p={p} />
          <Cta text={c.cta} d={d} p={p} />
        </Column>
      </AbsoluteFill>
    );
  }
  const photoH = d.H * (d.story ? 0.5 : 0.52);
  const textW = d.W - 2 * d.pad;
  return (
    <AbsoluteFill style={{ background: p.palette.bg }}>
      {p.photo ? (
        <Img src={staticFile(p.photo.src)} style={{ position: "absolute", left: 0, top: 0, width: d.W, height: photoH, objectFit: p.photo.cutout ? "contain" : "cover", background: p.palette.surface }} />
      ) : (
        <div style={{ position: "absolute", left: 0, top: 0, width: d.W, height: photoH, background: `linear-gradient(140deg, ${p.palette.accent}, ${p.palette.surface})` }} />
      )}
      <div style={{ position: "absolute", left: 0, right: 0, top: photoH - 6, height: 12 * d.u, background: p.palette.accent }} />
      <Logo d={d} p={p} />
      <Column d={d} style={{ left: d.pad, width: textW, top: photoH + 60 * d.u, bottom: d.bottom }}>
        <Headline text={c.headline} width={textW} maxLines={3} maxSize={110 * d.u} p={p} />
        <Body text={c.subline} size={34 * d.u} p={p} />
        <div style={{ flex: 1 }} />
        <Cta text={c.cta} d={d} p={p} />
      </Column>
    </AbsoluteFill>
  );
};

const OfferBurst: T = ({ p, d }) => {
  const c = p.content;
  const R = (d.landscape ? 0.36 : 0.62) * Math.min(d.W, d.H) / 2;
  const cx = d.landscape ? d.W * 0.75 : d.W / 2;
  const cy = d.landscape || d.story ? d.H / 2 : d.top + 330 * d.u + R;
  const points = Array.from({ length: 32 }, (_, i) => {
    const a = (i / 32) * Math.PI * 2;
    const r = i % 2 ? R * 0.86 : R;
    return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`;
  }).join(" ");
  const textW = d.landscape ? d.W * 0.46 : d.W - 2 * d.pad;
  return (
    <AbsoluteFill>
      <Background p={p} d={d} scrim="none" />
      <svg width={d.W} height={d.H} style={{ position: "absolute" }}>
        <polygon points={points} fill={p.palette.accent} />
      </svg>
      <div style={{ position: "absolute", left: cx - R * 0.75, top: cy - R * 0.5, width: R * 1.5, height: R, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
        <Headline text={c.price || c.badge || "OFFER"} width={R * 1.4} maxLines={1} maxSize={R * 0.62} p={p} align="center" color={p.palette.accentText} />
        {c.oldPrice && <div style={{ fontFamily: FONTS[p.fontPair].body, fontSize: R * 0.14, color: p.palette.accentText, opacity: 0.75, textDecoration: "line-through" }}>{c.oldPrice}</div>}
      </div>
      <Logo d={d} p={p} />
      {d.landscape ? (
        <Column d={d} style={{ left: d.pad, top: d.pad + 80 * d.u, width: textW, bottom: d.pad, justifyContent: "center" }}>
          <Headline text={c.headline} width={textW} maxLines={3} maxSize={100 * d.u} p={p} />
          <Body text={c.subline} size={30 * d.u} p={p} />
          <Cta text={c.cta} d={d} p={p} />
        </Column>
      ) : (
        <>
          <Column d={d} style={{ left: d.pad, width: textW, top: d.top + 100 * d.u }}>
            <Headline text={c.headline} width={textW} maxLines={2} maxSize={104 * d.u} p={p} align="center" />
          </Column>
          <Column d={d} style={{ left: d.pad, width: textW, bottom: d.bottom, alignItems: "center" }}>
            <Body text={c.subline} size={34 * d.u} p={p} align="center" />
            <div style={{ display: "flex", justifyContent: "center", width: "100%" }}>
              <Cta text={c.cta} d={d} p={p} />
            </div>
          </Column>
        </>
      )}
      {p.photo?.cutout && !d.landscape && <Product p={p} d={d} box={{ left: cx + R * 0.35, top: cy + R * 0.3, width: R * 0.95, height: R * 0.95 }} />}
    </AbsoluteFill>
  );
};

const Testimonial: T = ({ p, d }) => {
  const c = p.content;
  const w = d.W - 2 * d.pad;
  const f = FONTS[p.fontPair];
  return (
    <AbsoluteFill>
      <Background p={p} d={d} scrim="bottom" />
      <Logo d={d} p={p} />
      <Column d={d} style={{ left: d.pad, width: w, top: d.top + 90 * d.u, bottom: d.bottom, justifyContent: "center" }}>
        <div style={{ fontFamily: '"DM Serif Display", serif', fontSize: 260 * d.u, lineHeight: 0.6, color: p.palette.accent, height: 120 * d.u }}>“</div>
        <Headline text={c.quote || c.headline} width={w} maxLines={d.landscape ? 4 : 6} maxSize={(d.landscape ? 70 : 92) * d.u}
          p={{ ...p, fontPair: p.fontPair === "bold_condensed" ? "modern" : p.fontPair }} maxHeight={(d.H - d.top - d.bottom) * 0.55} />
        <div style={{ display: "flex", alignItems: "center", gap: 20 * d.u, marginTop: 10 * d.u }}>
          {p.photo && <Img src={staticFile(p.photo.src)} style={{ width: 96 * d.u, height: 96 * d.u, borderRadius: 999, objectFit: "cover", border: `${4 * d.u}px solid ${p.palette.accent}` }} />}
          <div>
            <div style={{ fontFamily: f.body, fontWeight: 800, fontSize: 34 * d.u, color: p.palette.text }}>{c.author}</div>
            <div style={{ fontSize: 34 * d.u, color: p.palette.accent, letterSpacing: 4 }}>★★★★★</div>
          </div>
        </div>
      </Column>
    </AbsoluteFill>
  );
};

const ListSteps: T = ({ p, d }) => {
  const c = p.content;
  const w = d.landscape ? d.W * 0.9 : d.W - 2 * d.pad;
  const f = FONTS[p.fontPair];
  const pts = c.points.slice(0, 4);
  return (
    <AbsoluteFill>
      <Background p={p} d={d} scrim="bottom" />
      <Logo d={d} p={p} />
      <Column d={d} style={{ left: d.pad, width: w, top: d.top + 100 * d.u, bottom: d.bottom }}>
        <Headline text={c.headline} width={w} maxLines={2} maxSize={(d.landscape ? 80 : 100) * d.u} p={p} />
        <div style={{ display: "flex", flexDirection: d.landscape ? "row" : "column", gap: 22 * d.u, marginTop: 16 * d.u }}>
          {pts.map((t, i) => (
            <div key={i} style={{ flex: d.landscape ? 1 : undefined, display: "flex", alignItems: "center", gap: 24 * d.u, background: p.palette.surface, borderRadius: 28 * d.u, padding: `${24 * d.u}px ${28 * d.u}px` }}>
              <div style={{ flexShrink: 0, width: 72 * d.u, height: 72 * d.u, borderRadius: 999, background: p.palette.accent, color: p.palette.accentText, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: f.head, fontWeight: f.headWeight, fontSize: 38 * d.u }}>
                {i + 1}
              </div>
              <div style={{ fontFamily: f.body, fontWeight: 600, fontSize: (d.landscape ? 28 : 40) * d.u, color: p.palette.text, lineHeight: 1.25 }}>{t}</div>
            </div>
          ))}
        </div>
        <div style={{ flex: 1 }} />
        <Cta text={c.cta} d={d} p={p} />
      </Column>
    </AbsoluteFill>
  );
};

const EventPoster: T = ({ p, d }) => {
  const c = p.content;
  const w = d.W - 2 * d.pad;
  const f = FONTS[p.fontPair];
  return (
    <AbsoluteFill>
      <Background p={p} d={d} scrim="bottom" />
      <Logo d={d} p={p} />
      <Column d={d} style={{ left: d.pad, width: w, top: d.top + 100 * d.u, bottom: d.bottom, justifyContent: "flex-end" }}>
        {c.eventDate && (
          <div style={{ alignSelf: "flex-start", fontFamily: f.body, fontWeight: 800, fontSize: 40 * d.u, color: p.palette.accentText, background: p.palette.accent, borderRadius: 16 * d.u, padding: `${12 * d.u}px ${26 * d.u}px` }}>
            {c.eventDate}
          </div>
        )}
        <Headline text={c.headline} width={w} maxLines={d.landscape ? 2 : 4} maxSize={(d.landscape ? 120 : 170) * d.u} p={p}
          maxHeight={(d.H - d.top - d.bottom) * 0.5} />
        <Body text={c.subline} size={36 * d.u} p={p} />
        {c.eventPlace && <Body text={`📍 ${c.eventPlace}`} size={34 * d.u} p={p} weight={600} opacity={1} />}
        <Cta text={c.cta} d={d} p={p} />
      </Column>
    </AbsoluteFill>
  );
};

const Announcement: T = ({ p, d }) => {
  const c = p.content;
  const w = d.landscape ? d.W * 0.5 : d.W - 2 * d.pad;
  const f = FONTS[p.fontPair];
  const hasProduct = !!p.photo;
  return (
    <AbsoluteFill>
      <Background p={p} d={d} scrim={d.landscape ? "left" : "bottom"} />
      <Logo d={d} p={p} />
      {hasProduct &&
        (d.landscape ? (
          <Product p={p} d={d} box={{ right: d.pad, top: d.pad, width: d.W * 0.4, height: d.H - 2 * d.pad }} />
        ) : (
          <Product p={p} d={d} box={{ left: d.pad * 2, right: d.pad * 2, top: d.top + 90 * d.u, height: d.H * (d.story ? 0.36 : 0.4) }} />
        ))}
      <Column d={d} style={{ left: d.pad, width: w, bottom: d.bottom, ...(d.landscape ? { top: d.pad + 80 * d.u, justifyContent: "center" } : {}) }}>
        <div style={{ alignSelf: "flex-start", fontFamily: f.body, fontWeight: 800, fontSize: 32 * d.u, letterSpacing: 3, color: p.palette.accent, border: `${3 * d.u}px solid ${p.palette.accent}`, borderRadius: 999, padding: `${8 * d.u}px ${22 * d.u}px` }}>
          {(c.badge || "NEW").toUpperCase()}
        </div>
        <Headline text={c.headline} width={w} maxLines={3} maxSize={(d.landscape ? 96 : 120) * d.u} p={p} />
        <Body text={c.subline} size={34 * d.u} p={p} />
        <Features d={d} p={p} />
        <Cta text={c.cta} d={d} p={p} />
      </Column>
    </AbsoluteFill>
  );
};

export const TEMPLATES: Record<DesignProps["template"], T> = {
  hero_product: HeroProduct,
  big_statement: BigStatement,
  split_photo: SplitPhoto,
  offer_burst: OfferBurst,
  testimonial: Testimonial,
  list_steps: ListSteps,
  event: EventPoster,
  announcement: Announcement,
};
