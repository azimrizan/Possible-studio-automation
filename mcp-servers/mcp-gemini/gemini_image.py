"""
Gemini multimodal image generation client.

Uses a Gemini *image* model (generateContent with IMAGE output), which — unlike
Imagen — accepts reference images. The product photo and brand logo are passed
as inline images alongside the art-directed prompt.

Model choice: GEMINI_IMAGE_MODEL env var, otherwise the best image model the
caller's key/account exposes (discovered via ListModels and cached per key).
"""
import base64
import hashlib
import io
import logging
import os
import time
from typing import Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("mcp_gemini.image")

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_IMAGE_MODEL = "gemini-2.5-flash-image"
SUPPORTED_ASPECT_RATIOS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}

# Discovery preference: "pro" image models render typography noticeably better.
_MODEL_PREFERENCE = ("pro-image", "flash-image")
_discovery_cache: Dict[str, Tuple[float, str]] = {}
_DISCOVERY_TTL_S = 3600


class GeminiImageError(Exception):
    """Raised when Gemini cannot produce an image. `retryable` marks transient failures."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class GeminiCredentials:
    """Either an API key or an OAuth bearer token (user's own Google account)."""

    def __init__(self, api_key: str = "", oauth_token: str = ""):
        self.api_key = (api_key or "").strip()
        self.oauth_token = (oauth_token or "").strip()

    @property
    def present(self) -> bool:
        return bool(self.api_key or self.oauth_token)

    def cache_key(self) -> str:
        raw = self.api_key or self.oauth_token
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def request_parts(self, url: str) -> Tuple[str, Dict[str, str]]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-goog-api-key"] = self.api_key
        else:
            headers["Authorization"] = f"Bearer {self.oauth_token}"
            # OAuth calls are billed to a Cloud project; set it explicitly if Google asks for a quota project.
            quota_project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
            if quota_project:
                headers["x-goog-user-project"] = quota_project
        return url, headers


async def resolve_image_model(creds: GeminiCredentials) -> str:
    configured = os.getenv("GEMINI_IMAGE_MODEL", "").strip()
    if configured:
        return configured

    key = creds.cache_key()
    cached = _discovery_cache.get(key)
    if cached and time.time() - cached[0] < _DISCOVERY_TTL_S:
        return cached[1]

    chosen = DEFAULT_IMAGE_MODEL
    try:
        url, headers = creds.request_parts(f"{API_BASE}/models?pageSize=1000")
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url, headers=headers)
        if res.status_code == 200:
            names = [
                m["name"].replace("models/", "")
                for m in res.json().get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])
            ]
            for marker in _MODEL_PREFERENCE:
                matches = sorted((n for n in names if marker in n), reverse=True)
                # Prefer stable names over previews when both exist.
                stable = [n for n in matches if "preview" not in n]
                if stable or matches:
                    chosen = (stable or matches)[0]
                    break
    except Exception as e:
        logger.warning(f"Gemini model discovery failed, using {chosen}: {e}")

    _discovery_cache[key] = (time.time(), chosen)
    logger.info(f"[GeminiImage] Using image model: {chosen}")
    return chosen


def _inline_part(image_bytes: bytes, mime_type: str) -> Dict:
    return {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(image_bytes).decode()}}


async def generate_image(
    prompt: str,
    creds: GeminiCredentials,
    reference_images: Optional[List[Tuple[bytes, str]]] = None,
    aspect_ratio: str = "4:5",
    timeout_s: float = 120.0,
) -> Tuple[bytes, str, str]:
    """
    Returns (image_bytes, mime_type, model_name).
    reference_images: ordered list of (bytes, mime_type); the prompt refers to them as Image 1, Image 2...
    """
    if not creds.present:
        raise GeminiImageError("No Gemini credentials. Connect your Google account or add a Gemini API key.")
    model = await resolve_image_model(creds)
    return await _generate_with_model(prompt, creds, reference_images, aspect_ratio, timeout_s, model)


