"""Phase 1: "any topic" must actually work, or say honestly that it cannot.

The failure these guard against: uploading a photosynthesis passage used to
return a full Ohm's Law lesson. It was honest about grounding (no fabricated
citations) but taught entirely the wrong subject, which is worse than
admitting the limitation.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from services.ingestion import ingest_text, ingest_topic  # noqa: E402
from services.planner import (  # noqa: E402
    _curated_catalogue_grounds,
    _ground_llm_scenes,
    _unsupported_topic_narration,
    plan_lesson,
)

BIOLOGY = """Photosynthesis
Photosynthesis is the process by which green plants use sunlight to synthesise
food from carbon dioxide and water.

Chlorophyll
Chlorophyll is the green pigment in leaves that absorbs light energy.

The Equation
Carbon dioxide plus water in sunlight produces glucose and oxygen."""

ELECTRICITY_NOTES = """Ohm's Law
The current through a resistor is inversely proportional to its resistance
when the potential difference is constant.

Resistance
Resistance is the property of a conductor to resist the flow of charges.

Potential Difference
Potential difference, measured in volts, drives the current round a circuit."""


def learner(**overrides):
    profile = {
        "level": "beginner",
        "language": "english",
        "availableMinutes": 10,
        "goal": "Learn the topic",
    }
    profile.update(overrides)
    return profile


# ---------------------------------------------------------------------------
# Which materials the curated catalogue can honestly teach
# ---------------------------------------------------------------------------


def test_builtin_corpus_is_teachable():
    assert _curated_catalogue_grounds(ingest_topic("Ohm's Law")) is True


def test_uploaded_electricity_notes_are_teachable():
    assert _curated_catalogue_grounds(ingest_text(ELECTRICITY_NOTES)) is True


def test_uploaded_biology_is_not_teachable_by_the_curated_catalogue():
    assert _curated_catalogue_grounds(ingest_text(BIOLOGY)) is False


def test_empty_material_is_not_teachable():
    assert _curated_catalogue_grounds(ingest_topic("Mughal architecture")) is False


# ---------------------------------------------------------------------------
# What the learner actually gets
# ---------------------------------------------------------------------------


def test_off_catalogue_upload_refuses_instead_of_teaching_electricity():
    """The core regression: do not answer 'photosynthesis' with Ohm's Law."""
    plan = plan_lesson(learner(), ingest_text(BIOLOGY), topic="Photosynthesis")

    assert plan["tier"] == "unsupported-topic"
    assert plan.get("unsupportedTopic") is True
    assert len(plan["scenes"]) == 1

    narration = plan["scenes"][0]["narration"].lower()
    assert "ohm" not in narration
    assert "electric current" not in narration
    # And it must not invent a citation for content it is not teaching.
    assert plan["scenes"][0]["citations"] == []


def test_an_upload_is_not_told_to_upload_something():
    """Advice has to match the situation the learner is actually in."""
    uploaded = _unsupported_topic_narration("english", ingest_text(BIOLOGY))
    topic_only = _unsupported_topic_narration("english", ingest_topic("Mughal art"))

    assert "api key" in uploaded.lower()
    assert "upload a document" not in uploaded.lower()
    assert "upload a document" in topic_only.lower()


@pytest.mark.parametrize("language", ["english", "hindi", "hinglish"])
def test_refusal_is_localised(language):
    plan = plan_lesson(
        learner(language=language), ingest_text(BIOLOGY), topic="Photosynthesis"
    )
    assert plan["scenes"][0]["narration"].strip()


def test_unknown_language_falls_back_to_english_not_the_word_english():
    """`dict.get(language, "english")` used to return the literal string."""
    assert _unsupported_topic_narration("klingon").startswith("I don't have")


def test_uploaded_electricity_lesson_cites_the_upload_not_the_builtin_corpus():
    material = ingest_text(ELECTRICITY_NOTES, title="My own notes")
    plan = plan_lesson(learner(), material, topic="Ohm's Law")

    assert plan["tier"] == "lesson"
    assert plan["documentTitle"] == "My own notes"
    cited = [c for scene in plan["scenes"] for c in scene["citations"]]
    assert cited, "an electricity upload should ground the lesson"
    assert all(c["documentId"] == material.document_id for c in cited)
    assert all(c["documentId"] != "ncert-class9-science-ch12" for c in cited)


def test_builtin_corpus_still_produces_the_full_lesson():
    """Guard against the tightened groundability check breaking the demo."""
    plan = plan_lesson(
        learner(language="hinglish", availableMinutes=20), ingest_topic("Ohm's Law")
    )
    # The tier label is owned by the study-mode logic ("lesson" for a normal
    # 20-minute plan); assert the substance rather than the label.
    assert plan.get("unsupportedTopic") is not True
    assert len(plan["scenes"]) == 7
    assert all(scene["citations"] for scene in plan["scenes"])


# ---------------------------------------------------------------------------
# LLM-authored scenes must still carry real citations
# ---------------------------------------------------------------------------


def test_llm_scenes_get_real_citations_attached():
    """The prompt tells the model to leave citations empty; we must fill them.

    Without this the LLM path - which is what an upload or a novel topic uses -
    returned every scene as `general_knowledge` with no citations, silently
    discarding the product's grounding story.
    """
    material = ingest_text(ELECTRICITY_NOTES)
    llm_scenes = [
        {
            "id": "scene-1-llm",
            "conceptId": "resistance",
            "objective": "Explain what resistance is",
            "narration": "Resistance opposes the flow of charge through a conductor.",
            "durationSeconds": 30,
            "visual": {"type": "concept_map", "data": {}},
            "citations": [],
            "groundingStatus": "general_knowledge",
        }
    ]
    grounded = _ground_llm_scenes(llm_scenes, material)

    assert grounded[0]["citations"], "citations should have been retrieved"
    assert grounded[0]["groundingStatus"] == "source_grounded"
    assert grounded[0]["citations"][0]["documentId"] == material.document_id


def test_llm_supplied_citations_are_not_overwritten():
    material = ingest_text(ELECTRICITY_NOTES)
    supplied = [
        {
            "conceptId": "resistance",
            "objective": "o",
            "narration": "n",
            "citations": [
                {"documentId": "model-choice", "pageOrSlide": 9, "excerpt": "kept"}
            ],
        }
    ]
    grounded = _ground_llm_scenes(supplied, material)
    assert grounded[0]["citations"][0]["documentId"] == "model-choice"


def test_llm_scenes_off_material_stay_honestly_ungrounded():
    """No material match must mean no citation, not a plausible-looking one."""
    material = ingest_text(BIOLOGY)
    scenes = [
        {
            "conceptId": "ohms-law",
            "objective": "Explain Ohm's Law",
            "narration": "V equals I times R.",
            "citations": [],
        }
    ]
    grounded = _ground_llm_scenes(scenes, material)
    assert grounded[0]["citations"] == []
    assert grounded[0]["groundingStatus"] == "general_knowledge"
