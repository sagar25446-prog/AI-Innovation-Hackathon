"""Model resolution and LLM plan normalisation.

All offline: the fallback logic is exercised with fake callables, so these run
without a key, without network, and without spending the free tier's quota.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from services import llm  # noqa: E402


@pytest.fixture(autouse=True)
def clean_model_state():
    """Model choice and the dead-model set are process-global; isolate them."""
    llm._MODEL_NAME = None
    llm._DEAD_MODELS.clear()
    yield
    llm._MODEL_NAME = None
    llm._DEAD_MODELS.clear()


class Boom(Exception):
    """Stand-in for the SDK's error type, which only carries a message."""


NOT_FOUND = "404 NOT_FOUND. This model is no longer available to new users."
BUSY = "503 UNAVAILABLE. This model is currently experiencing high demand."
QUOTA = "429 RESOURCE_EXHAUSTED. You exceeded your current quota."


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


def test_classifies_a_retired_model_as_unavailable():
    assert llm._is_model_unavailable(Boom(NOT_FOUND)) is True
    assert llm._is_model_unavailable(Boom(BUSY)) is False


def test_classifies_overload_as_transient_but_not_quota():
    assert llm._is_transient(Boom(BUSY)) is True
    assert llm._is_quota_exhausted(Boom(BUSY)) is False


def test_classifies_quota_separately_from_plain_overload():
    assert llm._is_quota_exhausted(Boom(QUOTA)) is True


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------


def test_skips_a_retired_model_and_uses_the_next_one():
    """The bug this fixes: gemini-2.5-flash 404s on keys issued after its retirement."""
    tried: list[str] = []

    def call(model):
        tried.append(model)
        if model == "gemini-3.6-flash":
            raise Boom(NOT_FOUND)
        return f"answer from {model}"

    result = llm._call_with_model_fallback(call)
    assert result.startswith("answer from")
    assert tried[0] == "gemini-3.6-flash"
    assert len(tried) >= 2


def test_a_retired_model_is_never_tried_twice():
    tried: list[str] = []

    def call(model):
        tried.append(model)
        if model == "gemini-3.6-flash":
            raise Boom(NOT_FOUND)
        return "ok"

    llm._call_with_model_fallback(call)
    assert "gemini-3.6-flash" in llm._DEAD_MODELS

    tried.clear()
    llm._MODEL_NAME = None  # force re-resolution
    llm._call_with_model_fallback(call)
    assert "gemini-3.6-flash" not in tried


def test_the_working_model_is_remembered():
    calls: list[str] = []

    def call(model):
        calls.append(model)
        return "ok"

    llm._call_with_model_fallback(call)
    first = llm._MODEL_NAME
    llm._call_with_model_fallback(call)

    assert llm._MODEL_NAME == first
    assert calls == [first, first], "second call should not re-resolve"


def test_a_busy_model_falls_through_to_another():
    def call(model):
        if model == "gemini-3.6-flash":
            raise Boom(BUSY)
        return "ok"

    assert llm._call_with_model_fallback(call) == "ok"
    # Busy is temporary, so the model must stay a candidate.
    assert "gemini-3.6-flash" not in llm._DEAD_MODELS


def test_a_transient_failure_gets_a_second_round():
    attempts = {"n": 0}

    def call(model):
        attempts["n"] += 1
        # Everything fails on the first pass, then recovers.
        if attempts["n"] <= len(llm._candidate_models()):
            raise Boom(BUSY)
        return "recovered"

    assert llm._call_with_model_fallback(call) == "recovered"


def test_exhausted_quota_does_not_burn_a_second_round():
    """A daily cap will not clear in 1.5s; retrying just stalls the lesson."""
    attempts: list[str] = []

    def call(model):
        attempts.append(model)
        raise Boom(QUOTA)

    with pytest.raises(Boom):
        llm._call_with_model_fallback(call)

    assert len(attempts) == len(llm._candidate_models()), (
        "quota exhaustion should stop after one pass, not retry every model twice"
    )


