"""
AI Video Edit: turn a raw talking-head take (+ optional hook takes) into finished reels.

    ingest (media.py) -> transcribe (transcribe.py: local free models / ElevenLabs)
    -> Claude plans the edit (director.py) -> frame-exact timeline with beats, zooms, sound cues (timeline.py)
    -> Claude checks rendered test frames (director.review_plan)
    -> cut-outs (masks.py) + sound effects (sfx.py) -> Remotion render + loudness finish (render.py)

Basic mode needs only Claude: speech-to-text, cut-outs, sound effects and rendering run on this server
with free tools. Reference photos (side / profile / from above) are stored for the generative
camera-angle and room steps of the advanced mode.
"""
from .director import BEAT_TYPES, DirectorError, director_mode, plan_edit, review_plan
from .masks import masks_available
from .media import MediaError, extract_audio, instagram_ready, normalise, probe, sample_frames
from .render import (RenderError, contact_sheet, cover_frame, finish_audio, prepare_variant, renderer_ready, run_job,
                     stage_inputs)
from .timeline import build_variants, mask_requests
from .transcribe import TranscriptionError, pick_engine, stt_mode, transcribe
from .transcribe_local import local_available

__all__ = [
    "BEAT_TYPES", "DirectorError", "MediaError", "RenderError", "TranscriptionError",
    "build_variants", "contact_sheet", "cover_frame", "director_mode", "extract_audio", "finish_audio",
    "instagram_ready", "local_available", "mask_requests", "masks_available", "normalise", "pick_engine", "plan_edit", "prepare_variant",
    "probe", "renderer_ready", "review_plan", "run_job", "sample_frames", "stage_inputs", "stt_mode", "transcribe",
]
