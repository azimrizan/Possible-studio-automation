"""
Free, on-server word timings with open models (sherpa-onnx), so the Basic mode needs no paid speech-to-text.

- English: NVIDIA Parakeet TDT 0.6B v2 (int8)
- Any other language: Meta Omnilingual ASR 1B CTC (int8, 1600+ languages incl. Malayalam, Hindi, Tamil)

Models are installed once by scripts/setup_reel_models.sh into data/models (REEL_MODELS_DIR to override).
Long audio is split at pauses into chunks the models handle well; times are offset back afterwards.
"""
import asyncio
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .media import detect_silences

MODELS_DIR = Path(os.getenv("REEL_MODELS_DIR") or Path(__file__).resolve().parents[3] / "data" / "models")
MAX_CHUNK_S = 24.0
MAX_WORD_S = 1.2


def _model_dir(kind: str) -> Path:
    return MODELS_DIR / kind


def local_available(language: str = "en") -> bool:
    kind = "parakeet" if language == "en" else "omni"
    return (_model_dir(kind) / "tokens.txt").exists()


@lru_cache(maxsize=2)
def _recognizer(kind: str):
    import sherpa_onnx

    d = _model_dir(kind)
    threads = max(1, min(4, (os.cpu_count() or 2) - 1))
    if kind == "parakeet":
        return sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(d / "encoder.int8.onnx"), decoder=str(d / "decoder.int8.onnx"), joiner=str(d / "joiner.int8.onnx"),
            tokens=str(d / "tokens.txt"), model_type="nemo_transducer", num_threads=threads,
        )
    return sherpa_onnx.OfflineRecognizer.from_omnilingual_asr_ctc(
        model=str(next(d.glob("model*.onnx"))), tokens=str(d / "tokens.txt"), num_threads=threads,
    )


def _chunks(duration: float, silences: List[Dict[str, float]]) -> List[Tuple[float, float]]:
    """Split at the middle of pauses so no chunk is longer than MAX_CHUNK_S (when a pause allows it)."""
    cuts, start = [], 0.0
    mids = [(s["start"] + s["end"]) / 2 for s in silences]
    while duration - start > MAX_CHUNK_S:
        candidates = [m for m in mids if start + 4.0 < m <= start + MAX_CHUNK_S]
        end = candidates[-1] if candidates else start + MAX_CHUNK_S
        cuts.append((start, end))
        start = end
    cuts.append((start, duration))
    return cuts


def _words_from_tokens(tokens: List[str], times: List[float], offset: float, chunk_end: float) -> List[Dict[str, Any]]:
    words: List[Dict[str, Any]] = []
    for tok, t in zip(tokens, times):
        boundary = tok.startswith(("▁", " ")) or not words
        piece = tok.replace("▁", " ").strip()
        if not piece:
            if tok.strip() == "" or tok == "▁":
                words.append({"text": "", "start": offset + t})  # explicit word separator token
            continue
        if boundary or (words and words[-1]["text"] == ""):
            if words and words[-1]["text"] == "":
                words[-1] = {"text": piece, "start": offset + t}
            else:
                words.append({"text": piece, "start": offset + t})
        else:
            words[-1]["text"] += piece
    words = [w for w in words if w["text"]]
    for i, w in enumerate(words):
        nxt = words[i + 1]["start"] if i + 1 < len(words) else offset + chunk_end
        w["start"] = round(w["start"], 3)
        w["end"] = round(min(nxt - 0.02, w["start"] + MAX_WORD_S), 3)
    return words


def _trim_to_speech(words: List[Dict[str, Any]], silences: List[Dict[str, float]]) -> None:
    """Token timings only give word starts; end a word where the next pause begins if that comes first."""
    for w in words:
        for s in silences:
            if w["start"] < s["start"] < w["end"]:
                w["end"] = round(max(w["start"] + 0.08, s["start"]), 3)
                break


def _run(kind: str, audio: Path, spans: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
    import soundfile as sf

    samples, sr = sf.read(str(audio), dtype="float32")
    rec = _recognizer(kind)
    words: List[Dict[str, Any]] = []
    for start, end in spans:
        seg = samples[int(start * sr):int(end * sr)]
        if len(seg) < sr * 0.2:
            continue
        stream = rec.create_stream()
        stream.accept_waveform(sr, seg)
        rec.decode_stream(stream)
        res = stream.result
        words.extend(_words_from_tokens(list(res.tokens), list(res.timestamps), start, end - start))
    return words


async def transcribe_local(audio: Path, duration: float, language: Optional[str]) -> Dict[str, Any]:
    lang = (language or "en").lower()
    kind = "parakeet" if lang == "en" else "omni"
    if not local_available(lang):
        raise FileNotFoundError(f"Local speech model '{kind}' is not installed. Run: bash scripts/setup_reel_models.sh")
    silences = await detect_silences(audio)
    spans = _chunks(duration, silences)
    words = await asyncio.to_thread(_run, kind, audio, spans)
    _trim_to_speech(words, silences)
    return {"language": lang, "words": words, "mode": f"local-{kind}"}