def _fallback_model(model: str) -> Optional[str]:
    """Pro image models have no free-tier quota; the Flash image model is the fallback."""
    return DEFAULT_IMAGE_MODEL if "pro-image" in model else None


async def _generate_with_model(
    prompt: str,
    creds: GeminiCredentials,
    reference_images: Optional[List[Tuple[bytes, str]]],
    aspect_ratio: str,
    timeout_s: float,
    model: str,
) -> Tuple[bytes, str, str]:
    parts: List[Dict] = [{"text": prompt}]
    for img_bytes, mime in reference_images or []:
        parts.append(_inline_part(img_bytes, mime))

    image_config: Dict[str, str] = {}
    if aspect_ratio in SUPPORTED_ASPECT_RATIOS:
        image_config["aspectRatio"] = aspect_ratio
    if "pro" in model:
        image_config["imageSize"] = os.getenv("GEMINI_IMAGE_SIZE", "2K")

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": image_config},
    }

    url, headers = creds.request_parts(f"{API_BASE}/models/{model}:generateContent")
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            res = await client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException:
        raise GeminiImageError(f"{model} timed out after {timeout_s:.0f}s", retryable=True)
    except httpx.HTTPError as e:
        raise GeminiImageError(f"Network error calling {model}: {e}", retryable=True)

    if res.status_code != 200:
        message = res.text[:600]
        try:
            message = res.json().get("error", {}).get("message", message)
        except ValueError:
            pass
        # "limit: 0" = this model has no quota on the project's tier (e.g. Pro image on the free tier).
        # Retrying cannot help; fall back to the Flash image model unless a model is pinned.
        no_quota = res.status_code == 429 and "limit: 0" in message
        if no_quota and _fallback_model(model) and not os.getenv("GEMINI_IMAGE_MODEL", "").strip():
            fallback = _fallback_model(model)
            logger.warning(f"[GeminiImage] {model} has no quota on this project; falling back to {fallback}")
            _discovery_cache[creds.cache_key()] = (time.time(), fallback)
            return await _generate_with_model(prompt, creds, reference_images, aspect_ratio, timeout_s, fallback)
        if no_quota:
            message = (
                f"No Gemini API quota for {model} on this Google Cloud project (free tier limit is 0). "
                "Enable billing for the project at https://aistudio.google.com/apikey. "
                "A Google AI Pro subscription does not cover API usage."
            )
        retryable = (res.status_code == 429 and not no_quota) or res.status_code in (500, 502, 503, 504)
        raise GeminiImageError(f"{model} returned {res.status_code}: {message}", retryable=retryable)

    data = res.json()
    candidates = data.get("candidates") or []
    if not candidates:
        block = (data.get("promptFeedback") or {}).get("blockReason", "no candidates")
        raise GeminiImageError(f"{model} returned no image ({block})")

    for part in candidates[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
            return base64.b64decode(inline["data"]), mime, model

    reason = candidates[0].get("finishReason", "unknown")
    raise GeminiImageError(f"{model} returned no image (finishReason={reason})", retryable=reason == "OTHER")


def mock_placeholder_png(label: str, aspect_ratio: str = "4:5") -> bytes:
    """Plainly-labelled placeholder used only when MOCK_GEMINI=true and no credentials exist."""
    from PIL import Image, ImageDraw

    w, h = 800, 1000
    if aspect_ratio == "1:1":
        h = 800
    elif aspect_ratio == "9:16":
        w, h = 720, 1280
    img = Image.new("RGB", (w, h), (30, 32, 38))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, w - 20, h - 20], outline=(90, 90, 100), width=3)
    lines = ["MOCK MODE", "Gemini not connected", "", label[:60]]
    y = h // 2 - 40
    for line in lines:
        tw = draw.textlength(line)
        draw.text(((w - tw) / 2, y), line, fill=(200, 200, 210))
        y += 24
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
