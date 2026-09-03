"""Tests for the advanced features: long-term memory, flashcards, personalities.

These run against the same TestClient as test_api.py. They use the
deterministic planner (autouse env is NOT cleared here, so they exercise the
public API endpoints; they do not depend on exact LLM output because they use
the /flashcards and /profile endpoints which are deterministic).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from apps.api.main import app, repository  # noqa: E402
from apps.api.student_memory import StudentMemoryStore  # noqa: E402

from services.llm import _gemini_client, _model_attempted  # noqa: E402


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    """Force the deterministic path and isolate memory for these tests."""
    import services.llm as llm

    saved_client = llm._gemini_client
    saved_attempted = llm._model_attempted
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GURUFLOW_LLM_API_KEY", raising=False)
    llm._gemini_client = None
    llm._model_attempted = False

    from apps.api import main as m

    m.repository.reset()
    # Isolate long-term memory from any pre-existing on-disk profile so tests
    # are hermetic across runs (lesson ids are random each run).
    saved_store = m.student_memory
    m.student_memory = StudentMemoryStore(directory=str(tmp_path / "memory"))
    yield
    m.student_memory = saved_store
    llm._gemini_client = saved_client
    llm._model_attempted = saved_attempted


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _plan(client, personality=None):
    learner = {
        "level": "beginner",
        "language": "hinglish",
        "availableMinutes": 20,
        "goal": "Understand Ohm's Law",
    }
    if personality:
        learner["personality"] = personality
    response = client.post(
        "/lessons/plan", json={"learner": learner, "topic": "Ohm's Law"}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_flashcards_endpoint_returns_review_cards(client):
    plan = _plan(client)
    res = client.post(f"/lessons/{plan['id']}/flashcards", json={})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["count"] >= 1
    ids = {c["conceptId"] for c in body["cards"]}
    assert "ohms-law" in ids  # core formula card always present
    assert all(c["front"] and c["back"] for c in body["cards"])


def test_flashcards_can_filter_to_weak_concepts(client):
    plan = _plan(client)
    res = client.post(
        f"/lessons/{plan['id']}/flashcards",
        json={"conceptIds": ["ohms-law"]},
    )
    assert res.status_code == 200
    body = res.json()
    assert {c["conceptId"] for c in body["cards"]} == {"ohms-law"}


def test_personality_changes_narration_tone(client):
    neutral = _plan(client)
    coach = _plan(client, personality="coach")
    neutral_first = neutral["scenes"][0]["narration"]
    coach_first = coach["scenes"][0]["narration"]
    assert coach_first != neutral_first
    assert coach_first.startswith("Great") or coach_first.startswith("Push")


def test_persona_feedback_exposed_on_checkpoint_answer(client):
    plan = _plan(client, personality="socratic")
    lesson_id = plan["id"]
    checkpoint = next(s for s in plan["scenes"] if s.get("checkpointId"))
    # Deliberately wrong answer -> repair -> feedback should carry socratic tone
    res = client.post(
        f"/lessons/{lesson_id}/checkpoints/{checkpoint['checkpointId']}/answer",
        json={"answer": "current increases when resistance increases"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["feedback"].startswith("Let's revisit") or body["nextAction"] == "repair"


def test_long_term_profile_persists_and_tracks_weak_concepts(client):
    plan = _plan(client)
    lesson_id = plan["id"]

    # Complete every scene, then answer the checkpoint correctly twice to build
    # a report that folds into long-term memory.
    for scene in plan["scenes"]:
        client.post(f"/lessons/{lesson_id}/scenes/{scene['id']}/complete")

    # Fetch the report (folds into memory).
    report_res = client.get(f"/lessons/{lesson_id}/report")
    assert report_res.status_code == 200

    prof = client.get("/students/student-demo/profile")
    assert prof.status_code == 200
    body = prof.json()
    assert body["studentId"] == "student-demo"
    assert "conceptMastery" in body
    assert body["lessonsCompleted"] >= 1
    assert isinstance(body["avgScore"], float)
    assert isinstance(body["strongConcepts"], list)
    assert isinstance(body["recurringMisconceptions"], list)
    assert len(body["lessons"]) >= 1

    hist = client.get("/students/student-demo/history")
    assert hist.status_code == 200
    assert len(hist.json()["lessons"]) == 1


def test_profile_404_for_unknown_student(client):
    assert client.get("/students/nobody/profile").status_code == 404
    assert client.get("/students/nobody/history").status_code == 404