def test_a_real_error_propagates_immediately():
    """A malformed request is not a model problem; do not mask it by retrying."""
    attempts: list[str] = []

    def call(model):
        attempts.append(model)
        raise Boom("400 INVALID_ARGUMENT: your prompt is malformed")

    with pytest.raises(Boom, match="INVALID_ARGUMENT"):
        llm._call_with_model_fallback(call)
    assert len(attempts) == 1


def test_an_explicit_model_override_is_tried_first(monkeypatch):
    monkeypatch.setattr(llm, "_CONFIGURED_MODEL", "my-pinned-model")
    assert llm._candidate_models()[0] == "my-pinned-model"


# ---------------------------------------------------------------------------
# Plan normalisation
# ---------------------------------------------------------------------------


def _scene(**overrides):
    scene = {
        "conceptId": "c",
        "objective": "o",
        "narration": "n",
        "durationSeconds": 30,
        "visual": {"type": "concept_map", "data": {}},
        "citations": [],
    }
    scene.update(overrides)
    return scene


def test_is_checkpoint_becomes_a_real_checkpoint_id():
    """The prompt asks for `isCheckpoint`; it used to be silently dropped."""
    from services.planner import _normalise_llm_scenes

    scenes = _normalise_llm_scenes([_scene(), _scene(isCheckpoint=True), _scene()])
    assert scenes[1].get("checkpointId")


def test_an_explicit_checkpoint_id_is_preserved():
    from services.planner import _normalise_llm_scenes

    scenes = _normalise_llm_scenes([_scene(checkpointId="cp-custom")])
    assert scenes[0]["checkpointId"] == "cp-custom"


def test_a_plan_with_no_checkpoint_gets_one_anyway():
    """Without a checkpoint the misconception-repair loop cannot run at all."""
    from services.planner import _normalise_llm_scenes

    scenes = _normalise_llm_scenes([_scene(), _scene(), _scene()])
    marked = [s for s in scenes if s.get("checkpointId")]
    assert len(marked) == 1
    # Penultimate, so a closing scene still follows the question.
    assert scenes[-2].get("checkpointId")


def test_normalisation_of_an_empty_plan_is_safe():
    from services.planner import _normalise_llm_scenes

    assert _normalise_llm_scenes([]) == []


# ---------------------------------------------------------------------------
# Live path (opt-in; skipped without a key, costs quota when it runs)
# ---------------------------------------------------------------------------


def _skip_if_llm_unusable():
    """Skip rather than fail when the model is reachable but unusable.

    A spent daily quota is an account state, not a regression, and a red suite
    for it would train everyone to ignore this test.
    """
    client = llm._get_gemini_client()
    if client is None:
        pytest.skip("Gemini client unavailable (no key, or SDK missing)")

    try:
        llm._call_with_model_fallback(
            lambda model: client.models.generate_content(
                model=model, contents="ping", config={"temperature": 0}
            ),
            rounds=1,
        )
    except Exception as exc:  # noqa: BLE001 - classify, then decide
        if llm._is_quota_exhausted(exc):
            pytest.skip("Gemini free-tier quota exhausted (20 requests/model/day)")
        if llm._is_transient(exc):
            pytest.skip(f"Gemini temporarily unavailable: {str(exc)[:80]}")
        raise


@pytest.mark.live_llm
def test_live_off_catalogue_topic_is_actually_taught():
    from services.ingestion import ingest_topic
    from services.planner import plan_lesson

    _skip_if_llm_unusable()
    material = ingest_topic("Photosynthesis")
    plan = plan_lesson(
        {
            "level": "beginner",
            "language": "english",
            "availableMinutes": 10,
            "goal": "Understand photosynthesis",
        },
        material,
        topic="Photosynthesis",
    )

    assert not plan.get("unsupportedTopic"), "an LLM-backed run should teach the topic"
    assert len(plan["scenes"]) > 1
    blob = " ".join(s["narration"] for s in plan["scenes"]).lower()
    assert any(word in blob for word in ("photosynth", "chlorophyll", "sunlight"))
    assert "ohm" not in blob, "must not leak the curated Electricity content"
    assert any(s.get("checkpointId") for s in plan["scenes"]), "needs a checkpoint"
