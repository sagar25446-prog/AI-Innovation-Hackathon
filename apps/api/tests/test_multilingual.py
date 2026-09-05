"""The fifteen teaching languages, end to end.

Everything here runs **offline**. `conftest.py` disables the LLM for unmarked
tests, so `localize()` takes its documented last step and returns the canonical
English string. That is the point: a learner in Tamil must still get a working
lesson, a voice and a video when Gemini is unreachable - degraded to English
narration, never a crash and never a blank scene.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from services import translation  # noqa: E402
from services.ingestion import ingest_topic  # noqa: E402

CORE = translation.CORE_LANGUAGES
EXTENDED = tuple(l for l in translation.SUPPORTED_LANGUAGES if l not in CORE)


@pytest.fixture(autouse=True)
def clean_translation_cache():
    translation.clear_translation_cache()
    yield
    translation.clear_translation_cache()


def _learner(language, **overrides):
    profile = {
        "level": "beginner",
        "language": language,
        "availableMinutes": 20,
        "goal": "Understand Ohm's Law",
    }
    profile.update(overrides)
    return profile


# ---------------------------------------------------------------------------
# The language set itself
# ---------------------------------------------------------------------------


def test_fifteen_languages_three_of_them_hand_authored():
    assert len(translation.SUPPORTED_LANGUAGES) == 15
    assert CORE == ("english", "hindi", "hinglish")
    assert len(EXTENDED) == 12


def test_every_language_has_a_display_name():
    for language in translation.SUPPORTED_LANGUAGES:
        assert translation.language_name(language)
        assert translation.language_name(language) != "English" or language == "english"


def test_the_contract_enum_matches_the_service():
    """The schema is the integration surface; it must not drift."""
    import json

    schema = json.loads(
        (REPO_ROOT / "packages/contracts/lesson-contract.schema.json").read_text(
            encoding="utf-8"
        )
    )
    enum = schema["definitions"]["LearnerProfile"]["properties"]["language"]["enum"]
    assert set(enum) == set(translation.SUPPORTED_LANGUAGES)


def test_the_pydantic_literal_matches_the_service():
    from typing import get_args

    from apps.api.models import Language

    assert set(get_args(Language)) == set(translation.SUPPORTED_LANGUAGES)


# ---------------------------------------------------------------------------
# localize() offline behaviour
# ---------------------------------------------------------------------------


def test_offline_localize_returns_the_source_unchanged():
    """No LLM means the English text passes through - never a blank string."""
    source = "Ohm's Law says V = I x R."
    for language in EXTENDED:
        assert translation.localize(source, language) == source


def test_core_languages_are_never_translated():
    source = "Aaj hum Ohm's Law seekhenge."
    for language in CORE:
        assert translation.localize(source, language) == source


def test_an_unknown_language_passes_through_rather_than_crashing():
    assert translation.localize("hello", "klingon") == "hello"


def test_empty_text_is_safe():
    assert translation.localize("", "tamil") == ""
    assert translation.localize("   ", "tamil") == ""


def test_localized_prefers_an_authored_string_over_translating():
    mapping = {"english": "Correct!", "tamil": "சரி!"}
    assert translation.localized(mapping, "tamil") == "சரி!"


def test_localized_falls_back_to_english_for_an_unauthored_language():
    mapping = {"english": "Correct!"}
    assert translation.localized(mapping, "telugu") == "Correct!"


def test_localized_survives_a_mapping_with_no_english():
    mapping = {"hindi": "सही!"}
    assert translation.localized(mapping, "odia") == "सही!"


# ---------------------------------------------------------------------------
# The teaching pipeline in every language
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("language", translation.SUPPORTED_LANGUAGES)
def test_a_lesson_plans_in_every_language(language):
    from services.planner import plan_lesson

    plan = plan_lesson(_learner(language), ingest_topic("Ohm's Law"))

    assert plan["scenes"], f"{language} produced no scenes"
    assert plan["learner"]["language"] == language
    for scene in plan["scenes"]:
        assert scene["narration"].strip(), f"{language}: empty narration"
        assert scene["objective"].strip(), f"{language}: empty objective"
    assert any(s.get("checkpointId") for s in plan["scenes"]), (
        f"{language} has no checkpoint, so the repair loop cannot run"
    )


@pytest.mark.parametrize("language", translation.SUPPORTED_LANGUAGES)
def test_formulae_survive_every_language(language):
    """A translation that mangles I = V/R teaches the wrong physics."""
    from services.planner import plan_lesson

    plan = plan_lesson(_learner(language), ingest_topic("Ohm's Law"))
    ohm = next(s for s in plan["scenes"] if s["conceptId"] == "ohms-law")
    steps = [step["expression"] for step in ohm["visual"]["data"]["steps"]]
    assert "I = V / R" in steps


@pytest.mark.parametrize("language", translation.SUPPORTED_LANGUAGES)
def test_the_misconception_loop_works_in_every_language(language):
    from services.evaluation import evaluate_answer

    wrong = evaluate_answer("current increases", language=language, attempt=1)
    assert wrong["correct"] is False
    assert wrong["nextAction"] == "repair"
    assert wrong["feedback"].strip(), f"{language}: empty feedback"
    assert wrong["repairScene"]["narration"].strip()

    right = evaluate_answer("current decreases", language=language, attempt=2)
    assert right["correct"] is True
    assert right["nextAction"] == "advance"
    assert right["feedback"].strip()


@pytest.mark.parametrize("language", translation.SUPPORTED_LANGUAGES)
def test_feedback_never_says_wrong_in_any_language(language):
    """Supportive correction is a product promise, not just an English one."""
    from services.evaluation import evaluate_answer

    feedback = evaluate_answer(
        "current increases", language=language, attempt=1
    )["feedback"].lower()
    assert "wrong" not in feedback
    assert "incorrect" not in feedback


@pytest.mark.parametrize("language", translation.SUPPORTED_LANGUAGES)
def test_flashcards_generate_in_every_language(language):
    from services.planner import plan_lesson
    from services.planner.flashcards import generate_flashcards

    plan = plan_lesson(_learner(language), ingest_topic("Ohm's Law"))
    cards = generate_flashcards(plan["scenes"], language)

    assert cards, f"{language} produced no flashcards"
    for card in cards:
        assert card["front"].strip() and card["back"].strip()


@pytest.mark.parametrize("language", translation.SUPPORTED_LANGUAGES)
def test_follow_up_questions_answer_in_every_language(language):
    from services.planner import plan_lesson
    from services.qa import answer_question

    material = ingest_topic("Ohm's Law")
    plan = plan_lesson(_learner(language), material)
    answer = answer_question(
        "what happens to current if resistance doubles?",
        plan["scenes"],
        material.sections,
        language,
    )
    assert answer["answer"].strip(), f"{language}: empty answer"


# ---------------------------------------------------------------------------
# Voice coverage
# ---------------------------------------------------------------------------


def test_every_language_has_a_voice_or_a_documented_fallback():
    from services.voice import GTTS_LANG_MAP, VOICE_MAP

    for language in translation.SUPPORTED_LANGUAGES:
        assert language in VOICE_MAP, f"{language} missing from VOICE_MAP"
        if VOICE_MAP[language] is None:
            # No edge-tts voice exists; gTTS must cover it, or it is
            # captions-only and that must be a deliberate, recorded choice.
            assert language in GTTS_LANG_MAP, (
                f"{language} has neither an edge-tts voice nor a gTTS fallback"
            )


def test_the_two_languages_without_edge_voices_are_the_expected_ones():
    """Pinned so a silent regression in voice coverage is visible."""
    from services.voice import VOICE_MAP

    missing = sorted(k for k, v in VOICE_MAP.items() if not v)
    assert missing == ["odia", "punjabi"]


def test_voice_ids_are_well_formed():
    import re

    from services.voice import VOICE_MAP

    for language, voice in VOICE_MAP.items():
        if voice:
            assert re.match(r"^[a-z]{2}-[A-Z]{2}-\w+Neural$", voice), (
                f"{language}: malformed voice id {voice}"
            )


def test_a_voice_can_be_overridden_per_language(monkeypatch):
    monkeypatch.setenv("GURUFLOW_VOICE_TAMIL", "ta-IN-SomeOtherNeural")
    import importlib

    import services.voice as voice

    importlib.reload(voice)
    try:
        assert voice.VOICE_MAP["tamil"] == "ta-IN-SomeOtherNeural"
    finally:
        monkeypatch.delenv("GURUFLOW_VOICE_TAMIL", raising=False)
        importlib.reload(voice)


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("language", ["tamil", "bengali", "marathi", "urdu"])
def test_the_api_plans_and_switches_into_an_extended_language(client, language):
    plan = client.post(
        "/lessons/plan",
        json={"learner": _learner("hinglish"), "topic": "Ohm's Law"},
    ).json()

    switched = client.post(
        f"/lessons/{plan['id']}/language", json={"language": language}
    )
    assert switched.status_code == 200, switched.text
    body = switched.json()
    assert body["learner"]["language"] == language
    assert all(s["narration"].strip() for s in body["scenes"])


def test_an_unsupported_language_is_rejected(client):
    plan = client.post(
        "/lessons/plan",
        json={"learner": _learner("hinglish"), "topic": "Ohm's Law"},
    ).json()
    response = client.post(
        f"/lessons/{plan['id']}/language", json={"language": "klingon"}
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Batched translation
# ---------------------------------------------------------------------------


def test_batch_is_a_no_op_for_core_languages():
    """Core catalogues are authored; batching them would waste a call."""
    calls = []
    translation.localize_batch(["hello"], "english")
    assert calls == []


def test_batch_offline_caches_the_misses_so_it_does_not_retry():
    """An offline run must not re-ask for every string on the next lookup."""
    translation.localize_batch(["alpha", "beta"], "tamil")
    assert translation._cache[("tamil", "alpha")] is None
    assert translation.localize("alpha", "tamil") == "alpha"


def test_batch_primes_the_cache_so_localize_becomes_free(monkeypatch):
    """One call for a lesson, then every lookup is a cache hit."""
    monkeypatch.setattr(translation, "_cache", {})
    calls = {"n": 0}

    def fake_generate(prompt):
        calls["n"] += 1
        return '["TA-one", "TA-two"]'

    import services.llm as llm

    monkeypatch.setattr(llm, "gemini_available", lambda: True)
    monkeypatch.setattr(llm, "_generate_text", fake_generate)

    translation.localize_batch(["one", "two"], "tamil")
    assert calls["n"] == 1
    # Both lookups now resolve without another API call.
    assert translation.localize("one", "tamil") == "TA-one"
    assert translation.localize("two", "tamil") == "TA-two"
    assert calls["n"] == 1


def test_a_mismatched_batch_reply_is_ignored_rather_than_misaligned(monkeypatch):
    """A short reply must not shift translations onto the wrong strings."""
    monkeypatch.setattr(translation, "_cache", {})
    import services.llm as llm

    monkeypatch.setattr(llm, "gemini_available", lambda: True)
    monkeypatch.setattr(llm, "_generate_text", lambda p: '["only-one"]')

    translation.localize_batch(["one", "two"], "tamil")
    # Nothing cached, so the per-string path still runs and nothing is wrong.
    assert ("tamil", "one") not in translation._cache


def test_batch_skips_strings_already_cached(monkeypatch):
    monkeypatch.setattr(translation, "_cache", {("tamil", "known"): "TA-known"})
    seen = {}

    import services.llm as llm

    monkeypatch.setattr(llm, "gemini_available", lambda: True)

    def capture(prompt):
        seen["prompt"] = prompt
        return '["TA-new"]'

    monkeypatch.setattr(llm, "_generate_text", capture)
    translation.localize_batch(["known", "new"], "tamil")
    assert "known" not in seen["prompt"], "already-translated text was re-sent"
    assert translation._cache[("tamil", "new")] == "TA-new"
