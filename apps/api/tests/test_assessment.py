"""The end-of-lesson quiz: what it asks, and what a grade is allowed to mean.

The quiz is the difference between "the student clicked through seven scenes"
and "the student can use Ohm's Law". These tests pin the properties that make
it an assessment rather than a form:

* it only asks about concepts the lesson actually taught;
* it spends its questions where the learner was weakest;
* a wrong answer is told *why* it is wrong, in the learner's language;
* the score it produces is the one the report shows.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from services.assessment import (  # noqa: E402
    PASS_THRESHOLD,
    QUESTION_BANK,
    build_quiz,
    grade_quiz,
)
from services.ingestion import ingest_topic  # noqa: E402
from services.planner import plan_lesson  # noqa: E402


def _scenes(language="english"):
    plan = plan_lesson(
        {
            "level": "beginner",
            "language": language,
            "availableMinutes": 20,
            "goal": "Understand Ohm's Law",
        },
        ingest_topic("Ohm's Law"),
    )
    return plan["scenes"]


# ---------------------------------------------------------------------------
# Choosing the questions
# ---------------------------------------------------------------------------


def test_a_quiz_is_built_from_the_lesson_that_was_taught():
    quiz = build_quiz(_scenes(), "english")
    assert quiz["questions"]
    taught = {s["conceptId"] for s in _scenes() if s.get("conceptId")}
    for question in quiz["questions"]:
        assert question["conceptId"] in taught


def test_it_never_asks_about_a_concept_the_lesson_skipped():
    """A five-minute lesson covers fewer concepts, so it earns fewer questions."""
    short = plan_lesson(
        {
            "level": "beginner",
            "language": "english",
            "availableMinutes": 5,
            "goal": "Understand Ohm's Law",
        },
        ingest_topic("Ohm's Law"),
    )["scenes"]
    taught = {s["conceptId"] for s in short if s.get("conceptId")}
    quiz = build_quiz(short, "english")
    assert {q["conceptId"] for q in quiz["questions"]} <= taught


def test_weak_concepts_are_asked_about_first():
    """The quiz should spend its questions where the doubt is."""
    quiz = build_quiz(_scenes(), "english", concept_mastery={"resistance": 0.2})
    assert quiz["questions"][0]["conceptId"] == "resistance"


def test_a_repair_scene_does_not_add_a_duplicate_question():
    scenes = _scenes()
    scenes.append(
        {"id": "scene-repair", "conceptId": "ohms-law", "isRepair": True, "narration": ""}
    )
    quiz = build_quiz(scenes, "english")
    concepts = [q["conceptId"] for q in quiz["questions"]]
    assert len(concepts) == len(set(concepts)) or concepts.count("ohms-law") <= len(
        QUESTION_BANK["ohms-law"]
    )


def test_the_quiz_mixes_question_types():
    """Recognition is not recall, and recall is not application."""
    quiz = build_quiz(_scenes(), "english")
    assert len({q["type"] for q in quiz["questions"]}) >= 2


def test_answer_keys_never_reach_the_client():
    """Sending `correct: true` to the browser makes the quiz decorative."""
    quiz = build_quiz(_scenes(), "english")
    for question in quiz["questions"]:
        assert "answer" not in question
        assert "keywords" not in question
        for option in question.get("options", []):
            assert "correct" not in option
            assert "why" not in option


def test_the_quiz_is_capped_so_it_stays_a_quiz():
    quiz = build_quiz(_scenes(), "english", max_questions=2)
    assert len(quiz["questions"]) == 2


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


def test_a_perfect_paper_scores_one():
    result = grade_quiz(
        [
            {"questionId": "q-ohms-numeric", "response": "3"},
            {"questionId": "q-ohms-mcq", "response": "a"},
            {"questionId": "q-current-mcq", "response": "a"},
            {"questionId": "q-resistance-mcq", "response": "a"},
        ],
        "english",
    )
    assert result["score"] == 1.0
    assert result["passed"] is True
    assert result["verdict"] == "strong"


def test_an_empty_paper_scores_zero_rather_than_crashing():
    result = grade_quiz([], "english")
    assert result["score"] == 0.0
    assert result["passed"] is False
    assert result["results"] == []


def test_application_is_worth_more_than_recognition():
    """Getting the numeric problem right must beat getting one MCQ right."""
    numeric = grade_quiz(
        [
            {"questionId": "q-ohms-numeric", "response": "3"},
            {"questionId": "q-ohms-mcq", "response": "b"},
        ],
        "english",
    )
    mcq = grade_quiz(
        [
            {"questionId": "q-ohms-numeric", "response": "99"},
            {"questionId": "q-ohms-mcq", "response": "a"},
        ],
        "english",
    )
    assert numeric["score"] > mcq["score"]


def test_a_wrong_option_is_told_why_it_is_wrong():
    """The quiz keeps teaching while it measures."""
    result = grade_quiz([{"questionId": "q-ohms-mcq", "response": "b"}], "english")
    explanation = result["results"][0]["explanation"]
    assert "V / R" in explanation or "V/R" in explanation
    assert "bottom" in explanation.lower()


def test_a_distractor_names_the_misconception_it_represents():
    """This is what lets the report say *what* was misunderstood."""
    result = grade_quiz([{"questionId": "q-ohms-mcq", "response": "b"}], "english")
    assert "inverse-relationship" in result["misconceptions"]


def test_grading_never_says_wrong_or_incorrect():
    """Supportive correction is a product promise, not a checkpoint-only one."""
    result = grade_quiz(
        [
            {"questionId": "q-ohms-mcq", "response": "b"},
            {"questionId": "q-current-mcq", "response": "b"},
            {"questionId": "q-resistance-mcq", "response": "c"},
        ],
        "english",
    )
    for item in result["results"]:
        lowered = item["explanation"].lower()
        assert "wrong" not in lowered
        assert "incorrect" not in lowered


def test_numeric_answers_accept_the_ways_a_student_writes_them():
    for written in ("3", "3.0", "3 A", "I = 3 amperes", " 3 "):
        result = grade_quiz(
            [{"questionId": "q-ohms-numeric", "response": written}], "english"
        )
        assert result["results"][0]["correct"], f"rejected {written!r}"


def test_a_numeric_answer_that_is_merely_close_is_still_wrong():
    result = grade_quiz(
        [{"questionId": "q-ohms-numeric", "response": "2.5"}], "english"
    )
    assert result["results"][0]["correct"] is False
    # ...and the working is shown, so the learner can see where they diverged.
    assert "12 / 4" in result["results"][0]["explanation"]


def test_a_blank_numeric_answer_does_not_crash_the_grader():
    result = grade_quiz([{"questionId": "q-ohms-numeric", "response": ""}], "english")
    assert result["results"][0]["correct"] is False


def test_short_answers_are_graded_on_meaning_not_spelling():
    hit = grade_quiz(
        [
            {
                "questionId": "q-voltage-short",
                "response": "its the push that drives charge round",
            }
        ],
        "english",
    )
    assert hit["results"][0]["correct"] is True


def test_an_unknown_question_id_is_skipped_not_fatal():
    """A stale client must not be able to fail the whole submission."""
    result = grade_quiz(
        [
            {"questionId": "q-does-not-exist", "response": "a"},
            {"questionId": "q-ohms-mcq", "response": "a"},
        ],
        "english",
    )
    assert result["questionCount"] == 1
    assert result["score"] == 1.0


def test_per_concept_mastery_comes_out_of_the_grade():
    """This is what the report and the study plan consume."""
    result = grade_quiz(
        [
            {"questionId": "q-ohms-numeric", "response": "3"},
            {"questionId": "q-ohms-mcq", "response": "b"},
            {"questionId": "q-current-mcq", "response": "a"},
        ],
        "english",
    )
    assert result["conceptMastery"]["ohms-law"] == 0.5
    assert result["conceptMastery"]["electric-current"] == 1.0


def test_the_pass_threshold_is_the_one_the_verdict_uses():
    just_under = grade_quiz(
        [
            {"questionId": "q-ohms-mcq", "response": "b"},
            {"questionId": "q-current-mcq", "response": "b"},
            {"questionId": "q-resistance-mcq", "response": "a"},
        ],
        "english",
    )
    assert (just_under["score"] >= PASS_THRESHOLD) == just_under["passed"]


# ---------------------------------------------------------------------------
# Multilingual
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("language", ["hindi", "hinglish", "tamil", "bengali"])
def test_the_quiz_is_asked_in_the_learners_language(language):
    quiz = build_quiz(_scenes(language), language)
    assert quiz["questions"]
    for question in quiz["questions"]:
        assert question["prompt"].strip()
        for option in question.get("options", []):
            assert option["text"].strip()


@pytest.mark.parametrize("language", ["hindi", "tamil"])
def test_feedback_on_a_wrong_answer_is_in_the_learners_language(language):
    """A learner taught in Tamil must not be corrected in English."""
    result = grade_quiz([{"questionId": "q-ohms-mcq", "response": "b"}], language)
    explanation = result["results"][0]["explanation"]
    assert explanation.strip()
    # The formula must survive translation into any script.
    assert "V / R" in explanation or "V/R" in explanation


# ---------------------------------------------------------------------------
# The API surface
# ---------------------------------------------------------------------------


def _plan(client, language="english"):
    return client.post(
        "/lessons/plan",
        json={
            "learner": {
                "level": "beginner",
                "language": language,
                "availableMinutes": 20,
                "goal": "Understand Ohm's Law",
            },
            "topic": "Ohm's Law",
        },
    ).json()


def test_the_api_serves_a_quiz_for_a_lesson(client):
    plan = _plan(client)
    response = client.post(f"/lessons/{plan['id']}/quiz")
    assert response.status_code == 200, response.text
    assert response.json()["questions"]


def test_the_api_rejects_a_quiz_for_an_unknown_lesson(client):
    assert client.post("/lessons/nope/quiz").status_code == 404


def test_submitting_the_quiz_returns_a_grade(client):
    plan = _plan(client)
    quiz = client.post(f"/lessons/{plan['id']}/quiz").json()
    responses = [{"questionId": q["id"], "response": "a"} for q in quiz["questions"]]
    result = client.post(
        f"/lessons/{plan['id']}/quiz/submit", json={"responses": responses}
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert 0.0 <= body["score"] <= 1.0
    assert len(body["results"]) == len(responses)


def test_the_quiz_score_becomes_the_report_score(client):
    """A report that ignored the quiz would make taking it pointless."""
    plan = _plan(client)
    quiz = client.post(f"/lessons/{plan['id']}/quiz").json()
    perfect = [
        {
            "questionId": q["id"],
            "response": "3" if q["type"] == "numeric" else "a",
        }
        for q in quiz["questions"]
    ]
    graded = client.post(
        f"/lessons/{plan['id']}/quiz/submit", json={"responses": perfect}
    ).json()

    report = client.get(f"/lessons/{plan['id']}/report").json()
    assert report["quizTaken"] is True
    assert report["quizScore"] == round(graded["score"], 2)
    assert report["score"] == round(graded["score"], 2)


def test_a_report_without_a_quiz_still_works(client):
    """A learner who leaves early must still get something useful."""
    plan = _plan(client)
    report = client.get(f"/lessons/{plan['id']}/report").json()
    assert report["quizTaken"] is False
    assert report["quizScore"] is None
    assert report["revisionActions"]


def test_revision_advice_is_written_in_the_learners_language(client):
    """The final screen used to switch back to English at the last moment."""
    english = client.get(f"/lessons/{_plan(client, 'english')['id']}/report").json()
    tamil = client.get(f"/lessons/{_plan(client, 'tamil')['id']}/report").json()
    assert tamil["revisionActions"] != english["revisionActions"]
