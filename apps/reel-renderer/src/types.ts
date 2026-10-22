// Mirrors apps/agent-runtime/reel_studio/timeline.py build_variants() props.
export type Clip = { src: string; startFrame: number; endFrame: number; from: number; zoom: number };
export type Word = { id: string; text: string; emphasis: boolean; startFrame: number; endFrame: number };

export type BeatType = "statement_card" | "counter" | "list" | "before_after" | "cta_comment" | "backtext";
export type Beat = {
  type: BeatType;
  startFrame: number;
  endFrame: number;
  text: string;
  sub: string;
  value: number;
  prefix: string;
  suffix: string;
  items: { text: string; frame: number }[];
  keyword: string;
};

export type ReelProps = {
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  clips: Clip[];
  words: Word[];
  hook: { text: string; accentWords: string[]; endFrame: number };
  title: { text: string; startFrame: number; endFrame: number } | null;
  subtitlePosition: "lower" | "middle" | "upper";
  beats: Beat[];
  punches: { startFrame: number; endFrame: number }[];
  grade: "none" | "natural" | "cinematic";
  accent: string;
  sfx: string | null;
  masks: { src: string; dir: string; frames: number[] }[];
};
