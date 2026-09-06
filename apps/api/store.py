"""Session state and persistence for the GuruFlow teacher brain.

``LessonRepository`` is the seam a Postgres or Supabase implementation slots
into later. The in-memory implementation keeps the hackathon demo free of
infrastructure while the API surface stays unchanged.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from services.ingestion import Material


@dataclass
class LessonSession:
    """Everything the teacher remembers about one learner's lesson."""

    lesson_id: str
    student_id: str
    plan: dict[str, Any]
    material_id: str
    started_at: float = field(default_factory=time.time)
    concept_mastery: dict[str, float] = field(default_factory=dict)
    misconceptions: dict[str, dict[str, Any]] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=dict)
    scenes_completed: set[str] = field(default_factory=set)
    checkpoints_passed: int = 0
    checkpoints_failed: int = 0
    # Result of the end-of-lesson quiz, once the learner has taken it. The
    # report prefers this over checkpoint evidence: one checkpoint answer is a
    # signal, a graded quiz is a measurement.
    quiz_result: dict[str, Any] | None = None

    def record_attempt(self, checkpoint_id: str) -> int:
        """Increment and return the 1-based attempt number for a checkpoint."""
        self.attempts[checkpoint_id] = self.attempts.get(checkpoint_id, 0) + 1
        return self.attempts[checkpoint_id]

    def attempt_count(self, checkpoint_id: str) -> int:
        return self.attempts.get(checkpoint_id, 0)

    def note_misconception(self, misconception: str, concept_id: str) -> None:
        """Record a misconception as open the first time it is diagnosed."""
        existing = self.misconceptions.get(misconception)
        if existing is None:
            self.misconceptions[misconception] = {
                "id": misconception,
                "status": "open",
                "concept": concept_id,
            }
        elif existing["status"] == "resolved":
            # Seen again after being resolved: it is open once more.
            existing["status"] = "open"

    def resolve_misconceptions(self) -> None:
        """Mark every open misconception resolved after a correct retry."""
        for record in self.misconceptions.values():
            if record["status"] == "open":
                record["status"] = "resolved"

    def set_mastery(self, concept_id: str, mastery: float) -> None:
        self.concept_mastery[concept_id] = mastery

    def record_quiz(self, result: dict[str, Any]) -> None:
        """Fold a graded quiz into the session's picture of the learner.

        Quiz evidence *replaces* the checkpoint estimate for any concept it
        covers: the checkpoint saw one answer to one question, the quiz saw the
        learner use the concept. Concepts the quiz did not ask about keep the
        mastery they already had.
        """
        self.quiz_result = result
        for concept_id, mastery in (result.get("conceptMastery") or {}).items():
            self.concept_mastery[concept_id] = mastery
        for misconception in result.get("misconceptions") or []:
            self.note_misconception(misconception, "")

    def elapsed_seconds(self) -> int:
        return int(time.time() - self.started_at)


class LessonRepository(ABC):
    """Storage seam for lessons, materials and learner sessions."""

    @abstractmethod
    def save_material(self, material: Material) -> None: ...

    @abstractmethod
    def get_material(self, material_id: str) -> Material | None: ...

    @abstractmethod
    def save_session(self, session: LessonSession) -> None: ...

    @abstractmethod
    def get_session(self, lesson_id: str) -> LessonSession | None: ...

    @abstractmethod
    def sessions_for_student(self, student_id: str) -> list[LessonSession]: ...



def _material_from_dict(data: dict[str, Any]) -> Material:
    """Reconstruct a Material from its to_dict() output."""
    return Material(
        material_id=data.get("materialId", data.get("material_id", "")),
        document_id=data.get("documentId", data.get("document_id", "")),
        title=data.get("title", ""),
        status=data.get("status", "ready"),
        sections=data.get("sections", []),
        origin=data.get("origin", "builtin"),
    )


