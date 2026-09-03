"""Tests for spaced revision planning and gamified study modes."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402
from services.planner.study_plan import build_study_plan  # noqa: E402


def test_build_study_plan_spans_one_week_with_expanding_reviews():
    plan = build_study_plan(
        "stu",
        concept_mastery={"current": 0.9, "voltage": 0.7, "resistance": 0.2},
        weak_concepts=["resistance"],
        start=date(2026, 1, 1),
    )
    assert plan["studentId"] == "stu"
    assert plan["strategy"] == "spaced-repetition"
    assert plan["horizonDays"] == 7
    assert len(plan["sessions"]) == 4

    days = [s["date"] for s in plan["sessions"]]
    assert "2026-01-01" in days  # day 1
    assert len(set(days)) == len(days), "each session must be on its own day"
    assert days == sorted(days), "reviews stay in chronological order"


def test_weak_concepts_revised_earliest_and_most_often():
    plan = build_study_plan(
        "stu",
        concept_mastery={"current": 0.9, "voltage": 0.7, "resistance": 0.2},
        weak_concepts=["resistance"],
        start=date(2026, 1, 1),
    )
    first = plan["sessions"][0]
    assert "resistance" in first["conceptIds"]
    weak_count = sum("resistance" in s["conceptIds"] for s in plan["sessions"])
    assert weak_count >= 2
    assert plan["weakConcepts"] == ["resistance"]
    assert "current" in plan["strongConcepts"]


def test_study_plan_estimates_total_review_minutes():
    plan = build_study_plan(
        "stu",
        concept_mastery={"a": 0.9, "b": 0.3},
        weak_concepts=["b"],
    )
    assert plan["totalReviewMinutes"] == sum(s["sessionMinutes"] for s in plan["sessions"])
    assert all(s["sessionMinutes"] >= 5 for s in plan["sessions"])


def test_empty_memory_still_produces_schedule():
    plan = build_study_plan("stu")
    assert len(plan["sessions"]) == 4
    assert plan["weakConcepts"] == []
    assert plan["strongConcepts"] == []