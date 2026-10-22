import React from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BackText, BeforeAfter, CtaComment, Counter, FONT, List, SHADOW, StatementCard } from "./Beats";
import { Beat, Clip, ReelProps, Word } from "./types";

const PHRASE_MAX_WORDS = 4;
const PHRASE_GAP_FRAMES = 9;
const HOLD_FRAMES = 6;
const SPLIT_TYPES = new Set(["counter", "list", "before_after", "cta_comment"]);
// Face card for split screens: x, y, w, h, radius. The video inside is scaled to the card width and
// shifted so the upper-middle of the frame (where a seated speaker's face is) stays in view.
const CARD = { x: 24, y: 24, w: 1032, h: 1100, r: 40 };
const SPLIT_SCALE = CARD.w / 1080;
const SPLIT_SHIFT = -170;
const GRADES: Record<ReelProps["grade"], string> = {
  none: "none",
  natural: "contrast(1.05) saturate(1.06)",
  cinematic: "contrast(1.12) saturate(1.08) brightness(0.98) sepia(0.06)",
};

type Phrase = { words: Word[]; start: number; end: number };

function toPhrases(words: Word[]): Phrase[] {
  const phrases: Phrase[] = [];
  for (const w of words) {
    const last = phrases[phrases.length - 1];
    const prev = last?.words[last.words.length - 1];
    const breakHere =
      !last || last.words.length >= PHRASE_MAX_WORDS || w.startFrame - last.end > PHRASE_GAP_FRAMES || /[.!?।]$/.test(prev?.text ?? "");
    if (breakHere) phrases.push({ words: [w], start: w.startFrame, end: w.endFrame });
    else {
      last.words.push(w);
      last.end = w.endFrame;
    }
  }
  return phrases;
}

const activeBeat = (beats: Beat[], frame: number) => beats.find((b) => frame >= b.startFrame && frame < b.endFrame);

// 0 = full face, 1 = split screen; eased in and out at the edges of split beats.
function splitAmount(beats: Beat[], frame: number): number {
  for (const b of beats) {
    if (!SPLIT_TYPES.has(b.type)) continue;
    if (frame >= b.startFrame - 2 && frame < b.endFrame + 6) {
      const inn = interpolate(frame, [b.startFrame - 2, b.startFrame + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
      const out = interpolate(frame, [b.endFrame - 4, b.endFrame + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
      const e = (t: number) => 1 - Math.pow(1 - t, 3);
      return e(inn) * (1 - e(out));
    }
  }
  return 0;
}

const Subtitles: React.FC<{ words: Word[]; top: number; size: number; accent: string; opacity: number }> = ({ words, top, size, accent, opacity }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const phrases = React.useMemo(() => toPhrases(words), [words]);
  const current = phrases.find((p, i) => frame >= p.start && frame < Math.min(p.end + HOLD_FRAMES, phrases[i + 1]?.start ?? Infinity));
  if (!current || opacity <= 0) return null;
  return (
    <div style={{ position: "absolute", left: 60, right: 60, top, display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0 18px", opacity }}>
      {current.words.map((w) => {
        const active = frame >= w.startFrame && frame < w.endFrame + 2;
        const shown = frame >= w.startFrame;
        const pop = spring({ frame: frame - w.startFrame, fps, config: { damping: 14, stiffness: 220 }, durationInFrames: 8 });
        return (
          <span
            key={w.id}
            style={{
              fontFamily: FONT,
              fontWeight: 800,
              fontSize: size,
              lineHeight: 1.15,
              color: w.emphasis ? accent : "#FFFFFF",
              opacity: shown ? (active || w.emphasis ? 1 : 0.85) : 0.35,
              transform: `scale(${shown ? 0.92 + 0.08 * pop + (active ? 0.04 : 0) : 0.92})`,
              textShadow: SHADOW,
              display: "inline-block",
            }}
          >
            {w.text}
          </span>
        );
      })}
    </div>
  );
};

const HookText: React.FC<{ text: string; accentWords: string[]; accent: string }> = ({ text, accentWords, accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const accents = new Set(accentWords.map((a) => a.toLowerCase()));
  const tokens = text.split(/\s+/).filter(Boolean);
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 230 }}>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0 22px", maxWidth: 940 }}>
        {tokens.map((t, i) => {
          const s = spring({ frame: frame - i * 2, fps, config: { damping: 12, stiffness: 180 } });
          const accent_ = accents.has(t.toLowerCase().replace(/[^\p{L}\p{N}]/gu, ""));
          return (
            <span
              key={i}
              style={{
                fontFamily: FONT,
                fontWeight: 900,
                fontSize: accent_ ? 128 : 96,
                lineHeight: 1.05,
                color: accent_ ? accent : "#FFFFFF",
                textShadow: SHADOW,
                transform: `translateY(${(1 - s) * 40}px)`,
                opacity: s,
                display: "inline-block",
              }}
            >
              {t}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Title: React.FC<{ text: string; duration: number }> = ({ text, duration }) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, duration], [0.9, 1.08]);
  const opacity = interpolate(frame, [0, 6, duration - 8, duration], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: 500 }}>
      <div style={{ fontFamily: 'Georgia, "Times New Roman", serif', fontSize: 170, color: "#F7EEDD", letterSpacing: 4, textShadow: SHADOW, transform: `scale(${scale})`, opacity, textAlign: "center", padding: "0 40px" }}>
        {text}
      </div>
    </AbsoluteFill>
  );
};

// The speaker: clips with per-cut zoom, push-ins, colour grade, and (for backtext) the giant word sandwiched
// between the video and a cut-out of the person.
const Speaker: React.FC<{ props: ReelProps }> = ({ props }) => {
  const frame = useCurrentFrame();
  const { clips, punches, beats, masks, accent, grade } = props;
  const clip: Clip | undefined = clips.find((c) => frame >= c.from && frame < c.from + c.endFrame - c.startFrame);
  const punch = punches.find((p) => frame >= p.startFrame && frame < p.endFrame);
  const punchZoom = punch
    ? interpolate(frame, [punch.startFrame, punch.startFrame + 4, punch.endFrame - 4, punch.endFrame], [0, 0.06, 0.06, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0;
  const zoom = (clip?.zoom ?? 1) + punchZoom;
  const back = beats.find((b) => b.type === "backtext" && frame >= b.startFrame && frame < b.endFrame);
  const srcFrame = clip ? clip.startFrame + frame - clip.from : -1;
  const mask = back && clip ? masks.find((m) => m.src === clip.src) : undefined;
  const cutout = mask && mask.frames.includes(srcFrame) ? staticFile(`${mask.dir}/${srcFrame}.webp`) : null;

  return (
    <AbsoluteFill style={{ transform: `scale(${zoom})`, transformOrigin: "50% 40%", filter: GRADES[grade] }}>
      {clips.map((c, i) => (
        <Sequence key={i} from={c.from} durationInFrames={c.endFrame - c.startFrame} layout="none">
          <OffthreadVideo src={staticFile(c.src)} trimBefore={c.startFrame} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover" }} />
        </Sequence>
      ))}
      {back && <BackText b={back} accent={accent} />}
      {cutout && <Img src={cutout} style={{ position: "absolute", width: "100%", height: "100%" }} />}
      {grade === "cinematic" && <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.45) 100%)" }} />}
    </AbsoluteFill>
  );
};

export const ReelEdit: React.FC<ReelProps> = (props) => {
  const { words, hook, title, subtitlePosition, beats, accent, sfx } = props;
  const frame = useCurrentFrame();
  const split = splitAmount(beats, frame);
  const beat = activeBeat(beats, frame);
  const onCard = beat?.type === "statement_card";

  // Interpolate the speaker between full frame and the split-screen face card.
  const x = CARD.x * split, y = CARD.y * split;
  const w = 1080 + (CARD.w - 1080) * split, h = 1920 + (CARD.h - 1920) * split;
  const scale = 1 + (SPLIT_SCALE - 1) * split;
  const shift = SPLIT_SHIFT * split;

  // Captions follow the layout: full face -> chosen height; split -> just under the face card; card -> hidden.
  const fullTop = subtitlePosition === "upper" ? 1920 * 0.18 : subtitlePosition === "middle" ? 1920 * 0.46 : 1920 * 0.68;
  const capTop = fullTop + (1140 - fullTop) * split;
  const capSize = 84 - 20 * split;
  // While the hook text is on screen, captions for that stretch are hidden so the two never overlap.
  const subtitleWords = hook.text ? words.filter((wd) => wd.startFrame >= hook.endFrame) : words;

  return (
    <AbsoluteFill style={{ background: "radial-gradient(120% 70% at 50% 80%, #1d1d22 0%, #0a0a0c 70%)" }}>
      <div style={{ position: "absolute", left: x, top: y, width: w, height: h, borderRadius: CARD.r * split, overflow: "hidden", boxShadow: split ? "0 24px 60px rgba(0,0,0,0.5)" : "none" }}>
        <div style={{ position: "absolute", left: 0, top: shift, width: 1080, height: 1920, transform: `scale(${scale})`, transformOrigin: "0 0" }}>
          <Speaker props={props} />
        </div>
      </div>
      {split === 0 && <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.35) 0%, rgba(0,0,0,0) 26%, rgba(0,0,0,0) 62%, rgba(0,0,0,0.35) 100%)" }} />}

      {beats.map((b, i) =>
        b.type === "backtext" ? null : (
          <Sequence key={i} from={0} durationInFrames={props.durationInFrames} layout="none">
            {frame >= b.startFrame - 2 && frame < b.endFrame + 2 && (
              <>
                {b.type === "statement_card" && <StatementCard b={b} accent={accent} />}
                {b.type === "counter" && <Counter b={b} accent={accent} />}
                {b.type === "list" && <List b={b} accent={accent} />}
                {b.type === "before_after" && <BeforeAfter b={b} accent={accent} />}
                {b.type === "cta_comment" && <CtaComment b={b} accent={accent} />}
              </>
            )}
          </Sequence>
        ),
      )}

      <Subtitles words={subtitleWords} top={capTop} size={capSize} accent={accent} opacity={onCard ? 0 : 1} />
      {title && (
        <Sequence from={title.startFrame} durationInFrames={Math.max(1, title.endFrame - title.startFrame)}>
          <Title text={title.text} duration={title.endFrame - title.startFrame} />
        </Sequence>
      )}
      {hook.text && hook.endFrame > 0 && (
        <Sequence from={0} durationInFrames={hook.endFrame}>
          <HookText text={hook.text} accentWords={hook.accentWords} accent={accent} />
        </Sequence>
      )}
      {sfx && <Audio src={staticFile(sfx)} />}
    </AbsoluteFill>
  );
};