class InMemoryLessonRepository(LessonRepository):
    """Process-local store with /tmp file-backed persistence.

    On serverless platforms like Vercel, each request can run on a different
    instance with empty memory.  This implementation keeps the fast in-memory
    dict *and* mirrors every write to ``/tmp/guruflow_store/`` as JSON files,
    so a cold-start instance recovers state from a prior invocation on the
    same container.  ``/tmp`` is per-container (not shared), but Vercel reuses
    containers for minutes, which is long enough for the demo flow.
    """

    _STORE_DIR = Path(os.environ.get(
        "GURUFLOW_STORE_DIR",
        str(Path(tempfile.gettempdir()) / "guruflow_store"),
    ))

    def __init__(self) -> None:
        self._materials: dict[str, Material] = {}
        self._sessions: dict[str, LessonSession] = {}
        self._STORE_DIR.mkdir(parents=True, exist_ok=True)
        self._load_all()

    # -- persistence helpers ------------------------------------------------

    def _session_path(self, lesson_id: str) -> Path:
        return self._STORE_DIR / f"session_{lesson_id}.json"

    def _material_path(self, material_id: str) -> Path:
        return self._STORE_DIR / f"material_{material_id}.json"

    def _persist_session(self, session: LessonSession) -> None:
        try:
            data = {
                "lesson_id": session.lesson_id,
                "student_id": session.student_id,
                "plan": session.plan,
                "material_id": session.material_id,
                "started_at": session.started_at,
                "concept_mastery": session.concept_mastery,
                "misconceptions": session.misconceptions,
                "attempts": session.attempts,
                "scenes_completed": list(session.scenes_completed),
                "checkpoints_passed": session.checkpoints_passed,
                "checkpoints_failed": session.checkpoints_failed,
                "quiz_result": session.quiz_result,
            }
            self._session_path(session.lesson_id).write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass  # best-effort; in-memory still works

    def _persist_material(self, material: Material) -> None:
        try:
            self._material_path(material.material_id).write_text(
                json.dumps(material.to_dict(), ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def _load_all(self) -> None:
        """Recover sessions and materials from /tmp on cold start."""
        try:
            for path in self._STORE_DIR.glob("session_*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    session = LessonSession(
                        lesson_id=data["lesson_id"],
                        student_id=data["student_id"],
                        plan=data["plan"],
                        material_id=data["material_id"],
                        started_at=data.get("started_at", time.time()),
                        concept_mastery=data.get("concept_mastery", {}),
                        misconceptions=data.get("misconceptions", {}),
                        attempts=data.get("attempts", {}),
                        scenes_completed=set(data.get("scenes_completed", [])),
                        checkpoints_passed=data.get("checkpoints_passed", 0),
                        checkpoints_failed=data.get("checkpoints_failed", 0),
                        quiz_result=data.get("quiz_result"),
                    )
                    self._sessions[session.lesson_id] = session
                except Exception:
                    pass
            for path in self._STORE_DIR.glob("material_*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    material = _material_from_dict(data)
                    self._materials[material.material_id] = material
                except Exception:
                    pass
        except Exception:
            pass

    # -- public interface ---------------------------------------------------

    def save_material(self, material: Material) -> None:
        self._materials[material.material_id] = material
        self._persist_material(material)

    def get_material(self, material_id: str) -> Material | None:
        mat = self._materials.get(material_id)
        if mat is None:
            # Try recovering from disk
            path = self._material_path(material_id)
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    mat = _material_from_dict(data)
                    self._materials[material_id] = mat
                except Exception:
                    pass
        return mat

    def save_session(self, session: LessonSession) -> None:
        self._sessions[session.lesson_id] = session
        self._persist_session(session)

    def get_session(self, lesson_id: str) -> LessonSession | None:
        session = self._sessions.get(lesson_id)
        if session is None:
            # Try recovering from disk
            path = self._session_path(lesson_id)
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    session = LessonSession(
                        lesson_id=data["lesson_id"],
                        student_id=data["student_id"],
                        plan=data["plan"],
                        material_id=data["material_id"],
                        started_at=data.get("started_at", time.time()),
                        concept_mastery=data.get("concept_mastery", {}),
                        misconceptions=data.get("misconceptions", {}),
                        attempts=data.get("attempts", {}),
                        scenes_completed=set(data.get("scenes_completed", [])),
                        checkpoints_passed=data.get("checkpoints_passed", 0),
                        checkpoints_failed=data.get("checkpoints_failed", 0),
                        quiz_result=data.get("quiz_result"),
                    )
                    self._sessions[lesson_id] = session
                except Exception:
                    pass
        return session

    def sessions_for_student(self, student_id: str) -> list[LessonSession]:
        matches = [s for s in self._sessions.values() if s.student_id == student_id]
        return sorted(matches, key=lambda s: s.started_at)

    def reset(self) -> None:
        """Clear all state. Used by tests and the demo-reset endpoint."""
        self._materials.clear()
        self._sessions.clear()
        try:
            for path in self._STORE_DIR.glob("*.json"):
                path.unlink(missing_ok=True)
        except Exception:
            pass
