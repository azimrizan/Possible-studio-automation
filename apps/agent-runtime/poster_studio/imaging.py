"""Pillow helpers: upload normalisation, downscaling for token-lean vision calls, logo lock."""
import base64
import io
from typing import Tuple

from PIL import Image, ImageDraw, ImageOps, ImageStat

ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}


class InvalidImageError(ValueError):
    pass


def normalise_upload(raw: bytes, max_side: int, keep_alpha: bool) -> Tuple[bytes, str, int, int]:
    """
    Validates and re-encodes an uploaded image: strips EXIF/metadata, applies the
    EXIF orientation, and caps the long edge. Returns (bytes, mime, width, height).
    """
    try:
        img = Image.open(io.BytesIO(raw))
        img_format = img.format
        img.load()
    except Exception:
        raise InvalidImageError("File is not a readable image")
    if img_format not in ALLOWED_FORMATS:
        raise InvalidImageError("Use PNG, JPG or WebP (export SVG logos as PNG)")

    img = ImageOps.exif_transpose(img)
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)

    buf = io.BytesIO()
    if keep_alpha and has_alpha:
        img.convert("RGBA").save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        img.convert("RGB").save(buf, "JPEG", quality=92, optimize=True)
        mime = "image/jpeg"
    return buf.getvalue(), mime, img.width, img.height


def to_data_url(raw: bytes, max_side: int, quality: int = 80) -> str:
    """Downscaled JPEG data URL for Groq vision calls; image tokens scale with resolution."""
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (128, 128, 128))  # neutral grey keeps white and black logos visible
        bg.paste(rgba, mask=rgba.split()[3])
        img = bg
    img = img.convert("RGB")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def to_png(raw: bytes) -> bytes:
    img = Image.open(io.BytesIO(raw))
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _luminance(img: Image.Image, mask=None) -> float:
    stat = ImageStat.Stat(img.convert("L"), mask)
    return stat.mean[0] if stat.count[0] else 128.0


def composite_logo(poster: bytes, logo: bytes, zone: str) -> bytes:
    """
    Deterministic "logo lock": places the exact uploaded logo in the concept's logo zone.
    Used only when QA finds the model-rendered logo missing or distorted. A soft backing
    plate is added when the logo would not contrast with the area under it.
    """
    base = Image.open(io.BytesIO(poster)).convert("RGBA")
    mark = Image.open(io.BytesIO(logo)).convert("RGBA")
    W, H = base.size

    max_w, max_h = int(W * 0.2), int(H * 0.09)
    mark.thumbnail((max_w, max_h), Image.LANCZOS)
    mw, mh = mark.size
    margin = int(W * 0.05)
    pad = int(mh * 0.35)

    x = {"left": margin + pad, "right": W - margin - pad - mw}.get(zone.split("_")[-1], (W - mw) // 2)
    y = margin + pad if zone.startswith("top") else H - margin - pad - mh

    alpha = mark.split()[3]
    logo_lum = _luminance(mark, alpha)
    area_lum = _luminance(base.crop((x, y, x + mw, y + mh)))
    if abs(logo_lum - area_lum) < 70:
        plate_fill = (255, 255, 255, 215) if logo_lum < 128 else (12, 12, 16, 200)
        plate = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ImageDraw.Draw(plate).rounded_rectangle(
            [x - pad, y - pad, x + mw + pad, y + mh + pad], radius=int(pad * 1.2), fill=plate_fill
        )
        base = Image.alpha_composite(base, plate)

    base.alpha_composite(mark, (x, y))
    buf = io.BytesIO()
    base.convert("RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def to_instagram_jpeg(raw: bytes, max_width: int = 1440) -> bytes:
    """Instagram and Meta ads want JPEG; also clamps to IG's supported 4:5 .. 1.91:1 aspect range by padding."""
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[3])
        img = bg
    img = img.convert("RGB")
    w, h = img.size
    ratio = w / h
    if ratio < 0.8 or ratio > 1.91:
        target_w, target_h = (w, int(w / 0.8)) if ratio < 0.8 else (w, int(w / 1.91))
        if ratio < 0.8:
            target_w, target_h = int(h * 0.8), h
        canvas = Image.new("RGB", (target_w, target_h), img.getpixel((0, 0)))
        canvas.paste(img, ((target_w - w) // 2, (target_h - h) // 2))
        img = canvas
    if img.width > max_width:
        img = img.resize((max_width, int(img.height * max_width / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92, optimize=True)
    return buf.getvalue()


def is_mp4(raw: bytes) -> bool:
    return len(raw) > 12 and raw[4:8] == b"ftyp"
