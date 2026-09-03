"""Photoreal talking-head generation for the teacher panel.

Optional. When it is not configured, the lesson video uses the drawn avatar and
nothing changes -- this is an enhancement path, never a dependency.

MuseTalk is used because it inpaints only the mouth region of an existing
video, so it fits in ~4-6 GB of VRAM where full-body diffusion models
(EchoMimic V2, Hallo 2) need 12-24 GB. It runs as a separate process in its own
environment: MuseTalk pins torch/mmcv/mmpose versions that would otherwise
fight with the API's dependencies.

IMPORTANT - portrait rights
---------------------------
The idle video must show a face you have the right to use: a synthetic portrait
you generated, a stock portrait you licensed, or someone who has consented on
the record. Do not point this at a photograph of a real person who has not
agreed to front your product; a lip-synced video of an identifiable person
saying things they never said is a deepfake regardless of intent.
``PORTRAIT_RIGHTS_NOTE`` is surfaced in the API and the setup docs so this is
not something a teammate can drift past by accident.
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
    "The idle video must use a face you have rights to: a synthetic portrait, "
    "a licensed stock portrait, or a person who has consented. Do not use a "
    "photograph of a real person without their permission."
)

# Where MuseTalk writes its results, relative to its own repository root.
_MUSETALK_RESULTS = Path("results")

_INFERENCE_TIMEOUT_SECONDS = int(
    os.environ.get("GURUFLOW_TALKING_HEAD_TIMEOUT", "900")
)


@dataclass(frozen=True)
class TalkingHeadConfig:
    """Everything needed to drive MuseTalk, all from the environment."""

    enabled: bool
    musetalk_dir: Path | None
    python_exe: str
    idle_video: Path | None
    bbox_shift: int
    version: str

    @classmethod
    def from_env(cls) -> "TalkingHeadConfig":
        raw_dir = os.environ.get("GURUFLOW_MUSETALK_DIR", "").strip()
        raw_idle = os.environ.get("GURUFLOW_TEACHER_IDLE_VIDEO", "").strip()
        return cls(
            enabled=os.environ.get("GURUFLOW_TALKING_HEAD", "0").strip().lower()
            in ("1", "true", "yes", "on"),
            musetalk_dir=Path(raw_dir) if raw_dir else None,
            # MuseTalk needs its own interpreter; point this at that venv.
            python_exe=os.environ.get("GURUFLOW_MUSETALK_PYTHON", "python"),
            idle_video=Path(raw_idle) if raw_idle else None,
            # MuseTalk's main quality knob: shifts the detected mouth box.
            # Negative values open the mouth more. Tune per portrait.
            bbox_shift=int(os.environ.get("GURUFLOW_MUSETALK_BBOX_SHIFT", "0")),
            version=os.environ.get("GURUFLOW_MUSETALK_VERSION", "v15"),
        )

    def problems(self) -> list[str]:
        """Human-readable reasons this cannot run, for the health endpoint."""
        issues: list[str] = []
        if not self.enabled:
            issues.append("GURUFLOW_TALKING_HEAD is not set to 1")
        if self.musetalk_dir is None:
            issues.append("GURUFLOW_MUSETALK_DIR is not set")
        elif not (self.musetalk_dir / "scripts").exists():
            issues.append(f"no MuseTalk checkout at {self.musetalk_dir}")
        if self.idle_video is None:
            issues.append("GURUFLOW_TEACHER_IDLE_VIDEO is not set")
        elif not self.idle_video.exists():
            issues.append(f"idle video not found at {self.idle_video}")
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
        "enabled": current.enabled,
        "usable": current.usable,
        "problems": current.problems(),
        "idleVideo": str(current.idle_video) if current.idle_video else None,
        "portraitRights": PORTRAIT_RIGHTS_NOTE,
    }


def _cache_key(audio_path: Path, cfg: TalkingHeadConfig) -> str:
    digest = hashlib.sha256()
    digest.update(audio_path.read_bytes())
    if cfg.idle_video and cfg.idle_video.exists():
        stat = cfg.idle_video.stat()
        digest.update(f"{cfg.idle_video}:{stat.st_size}:{int(stat.st_mtime)}".encode())
    digest.update(f"{cfg.bbox_shift}:{cfg.version}".encode())
    return digest.hexdigest()[:20]


def _newest_result(results_dir: Path) -> Path | None:
    if not results_dir.exists():
        return None
    videos = list(results_dir.rglob("*.mp4"))
    if not videos:
        return None
    return max(videos, key=lambda p: p.stat().st_mtime)


def generate(audio_path: Path, cache_dir: Path) -> Path | None:
    """Lip-sync the idle teacher video to a narration track.

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

        # MuseTalk feeds audio to Whisper, which wants 16 kHz mono PCM.
        wav_path = work_dir / "narration.wav"
        if not to_wav_16k_mono(audio_path, wav_path):
            logger.warning("Could not convert narration to 16 kHz wav.")
            return None

        config_path = work_dir / "guruflow_task.yaml"
        config_path.write_text(
            "task_0:\n"
            f'  video_path: "{cfg.idle_video.as_posix()}"\n'
            f'  audio_path: "{wav_path.as_posix()}"\n'
            f"  bbox_shift: {cfg.bbox_shift}\n",
            encoding="utf-8",
        )

        command = [
            cfg.python_exe, "-m", "scripts.inference",
            "--inference_config", str(config_path),
            "--result_dir", str(work_dir / "results"),
        ]
        # MuseTalk 1.5 selects the model generation with --version.
        if cfg.version:
            command += ["--version", cfg.version]

        logger.info("Running MuseTalk: %s", " ".join(command))
        try:
            completed = subprocess.run(
                command,
                cwd=str(cfg.musetalk_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=_INFERENCE_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.error("MuseTalk timed out after %ss.", _INFERENCE_TIMEOUT_SECONDS)
            return None
        except FileNotFoundError:
            logger.error("MuseTalk python not found: %s", cfg.python_exe)
            return None

        if completed.returncode != 0:
            tail = completed.stdout.decode("utf-8", "replace")[-600:]
            logger.error("MuseTalk failed (exit %s): %s", completed.returncode, tail)
            return None

        produced = _newest_result(work_dir / "results")
        if produced is None:
            # Older MuseTalk builds ignore --result_dir and write in-tree.
            produced = _newest_result(cfg.musetalk_dir / _MUSETALK_RESULTS)
        if produced is None:
            logger.error("MuseTalk produced no video.")
            return None

        staging = cache_dir / f"head-{key}.part.mp4"
        shutil.copy2(produced, staging)
        staging.replace(cached)
        return cached
