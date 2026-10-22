// Beat graphics. Each one illustrates the words being said and lands on the word (frames come from the plan).
// Panel beats live in the lower part of a split screen (y ~1250-1700, inside Instagram's safe zones).
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Beat } from "./types";

export const FONT = '-apple-system, "Helvetica Neue", "Noto Sans", "Noto Sans Malayalam", "Malayalam Sangam MN", "Noto Sans Devanagari", sans-serif';
export const SHADOW = "0 4px 18px rgba(0,0,0,0.55), 0 2px 4px rgba(0,0,0,0.6)";
export const PANEL_TOP = 1250;

const ease = (f: number, start: number, dur: number) =>
  interpolate(f, [start, start + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: (t) => 1 - Math.pow(1 - t, 3) });

const usePop = (start: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - start, fps, config: { damping: 11, stiffness: 190 } });
  return { scale: frame < start ? 0.6 : 0.6 + 0.4 * s, opacity: frame < start ? 0 : Math.min(1, s * 1.4) };
};

// Fades a panel beat in after the layout has moved and out before it moves back.
const usePanelIn = (b: Beat) => {
  const frame = useCurrentFrame();
  return Math.min(ease(frame, b.startFrame + 4, 8), 1 - ease(frame, b.endFrame - 8, 6));
};

const Panel: React.FC<{ b: Beat; children: React.ReactNode }> = ({ b, children }) => {
  const o = usePanelIn(b);
  return (
    <AbsoluteFill style={{ opacity: o, transform: `translateY(${(1 - o) * 30}px)` }}>
      <div style={{ position: "absolute", left: 60, right: 150, top: PANEL_TOP, height: 450 }}>{children}</div>
    </AbsoluteFill>
  );
};

const label: React.CSSProperties = { fontFamily: FONT, fontWeight: 700, fontSize: 40, color: "rgba(255,255,255,0.7)", letterSpacing: 1 };

export const StatementCard: React.FC<{ b: Beat; accent: string }> = ({ b, accent }) => {
  const frame = useCurrentFrame();
  const e = ease(frame, b.startFrame, 10);
  const out = ease(frame, b.endFrame - 7, 7);
  const sub = usePop(b.startFrame + 10);
  return (
    <AbsoluteFill
      style={{
        backgroundColor: accent,
        backgroundImage: "radial-gradient(120% 80% at 30% 15%, rgba(255,255,255,0.25) 0%, rgba(0,0,0,0) 50%, rgba(0,0,0,0.35) 110%)",
        opacity: e * (1 - out),
        transform: `scale(${1.06 - 0.06 * e})`,
        justifyContent: "center",
        padding: "0 90px",
      }}
    >
      <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: 132, lineHeight: 1.02, color: "#0B0B0B", letterSpacing: -2 }}>{b.text}</div>
      {b.sub && (
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 52, color: "#0B0B0B", opacity: 0.75 * sub.opacity, marginTop: 30, transform: `scale(${sub.scale})`, transformOrigin: "left" }}>
          {b.sub}
        </div>
      )}
    </AbsoluteFill>
  );
};

export const Counter: React.FC<{ b: Beat; accent: string }> = ({ b, accent }) => {
  const frame = useCurrentFrame();
  const p = ease(frame, b.startFrame + 9, 20);
  const decimals = Number.isInteger(b.value) ? 0 : 1;
  const shown = (b.value * p).toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return (
    <Panel b={b}>
      <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: 200, lineHeight: 1, color: accent, textShadow: `0 0 40px ${accent}55` }}>
        {b.prefix}
        {shown}
        {b.suffix}
      </div>
      {b.text && <div style={{ ...label, marginTop: 24, fontSize: 52, color: "#fff" }}>{b.text}</div>}
    </Panel>
  );
};

