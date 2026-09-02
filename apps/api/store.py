"""Session state and persistence for the GuruFlow teacher brain.

``LessonRepository`` is the seam a Postgres or Supabase implementation slots
into later. The in-memory implementation keeps the hackathon demo free of
infrastructure while the API surface stays unchanged.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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


class InMemoryLessonRepository(LessonRepository):
    """Process-local store. Adequate for the demo, replaceable in one class."""

    def __init__(self) -> None:
        self._materials: dict[str, Material] = {}
        self._sessions: dict[str, LessonSession] = {}

    def save_material(self, material: Material) -> None:
        self._materials[material.material_id] = material

    def get_material(self, material_id: str) -> Material | None:
        return self._materials.get(material_id)

    def save_session(self, session: LessonSession) -> None:
        self._sessions[session.lesson_id] = session

    def get_session(self, lesson_id: str) -> LessonSession | None:
        return self._sessions.get(lesson_id)

    def sessions_for_student(self, student_id: str) -> list[LessonSession]:
        matches = [s for s in self._sessions.values() if s.student_id == student_id]
        return sorted(matches, key=lambda s: s.started_at)

    def reset(self) -> None:
        """Clear all state. Used by tests and the demo-reset endpoint."""
        self._materials.clear()
        self._sessions.clear()
