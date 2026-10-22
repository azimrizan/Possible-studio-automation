"""
ffmpeg helpers for the reel editor: normalise uploads, pull audio for transcription,
find pauses, and sample frames for Claude to look at.

Uses the static ffmpeg binary from imageio-ffmpeg (no system install needed); set FFMPEG_BIN to override.
"""
import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

OUT_W, OUT_H, OUT_FPS = 1080, 1920, 30


class MediaError(RuntimeError):
    pass


def ffmpeg_exe() -> str:
    if os.getenv("FFMPEG_BIN"):
        return os.environ["FFMPEG_BIN"]
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


async def _run(*args: str, timeout: float = 900) -> Tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        ffmpeg_exe(), "-hide_banner", "-nostdin", *args,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise MediaError("ffmpeg timed out")
    return proc.returncode, err.decode("utf-8", "replace")


async def probe(path: Path) -> Dict[str, Any]:
    """Duration and stream info, parsed from `ffmpeg -i` (the bundled binary has no ffprobe)."""
    _, err = await _run("-i", str(path), timeout=60)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if not m:
        raise MediaError("Not a readable video file")
    duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    video = re.search(r"Stream #.*Video: .*?, (\d{2,5})x(\d{2,5})", err)
    return {
        "duration": round(duration, 3),
        "width": int(video.group(1)) if video else 0,
        "height": int(video.group(2)) if video else 0,
        "has_video": bool(video),
        "has_audio": bool(re.search(r"Stream #.*Audio:", err)),
    }


IG_MAX_VIDEO_KBPS = 25000  # Instagram Reels limits for API uploads
IG_AUDIO = ("-c:a", "aac", "-b:a", "112k", "-ar", "48000", "-ac", "2")


async def instagram_ready(src: Path, dst: Path) -> None:
    """Copy of a video within Instagram's Reels limits (H.264 yuv420p <= 25 Mbps, AAC under the 128 kbps cap, faststart).
    A compliant H.264 stream is copied untouched; only the audio is re-encoded."""
    _, info = await _run("-i", str(src), timeout=60)
    video = re.search(r"Stream #.*Video: (\w+).*?, (yuv\w+)[^,]*,.*?(\d+) kb/s", info)
    copy_video = bool(video and video.group(1) == "h264" and video.group(2) == "yuv420p"
                      and int(video.group(3)) <= IG_MAX_VIDEO_KBPS)
    v_args = ["-c:v", "copy"] if copy_video else [
        "-vf", "scale='min(1080,iw)':-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-maxrate", "20M", "-bufsize", "40M", "-pix_fmt", "yuv420p",
    ]
    code, err = await _run("-y", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?", *v_args, *IG_AUDIO,
                           "-movflags", "+faststart", str(dst))
    if code != 0:
        raise MediaError("Could not prepare the video for Instagram: " + (err.strip().splitlines() or ["ffmpeg failed"])[-1][:200])


async def normalise(src: Path, dst: Path) -> Dict[str, Any]:
    """Vertical 1080x1920 @30fps H.264 + AAC. Crops to fill (phone footage is usually already 9:16)."""
    info = await probe(src)
    if not info["has_video"]:
        raise MediaError("The file has no video track")
    if not info["has_audio"]:
        raise MediaError("The video has no sound. Record with the microphone on: the edit keeps your real voice.")
    code, err = await _run(
        "-y", "-i", str(src),
        "-vf", f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,crop={OUT_W}:{OUT_H},fps={OUT_FPS},setsar=1",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(dst),
    )
    if code != 0:
        raise MediaError("Could not convert the video: " + err.strip().splitlines()[-1][:200])
    return {**info, "width": OUT_W, "height": OUT_H, "fps": OUT_FPS}


async def extract_audio(src: Path, dst: Path) -> None:
    """16 kHz mono WAV: small, and what speech-to-text services want."""
    code, err = await _run("-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst))
    if code != 0:
        raise MediaError("Could not extract audio: " + err.strip().splitlines()[-1][:200])


async def detect_silences(src: Path, noise_db: int = -35, min_s: float = 0.3) -> List[Dict[str, float]]:
    _, err = await _run("-i", str(src), "-af", f"silencedetect=noise={noise_db}dB:d={min_s}", "-f", "null", "-")
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return [{"start": round(s, 3), "end": round(e, 3)} for s, e in zip(starts, ends)]


async def sample_frames(src: Path, out_dir: Path, duration: float, count: int = 6) -> List[Path]:
    """Evenly spaced JPEG frames (540px wide) for Claude to look at."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        t = duration * (i + 0.5) / count
        p = out_dir / f"frame_{i}.jpg"
        code, _ = await _run("-y", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1", "-vf", "scale=540:-2", "-q:v", "4", str(p))
        if code == 0 and p.exists():
            paths.append(p)
    return paths
