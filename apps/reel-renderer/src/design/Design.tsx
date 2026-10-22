import React from "react";
import { AbsoluteFill, cancelRender, continueRender, delayRender } from "remotion";
import { FONT_LOADS } from "./fonts";
import { dims } from "./parts";
import { TEMPLATES } from "./templates";
import { DesignProps } from "./types";

// Headlines are measured with the real fonts, so nothing renders until every font (incl. Malayalam) is loaded.
const FontGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [handle] = React.useState(() => delayRender("Loading fonts"));
  const [ready, setReady] = React.useState(false);
  React.useEffect(() => {
    Promise.all(FONT_LOADS.map((f) => document.fonts.load(f, "Aa മലയാളം 0123")))
      .then(() => document.fonts.ready)
      .then(() => {
        setReady(true);
        continueRender(handle);
      })
      .catch((err) => cancelRender(err));
  }, [handle]);
  return ready ? <>{children}</> : null;
};

export const Design: React.FC<DesignProps> = (props) => {
  const Template = TEMPLATES[props.template] || TEMPLATES.big_statement;
  return (
    <AbsoluteFill style={{ background: props.palette.bg, overflow: "hidden" }}>
      <FontGate>
        <Template p={props} d={dims(props.width, props.height)} />
      </FontGate>
    </AbsoluteFill>
  );
};
