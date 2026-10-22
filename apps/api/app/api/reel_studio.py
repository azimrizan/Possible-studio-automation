"""
AI Video Edit: raw talking-head take (+ hook takes) -> Claude-planned, subtitled, graphics-edited reels.

Modes
- basic:    Claude + free tools on this server (local speech models, cut-outs, synthesised sound effects).
- advanced: same edit with ElevenLabs transcription first; generative camera angles / room come later.

Flow: create project -> upload files -> POST /plan (transcribe + Claude + Claude's self-check, background)
      -> review / tweak plan (PUT /plan) -> POST /render (background) -> download variants.
"""
import asyncio
import logging
import re
import secrets
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

import reel_studio as rs
from poster_studio import StoreError, StudioStore
from poster_studio.imaging import InvalidImageError, normalise_upload

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/studio/reels", tags=["AI Video Edit"])
store = StudioStore()

MAX_UPLOAD_BYTES = 600 * 1024 * 1024
MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_MAIN_S, MAX_HOOK_S = 180.0, 20.0
MAX_HOOKS, MAX_REFERENCES = 3, 6
ANGLES = {"left_side", "right_side", "close_profile", "from_above", "front", "other"}
MODES = {"basic", "advanced"}
LANGUAGES = {"en", "ml", "hi", "ta", "te", "kn", "ar", "other"}
BUSY = {"planning", "rendering"}
REVIEW_FRAMES = 6
_tasks: set = set()


def _ws(workspace: Optional[str]) -> str:
    if not workspace:
        raise HTTPException(status_code=400, detail="X-Studio-Workspace header required")
    return workspace


def _now() -> int:
    return int(time.time())


def _load(ws: str, rid: str) -> Dict[str, Any]:
    try:
        r = store.load_doc(ws, "reels", rid)
    except StoreError:
        raise HTTPException(status_code=404, detail="Video project not found")
    r.setdefault("mode", "basic")
    r.setdefault("language", "en")
    r.setdefault("glossary", "")
    return r


def _save(ws: str, r: Dict[str, Any]) -> Dict[str, Any]:
    r["updated_at"] = _now()
    return store.save_doc(ws, "reels", r["id"], r)


def _progress(ws: str, r: Dict[str, Any], message: str) -> None:
    r["progress"] = message
    _save(ws, r)


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def _modes(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "transcription": rs.pick_engine(r.get("mode", "basic"), r.get("language")),
        "director": rs.director_mode(),
        "renderer_ready": rs.renderer_ready(),
        "local_speech": rs.local_available("en"), "local_speech_multilingual": rs.local_available("ml"),
        "cutouts": rs.masks_available(),
    }


def _public(r: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in r.items() if k != "sources"}
    # The transcript is shown in the review screen; word timings stay server-side.
    out["transcript"] = {
        name: [{"id": w["id"], "text": w["text"]} for w in src["words"]]
        for name, src in (r.get("sources") or {}).items()
    }
    out["modes"] = _modes(r)
    return out


