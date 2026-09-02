"""Planner tests: language, level depth, time adaptation and citations."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from services.ingestion import ingest_text, ingest_topic  # noqa: E402
from services.planner import plan_lesson, select_tier  # noqa: E402


@pytest.fixture(autouse=True)
def deterministic_engine(monkeypatch):
    """Force the deterministic planner for these unit tests.

    These tests assert the deterministic engine's exact structure (concept ids,
    narrations, visuals, substeps). With a live GEMINI_API_KEY set, plan_lesson
    would take the LLM path and the structural assertions would become flaky.
    We suppress the key and reset the cached Gemini client so every call here
    exercises the deterministic path deterministically.
    """
    import services.llm as llm

    saved_client = llm._gemini_client
    saved_attempted = llm._model_attempted

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GURUFLOW_LLM_API_KEY", raising=False)
    llm._gemini_client = None
    llm._model_attempted = False
    try:
        yield
    finally:
        llm._gemini_client = saved_client
        llm._model_attempted = saved_attempted


def learner(**overrides):
    profile = {
        "level": "beginner",
        "language": "hinglish",
        "availableMinutes": 20,
        "goal": "Understand Ohm's Law",
    }
    profile.update(overrides)
    return profile


@pytest.fixture
def material():
    return ingest_topic("Ohm's Law")


def test_hinglish_beginner_plan_matches_hero_flow(material):
    plan = plan_lesson(learner(), material)

    assert plan["learner"]["language"] == "hinglish"
    concept_ids = [scene["conceptId"] for scene in plan["scenes"]]
    assert concept_ids == [
        "intro-electricity",
        "electric-current",
        "voltage",
        "resistance",
        "ohms-law",
        "ohms-law-application",
        "lesson-summary",
    ]
    # Hinglish narration, not English.
    assert "Aaj hum Electric Current" in plan["scenes"][1]["narration"]


def test_every_scene_carries_source_citations(material):
    plan = plan_lesson(learner(), material)

    for scene in plan["scenes"]:
        assert scene["citations"], f"{scene['id']} has no citation"
        for citation in scene["citations"]:
            assert citation["documentId"] == "ncert-class9-science-ch12"
            assert citation["pageOrSlide"] >= 1
            assert citation["excerpt"]
        assert scene["groundingStatus"] == "source_grounded"


@pytest.mark.parametrize(
    "minutes,expected_tier",
    [(5, "compact"), (10, "standard"), (20, "full"), (60, "deep")],
)
def test_time_budget_selects_tier(minutes, expected_tier):
    tier, _ = select_tier(minutes)
    assert tier == expected_tier


@pytest.mark.parametrize("minutes", [5, 10, 20, 60])
def test_plan_never_exceeds_time_budget(material, minutes):
    plan = plan_lesson(learner(availableMinutes=minutes), material)
    assert plan["estimatedSeconds"] <= minutes * 60


def test_shorter_budget_produces_fewer_scenes(material):
    short = plan_lesson(learner(availableMinutes=5), material)
    long = plan_lesson(learner(availableMinutes=60), material)
    assert len(short["scenes"]) < len(long["scenes"])
    # The core concept and the checkpoint survive even the tightest budget.
    short_concepts = {scene["conceptId"] for scene in short["scenes"]}
    assert "ohms-law" in short_concepts
    assert "ohms-law-application" in short_concepts


def test_level_changes_depth_not_structure(material):
    beginner = plan_lesson(learner(level="beginner"), material)
    advanced = plan_lesson(learner(level="advanced"), material)

    assert [s["conceptId"] for s in beginner["scenes"]] == [
        s["conceptId"] for s in advanced["scenes"]
    ]
    beginner_ohm = next(s for s in beginner["scenes"] if s["conceptId"] == "ohms-law")
    advanced_ohm = next(s for s in advanced["scenes"] if s["conceptId"] == "ohms-law")
    assert len(advanced_ohm["narration"]) > len(beginner_ohm["narration"])
    assert "non-ohmic" in advanced_ohm["narration"]


@pytest.mark.parametrize("language", ["english", "hindi", "hinglish"])
def test_formulae_survive_every_language(material, language):
    plan = plan_lesson(learner(language=language), material)
    ohm_scene = next(s for s in plan["scenes"] if s["conceptId"] == "ohms-law")

    assert "V = I x R" in ohm_scene["narration"]
    assert "I = V/R" in ohm_scene["narration"]
    steps = [step["expression"] for step in ohm_scene["visual"]["data"]["steps"]]
    assert "I = V / R" in steps


def test_checkpoint_scene_is_marked(material):
    plan = plan_lesson(learner(), material)
    checkpoint_scenes = [s for s in plan["scenes"] if s.get("checkpointId")]
    assert len(checkpoint_scenes) == 1
    assert checkpoint_scenes[0]["conceptId"] == "ohms-law-application"


def test_unknown_topic_is_flagged_not_fabricated():
    """An off-syllabus topic must admit it is ungrounded, not invent citations."""
    material = ingest_topic("Mughal architecture")
    plan = plan_lesson(learner(), material, topic="Mughal architecture")

    for scene in plan["scenes"]:
        assert scene["citations"] == []
        assert scene["groundingStatus"] == "general_knowledge"


def test_uploaded_text_produces_page_numbered_citations():
    material = ingest_text(
        "Ohm's Law\nThe current through a resistor is inversely proportional to "
        "its resistance when voltage is constant.\n\n"
        "Resistance\nResistance is the property of a conductor to resist the "
        "flow of charges through it.",
        title="My notes",
    )
    assert material.origin == "upload"
    assert len(material.sections) == 2
    assert material.sections[0]["pageOrSlide"] == 1

    plan = plan_lesson(learner(), material)
    cited = [s for s in plan["scenes"] if s["citations"]]
    assert cited, "uploaded material should ground at least one scene"
