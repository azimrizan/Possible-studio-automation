"""
Product cut-outs (background removal) on this server with the open IS-Net general-use model (onnxruntime, CPU).

Returns an RGBA PNG cropped to the product with a small margin, so templates can place it, add a shadow
and relight it with the background. Photos that already have transparency are kept as they are.
"""
import io
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

from reel_studio.transcribe_local import MODELS_DIR

MODEL = MODELS_DIR / "seg" / "isnet-general-use.onnx"
SIZE = 1024


def cutout_available() -> bool:
    return MODEL.exists()


@lru_cache(maxsize=1)
def _session():
    import onnxruntime as ort

    return ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])


def _has_real_alpha(img) -> bool:
    if img.mode != "RGBA":
        return False
    a = np.asarray(img.getchannel("A"))
    return (a < 250).mean() > 0.02


def cut_out(raw: bytes, max_side: int = 1600) -> Optional[bytes]:
    """PNG bytes of the product on transparency, or None when the model finds nothing usable."""
    from PIL import Image, ImageOps

    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    img.thumbnail((max_side, max_side))
    if _has_real_alpha(img):
        rgba = img.convert("RGBA")
    else:
        if not cutout_available():
            return None
        rgb = img.convert("RGB")
        x = np.asarray(rgb.resize((SIZE, SIZE), Image.BILINEAR), dtype=np.float32)
        x = x / max(x.max(), 1.0) - 0.5
        x = x.transpose(2, 0, 1)[None].astype(np.float32)
        sess = _session()
        pred = sess.run(None, {sess.get_inputs()[0].name: x})[0][0, 0]
        pred = (pred - pred.min()) / max(pred.max() - pred.min(), 1e-6)
        alpha = Image.fromarray((np.clip((pred - 0.25) / 0.5, 0, 1) * 255).astype(np.uint8)).resize(rgb.size, Image.BILINEAR)
        rgba = rgb.copy()
        rgba.putalpha(alpha)
    a = np.asarray(rgba.getchannel("A"))
    ys, xs = np.where(a > 24)
    if len(xs) < 0.01 * a.size:  # nothing that looks like a product
        return None
    m = int(0.03 * max(rgba.size))
    box = (max(0, xs.min() - m), max(0, ys.min() - m), min(rgba.width, xs.max() + m), min(rgba.height, ys.max() + m))
    out = io.BytesIO()
    rgba.crop(box).save(out, "PNG", optimize=True)
    return out.getvalue()


def cut_out_file(src: Path, dst: Path) -> bool:
    data = cut_out(src.read_bytes())
    if data is None:
        return False
    dst.write_bytes(data)
    return True