def _accent(ws: str) -> Optional[str]:
    """First brand colour, lightened until it reads as text on video (dark brand colours are common)."""
    colors = store.load_brand_kit(ws).get("colors") or []
    if not colors or not re.fullmatch(r"#[0-9a-fA-F]{6}", str(colors[0])):
        return None
    import colorsys

    r, g, b = (int(colors[0][i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    # Keep the hue; make it bright and saturated enough to read as text and graphics on video.
    rgb = colorsys.hls_to_rgb(h, max(l, 0.62), max(s, 0.65) if s > 0.08 else s)
    return "#" + "".join(f"{round(v * 255):02X}" for v in rgb)


def _style(ws: str) -> Dict[str, Any]:
    accent = _accent(ws)
    return {"accent": accent} if accent else {}


# ---- projects ---------------------------------------------------------------------

class CreateBody(BaseModel):
    name: str = Field("Untitled video", max_length=120)
    mode: str = "basic"
    language: str = "en"


class SettingsBody(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    mode: Optional[str] = None
    language: Optional[str] = None
    glossary: Optional[str] = Field(None, max_length=1000)


@router.get("")
async def list_reels(x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    return [
        {"id": r["id"], "name": r["name"], "status": r["status"], "mode": r.get("mode", "basic"), "updated_at": r.get("updated_at"),
         "cover_url": next((v.get("cover_url") for v in r.get("variants") or [] if v.get("cover_url")), None)}
        for r in store.list_docs(ws, "reels")
    ]


@router.post("")
async def create_reel(body: CreateBody, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    if body.mode not in MODES or body.language not in LANGUAGES:
        raise HTTPException(status_code=400, detail="Unknown mode or language")
    r = {
        "id": secrets.token_hex(12), "name": body.name.strip() or "Untitled video", "created_at": _now(),
        "mode": body.mode, "language": body.language, "glossary": "",
        "status": "draft", "error": "", "progress": "",
        "files": {"main": None, "hooks": [], "references": []},
        "instruction": "", "sources": {}, "plan": None, "variants": [],
    }
    return _public(_save(ws, r))


@router.get("/{rid}")
async def get_reel(rid: str, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    return _public(_load(ws, rid))


@router.patch("/{rid}")
async def update_settings(rid: str, body: SettingsBody, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    r = _load(ws, rid)
    if r["status"] in BUSY:
        raise HTTPException(status_code=409, detail="Wait for the current step to finish")
    if body.mode is not None and body.mode not in MODES:
        raise HTTPException(status_code=400, detail="mode must be basic or advanced")
    if body.language is not None and body.language not in LANGUAGES:
        raise HTTPException(status_code=400, detail="Unknown language")
    for key in ("name", "mode", "language", "glossary"):
        value = getattr(body, key)
        if value is not None:
            r[key] = value.strip() if isinstance(value, str) else value
    return _public(_save(ws, r))


# ---- files ------------------------------------------------------------------------

async def _receive(file: UploadFile, dst: Path, limit: int) -> int:
    size = 0
    with dst.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                raise HTTPException(status_code=413, detail=f"Files must be {limit // (1024 * 1024)} MB or smaller")
            f.write(chunk)
    if not size:
        raise HTTPException(status_code=400, detail="Empty file")
    return size


@router.post("/{rid}/files")
async def add_file(rid: str, role: str = Form(...), angle: str = Form("other"), file: UploadFile = File(...),
                   x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    r = _load(ws, rid)
    if r["status"] in BUSY:
        raise HTTPException(status_code=409, detail="Wait for the current step to finish")
    if role not in ("main", "hook", "reference"):
        raise HTTPException(status_code=400, detail="role must be main, hook or reference")
    if role == "hook" and len(r["files"]["hooks"]) >= MAX_HOOKS:
        raise HTTPException(status_code=400, detail=f"Up to {MAX_HOOKS} hook takes")
    if role == "reference" and len(r["files"]["references"]) >= MAX_REFERENCES:
        raise HTTPException(status_code=400, detail=f"Up to {MAX_REFERENCES} reference photos")

    if role == "reference":
        if angle not in ANGLES:
            raise HTTPException(status_code=400, detail="Unknown angle")
        raw = await file.read(MAX_IMAGE_BYTES + 1)
        if len(raw) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Photos must be 15 MB or smaller")
        try:
            data, mime, _, _ = normalise_upload(raw, max_side=2048, keep_alpha=False)
        except InvalidImageError:
            raise HTTPException(status_code=400, detail="Upload a JPG, PNG or WebP photo")
        asset = store.save_asset(ws, data, mime)
        r["files"]["references"].append({"asset_id": asset["asset_id"], "url": asset["url"], "angle": angle,
                                         "name": file.filename or ""})
        return _public(_save(ws, r))

    work = store.work_dir(ws, "reels", rid)
    tmp = work / f"upload_{secrets.token_hex(4)}"
    norm = work / f"norm_{secrets.token_hex(4)}.mp4"
    try:
        await _receive(file, tmp, MAX_UPLOAD_BYTES)
        try:
            info = await rs.normalise(tmp, norm)
        except rs.MediaError as e:
            raise HTTPException(status_code=400, detail=str(e))
        limit = MAX_MAIN_S if role == "main" else MAX_HOOK_S
        if info["duration"] > limit:
            raise HTTPException(status_code=400, detail=f"{'Main take' if role == 'main' else 'Hook takes'} can be up to {int(limit)} seconds")
        asset = store.save_asset(ws, norm.read_bytes(), "video/mp4")
    finally:
        tmp.unlink(missing_ok=True)
        norm.unlink(missing_ok=True)

    entry = {"asset_id": asset["asset_id"], "url": asset["url"], "duration": info["duration"], "name": file.filename or ""}
    if role == "main":
        r["files"]["main"] = entry
    else:
        r["files"]["hooks"].append(entry)
    # New footage invalidates any earlier plan and renders.
    r.update(status="draft", plan=None, variants=[], sources={}, error="")
    return _public(_save(ws, r))


@router.delete("/{rid}/files/{asset_id}")
async def remove_file(rid: str, asset_id: str, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    r = _load(ws, rid)
    if r["status"] in BUSY:
        raise HTTPException(status_code=409, detail="Wait for the current step to finish")
    f = r["files"]
    if f["main"] and f["main"]["asset_id"] == asset_id:
        f["main"] = None
    f["hooks"] = [h for h in f["hooks"] if h["asset_id"] != asset_id]
    refs_before = len(f["references"])
    f["references"] = [x for x in f["references"] if x["asset_id"] != asset_id]
    if len(f["references"]) == refs_before:  # footage changed
        r.update(status="draft", plan=None, variants=[], sources={})
    return _public(_save(ws, r))


# ---- plan ---------------------------------------------------------------------------

class PlanBody(BaseModel):
    instruction: str = Field("", max_length=1500)
    glossary: Optional[str] = Field(None, max_length=1000)


def _source_names(r: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    names = {"main": r["files"]["main"]}
    for i, h in enumerate(r["files"]["hooks"]):
        names[f"hook{i + 1}"] = h
    return names


def _stage(ws: str, r: Dict[str, Any], public_dir: Path) -> None:
    rs.stage_inputs(public_dir, {f"{name}.mp4": store.asset_path(ws, f["asset_id"]) for name, f in _source_names(r).items()})


def _review_frames(variant: Dict[str, Any]) -> List[int]:
    """Frames that show the most: the hook, each beat at its fullest, and plain talking in between."""
    p = variant["props"]
    picks = [max(1, p["hook"]["endFrame"] - 10)] if p["hook"]["endFrame"] else [15]
    for b in p["beats"]:
        picks.append(min(b["endFrame"] - 10, b["startFrame"] + 24))
    gaps = [f for f in range(60, p["durationInFrames"] - 30, 90) if not any(b["startFrame"] <= f < b["endFrame"] for b in p["beats"])]
    picks += gaps[: max(0, REVIEW_FRAMES - len(picks))]
    return sorted(set(picks))[:REVIEW_FRAMES]


async def _self_check(ws: str, r: Dict[str, Any], sources: Dict[str, Any], plan: Dict[str, Any], work: Path) -> Dict[str, Any]:
    """Claude looks at rendered test frames of version 1 and returns a corrected plan."""
    variants = rs.build_variants(sources, plan, _style(ws))
    if not variants:
        return plan
    public_dir = work / "public"
    _stage(ws, r, public_dir)
    v = variants[0]
    props = await rs.prepare_variant(public_dir, v, with_sfx=False)
    frames = _review_frames(v)
    stills_dir = work / "review"
    if stills_dir.exists():
        shutil.rmtree(stills_dir)
    stills_dir.mkdir()
    await rs.run_job(work, public_dir, [{"kind": "stills", "props": props, "frames": frames,
                                          "outPattern": str(stills_dir / "f_{frame}.jpg")}])
    paths = [stills_dir / f"f_{f}.jpg" for f in frames]
    labels = [f"{f / 30:.1f}s" for f in frames]
    sheet = rs.contact_sheet(paths, labels, stills_dir / "sheet.jpg")
    revised = await rs.review_plan(sources, plan, sheet, labels, r.get("instruction", ""), r.get("glossary", ""))
    return revised or plan


async def _run_plan(ws: str, rid: str) -> None:
    r = _load(ws, rid)
    try:
        work = store.work_dir(ws, "reels", rid)
        engine = rs.pick_engine(r["mode"], r["language"])
        language = None if r["language"] == "other" else r["language"]
        sources: Dict[str, Dict[str, Any]] = {}
        for name, f in _source_names(r).items():
            cached = (r.get("sources") or {}).get(name)
            if cached and cached.get("asset_id") == f["asset_id"] and cached.get("engine") == engine and cached.get("lang") == r["language"]:
                sources[name] = cached
                continue
            label = "main take" if name == "main" else name.replace("hook", "hook take ")
            _progress(ws, r, f"Listening to the {label}" + (" (free speech model, first run loads it)" if engine == "local" else ""))
            video = store.asset_path(ws, f["asset_id"])
            wav = work / f"{name}.wav"
            await rs.extract_audio(video, wav)
            tr = await rs.transcribe(wav, f["duration"], language if engine != "local" else (language or "ml"), engine)
            wav.unlink(missing_ok=True)
            sources[name] = {
                "asset_id": f["asset_id"], "file": f"{name}.mp4", "duration": f["duration"], "language": tr["language"],
                "engine": engine, "lang": r["language"], "mode": tr["mode"],
                "words": [{**w, "id": f"{name}:{i}"} for i, w in enumerate(tr["words"])],
            }
        if not sources["main"]["words"]:
            raise RuntimeError("No speech found in the main take. Check the microphone was on.")
        r["sources"] = sources
        _progress(ws, r, "Claude is watching your video and planning the edit")
        frames = await rs.sample_frames(store.asset_path(ws, r["files"]["main"]["asset_id"]), work / "frames",
                                        r["files"]["main"]["duration"])
        plan = await rs.plan_edit(sources, frames, r.get("instruction", ""), r.get("glossary", ""))
        if plan.get("mode") == "claude":
            _progress(ws, r, "Claude is checking test frames of the edit")
            try:
                plan = await _self_check(ws, r, sources, plan, work)
            except (rs.RenderError, rs.MediaError) as e:  # the first plan is still usable
                logger.warning(f"[Reels] self-check skipped for {rid}: {e}")
        r["plan"] = plan
        r["variants"] = _variant_summaries(rs.build_variants(sources, plan, _style(ws)))
        r.update(status="planned", progress="", error="")
    except (rs.MediaError, rs.TranscriptionError, rs.DirectorError, RuntimeError, FileNotFoundError) as e:
        logger.error(f"[Reels] planning failed for {rid}: {e}")
        r.update(status="failed", progress="", error=str(e))
    _save(ws, r)


def _variant_summaries(variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"index": v["index"], "label": v["label"], "duration_s": v["duration_s"],
             "hook_text": v["props"]["hook"]["text"], "beats": len(v["props"]["beats"])} for v in variants]


@router.post("/{rid}/plan")
async def plan_reel(rid: str, body: PlanBody, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    r = _load(ws, rid)
    if r["status"] in BUSY:
        raise HTTPException(status_code=409, detail="Already working on this video")
    if not r["files"]["main"]:
        raise HTTPException(status_code=400, detail="Upload the main take first")
    if body.glossary is not None:
        r["glossary"] = body.glossary.strip()
    r.update(instruction=body.instruction.strip(), status="planning", error="", progress="Starting", variants=[])
    _save(ws, r)
    _spawn(_run_plan(ws, rid))
    return _public(r)


class HookEdit(BaseModel):
    source: str
    overlay_text: str = Field("", max_length=120)
    accent_words: List[str] = []


class ItemEdit(BaseModel):
    text: str = Field("", max_length=60)
    at_word_id: str = ""


class BeatEdit(BaseModel):
    type: str
    start_word_id: str
    end_word_id: str
    text: str = Field("", max_length=80)
    sub: str = Field("", max_length=80)
    value: float = 0
    prefix: str = Field("", max_length=4)
    suffix: str = Field("", max_length=6)
    items: List[ItemEdit] = Field([], max_length=4)
    keyword: str = Field("", max_length=24)


class CorrectionEdit(BaseModel):
    word_id: str
    text: str = Field(..., max_length=60)


class PlanEdits(BaseModel):
    remove_word_ids: List[str]
    emphasis_word_ids: List[str]
    punch_word_ids: List[str] = []
    corrections: List[CorrectionEdit] = []
    beats: List[BeatEdit] = Field([], max_length=20)
    hooks: List[HookEdit] = Field(..., max_length=3)
    caption: str = Field("", max_length=2200)
    hashtags: List[str] = []
    title_text: str = Field("", max_length=60)
    title_at_word_id: str = ""
    subtitle_position: str = "lower"
    grade: str = "natural"


@router.put("/{rid}/plan")
async def edit_plan(rid: str, body: PlanEdits, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    r = _load(ws, rid)
    if r["status"] in BUSY or not r.get("plan"):
        raise HTTPException(status_code=409, detail="Plan the edit first")
    if body.subtitle_position not in ("lower", "middle", "upper") or body.grade not in ("none", "natural", "cinematic"):
        raise HTTPException(status_code=400, detail="Unknown subtitle position or grade")
    if any(b.type not in rs.BEAT_TYPES for b in body.beats):
        raise HTTPException(status_code=400, detail="Unknown beat type")
    r["plan"].update(body.model_dump())
    r["plan"]["edited_by_user"] = True
    r["variants"] = _variant_summaries(rs.build_variants(r["sources"], r["plan"], _style(ws)))
    r["status"] = "planned"
    return _public(_save(ws, r))


# ---- render -------------------------------------------------------------------------

async def _run_render(ws: str, rid: str) -> None:
    r = _load(ws, rid)
    try:
        work = store.work_dir(ws, "reels", rid)
        public_dir = work / "public"
        _stage(ws, r, public_dir)
        variants = rs.build_variants(r["sources"], r["plan"], _style(ws))
        tasks = []
        for v in variants:
            _progress(ws, r, f"Preparing {v['label']}: cut-outs and sound")
            props = await rs.prepare_variant(public_dir, v)
            tasks.append({"kind": "video", "props": props, "out": str(work / f"raw_{v['index']}.mp4"),
                          "cover": {"frame": rs.cover_frame(props), "out": str(work / f"cover_{v['index']}.jpg")}})
        _progress(ws, r, "Rendering")
        await rs.run_job(work, public_dir, tasks, on_progress=lambda m: _progress(ws, r, f"Rendering {m}"))
        done = []
        for v in variants:
            raw, final, cover = work / f"raw_{v['index']}.mp4", work / f"final_{v['index']}.mp4", work / f"cover_{v['index']}.jpg"
            _progress(ws, r, f"Finishing sound for {v['label']}")
            await rs.finish_audio(raw, final)
            video = store.save_asset(ws, final.read_bytes(), "video/mp4")
            cover_asset = store.save_asset(ws, cover.read_bytes(), "image/jpeg")
            for p in (raw, final, cover):
                p.unlink(missing_ok=True)
            done.append({**_variant_summaries([v])[0], "video_asset_id": video["asset_id"], "video_url": video["url"],
                         "cover_asset_id": cover_asset["asset_id"], "cover_url": cover_asset["url"]})
        r["variants"] = done
        r.update(status="rendered", progress="", error="")
    except (rs.RenderError, rs.MediaError, StoreError, OSError) as e:
        logger.error(f"[Reels] render failed for {rid}: {e}")
        r.update(status="failed", progress="", error=str(e))
    _save(ws, r)


@router.post("/{rid}/render")
async def render_reel(rid: str, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    r = _load(ws, rid)
    if r["status"] in BUSY:
        raise HTTPException(status_code=409, detail="Already working on this video")
    if not r.get("plan"):
        raise HTTPException(status_code=400, detail="Plan the edit first")
    if not rs.renderer_ready():
        raise HTTPException(status_code=500, detail="The renderer isn't installed. Run: npm --prefix apps/reel-renderer install")
    r.update(status="rendering", error="", progress="Preparing")
    _save(ws, r)
    _spawn(_run_render(ws, rid))
    return _public(r)
