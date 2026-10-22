"""
Sound effects synthesised in code: no downloads, no music, nothing melodic.

Kinds: air (whoosh), pop, tap, key (keyboard), ticks (counting), hit (low thump).
Levels are dBFS peaks; the defaults in timeline.py keep everything quiet under the voice.
"""
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

SR = 48000
FPS = 30


def _env(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(t - attack, 0) / max(decay, 1e-4))


def _lowpass(x: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha[i] * (x[i] - acc)
        y[i] = acc
    return y


def _air(rng: np.random.Generator, dur: float = 0.45) -> np.ndarray:
    n = int(SR * dur)
    noise = rng.standard_normal(n)
    # Filter sweeps up then down: the "swish" of something passing the camera.
    sweep = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    alpha = 0.02 + 0.25 * sweep
    return _lowpass(noise, alpha) * sweep


def _pop(rng: np.random.Generator) -> np.ndarray:
    n = int(SR * 0.09)
    t = np.arange(n) / SR
    freq = 900 * np.exp(-t * 35) + 280
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * _env(n, 0.002, 0.025)


def _tap(rng: np.random.Generator) -> np.ndarray:
    n = int(SR * 0.04)
    return _lowpass(rng.standard_normal(n), np.full(n, 0.5)) * _env(n, 0.0005, 0.008)


def _key(rng: np.random.Generator) -> np.ndarray:
    n = int(SR * 0.05)
    click = _lowpass(rng.standard_normal(n), np.full(n, 0.35)) * _env(n, 0.0005, 0.006)
    body = np.sin(2 * np.pi * rng.uniform(1800, 2600) * np.arange(n) / SR) * _env(n, 0.0005, 0.004) * 0.3
    return click + body


def _hit(rng: np.random.Generator) -> np.ndarray:
    n = int(SR * 0.7)
    t = np.arange(n) / SR
    freq = 65 * np.exp(-t * 3) + 38
    thump = np.sin(2 * np.pi * np.cumsum(freq) / SR) * _env(n, 0.003, 0.22)
    transient = _lowpass(rng.standard_normal(n), np.full(n, 0.3)) * _env(n, 0.0005, 0.012) * 0.5
    return thump + transient


def _ticks(rng: np.random.Generator, frames: int) -> np.ndarray:
    out = np.zeros(int(SR * frames / FPS) + SR // 10)
    step = int(SR * 0.045)
    for k, start in enumerate(range(0, len(out) - step, step)):
        t = _tap(rng) * (0.6 + 0.4 * (k % 2))
        out[start:start + len(t)] += t
    return out


def render_sfx(events: List[Dict[str, Any]], duration_frames: int, out: Path, seed: int = 7) -> bool:
    """Writes a mono 48 kHz WAV the length of the reel. Returns False when there is nothing to play."""
    if not events:
        return False
    import soundfile as sf

    rng = np.random.default_rng(seed)
    track = np.zeros(int(SR * duration_frames / FPS) + SR)
    for ev in events:
        kind = ev["kind"]
        if kind == "air":
            s = _air(rng)
            offset = -len(s) // 2  # centred on the cut
        elif kind == "ticks":
            s, offset = _ticks(rng, ev.get("frames", 18)), 0
        else:
            s, offset = {"pop": _pop, "tap": _tap, "key": _key, "hit": _hit}[kind](rng), 0
        peak = np.max(np.abs(s)) or 1.0
        s = s / peak * (10 ** (ev.get("db", -32) / 20))
        start = max(0, int(SR * ev["frame"] / FPS) + offset)
        end = min(len(track), start + len(s))
        track[start:end] += s[: end - start]
    track = np.clip(track[: int(SR * duration_frames / FPS)], -1, 1)
    sf.write(str(out), track.astype(np.float32), SR)
    return True