const ListItem: React.FC<{ text: string; frame: number; accent: string; i: number }> = ({ text, frame, accent, i }) => {
  const p = usePop(frame);
  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 22, marginBottom: 22, opacity: p.opacity, transform: `scale(${p.scale})`, transformOrigin: "left",
        background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.14)", borderRadius: 26, padding: "18px 28px",
      }}
    >
      <span style={{ fontFamily: FONT, fontWeight: 900, fontSize: 40, color: "#0B0B0B", background: accent, borderRadius: 999, width: 58, height: 58, display: "flex", alignItems: "center", justifyContent: "center" }}>
        {i + 1}
      </span>
      <span style={{ fontFamily: FONT, fontWeight: 800, fontSize: 54, color: "#fff" }}>{text}</span>
    </div>
  );
};

export const List: React.FC<{ b: Beat; accent: string }> = ({ b, accent }) => (
  <Panel b={b}>
    {b.text && <div style={{ ...label, marginBottom: 18 }}>{b.text}</div>}
    {b.items.map((it, i) => (
      <ListItem key={i} text={it.text} frame={it.frame} accent={accent} i={i} />
    ))}
  </Panel>
);

export const BeforeAfter: React.FC<{ b: Beat; accent: string }> = ({ b, accent }) => {
  const frame = useCurrentFrame();
  const strike = ease(frame, b.startFrame + 16, 10);
  const after = usePop(b.startFrame + 26);
  return (
    <Panel b={b}>
      <div style={{ position: "relative", display: "inline-block", fontFamily: FONT, fontWeight: 800, fontSize: 64, color: "rgba(255,255,255,0.6)" }}>
        {b.text}
        <div style={{ position: "absolute", left: -8, top: "52%", height: 9, borderRadius: 9, background: "#FF4D4D", width: `calc(${strike * 100}% + 16px)` }} />
      </div>
      <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: 84, color: accent, marginTop: 40, opacity: after.opacity, transform: `scale(${after.scale})`, transformOrigin: "left" }}>
        {b.sub}
      </div>
    </Panel>
  );
};

export const CtaComment: React.FC<{ b: Beat; accent: string }> = ({ b, accent }) => {
  const frame = useCurrentFrame();
  const typed = Math.max(0, Math.min(b.keyword.length, Math.floor((frame - b.startFrame - 12) / 3)));
  const sent = frame > b.startFrame + 14 + b.keyword.length * 3 + 10;
  const caret = Math.floor(frame / 15) % 2 === 0;
  return (
    <Panel b={b}>
      {b.text && <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 56, color: "#fff", marginBottom: 26 }}>{b.text}</div>}
      <div style={{ background: "#fff", borderRadius: 28, padding: "26px 30px", display: "flex", alignItems: "center", gap: 20, boxShadow: "0 20px 50px rgba(0,0,0,0.45)" }}>
        <div style={{ width: 64, height: 64, borderRadius: 999, background: `linear-gradient(135deg, ${accent}, #7B5CFF)` }} />
        <div style={{ flex: 1, fontFamily: FONT, fontWeight: 700, fontSize: 50, color: typed ? "#111" : "#999" }}>
          {typed ? b.keyword.slice(0, typed) : "Add a comment…"}
          {!sent && caret && <span style={{ color: "#111" }}>|</span>}
        </div>
        <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 44, color: sent ? "#3B82F6" : "#9DB8F5" }}>Post</div>
      </div>
    </Panel>
  );
};

export const BackText: React.FC<{ b: Beat; accent: string }> = ({ b, accent }) => {
  const frame = useCurrentFrame();
  const e = ease(frame, b.startFrame, 10);
  const out = ease(frame, b.endFrame - 8, 8);
  const glow = 0.4 + 0.6 * Math.abs(Math.sin((frame - b.startFrame) / 9));
  const size = b.text.length > 7 ? 230 : 300;
  return (
    <AbsoluteFill style={{ alignItems: "center" }}>
      <div
        style={{
          position: "absolute", top: 520, width: "100%", textAlign: "center", fontFamily: FONT, fontWeight: 900, fontSize: size,
          letterSpacing: -6, lineHeight: 1, color: accent, opacity: e * (1 - out), transform: `scale(${0.92 + 0.08 * e})`,
          textShadow: `0 0 ${30 + 40 * glow}px ${accent}88`,
        }}
      >
        {b.text}
      </div>
    </AbsoluteFill>
  );
};
