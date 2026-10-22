// Renders one job for the API: bundle the composition once, then render every task in it.
//   node render-job.mjs <job.json>
// job = { publicDir, tasks: [
//   { kind: "video",  props, out, cover: { frame, out } },
//   { kind: "stills", props, frames: [..], outPattern: "/dir/still_{frame}.jpg" },
//   { kind: "still", composition: "Design", props, out: "/dir/design.png" } ]
// Tasks use the ReelEdit composition unless they name another.
// Prints one JSON line per finished task, then {"done":true}.
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const job = JSON.parse(readFileSync(process.argv[2], "utf8"));
const serveUrl = await bundle({ entryPoint: path.join(here, "src/index.ts"), publicDir: job.publicDir });
const log = (o) => process.stdout.write(JSON.stringify(o) + "\n");

for (const task of job.tasks) {
  const composition = await selectComposition({ serveUrl, id: task.composition || "ReelEdit", inputProps: task.props, logLevel: "error" });
  if (task.kind === "still") {
    const imageFormat = task.out.endsWith(".png") ? "png" : "jpeg";
    await renderStill({ serveUrl, composition, inputProps: task.props, frame: 0, output: task.out, imageFormat,
      ...(imageFormat === "jpeg" ? { jpegQuality: 92 } : {}), logLevel: "error" });
    log({ done: task.out });
  } else if (task.kind === "video") {
    let last = -1;
    await renderMedia({
      serveUrl, composition, inputProps: task.props, codec: "h264", crf: 20, pixelFormat: "yuv420p",
      outputLocation: task.out, logLevel: "error",
      onProgress: ({ progress }) => {
        const pct = Math.floor(progress * 10) * 10;
        if (pct !== last) { last = pct; log({ progress: pct, out: task.out }); }
      },
    });
    if (task.cover) {
      await renderStill({ serveUrl, composition, inputProps: task.props, frame: task.cover.frame, output: task.cover.out, imageFormat: "jpeg", logLevel: "error" });
    }
    log({ done: task.out });
  } else {
    for (const frame of task.frames) {
      const out = task.outPattern.replace("{frame}", String(frame));
      await renderStill({ serveUrl, composition, inputProps: task.props, frame, output: out, imageFormat: "jpeg", logLevel: "error" });
    }
    log({ done: "stills" });
  }
}
log({ done: true });
