"""Long-term, cross-session student memory for GuruFlow.

The lesson repository stores what happens inside one session (process-local).
This module adds genuinely persistent memory that survives a server restart:
it flushes each student's accumulated profile to disk (JSON) so a returning
learner's weak spots and mastery are remembered across lessons.

Storage is intentionally dependency-light: a directory of per-student JSON
files (``GURUFLOW_MEMORY_DIR`` or a temp dir). The in-memory cache makes
reads cheap; every mutation is persisted immediately.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from .store import LessonSession

DEFAULT_MEMORY_DIR = os.environ.get(
    "GURUFLOW_MEMORY_DIR",
    str(Path(tempfile.gettempdir()) / "guruflow_students"),
)

_MASTERY_FLOOR = 0.5


class StudentMemoryStore:
    """File-backed, thread-safe long-term memory for students.

    Responsible for durability across restarts; callers supply the current
    lesson's report for a student and we fold it into their evolving profile.
    """

    def __init__(self, directory: str | None = None) -> None:
        self._dir = Path(directory or DEFAULT_MEMORY_DIR)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._cache: dict[str, dict[str, Any]] = {}

    # -- profiles ------------------------------------------------------------

    def _path(self, student_id: str) -> Path:
        safe = "".join(c for c in student_id if c.isalnum() or c in "-_.") or "student"
        return self._dir / f"{safe}.json"

    def _load(self, student_id: str) -> dict[str, Any]:
        with self._lock:
            if student_id in self._cache:
                return self._cache[student_id]
            path = self._path(student_id)
            profile: dict[str, Any] = {
                "studentId": student_id,
                "createdAt": _now_ms(),
                "lessons": [],
                "conceptMastery": {},
                "weakConcepts": [],
                "misconceptions": [],
            }
            if path.exists():
                try:
                    profile.update(json.loads(path.read_text(encoding="utf-8")))
                except (ValueError, OSError):
                    pass
            self._cache[student_id] = profile
            return profile

    def _save(self, profile: dict[str, Any]) -> None:
        with self._lock:
            self._cache[profile["studentId"]] = profile
            path = self._path(profile["studentId"])
            tmp = path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(profile, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(path)

    # -- public API ------------------------------------------------------------

    def record_lesson(
        self,
        session: LessonSession,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        """Fold a finished lesson's report into the student's long-term memory.

        Mastery is a running average per concept; recurring misconceptions are
        counted; a lesson history entry is appended for the dashboard.
        """
        student_id = session.student_id
        profile = self._load(student_id)

        # Per-concept running mastery.
        for concept, mastery in report.get("conceptMastery", {}).items():
            current = profile["conceptMastery"].get(concept)
            if current is None:
                profile["conceptMastery"][concept] = round(mastery, 3)
            else:
                profile["conceptMastery"][concept] = round(
                    (current + mastery) / 2, 3
                )

        # Recurring misconception count so the dashboard can show habits.
        existing = {m["id"]: m for m in profile["misconceptions"]}
        for mis in report.get("misconceptions", []):
            mid = mis.get("id", mis.get("misconception"))
            if not mid:
                continue
            entry = existing.get(mid)
            if entry is None:
                existing[mid] = {
                    "id": mid,
                    "concept": mis.get("concept", ""),
                    "timesSeen": 0,
                    "lastStatus": mis.get("status", "open"),
                }
                entry = existing[mid]
            entry["timesSeen"] = entry.get("timesSeen", 0) + 1
            entry["lastStatus"] = mis.get("status", entry.get("lastStatus", "open"))
        profile["misconceptions"] = sorted(
            existing.values(), key=lambda m: m.get("timesSeen", 0), reverse=True
        )

        # Lesson history (most recent last), idempotent per lesson id so
        # re-fetching a report never double-counts the same lesson.
        lesson_ids = {entry["lessonId"] for entry in profile["lessons"]}
        if session.lesson_id not in lesson_ids:
            profile["lessons"].append({
                "lessonId": session.lesson_id,
                "topic": session.plan.get("topic", "Ohm's Law"),
                "score": report.get("score", 0.0),
                "weakConcepts": report.get("weakConcepts", []),
                "completedAt": _now_ms(),
            })

        # Recompute weak concepts across all history (weak == low mastery).
        profile["weakConcepts"] = [
            c
            for c, m in sorted(
                profile["conceptMastery"].items(),
                key=lambda kv: kv[1],
            )
            if m < _MASTERY_FLOOR
        ]

        self._save(profile)
        return profile

    def get_profile(self, student_id: str) -> dict[str, Any] | None:
        """Return a student's accumulated memory, or ``None`` if unknown."""
        profile = self._load(student_id)
        if not profile.get("lessons") and not profile.get("conceptMastery"):
            return None

        # Derived summary fields for a richer dashboard, without mutating the
        # stored record.
        lessons = profile.get("lessons", [])
        mastery = profile.get("conceptMastery", {})
        avg = (
            round(sum(l.get("score", 0.0) for l in lessons) / len(lessons), 3)
            if lessons else 0.0
        )
        return {
            **profile,
            "lessonsCompleted": len(lessons),
            "avgScore": avg,
            "strongConcepts": [
                c
                for c, m in sorted(mastery.items(), key=lambda kv: kv[1], reverse=True)
                if m >= _MASTERY_FLOOR
            ],
            "recurringMisconceptions": [
                m["id"]
                for m in profile.get("misconceptions", [])
                if m.get("timesSeen", 0) > 0
            ],
        }

    def reset(self) -> None:
        """Clear the in-memory cache (used by tests). Keeps files on disk."""
        with self._lock:
            self._cache.clear()


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)
