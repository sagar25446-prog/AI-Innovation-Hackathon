"""Teaching-video generation.

Turns a contract ``Scene`` into a narrated MP4:

    Scene -> Manim animation (silent mp4)
          -> edge-tts narration  (mp3)
          -> ffmpeg mux          -> cached mp4

Videos are cached on a hash of everything that affects the output, so a scene
renders once and is served instantly thereafter. Nothing here is on the request
path by default: the API renders in a background thread and the client keeps
showing the animated SVG until the file is ready.

Design note: the visuals are drawn programmatically rather than sampled from a
generative video model. A text-to-video model cannot be trusted to draw a
correct circuit or a correct I = V/R curve, and a plausible-but-wrong diagram
would undermine the source-grounding the product is built on.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.ffmpeg_util import ffmpeg_available, mux_audio_video
from services.voice import caption_lines, synthesize

logger = logging.getLogger(__name__)

# Cache lives outside the repo by default: AGENTS.md forbids committing large
# generated media, and these are regenerable artefacts.
CACHE_DIR = Path(
    os.environ.get(
        "GURUFLOW_VIDEO_CACHE",
        str(Path(tempfile.gettempdir()) / "guruflow_videos"),
    )
)

# 720p30 by default. Set GURUFLOW_VIDEO_QUALITY=low for ~4x faster renders when
# demonstrating on a slow machine.
QUALITY = os.environ.get("GURUFLOW_VIDEO_QUALITY", "medium").strip().lower()

# Manim's own quality keys; each one already implies resolution and frame rate.
_QUALITY_MAP = {
    "low": "low_quality",        # 854x480 @ 15fps
    "medium": "medium_quality",  # 1280x720 @ 30fps
    "high": "high_quality",      # 1920x1080 @ 60fps
}

# One render at a time. Manim mutates global config, and parallel renders on a
# laptop only make each other slower.
_RENDER_LOCK = threading.Lock()

# Hash -> "rendering" | "ready" | "failed:<reason>"
_STATUS: dict[str, str] = {}
_STATUS_LOCK = threading.Lock()


@dataclass
class VideoResult:
    video_id: str
    path: Path | None
    status: str
    detail: str = ""

    @property
    def ready(self) -> bool:
        return self.status == "ready" and self.path is not None


def manim_available() -> bool:
    try:
        import manim  # noqa: F401
    except Exception:
        return False
    return True


def video_generation_available() -> bool:
    return manim_available() and ffmpeg_available()


def video_id(scene: dict[str, Any], language: str) -> str:
    """Stable id over everything that changes the rendered output."""
    payload = {
        "narration": scene.get("narration", ""),
        "objective": scene.get("objective", ""),
        "visual": scene.get("visual", {}),
        "duration": scene.get("durationSeconds", 0),
        "isRepair": bool(scene.get("isRepair")),
        "grounded": bool(scene.get("citations")),
        "language": language,
        "quality": QUALITY,
        # Bump when the renderer's look changes so stale videos are not served.
        "renderer": "v2",
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:20]


def cached_path(vid: str) -> Path | None:
    path = CACHE_DIR / f"{vid}.mp4"
    return path if path.exists() and path.stat().st_size > 0 else None


def get_status(vid: str) -> str:
    if cached_path(vid) is not None:
        return "ready"
    with _STATUS_LOCK:
        return _STATUS.get(vid, "absent")


def _set_status(vid: str, status: str) -> None:
    with _STATUS_LOCK:
        _STATUS[vid] = status


def _first_citation(scene: dict[str, Any]) -> str:
    citations = scene.get("citations") or []
    if not citations:
        return "Taught from general knowledge - not from the uploaded material"
    first = citations[0]
    heading = first.get("heading")
    where = f"page {first.get('pageOrSlide')}"
    document = first.get("documentId", "source")
    return f"Source: {document}, {where}" + (f" - {heading}" if heading else "")


def _render_manim(payload: dict[str, Any], out_path: Path) -> bool:
    """Render the silent animation. Returns True on success."""
    import imageio_ffmpeg
    from manim import config, tempconfig

    from services.video.scenes import LessonVideoScene

    quality_name = _QUALITY_MAP.get(QUALITY, _QUALITY_MAP["medium"])

    with tempfile.TemporaryDirectory(prefix="guruflow_manim_") as work_dir:
        settings = {
            "media_dir": work_dir,
            "video_dir": work_dir,
            "quality": quality_name,
            "disable_caching": True,
            "verbosity": "ERROR",
            "progress_bar": "none",
            "ffmpeg_executable": imageio_ffmpeg.get_ffmpeg_exe(),
            "output_file": "scene",
        }
        try:
            with tempconfig(settings):
                LessonVideoScene.payload = payload
                scene = LessonVideoScene()
                scene.render()
                produced = Path(scene.renderer.file_writer.movie_file_path)
            if not produced.exists():
                logger.error("Manim reported success but produced no file.")
                return False
            out_path.parent.mkdir(parents=True, exist_ok=True)
            # Copy then rename so a partially copied file is never observable.
            staging = out_path.with_suffix(".copying")
            shutil.copy2(produced, staging)
            staging.replace(out_path)
            return True
        except Exception as exc:
            logger.exception("Manim render failed: %s", exc)
            return False


def render_scene_video(
    scene: dict[str, Any],
    language: str = "hinglish",
    force: bool = False,
) -> VideoResult:
    """Render (or fetch from cache) the teaching video for one Scene.

    Blocking. Callers on a request path should use the background renderer.
    """
    vid = video_id(scene, language)

    existing = cached_path(vid)
    if existing is not None and not force:
        return VideoResult(vid, existing, "ready")

    if not video_generation_available():
        detail = "manim not installed" if not manim_available() else "ffmpeg unavailable"
        _set_status(vid, f"failed:{detail}")
        return VideoResult(vid, None, "failed", detail)

    with _RENDER_LOCK:
        # Another thread may have finished this while we waited for the lock.
        existing = cached_path(vid)
        if existing is not None and not force:
            return VideoResult(vid, existing, "ready")

        _set_status(vid, "rendering")
        narration = scene.get("narration", "") or ""

        try:
            speech = synthesize(narration, language)
        except Exception as exc:
            logger.warning("Narration failed for %s: %s", vid, exc)
            speech = None

        if speech is not None and speech.duration_seconds:
            duration = speech.duration_seconds
        else:
            duration = float(scene.get("durationSeconds", 12) or 12)

        # A little tail so the last caption is readable before the cut.
        duration = max(4.0, duration + 0.6)

        captions = (
            caption_lines(speech, narration) if speech is not None else []
        )

        payload = {
            "objective": scene.get("objective", ""),
            "visual": scene.get("visual", {}),
            "captions": captions,
            "duration": duration,
            "grounded": bool(scene.get("citations")),
            "isRepair": bool(scene.get("isRepair")),
            "citation": _first_citation(scene),
        }

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        silent = CACHE_DIR / f"{vid}.silent.mp4"
        final = CACHE_DIR / f"{vid}.mp4"

        if not _render_manim(payload, silent):
            _set_status(vid, "failed:render")
            return VideoResult(vid, None, "failed", "animation render failed")

        # No audio? The silent animation is still a usable teaching video.
        if speech is None or not speech.has_audio:
            silent.replace(final)
            _set_status(vid, "ready")
            return VideoResult(vid, final, "ready", "no narration audio")

        audio_path = CACHE_DIR / f"{vid}.mp3"
        audio_path.write_bytes(speech.audio)

        # Mux to a scratch name and rename only once ffmpeg has finished.
        # Writing straight to the final path makes the file visible - and so
        # "ready" - while it is still being written, and the browser then
        # caches a truncated, undecodable video.
        staged = CACHE_DIR / f"{vid}.part.mp4"
        if mux_audio_video(silent, audio_path, staged):
            staged.replace(final)
            silent.unlink(missing_ok=True)
            audio_path.unlink(missing_ok=True)
            _set_status(vid, "ready")
            return VideoResult(vid, final, "ready", speech.provider)
        staged.unlink(missing_ok=True)

        # Mux failed: keep the silent video rather than losing the scene.
        silent.replace(final)
        audio_path.unlink(missing_ok=True)
        _set_status(vid, "ready")
        return VideoResult(vid, final, "ready", "mux failed - silent video")


def render_in_background(scene: dict[str, Any], language: str = "hinglish") -> str:
    """Kick off a render and return immediately with the video id."""
    vid = video_id(scene, language)
    if cached_path(vid) is not None:
        return vid
    with _STATUS_LOCK:
        if _STATUS.get(vid) == "rendering":
            return vid
        _STATUS[vid] = "rendering"

    def worker() -> None:
        try:
            render_scene_video(scene, language)
        except Exception as exc:
            logger.exception("Background render failed: %s", exc)
            _set_status(vid, "failed:worker")

    threading.Thread(target=worker, daemon=True, name=f"video-{vid}").start()
    return vid


def prerender_lesson(scenes: list[dict[str, Any]], language: str = "hinglish") -> list[str]:
    """Render every scene of a lesson in order, in one background thread."""
    ids = [video_id(scene, language) for scene in scenes]

    def worker() -> None:
        for scene in scenes:
            try:
                render_scene_video(scene, language)
            except Exception as exc:
                logger.warning("Prerender skipped a scene: %s", exc)

    for vid in ids:
        with _STATUS_LOCK:
            if cached_path(vid) is None and vid not in _STATUS:
                _STATUS[vid] = "rendering"

    threading.Thread(target=worker, daemon=True, name="video-prerender").start()
    return ids


def cache_stats() -> dict[str, Any]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    files = list(CACHE_DIR.glob("*.mp4"))
    return {
        "dir": str(CACHE_DIR),
        "videos": len(files),
        "bytes": sum(f.stat().st_size for f in files),
        "quality": QUALITY,
        "available": video_generation_available(),
    }
