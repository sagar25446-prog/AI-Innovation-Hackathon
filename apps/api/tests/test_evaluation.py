"""Evaluation tests: the correct / wrong / repair / retry branches."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from services.evaluation import (  # noqa: E402
    CONSTANT_CURRENT,
    DIRECT_PROPORTIONALITY,
    build_report,
    evaluate_answer,
)
from services.evaluation.misconceptions import classify_answer  # noqa: E402


# ---------------------------------------------------------------------------
# Answer classification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "answer",
    [
        "Current decreases.",
        "The current will be less.",
        "current kam hoga",
        "resistance badhne se current kam hoga",
        "If resistance is doubled the current gets halved",
        "It is inversely proportional so current falls",
        "धारा कम होगी",
        "प्रतिरोध बढ़ने पर धारा घटेगी",
    ],
)
def test_correct_answers_classified_correct(answer):
    assert classify_answer(answer) == "correct"


@pytest.mark.parametrize(
    "answer",
    [
        "Current increases when resistance increases.",
        "current bhi badhega",
        "The current will be more",
        "resistance badhega toh current zyada hoga",
        "धारा बढ़ेगी",
    ],
)
def test_misconception_answers_classified(answer):
    assert classify_answer(answer) == "direct-proportionality"


@pytest.mark.parametrize(
    "answer", ["It stays the same", "no change", "current constant rahega"]
)
def test_constant_current_answers_classified(answer):
    assert classify_answer(answer) == "constant-current"


@pytest.mark.parametrize("answer", ["", "hmm", "I don't know"])
def test_unclear_answers_classified(answer):
    assert classify_answer(answer) == "unclear"


def test_mcq_option_short_circuits_text():
    assert classify_answer("", option_id="decreases") == "correct"
    assert classify_answer("", option_id="increases") == "direct-proportionality"
    assert classify_answer("", option_id="no-change") == "constant-current"


# ---------------------------------------------------------------------------
# Evaluation branches
# ---------------------------------------------------------------------------


def test_first_try_correct_advances():
    result = evaluate_answer("Current decreases", language="hinglish", attempt=1)

    assert result["correct"] is True
    assert result["nextAction"] == "advance"
    assert result["mastery"] == 0.75
    assert "misconception" not in result
    assert "repairScene" not in result


def test_required_misconception_triggers_repair():
    """The brief's required case: current rises when resistance rises."""
    result = evaluate_answer(
        "Current increases when resistance increases.", language="hinglish", attempt=1
    )

    assert result["correct"] is False
    assert result["misconception"] == DIRECT_PROPORTIONALITY
    assert result["nextAction"] == "repair"
    assert result["mastery"] == 0.35
    assert "repairScene" in result


def test_repair_feedback_is_supportive_never_wrong():
    for language in ("english", "hindi", "hinglish"):
        result = evaluate_answer(
            "current badhega", language=language, attempt=1
        )
        feedback = result["feedback"].lower()
        assert "wrong" not in feedback
        assert "incorrect" not in feedback
        assert feedback.strip()


def test_repair_scene_differs_from_original_and_carries_all_three_aids():
    result = evaluate_answer("current increases", language="hinglish", attempt=1)
    scene = result["repairScene"]

    assert scene["id"] != "scene-6-ohms-law-application"
    assert scene["conceptId"] == "ohms-law"
    assert scene["isRepair"] is True
    # 20-45 second coherent repair scene.
    assert 20 <= scene["durationSeconds"] <= 45

    data = scene["visual"]["data"]
    assert "I = V / R" in data["steps"]          # equation transformation
    assert data["analogy"] == "water-pipe"        # analogy
    ys = [point["y"] for point in data["graph"]["points"]]
    assert ys == sorted(ys, reverse=True)         # descending graph
    assert scene["citations"][0]["pageOrSlide"] == 205


def test_correct_retry_after_repair_advances_with_lower_mastery():
    evaluate_answer("current increases", language="hinglish", attempt=1)
    retry = evaluate_answer("current kam hoga", language="hinglish", attempt=2)

    assert retry["correct"] is True
    assert retry["nextAction"] == "advance"
    assert retry["mastery"] == 0.6
    assert "Water pipe analogy" in retry["feedback"]


def test_unclear_answer_asks_for_retry_not_repair():
    result = evaluate_answer("I don't know", language="english", attempt=1)
    assert result["nextAction"] == "retry"
    assert "repairScene" not in result


def test_constant_current_gets_its_own_repair_scene():
    result = evaluate_answer("it stays the same", language="english", attempt=1)
    assert result["misconception"] == CONSTANT_CURRENT
    assert result["nextAction"] == "repair"
    assert "pipe" in result["repairScene"]["narration"].lower()


@pytest.mark.parametrize("language", ["english", "hindi", "hinglish"])
def test_repair_narration_localised_but_formula_preserved(language):
    result = evaluate_answer("current increases", language=language, attempt=1)
    assert "I = V/R" in result["repairScene"]["narration"]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def test_report_summarises_strengths_weaknesses_and_next_topic():
    report = build_report(
        student_id="student-demo",
        lesson_id="lesson-1",
        concept_mastery={
            "electric-current": 0.8,
            "voltage": 0.8,
            "ohms-law": 0.6,
        },
        misconceptions=[
            {"id": DIRECT_PROPORTIONALITY, "status": "resolved", "concept": "ohms-law"}
        ],
        scenes_completed=7,
        checkpoints_passed=1,
        checkpoints_failed=1,
        total_time_seconds=1200,
    )

    assert report["strongConcepts"] == ["electric-current", "voltage"]
    assert report["weakConcepts"] == ["ohms-law"]
    assert report["misconceptions"][0]["status"] == "resolved"
    assert report["nextTopic"]["id"] == "series-parallel-circuits"
    assert any("I = V/R" in action for action in report["revisionActions"])
    assert report["score"] == 0.73
