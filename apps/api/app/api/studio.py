"""
Poster Studio API.

Workspace scoping: the web app has no platform login yet, so each browser sends a
random workspace id in `X-Studio-Workspace`. Asset URLs are unguessable (128-bit ids).
TODO: replace with the JWT tenant context (deps.get_tenant_context) once the web app
signs users in.
"""
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from gemini_image import GeminiCredentials, GeminiImageError, generate_image, mock_placeholder_png
from model_gateway import GroqCallError
from poster_studio import (
    PipelineError,
    PosterAgents,
    PosterPipeline,
    PosterRequest,
    RegenerateRequest,
    StoreError,
    StudioStore,
)
from poster_studio.imaging import InvalidImageError, normalise_upload

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/studio", tags=["Poster Studio"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

store = StudioStore()
agents = PosterAgents()
pipeline = PosterPipeline(store, agents)
QA_ENABLED = os.getenv("POSTER_QA_ENABLED", "true").lower() == "true"


def _ws(workspace: Optional[str]) -> str:
    if not workspace:
        raise HTTPException(status_code=400, detail="X-Studio-Workspace header required")
    return workspace


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    return data


# ---- brand kit (every field optional) ----------------------------------------

class BrandKitUpdate(BaseModel):
    brand_name: Optional[str] = Field(None, max_length=80)
    colors: Optional[List[str]] = None
    tone: Optional[str] = Field(None, max_length=200)
    tagline: Optional[str] = Field(None, max_length=120)
    typography: Optional[str] = Field(None, max_length=80)


def _public_kit(kit: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "brand_name": kit.get("brand_name", ""),
        "colors": kit.get("colors", []),
        "tone": kit.get("tone", ""),
        "tagline": kit.get("tagline", ""),
        "typography": kit.get("typography", ""),
        "logo": kit.get("logo"),
        "logo_profile": kit.get("logo_profile"),
        "updated_at": kit.get("updated_at"),
    }


@router.get("/brand-kit")
async def get_brand_kit(x_studio_workspace: Optional[str] = Header(None)):
    try:
        return _public_kit(store.load_brand_kit(_ws(x_studio_workspace)))
    except StoreError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/brand-kit")
