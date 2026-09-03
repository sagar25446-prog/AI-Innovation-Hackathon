"""Spaced multi-day revision planning ("the 7-day rhythm").

GuruFlow does not just teach a single lesson: when a learner studies over a
window, it builds a spaced-repetition study plan that schedules *revision
sessions* across several days. Weak concepts are revised earliest and most
often; stronger concepts are reinforced later.

This is deterministic, offline and testable -- it turns the student's long-term
memory (concept mastery + weak concepts) into a concrete calendar:

    Day 1  -> weak concepts, once
    Day 2  -> weak concepts, again (early repetition)
    Day 4  -> weak + borderline concepts
    Day 7  -> full mixed review

The concept ids map directly to flashcard-able scenes, so `build_study_plan`
dovetails with flashcards and long-term memory.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

# How soon each review happens (days after the previous one). This is a simple
# classic SM-2-ish expansion: 1 -> 2 -> 3 days further apart across a week.
_REVIEW_OFFSETS_DAYS = [1, 2, 4, 7]

MASTERY_FLOOR = 0.6


def select_tier_within(
    concept_mastery: dict[str, float],
    weak_concepts: list[str],
) -> tuple[list[str], list[str]]:
    """Split concepts into ``weak`` (revise early) and ``strong`` (reinforce)."""
    weak: list[str] = []
    strong: list[str] = []
    for concept_id, mastery in sorted(concept_mastery.items(), key=lambda kv: kv[1]):
        if concept_id in weak_concepts or mastery < MASTERY_FLOOR:
            weak.append(concept_id)
        else:
            strong.append(concept_id)
    # Any names weak_concepts mentions but mastery doesn't know about yet.
    known = set(concept_mastery)
    for cid in weak_concepts:
        if cid not in known:
            weak.append(cid)
    return weak, strong


def build_study_plan(
    student_id: str,
    concept_mastery: dict[str, float] | None = None,
    weak_concepts: list[str] | None = None,
    *,
    start: date | None = None,
) -> dict[str, Any]:
    """Build a one-week spaced revision schedule from long-term memory.

    Parameters
    ----------
    concept_mastery:
        Per-concept mastery (0..1) from ``StudentMemoryStore``.
    weak_concepts:
        Concepts the student has repeatedly missed.
    start:
        First study day. Defaults to today.
    """
    mastery = dict(concept_mastery or {})
    weak = list(weak_concepts or [])
    start = start or date.today()

    weak_concepts_list, strong_concepts_list = select_tier_within(mastery, weak)

    # Day-by-day sessions using the classic expanding intervals. The offsets
    # are absolute day numbers from the start: revise on day 1, day 2, day 4
    # and day 7 (a one-week horizon).
    days: list[dict[str, Any]] = []
    for session_number, day_offset in enumerate(_REVIEW_OFFSETS_DAYS, start=1):
        session_date = start + timedelta(days=day_offset - 1)
        focus: list[str]
        if session_number == 1:
            focus = weak_concepts_list
        elif session_number <= 3:
            # Early sessions hammer the weak concepts; add borderline later.
            focus = weak_concepts_list + [c for c in strong_concepts_list if _is_borderline(mastery, c)]
        else:
            # Final session: full mixed review.
            focus = weak_concepts_list + strong_concepts_list

        days.append({
            "day": session_number,
            "date": session_date.isoformat(),
            "title": _day_title(session_number),
            "conceptIds": _dedupe(focus),
            "sessionMinutes": _estimate_minutes(len(_dedupe(focus))),
            "mode": "revision",
        })

    return {
        "studentId": student_id,
        "producedAt": start.isoformat(),
        "horizonDays": 7,
        "strategy": "spaced-repetition",
        "weakConcepts": weak_concepts_list,
        "strongConcepts": strong_concepts_list,
        "sessions": days,
        "totalReviewMinutes": sum(s["sessionMinutes"] for s in days),
    }


def _day_title(day: int) -> str:
    return {
        1: "Relearn what you missed",
        2: "Reinforce today",
        4: "Bring back borderline ideas",
        7: "Full mixed review",
    }.get(day, f"Review on day {day}")


def _is_borderline(mastery: dict[str, float], concept_id: str) -> bool:
    m = mastery.get(concept_id, 0.0)
    return MASTERY_FLOOR <= m < 0.8


def _estimate_minutes(concept_count: int) -> int:
    return max(5, concept_count * 5)


def _dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen