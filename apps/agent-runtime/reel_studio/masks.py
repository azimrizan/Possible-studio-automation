"""
Person cut-outs for "big text behind the speaker's head" (backtext beats).

Uses the open U^2-Net human-segmentation model (onnxruntime, CPU). Only the source frames that a
backtext beat covers are processed (~0.3-0.6 s per frame), and each cut-out is written as an RGBA
WebP the renderer layers on top of the text.
"""
import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

import numpy as np

from .media import _run
from .transcribe_local import MODELS_DIR

MODEL = MODELS_DIR / "seg" / "u2net_human_seg.onnx"
SIZE = 320
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def masks_available() -> bool:
    return MODEL.exists()


@lru_cache(maxsize=1)
def _session():
    import onnxruntime as ort

    return ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])


def _alpha(rgb: np.ndarray) -> np.ndarray:
    from PIL import Image

    h, w = rgb.shape[:2]
    small = np.asarray(Image.fromarray(rgb).resize((SIZE, SIZE), Image.BILINEAR), dtype=np.float32)
    x = (small / max(small.max(), 1.0) - MEAN) / STD
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    sess = _session()
    pred = sess.run(None, {sess.get_inputs()[0].name: x})[0][0, 0]
    pred = (pred - pred.min()) / max(pred.max() - pred.min(), 1e-6)
    soft = np.clip((pred - 0.35) / 0.3, 0, 1)  # crisp edge, slight feather
    return np.asarray(Image.fromarray((soft * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR))


def _runs(frames: Iterable[int]) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
    for f in sorted(frames):
        if runs and f == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], f)
        else:
            runs.append((f, f))
    return runs


def _cutouts(frames_dir: Path, out_dir: Path, first: int) -> List[int]:
    from PIL import Image

    done = []
    for p in sorted(frames_dir.glob("*.png")):
        idx = first + int(p.stem) - 1
        rgb = np.asarray(Image.open(p).convert("RGB"))
        rgba = np.dstack([rgb, _alpha(rgb)])
        Image.fromarray(rgba, "RGBA").save(out_dir / f"{idx}.webp", quality=88, method=4)
        p.unlink()
        done.append(idx)
    return done


async def make_cutouts(video: Path, frames: Set[int], out_dir: Path, fps: int = 30) -> List[int]:
    """Writes out_dir/<source frame>.webp for each requested frame; returns the frames written."""
    if not frames or not masks_available():
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[int] = []
    for a, b in _runs(f for f in frames if not (out_dir / f"{f}.webp").exists()):
        tmp = out_dir / f"tmp_{a}"
        tmp.mkdir(exist_ok=True)
        # -ss before -i seeks to the frame; -frames:v grabs exactly this run of frames.
        await _run("-y", "-ss", f"{a / fps:.4f}", "-i", str(video), "-frames:v", str(b - a + 1), str(tmp / "%05d.png"))
        written += await asyncio.to_thread(_cutouts, tmp, out_dir, a)
        tmp.rmdir()
    return sorted(set(written) | {f for f in frames if (out_dir / f"{f}.webp").exists()})
