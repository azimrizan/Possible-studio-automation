"""
Rendering: prepares each variant's extras (person cut-outs, sound effects), runs the Remotion job
runner (apps/reel-renderer/render-job.mjs: one bundle for every variant), then finishes the audio
(high-pass + Instagram loudness, -14 LUFS).

Inputs live in a per-project public dir the composition reads with staticFile(); nothing is served
over HTTP during rendering.
"""
import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .masks import make_cutouts
from .media import MediaError, _run
from .sfx import render_sfx
from .timeline import mask_requests

RENDERER_DIR = Path(__file__).resolve().parents[2] / "reel-renderer"
NODE = os.getenv("NODE_BIN", "node")


class RenderError(RuntimeError):
    pass


def renderer_ready() -> bool:
    return (RENDERER_DIR / "node_modules" / "@remotion" / "renderer").exists()


def stage_inputs(public_dir: Path, files: Dict[str, Path]) -> None:
    """Hard-link (or copy) each source video into the render's public dir under its plan name."""
    public_dir.mkdir(parents=True, exist_ok=True)
    for name, src in files.items():
        dst = public_dir / name
        if dst.exists():
            dst.unlink()
        try:
            os.link(src, dst)
        except OSError:
            shutil.copyfile(src, dst)


async def prepare_variant(public_dir: Path, variant: Dict[str, Any], with_sfx: bool = True) -> Dict[str, Any]:
    """Cut-outs for backtext beats and the sound-effects track; returns render props."""
    props = dict(variant["props"])
    props["masks"] = []
    for src, frames in mask_requests(variant).items():
        stem = src.rsplit(".", 1)[0]
        done = await make_cutouts(public_dir / src, frames, public_dir / "masks" / stem)
        if done:
            props["masks"].append({"src": src, "dir": f"masks/{stem}", "frames": done})
    props["sfx"] = None
    if with_sfx:
        name = f"sfx_{variant['index']}.wav"
        if await asyncio.to_thread(render_sfx, variant["sfx_events"], props["durationInFrames"], public_dir / name):
            props["sfx"] = name
    return props


async def run_job(work: Path, public_dir: Path, tasks: List[Dict[str, Any]],
                  on_progress: Optional[Callable[[str], None]] = None, timeout: float = 3600) -> None:
    if not renderer_ready():
        raise RenderError("The renderer isn't installed. Run: npm --prefix apps/reel-renderer install")
    job = work / "render_job.json"
    job.write_text(json.dumps({"publicDir": str(public_dir), "tasks": tasks}))
    proc = await asyncio.create_subprocess_exec(
        NODE, str(RENDERER_DIR / "render-job.mjs"), str(job), cwd=str(RENDERER_DIR),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )

    async def read_progress():
        assert proc.stdout
        async for line in proc.stdout:
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if on_progress and "progress" in msg:
                on_progress(f"{Path(msg['out']).stem.replace('_', ' ')}: {msg['progress']}%")

    try:
        _, err = await asyncio.wait_for(asyncio.gather(read_progress(), proc.stderr.read()), timeout=timeout)  # type: ignore
        await proc.wait()
    except asyncio.TimeoutError:
        proc.kill()
        raise RenderError("Rendering timed out")
    if proc.returncode != 0:
        tail = err.decode("utf-8", "replace").strip().splitlines()[-6:]
        raise RenderError("Render failed: " + " | ".join(tail)[:600])


async def finish_audio(src: Path, dst: Path) -> None:
    """Rumble filter + loudness to Instagram's -14 LUFS; video is copied untouched."""
    code, err = await _run("-y", "-i", str(src), "-c:v", "copy",
                           "-af", "highpass=f=70,loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(dst))
    if code != 0:
        raise MediaError("Could not finish the audio: " + err.strip().splitlines()[-1][:200])


def cover_frame(props: Dict[str, Any]) -> int:
    """The moment the hook text has fully landed (or 1 s in when there is no hook text)."""
    hook_end = props["hook"]["endFrame"]
    return min(props["durationInFrames"] - 1, max(15, hook_end - 10) if hook_end else 30)


def contact_sheet(paths: List[Path], labels: List[str], out: Path, cols: int = 3, width: int = 300) -> Path:
    """Labelled grid of test frames: one image for Claude to review instead of six."""
    from PIL import Image, ImageDraw

    thumbs = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        thumbs.append(im.resize((width, int(im.height * width / im.width))))
    h = max(t.height for t in thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * width + (cols + 1) * 8, rows * (h + 28) + 8), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    for i, (im, label) in enumerate(zip(thumbs, labels)):
        x, y = 8 + (i % cols) * (width + 8), 8 + (i // cols) * (h + 28)
        sheet.paste(im, (x, y + 20))
        draw.text((x, y + 4), label, fill=(240, 240, 240))
    sheet.save(out, quality=85)
    return out
