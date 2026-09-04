"""Photoreal talking-head generation for the teacher panel.

Optional. When it is not configured, the lesson video uses the drawn avatar and
nothing changes -- this is an enhancement path, never a dependency.

Driven by **SadTalker**, which takes a *still portrait* plus an audio track and
synthesises head motion, blinks and lip movement from scratch. That removes the
idle-video step an inpainting model needs: no LivePortrait pass, no seamless
loop to prepare, one asset instead of two.

Why not the alternatives
------------------------
* **MuseTalk** inpaints only the mouth of an existing video. Cheaper, but the
  sync quality was not good enough here, and it needs an idle clip.
* **EchoMimic V2 / AniPortrait / LatentSync** are better but want 12-24 GB of
  VRAM. Out of reach on a 6 GB card.

Fitting SadTalker into 6 GB
---------------------------
``--preprocess crop`` with ``--size 256`` is the low-VRAM configuration, and it
happens to be exactly right here: the teacher panel is only ~248x292 px in a
720p frame, so a 256x256 face is already at native resolution. Running the
GFPGAN enhancer or ``--size 512`` would cost VRAM and minutes to produce detail
the panel physically cannot show.

SadTalker generates rather than inpaints, so expect **minutes per scene**, not
seconds. Pre-render before demonstrating.

IMPORTANT - portrait rights
---------------------------
The portrait must be a face you have the right to use: one you generated
synthetically, a licensed stock portrait, or a person who has consented on the
record. Do not point this at a photograph of a real person who has not agreed;
a lip-synced video of an identifiable person saying things they never said is a
deepfake regardless of intent. ``PORTRAIT_RIGHTS_NOTE`` is surfaced in
``/health`` and the setup docs so this is not something a teammate can drift
past by accident.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from services.ffmpeg_util import to_wav_16k_mono

logger = logging.getLogger(__name__)

PORTRAIT_RIGHTS_NOTE = (
    "The portrait must use a face you have rights to: a synthetic portrait, "
    "a licensed stock portrait, or a person who has consented. Do not use a "
    "photograph of a real person without their permission."
)

_PORTRAIT_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

_INFERENCE_TIMEOUT_SECONDS = int(
    os.environ.get("GURUFLOW_TALKING_HEAD_TIMEOUT", "1800")
)


@dataclass(frozen=True)
class TalkingHeadConfig:
    """Everything needed to drive SadTalker, all from the environment."""

    enabled: bool
    sadtalker_dir: Path | None
    python_exe: str
    portrait: Path | None
    preprocess: str
    size: int
    still: bool
    expression_scale: float
    enhancer: str | None

    @classmethod
    def from_env(cls) -> "TalkingHeadConfig":
        raw_dir = os.environ.get("GURUFLOW_SADTALKER_DIR", "").strip()
        raw_portrait = os.environ.get("GURUFLOW_TEACHER_PORTRAIT", "").strip()
        enhancer = os.environ.get("GURUFLOW_SADTALKER_ENHANCER", "").strip()
        return cls(
            enabled=os.environ.get("GURUFLOW_TALKING_HEAD", "0").strip().lower()
            in ("1", "true", "yes", "on"),
            sadtalker_dir=Path(raw_dir) if raw_dir else None,
            # SadTalker needs its own interpreter; point this at that venv.
            python_exe=os.environ.get("GURUFLOW_SADTALKER_PYTHON", "python"),
            portrait=Path(raw_portrait) if raw_portrait else None,
            # "crop" is the low-VRAM path and the right one for a small panel.
            preprocess=os.environ.get("GURUFLOW_SADTALKER_PREPROCESS", "crop"),
            size=int(os.environ.get("GURUFLOW_SADTALKER_SIZE", "256")),
            # Still mode suppresses head sway, which reads better for a teacher
            # and avoids the face drifting out of the panel.
            still=os.environ.get("GURUFLOW_SADTALKER_STILL", "1").strip().lower()
            in ("1", "true", "yes", "on"),
            # Mouth openness. Raise toward ~1.3 if the lips look under-articulated.
            expression_scale=float(
                os.environ.get("GURUFLOW_SADTALKER_EXPRESSION", "1.0")
            ),
            # GFPGAN roughly doubles runtime and VRAM; off by default on 6 GB.
            enhancer=enhancer or None,
        )

    def problems(self) -> list[str]:
        """Human-readable reasons this cannot run, for the health endpoint."""
        issues: list[str] = []
        if not self.enabled:
            issues.append("GURUFLOW_TALKING_HEAD is not set to 1")
        if self.sadtalker_dir is None:
            issues.append("GURUFLOW_SADTALKER_DIR is not set")
        elif not (self.sadtalker_dir / "inference.py").exists():
            issues.append(f"no SadTalker checkout at {self.sadtalker_dir}")
        if self.portrait is None:
            issues.append("GURUFLOW_TEACHER_PORTRAIT is not set")
        elif not self.portrait.exists():
            issues.append(f"portrait not found at {self.portrait}")
        elif self.portrait.suffix.lower() not in _PORTRAIT_SUFFIXES:
            issues.append(
                f"portrait must be a still image, got {self.portrait.suffix} "
                "(SadTalker takes an image, not a video)"
            )
        return issues

    @property
    def usable(self) -> bool:
        return not self.problems()


def config() -> TalkingHeadConfig:
    # Read every call so a .env edit does not need a restart.
    return TalkingHeadConfig.from_env()


def available() -> bool:
    return config().usable


def status() -> dict[str, object]:
    current = config()
    return {
        "engine": "sadtalker",
        "enabled": current.enabled,
        "usable": current.usable,
        "problems": current.problems(),
        "portrait": str(current.portrait) if current.portrait else None,
        "preprocess": current.preprocess,
        "size": current.size,
        "portraitRights": PORTRAIT_RIGHTS_NOTE,
    }


def _cache_key(audio_path: Path, cfg: TalkingHeadConfig) -> str:
    digest = hashlib.sha256()
    digest.update(audio_path.read_bytes())
    if cfg.portrait and cfg.portrait.exists():
        stat = cfg.portrait.stat()
        digest.update(f"{cfg.portrait}:{stat.st_size}:{int(stat.st_mtime)}".encode())
    digest.update(
        f"{cfg.preprocess}:{cfg.size}:{cfg.still}:{cfg.expression_scale}:"
        f"{cfg.enhancer}".encode()
    )
    return digest.hexdigest()[:20]


def _newest_result(results_dir: Path) -> Path | None:
    """SadTalker writes into a timestamped subdirectory under result_dir."""
    if not results_dir.exists():
        return None
    videos = [p for p in results_dir.rglob("*.mp4") if p.stat().st_size > 0]
    if not videos:
        return None
    return max(videos, key=lambda p: p.stat().st_mtime)



def _subprocess_env() -> dict[str, str]:
    """Environment for SadTalker, guaranteed to have `ffmpeg` on PATH.

    SadTalker's `save_video_with_watermark` shells out to a bare `ffmpeg`, so
    without it on PATH the model runs to completion and then dies on the final
    mux - having burned the whole render. GuruFlow ships `imageio-ffmpeg`, but
    its binary is named `ffmpeg-win-x86_64-v7.1.exe`, so putting that directory
    on PATH does not satisfy a bare `ffmpeg` call.

    If nothing resolves, a directory containing a correctly-named copy is
    materialised once and prepended. That way the integration does not depend
    on the operator having installed ffmpeg system-wide.
    """
    env = dict(os.environ)

    if shutil.which("ffmpeg", path=env.get("PATH", "")):
        return env

    from services.ffmpeg_util import ffmpeg_path

    binary = ffmpeg_path()
    if binary is None:
        logger.warning("No ffmpeg available; SadTalker will fail at the mux step.")
        return env

    shim_dir = Path(tempfile.gettempdir()) / "guruflow_ffmpeg_shim"
    shim_dir.mkdir(parents=True, exist_ok=True)
    shim = shim_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if not shim.exists():
        shutil.copy2(binary, shim)
        logger.info("Created ffmpeg shim for SadTalker at %s", shim)

    env["PATH"] = f"{shim_dir}{os.pathsep}{env.get('PATH', '')}"
    return env


def generate(audio_path: Path, cache_dir: Path) -> Path | None:
    """Animate the teacher portrait so it speaks the given narration.

    Returns a path to the generated clip, or None if generation is
    unconfigured or fails. Failure is never fatal: the caller falls back to the
    drawn avatar.
    """
    cfg = config()
    if not cfg.usable:
        logger.debug("Talking head not configured: %s", cfg.problems())
        return None

    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(audio_path, cfg)
    cached = cache_dir / f"head-{key}.mp4"
    if cached.exists() and cached.stat().st_size > 0:
        return cached

    with tempfile.TemporaryDirectory(prefix="guruflow_head_") as work:
        work_dir = Path(work)
        results_dir = work_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        # SadTalker is happiest with plain PCM wav; edge-tts gives us 24 kHz MP3.
        wav_path = work_dir / "narration.wav"
        if not to_wav_16k_mono(audio_path, wav_path):
            logger.warning("Could not convert narration to wav.")
            return None

        command = [
            cfg.python_exe, "inference.py",
            "--driven_audio", str(wav_path),
            "--source_image", str(cfg.portrait),
            "--result_dir", str(results_dir),
            "--preprocess", cfg.preprocess,
            "--size", str(cfg.size),
            "--expression_scale", str(cfg.expression_scale),
        ]
        if cfg.still:
            command.append("--still")
        if cfg.enhancer:
            command += ["--enhancer", cfg.enhancer]

        logger.info("Running SadTalker: %s", " ".join(command))
        try:
            completed = subprocess.run(
                command,
                cwd=str(cfg.sadtalker_dir),
                env=_subprocess_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=_INFERENCE_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.error(
                "SadTalker timed out after %ss. It generates rather than "
                "inpaints, so long scenes are slow; raise "
                "GURUFLOW_TALKING_HEAD_TIMEOUT or lower GURUFLOW_VIDEO_QUALITY.",
                _INFERENCE_TIMEOUT_SECONDS,
            )
            return None
        except FileNotFoundError:
            logger.error("SadTalker python not found: %s", cfg.python_exe)
            return None

        if completed.returncode != 0:
            tail = completed.stdout.decode("utf-8", "replace")[-800:]
            logger.error(
                "SadTalker failed (exit %s). Last output:\n%s",
                completed.returncode,
                tail,
            )
            return None

        produced = _newest_result(results_dir)
        if produced is None:
            # Some builds ignore --result_dir and write into ./results.
            produced = _newest_result(cfg.sadtalker_dir / "results")
        if produced is None:
            logger.error("SadTalker produced no video.")
            return None

        staging = cache_dir / f"head-{key}.part.mp4"
        shutil.copy2(produced, staging)
        staging.replace(cached)
        return cached
