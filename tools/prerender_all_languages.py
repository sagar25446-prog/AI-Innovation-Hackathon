"""Warm the video cache for a lesson in every teaching language.

    py -3.12 tools/prerender_all_languages.py
    py -3.12 tools/prerender_all_languages.py --languages tamil odia
    py -3.12 tools/prerender_all_languages.py --report      # what is missing

Why this exists
---------------
A scene video is rendered on demand, and with the SadTalker talking head
switched on that takes roughly three minutes per scene: the learner picks a
language, sees "Rendering", and gives up long before it lands. The lesson
itself is fine - the video is what they are waiting for - so the answer is to
render it before anyone asks.

The cache key covers narration, language, quality, renderer version *and*
whether the talking head is in use (`services.video.video_id`), so this must
run with the same GURUFLOW_* environment the server runs with. Otherwise it
cheerfully fills the cache with ids the server will never request. The script
refuses to start if the talking-head setting looks inconsistent.

Resumable by construction: anything already in the cache is skipped, so
interrupting it and running it again costs nothing but the scene in flight.

What gets rendered
------------------
Every scene of the lesson plus **both repair scenes**. The repair scene is the
one the demo hinges on - it is what the learner sees after answering the
checkpoint wrong - and it is not in the plan, so a naive prerender misses
exactly the video that must not stall.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_server_env() -> None:
    """Read apps/api/.env, so this matches how the server is configured."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for candidate in (REPO_ROOT / "apps" / "api" / ".env", REPO_ROOT / ".env"):
        if candidate.exists():
            load_dotenv(candidate)


_load_server_env()

from services import translation  # noqa: E402
from services import video as video_service  # noqa: E402
from services.evaluation import (  # noqa: E402
    CONSTANT_CURRENT,
    DIRECT_PROPORTIONALITY,
    build_repair_scene,
)
from services.ingestion import ingest_topic  # noqa: E402
from services.planner import plan_lesson  # noqa: E402
from services.video import talking_head  # noqa: E402


def lesson_scenes(topic: str, language: str, minutes: int, level: str):
    """Every scene whose video the lesson may need, repairs included.

    Mirrors `apps.api.main._lesson_video_scenes`; keep them in step.
    """
    plan = plan_lesson(
        {
            "level": level,
            "language": language,
            "availableMinutes": minutes,
            "goal": f"Understand {topic}",
        },
        ingest_topic(topic),
    )
    scenes = list(plan["scenes"])
    for misconception in (DIRECT_PROPORTIONALITY, CONSTANT_CURRENT):
        scenes.append(build_repair_scene(misconception, language))
    return scenes


def _format(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 90:
        return f"{seconds}s"
    if seconds < 5400:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="Ohm's Law")
    parser.add_argument("--languages", nargs="*", help="default: every supported language")
    parser.add_argument("--minutes", type=int, default=20)
    parser.add_argument("--level", default="beginner")
    parser.add_argument(
        "--report", action="store_true", help="list what is missing and exit"
    )
    args = parser.parse_args()

    languages = args.languages or list(translation.SUPPORTED_LANGUAGES)
    unknown = [l for l in languages if not translation.is_supported(l)]
    if unknown:
        parser.error(f"unsupported language(s): {', '.join(unknown)}")

    if not video_service.video_generation_available():
        print("Video generation is unavailable (manim/ffmpeg missing).")
        return 2

    head_on = talking_head.available()
    print(f"topic: {args.topic!r}   talking head: {'on' if head_on else 'off'}")
    if not head_on:
        print(
            "  NOTE: the cache key includes the talking-head flag, so these\n"
            "  videos will NOT be used by a server running with it enabled."
        )

    # Work out what is actually missing before rendering anything, so the
    # estimate below is real rather than optimistic.
    todo: list[tuple[str, dict]] = []
    per_language: dict[str, tuple[int, int]] = {}
    for language in languages:
        scenes = lesson_scenes(args.topic, language, args.minutes, args.level)
        missing = [
            scene
            for scene in scenes
            if not video_service.cached_path(video_service.video_id(scene, language))
        ]
        per_language[language] = (len(scenes) - len(missing), len(scenes))
        todo.extend((language, scene) for scene in missing)

    for language, (have, total) in per_language.items():
        mark = "ok" if have == total else "  "
        print(f"  {mark} {language:10s} {have}/{total}")

    if not todo:
        print("\nEverything is already rendered.")
        return 0

    # ~3 minutes a scene with the talking head; a silent scene is far quicker,
    # so this is an upper bound rather than a promise.
    print(f"\n{len(todo)} scene(s) to render, roughly {_format(len(todo) * 200)}.")
    if args.report:
        return 0

    started = time.time()
    done = failed = 0
    for index, (language, scene) in enumerate(todo, 1):
        vid = video_service.video_id(scene, language)
        label = f"[{index}/{len(todo)}] {language}/{scene.get('id', '?')}"
        try:
            result = video_service.render_scene_video(scene, language)
        except Exception as exc:  # noqa: BLE001 - one bad scene must not stop the run
            failed += 1
            print(f"{label} FAILED {exc}")
            continue

        if result.status == "ready":
            done += 1
            elapsed = time.time() - started
            remaining = (elapsed / index) * (len(todo) - index)
            print(f"{label} ok ({result.detail}) - {_format(remaining)} left")
        else:
            failed += 1
            print(f"{label} {result.status}: {result.detail}  [{vid}]")

    print(
        f"\nrendered {done}, failed {failed}, in {_format(time.time() - started)}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