async def update_brand_kit(body: BrandKitUpdate, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    try:
        kit = store.load_brand_kit(ws)
        updates = body.model_dump(exclude_unset=True)
        if "colors" in updates:
            updates["colors"] = [c for c in (updates["colors"] or []) if HEX_RE.match(c)][:5]
        for key, value in updates.items():
            kit[key] = value.strip() if isinstance(value, str) else value
        kit["updated_at"] = int(time.time())
        return _public_kit(store.save_brand_kit(ws, kit))
    except StoreError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/brand-kit/logo")
async def upload_logo(file: UploadFile = File(...), x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    raw = await _read_upload(file)
    try:
        data, mime, _, _ = normalise_upload(raw, max_side=1024, keep_alpha=True)
        asset = store.save_asset(ws, data, mime)
        kit = store.load_brand_kit(ws)
        old = (kit.get("logo") or {}).get("asset_id")
        if old:
            store.delete_asset(ws, old)
    except InvalidImageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StoreError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # One-time logo analysis; every later poster run reuses this ~40-token profile.
    profile = None
    try:
        result, usage = await agents.analyse_logo(data)
        profile = result.model_dump()
        logger.info(f"[Studio] Logo analysed ({usage['prompt_tokens']}+{usage['completion_tokens']} tokens)")
    except Exception as e:
        logger.warning(f"[Studio] Logo analysis skipped: {e}")

    kit["logo"] = {"asset_id": asset["asset_id"], "url": asset["url"]}
    kit["logo_profile"] = profile
    kit["updated_at"] = int(time.time())
    return _public_kit(store.save_brand_kit(ws, kit))


@router.delete("/brand-kit/logo")
async def delete_logo(x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    kit = store.load_brand_kit(ws)
    old = (kit.get("logo") or {}).get("asset_id")
    if old:
        store.delete_asset(ws, old)
    kit["logo"], kit["logo_profile"] = None, None
    kit["updated_at"] = int(time.time())
    return _public_kit(store.save_brand_kit(ws, kit))


@router.delete("/brand-kit")
async def reset_brand_kit(x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    old = (store.load_brand_kit(ws).get("logo") or {}).get("asset_id")
    if old:
        store.delete_asset(ws, old)
    return _public_kit(store.save_brand_kit(ws, {"updated_at": int(time.time())}))


# ---- product uploads and asset serving ------------------------------------------

@router.post("/uploads")
async def upload_product_image(file: UploadFile = File(...), x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    raw = await _read_upload(file)
    try:
        data, mime, width, height = normalise_upload(raw, max_side=2048, keep_alpha=True)
        asset = store.save_asset(ws, data, mime)
    except (InvalidImageError, StoreError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"asset_id": asset["asset_id"], "url": asset["url"], "width": width, "height": height, "name": file.filename}


@router.get("/assets/{workspace}/{filename}")
async def get_asset(workspace: str, filename: str):
    try:
        path = store.asset_path(workspace, filename)
    except StoreError:
        raise HTTPException(status_code=404, detail="Not found")
    # FileResponse supports Range requests, which browsers (and Instagram) need for video.
    mime = {"png": "image/png", "jpg": "image/jpeg", "mp4": "video/mp4"}[filename.rsplit(".", 1)[1]]
    return FileResponse(path, media_type=mime, headers={"Cache-Control": "private, max-age=31536000, immutable"})


# ---- poster generation ----------------------------------------------------------

class GenerateBody(PosterRequest):
    api_key: Optional[str] = None
    oauth_token: Optional[str] = None


class RegenerateBody(RegenerateRequest):
    api_key: Optional[str] = None
    oauth_token: Optional[str] = None


def _image_backend(api_key: Optional[str], oauth_token: Optional[str]):
    """Returns (image_fn, is_mock). User credentials win; env key next; mock only if explicitly enabled."""
    mock_enabled = os.getenv("MOCK_GEMINI", "false").lower() == "true"
    creds = GeminiCredentials(api_key or "", oauth_token or "")
    if not creds.present and not mock_enabled:
        creds = GeminiCredentials(os.getenv("GEMINI_API_KEY", ""), "")

    if creds.present:
        async def live(prompt, refs, aspect_ratio):
            try:
                return await generate_image(prompt, creds, refs, aspect_ratio)
            except GeminiImageError as e:
                if not e.retryable:
                    raise
                logger.warning(f"[Studio] Gemini transient error, retrying once: {e}")
                return await generate_image(prompt, creds, refs, aspect_ratio)
        return live, False

    if mock_enabled:
        async def mock(prompt, refs, aspect_ratio):
            headline = prompt.split('Headline: "', 1)[-1].split('"', 1)[0] if 'Headline: "' in prompt else ""
            return mock_placeholder_png(headline, aspect_ratio), "image/png", "mock"
        return mock, True

    raise HTTPException(
        status_code=400,
        detail="Gemini is not connected. Sign in with Google or add your Gemini API key in Integrations.",
    )


@router.post("/posters/generate")
async def generate_posters(body: GenerateBody, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    image_fn, is_mock = _image_backend(body.api_key, body.oauth_token)
    started = time.time()
    try:
        result = await pipeline.generate(ws, body, image_fn, run_qa=QA_ENABLED and not is_mock)
    except StoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (PipelineError, GroqCallError, ValueError) as e:
        logger.error(f"[Studio] Poster generation failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    result["mock"] = is_mock
    result["elapsed_s"] = round(time.time() - started, 1)
    return {"success": True, "data": result}


@router.post("/posters/regenerate")
async def regenerate_poster(body: RegenerateBody, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    image_fn, is_mock = _image_backend(body.api_key, body.oauth_token)
    try:
        result = await pipeline.regenerate(ws, body, image_fn, run_qa=QA_ENABLED and not is_mock)
    except StoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (PipelineError, GroqCallError, ValueError) as e:
        logger.error(f"[Studio] Poster regeneration failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    result["mock"] = is_mock
    return {"success": True, "data": result}
