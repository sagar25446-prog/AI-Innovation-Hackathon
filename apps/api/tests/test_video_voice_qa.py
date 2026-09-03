"""Tests for voice synthesis, teaching-video generation and follow-up Q&A.

Anything that needs the network or a multi-second Manim render is marked slow
and skipped by default, so the core suite stays fast and offline. Run the full
set with:

    pytest apps/api/tests -q -m "slow or not slow"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from apps.api.main import app, repository  # noqa: E402
from services import video as video_service  # noqa: E402
from services.evaluation import DIRECT_PROPORTIONALITY, build_repair_scene  # noqa: E402
from services.ingestion import ingest_topic  # noqa: E402
from services.qa import answer_question  # noqa: E402
from services.voice import SpeechResult, caption_lines, estimate_duration  # noqa: E402

RUN_SLOW = os.environ.get("GURUFLOW_RUN_SLOW_TESTS") == "1"
slow = pytest.mark.skipif(not RUN_SLOW, reason="set GURUFLOW_RUN_SLOW_TESTS=1")


@pytest.fixture
def client():
    repository.reset()
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Captions
# ---------------------------------------------------------------------------


def test_captions_split_long_narration_into_readable_lines():
    text = " ".join(["word"] * 60)
    result = SpeechResult(audio=b"", duration_seconds=20.0, provider="none")
    lines = caption_lines(result, text, max_chars=40)

    assert len(lines) > 1
    assert all(len(line["text"]) <= 45 for line in lines)
    # Monotonic, gap-free and covering the whole clip.
    assert lines[0]["start"] == pytest.approx(0.0, abs=0.01)
    assert lines[-1]["end"] == pytest.approx(20.0, abs=0.01)
    for earlier, later in zip(lines, lines[1:]):
        assert earlier["end"] <= later["start"] + 0.001


def test_captions_subdivide_a_sentence_level_boundary():
    """edge-tts gives Indian voices one SentenceBoundary for a whole sentence."""
    text = "Ohm's Law kehta hai ki V = I x R aur agar I nikalna ho toh I = V/R hota hai"
    result = SpeechResult(
        audio=b"",
        duration_seconds=10.0,
        provider="edge-tts",
        word_boundaries=[{"text": text, "start": 0.0, "end": 10.0}],
    )
    lines = caption_lines(result, text, max_chars=40)
    assert len(lines) > 1, "a long sentence boundary must still be broken up"
    assert lines[-1]["end"] == pytest.approx(10.0, abs=0.01)


def test_caption_lines_handles_empty_narration():
    assert caption_lines(SpeechResult(b"", 0.0, "none"), "") == []


def test_duration_estimate_is_positive():
    assert estimate_duration("") == 1.0
    assert estimate_duration("one two three four five") > 1.0


# ---------------------------------------------------------------------------
# Video service
# ---------------------------------------------------------------------------


def test_video_id_is_stable_and_content_addressed():
    scene = {
        "narration": "Current flows",
        "objective": "Explain current",
        "visual": {"type": "circuit", "data": {}},
        "durationSeconds": 30,
    }
    first = video_service.video_id(scene, "hinglish")
    assert first == video_service.video_id(dict(scene), "hinglish")

    # Language and narration both change the rendered output.
    assert first != video_service.video_id(scene, "english")
    changed = dict(scene, narration="Current does not flow")
    assert first != video_service.video_id(changed, "hinglish")


def test_video_status_is_absent_before_any_render():
    assert video_service.get_status("does-not-exist-at-all") == "absent"


def test_video_render_endpoint_rejects_a_missing_scene(client):
    assert client.post("/video/render", json={}).status_code in (400, 503)


def test_serving_an_unrendered_video_is_404(client):
    assert client.get("/video/nope.mp4").status_code == 404


def test_health_reports_video_capability(client):
    body = client.get("/health").json()
    assert "video" in body
    assert set(body["video"]) >= {"available", "quality", "videos"}


# ---------------------------------------------------------------------------
# Follow-up questions
# ---------------------------------------------------------------------------


def test_followup_answer_is_grounded_with_citations():
    material = ingest_topic("Ohm's Law")
    result = answer_question(
        "what happens to the current when resistance increases?",
        material.sections,
        material.document_id,
        language="english",
    )
    assert result["grounded"] is True
    assert result["citations"]
    assert result["citations"][0]["pageOrSlide"] >= 1


def test_followup_refuses_to_answer_off_material_questions():
    """The whole point of grounding: no answer beats a fabricated one."""
    material = ingest_topic("Ohm's Law")
    result = answer_question(
        "who won the 1998 football world cup?",
        material.sections,
        material.document_id,
        language="english",
    )
    assert result["grounded"] is False
    assert result["citations"] == []
    assert "could not find" in result["answer"].lower()


@pytest.mark.parametrize("language", ["english", "hindi", "hinglish"])
def test_followup_answers_in_the_learners_language(language):
    material = ingest_topic("Ohm's Law")
    result = answer_question(
        "what is resistance?", material.sections, material.document_id, language=language
    )
    assert result["answer"].strip()


def test_ask_endpoint_end_to_end(client):
    plan = client.post(
        "/lessons/plan",
        json={
            "learner": {
                "level": "beginner",
                "language": "hinglish",
                "availableMinutes": 20,
                "goal": "Understand Ohm's Law",
            },
            "topic": "Ohm's Law",
        },
    ).json()

    response = client.post(
        f"/lessons/{plan['id']}/ask",
        json={"question": "does current fall when resistance rises?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["citations"]


def test_ask_endpoint_validates_input(client):
    plan = client.post(
        "/lessons/plan",
        json={
            "learner": {
                "level": "beginner",
                "language": "english",
                "availableMinutes": 5,
                "goal": "g",
            }
        },
    ).json()
    assert client.post(f"/lessons/{plan['id']}/ask", json={"question": "  "}).status_code == 400
    assert client.post("/lessons/missing/ask", json={"question": "x"}).status_code == 404


# ---------------------------------------------------------------------------
# Slow: real renders
# ---------------------------------------------------------------------------


@slow
def test_repair_scene_renders_to_a_playable_video():
    from services.ffmpeg_util import probe_duration

    scene = build_repair_scene(DIRECT_PROPORTIONALITY, "hinglish")
    result = video_service.render_scene_video(scene, "hinglish")

    assert result.ready, f"render failed: {result.detail}"
    assert result.path.stat().st_size > 10_000
    duration = probe_duration(result.path)
    assert duration and duration > 3
