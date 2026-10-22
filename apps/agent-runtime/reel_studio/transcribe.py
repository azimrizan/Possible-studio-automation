"""
Word-level transcription. Claude can't take audio, so speech-to-text gives it (and the subtitles) the words.

- ELEVENLABS_API_KEY set: ElevenLabs Scribe (handles Malayalam, Hindi, English and ~90 more).
- Otherwise: a clearly-labelled demo transcript timed to where speech actually is, so the
  rest of the pipeline can be exercised without a key.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .media import detect_silences

STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
DEMO_WORDS = ("demo transcript: add an ElevenLabs key in .env to see your real words here "
              "with every word timed to your voice").split()


class TranscriptionError(RuntimeError):
    pass


def stt_mode() -> str:
    return "elevenlabs" if os.getenv("ELEVENLABS_API_KEY") else "demo"


def pick_engine(edit_mode: str, language: Optional[str]) -> str:
    """Basic = Claude + free local models; Advanced = ElevenLabs first. Each falls back to the other, then demo."""
    from .transcribe_local import local_available

    local = local_available((language or "en").lower())
    paid = bool(os.getenv("ELEVENLABS_API_KEY"))
    order = ["local", "elevenlabs"] if edit_mode == "basic" else ["elevenlabs", "local"]
    for engine in order:
        if (engine == "local" and local) or (engine == "elevenlabs" and paid):
            return engine
    return "demo"


async def transcribe(audio: Path, duration: float, language: Optional[str] = None, engine: Optional[str] = None) -> Dict[str, Any]:
    engine = engine or stt_mode()
    if engine == "local":
        from .transcribe_local import transcribe_local

        return await transcribe_local(audio, duration, language)
    if engine == "demo":
        return await _demo(audio, duration)
    data = {"model_id": os.getenv("ELEVENLABS_STT_MODEL", "scribe_v1"), "timestamps_granularity": "word",
            "tag_audio_events": "false"}
    if language:
        data["language_code"] = language
    async with httpx.AsyncClient(timeout=300.0) as client:
        with audio.open("rb") as f:
            res = await client.post(STT_URL, headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                                    data=data, files={"file": (audio.name, f, "audio/wav")})
    if res.status_code != 200:
        raise TranscriptionError(f"Speech-to-text failed ({res.status_code}): {res.text[:300]}")
    body = res.json()
    words = [
        {"text": w["text"].strip(), "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)}
        for w in body.get("words", []) if w.get("type", "word") == "word" and w.get("text", "").strip()
    ]
    return {"language": body.get("language_code", language or ""), "words": words, "mode": "elevenlabs"}


async def _demo(audio: Path, duration: float) -> Dict[str, Any]:
    silences = await detect_silences(audio)
    spans, cursor = [], 0.0
    for s in silences:
        if s["start"] - cursor > 0.2:
            spans.append((cursor, s["start"]))
        cursor = s["end"]
    if duration - cursor > 0.2:
        spans.append((cursor, duration))
    words: List[Dict[str, Any]] = []
    for start, end in spans:
        t = start
        while t + 0.15 < end:
            step = min(0.42, end - t)
            words.append({"text": DEMO_WORDS[len(words) % len(DEMO_WORDS)], "start": round(t, 3), "end": round(t + step - 0.04, 3)})
            t += step
    return {"language": "en", "words": words, "mode": "demo"}
