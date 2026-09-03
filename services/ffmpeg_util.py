"""Locate and drive ffmpeg.

``imageio-ffmpeg`` ships a static ffmpeg binary as a wheel, so neither a judge
nor CI needs a system ffmpeg install. A system binary on PATH is preferred when
present because it is usually newer.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)")


@lru_cache(maxsize=1)
def ffmpeg_path() -> str | None:
    """Path to an ffmpeg binary, or None if there genuinely is not one."""
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        logger.warning("No ffmpeg available: %s", exc)
        return None


def ffmpeg_available() -> bool:
    return ffmpeg_path() is not None


def _run(args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def probe_duration(audio_path: str | Path) -> float | None:
    """Read a media file's duration in seconds.

    Parsed out of ffmpeg's own stderr banner so no separate ffprobe binary is
    required (imageio-ffmpeg ships ffmpeg only).
    """
    binary = ffmpeg_path()
    if binary is None:
        return None
    result = _run([binary, "-hide_banner", "-i", str(audio_path)], timeout=60)
    match = _DURATION_RE.search(result.stderr.decode("utf-8", "replace"))
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def probe_duration_bytes(audio: bytes, suffix: str = ".mp3") -> float | None:
    """Duration of an in-memory media buffer."""
    if not audio:
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(audio)
        tmp.close()
        return probe_duration(tmp.name)
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def mux_audio_video(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    timeout: int = 600,
) -> bool:
    """Combine a silent video with a narration track into one MP4.

    The video is padded to the audio length by the caller, so ``-shortest``
    only trims the sub-second tail.
    """
    binary = ffmpeg_path()
    if binary is None:
        return False

    args = [
        binary, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
    result = _run(args, timeout=timeout)
    if result.returncode != 0:
        logger.error(
            "ffmpeg mux failed: %s", result.stderr.decode("utf-8", "replace")[:400]
        )
        return False
    return True


def to_wav_16k_mono(source: str | Path, output: str | Path) -> bool:
    """Convert audio to 16 kHz mono WAV.

    SadTalker expects a plain PCM wav and edge-tts hands us a 24 kHz MP3, so
    the conversion is mandatory rather than cosmetic.
    """
    binary = ffmpeg_path()
    if binary is None:
        return False
    result = _run([
        binary, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        str(output),
    ])
    if result.returncode != 0:
        logger.error(
            "wav conversion failed: %s",
            result.stderr.decode("utf-8", "replace")[:300],
        )
        return False
    return True


def overlay_video(
    base_path: str | Path,
    overlay_path: str | Path,
    output_path: str | Path,
    x: int,
    y: int,
    width: int,
    height: int,
    timeout: int = 900,
) -> bool:
    """Composite one video over another at a pixel rectangle.

    Used to drop a talking-head clip into the teacher panel of the rendered
    lesson frame. The overlay is looped so a short idle clip still covers a
    longer scene, and ``-shortest`` then takes the length from the base.
    """
    binary = ffmpeg_path()
    if binary is None:
        return False

    # The head clip is looped so a short idle video covers a longer scene.
    # `shortest=1` on the overlay filter - not the `-shortest` output flag - is
    # what actually terminates the render: with `-stream_loop -1` the second
    # input never ends, and `-shortest` does not reliably bound a
    # filter_complex output, so the encode runs forever.
    filter_graph = (
        f"[1:v]scale={width}:{height},setsar=1[head];"
        f"[0:v][head]overlay={x}:{y}:shortest=1[out]"
    )
    result = _run([
        binary, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(base_path),
        "-stream_loop", "-1", "-i", str(overlay_path),
        "-filter_complex", filter_graph,
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ], timeout=timeout)

    if result.returncode != 0:
        logger.error(
            "overlay failed: %s", result.stderr.decode("utf-8", "replace")[:400]
        )
        return False
    return True
