import React from "react";
import { CalculateMetadataFunction, Composition } from "remotion";
import { ReelEdit } from "./ReelEdit";
import { Design } from "./design/Design";
import { DesignProps } from "./design/types";
import { ReelProps } from "./types";

const defaultProps: ReelProps = {
  fps: 30,
  width: 1080,
  height: 1920,
  durationInFrames: 90,
  clips: [],
  words: [],
  hook: { text: "", accentWords: [], endFrame: 0 },
  title: null,
  subtitlePosition: "lower",
  beats: [],
  punches: [],
  grade: "none",
  accent: "#F5C451",
  sfx: null,
  masks: [],
};

// Size and length come from the edit plan, so every variant renders at its own duration.
const calculateMetadata: CalculateMetadataFunction<ReelProps> = ({ props }) => ({
  durationInFrames: Math.max(1, props.durationInFrames),
  fps: props.fps,
  width: props.width,
  height: props.height,
});

const designDefaults: DesignProps = {
  width: 1080,
  height: 1080,
  template: "big_statement",
  fontPair: "modern",
  palette: { bg: "#111111", surface: "#222222", text: "#FFFFFF", accent: "#F5C451", accentText: "#111111" },
  bgStyle: "solid",
  decoration: "circles",
  content: { headline: "Your *headline* here", subline: "", cta: "", price: "", oldPrice: "", badge: "", points: [], features: [], quote: "", author: "", eventDate: "", eventPlace: "", brandName: "" },
  photo: null,
  plate: null,
  logo: null,
};

const designMetadata: CalculateMetadataFunction<DesignProps> = ({ props }) => ({
  durationInFrames: 1,
  fps: 30,
  width: props.width,
  height: props.height,
});

export const Root: React.FC = () => (
  <>
  <Composition
    id="Design"
    component={Design}
    defaultProps={designDefaults}
    calculateMetadata={designMetadata}
    durationInFrames={1}
    fps={30}
    width={1080}
    height={1080}
  />
  <Composition
    id="ReelEdit"
    component={ReelEdit}
    defaultProps={defaultProps}
    calculateMetadata={calculateMetadata}
    durationInFrames={90}
    fps={30}
    width={1080}
    height={1920}
  />
  </>
);
