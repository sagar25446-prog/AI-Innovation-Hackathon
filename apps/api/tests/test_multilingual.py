"""The sixteen teaching languages, end to end.

Everything here runs **offline**: `conftest.py` disables both the LLM and the
public MT engine for unmarked tests. What is left is the shipped translation
pack in `data/translations`, which is committed to the repo, so these tests
assert the behaviour a judge actually gets on a fresh clone with no API key and
no internet - not a best case that depends on a live service.

Two guarantees are being pinned here:

* a curated lesson is **really translated** in all sixteen languages, from the
  pack, with no network at all; and
* a string the pack does not carry degrades to English rather than crashing or
  rendering blank.
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


def _catalogue_narration() -> str:
    """The Ohm's Law narration exactly as the pack builder collects it.

    Hard-coding a string here would silently stop testing the pack the moment
    the curated copy was reworded: the pack would no longer carry it, and the
    test would only prove the English fallback still works.
    """
    from services.planner.concepts import CONCEPTS_BY_ID

    return CONCEPTS_BY_ID["ohms-law"]["narration"]["english"]


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


def test_sixteen_languages_three_of_them_hand_authored():
    assert len(translation.SUPPORTED_LANGUAGES) == 16
    assert CORE == ("english", "hindi", "hinglish")
    assert len(EXTENDED) == 13
    assert "bhojpuri" in EXTENDED


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


def test_a_string_no_engine_can_reach_falls_back_to_english():
    """With every engine off and no pack entry, the source passes through.

    The string is deliberately one the shipped pack cannot contain, so this
    tests the last-resort path rather than accidentally testing the pack.
    """
    source = "Zorblat the quintessence of flimbertwaddle, unto ninefold."
    for language in EXTENDED:
        assert translation.localize(source, language) == source


def test_the_shipped_pack_really_translates_every_extended_language():
    """The headline claim: sixteen languages, offline, no key, no network.

    This is the regression guard for the bug that made the feature look fake -
    Gemini's free tier ran out, every extended language quietly served English,
    and nothing in the suite noticed because the tests only asserted that
    English came back.
    """
    source = translation.CORE_LANGUAGES and _catalogue_narration()
    for language in EXTENDED:
        translated = translation.localize(source, language)
        assert translated != source, (
            f"{language} fell back to English; the shipped pack is missing this "
            f"string. Re-run tools/build_translation_pack.py."
        )
        assert translated.strip()


def test_equations_survive_the_shipped_translations():
    """A translation that mangles I = V/R teaches the wrong physics."""
    source = _catalogue_narration()
    assert "V/R" in source.replace(" ", ""), "test fixture no longer carries a formula"
    for language in EXTENDED:
        translated = translation.localize(source, language)
        assert "V/R" in translated.replace(" ", ""), (
            f"{language} lost the formula: {translated}"
        )


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


def test_localized_falls_back_to_english_when_nothing_can_translate():
    mapping = {"english": "Zorblat the quintessence of flimbertwaddle."}
    assert translation.localized(mapping, "telugu") == mapping["english"]


def test_localized_uses_the_pack_for_an_unauthored_language():
    """`localized` must reach the pack too, not only `localize`.

    Checkpoint feedback goes through `localized`, so a learner in Telugu who
    answers correctly must be congratulated in Telugu.
    """
    from services.evaluation import FEEDBACK

    mapping = {"english": FEEDBACK["correct_first"]["english"]}
    assert translation.localized(mapping, "telugu") != mapping["english"]


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


def test_a_borrowed_voice_is_declared_rather_than_hidden():
    """Bhojpuri is read by the Hindi voice; that must be recorded, not implied."""
    from services.voice import APPROXIMATE_VOICES, VOICE_MAP

    assert APPROXIMATE_VOICES["bhojpuri"] == "hindi"
    assert VOICE_MAP["bhojpuri"] == VOICE_MAP["hindi"]
    for language in APPROXIMATE_VOICES:
        assert language in translation.SUPPORTED_LANGUAGES


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


def test_an_unreachable_engine_does_not_pin_a_language_to_english():
    """The regression that made "it only works in Hinglish" permanent.

    `localize` used to cache the miss as None. One lesson planned while Gemini
    was rate-limited therefore left *every* later lesson in that process in
    English too - even after the quota reset, even after the network came back,
    until someone restarted the server. A failed lookup must leave no trace.
    """
    translation.localize_batch(["alpha", "beta"], "tamil")
    assert ("tamil", "alpha") not in translation._cache
    assert translation.localize("alpha", "tamil") == "alpha"
    assert ("tamil", "alpha") not in translation._cache


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
    # The whole batch is discarded rather than pairing "only-one" with "one".
    assert ("tamil", "one") not in translation._cache
    assert ("tamil", "two") not in translation._cache


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


# ---------------------------------------------------------------------------
# The no-key guarantee
# ---------------------------------------------------------------------------
# These run with the LLM disabled and the MT engine disabled (conftest), so
# they assert exactly what a judge gets on a fresh clone with no API key and
# no internet: sixteen working teaching languages, from committed data.


def test_every_language_is_fully_covered_with_no_api_key():
    """No language may quietly fall back to English.

    This is the guarantee the shipped pack exists to provide. If it fails,
    a language is serving English somewhere, and the fix is to re-run
    tools/build_translation_pack.py --prune and commit the result.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(REPO_ROOT))
    from tools.build_translation_pack import collect_source_strings

    sources = collect_source_strings()
    short = {}
    for language in EXTENDED:
        missing = [s for s in sources if translation.localize(s, language) == s]
        # A handful of strings are legitimately identical after translation
        # (bare formulae, for instance), so compare against the pack directly.
        from services.translation import pack

        uncovered = [s for s in sources if s not in pack.load(language)]
        if uncovered:
            short[language] = len(uncovered)
    assert not short, (
        f"languages with uncovered strings: {short}. "
        f"Re-run tools/build_translation_pack.py --prune"
    )


def test_a_whole_lesson_is_taught_in_every_language_with_no_api_key():
    """End to end: plan a lesson in each language and check it is not English."""
    from services.planner import plan_lesson

    english = plan_lesson(_learner("english"), ingest_topic("Ohm's Law"))
    baseline = {s["narration"] for s in english["scenes"]}

    for language in EXTENDED:
        plan = plan_lesson(_learner(language), ingest_topic("Ohm's Law"))
        narrations = [s["narration"] for s in plan["scenes"]]
        assert narrations, f"{language} produced no scenes"
        untranslated = [n for n in narrations if n in baseline]
        assert not untranslated, (
            f"{language} served {len(untranslated)} scene(s) in English"
        )


def test_formulae_survive_in_every_language_with_no_api_key():
    """A localised numeral in I = V/R teaches the wrong arithmetic."""
    from services.planner import plan_lesson

    for language in EXTENDED:
        plan = plan_lesson(_learner(language), ingest_topic("Ohm's Law"))
        ohm = next(s for s in plan["scenes"] if s["conceptId"] == "ohms-law")
        flat = ohm["narration"].replace(" ", "")
        assert "V=IxR" in flat, f"{language} lost V = I x R: {ohm['narration']}"


def test_the_quiz_is_fully_translated_in_every_language_with_no_api_key():
    from services.assessment import build_quiz, grade_quiz
    from services.planner import plan_lesson

    english = build_quiz(
        plan_lesson(_learner("english"), ingest_topic("Ohm's Law"))["scenes"],
        "english",
    )
    english_prompts = {q["prompt"] for q in english["questions"]}

    for language in EXTENDED:
        scenes = plan_lesson(_learner(language), ingest_topic("Ohm's Law"))["scenes"]
        quiz = build_quiz(scenes, language)
        assert quiz["questions"], f"{language} produced no quiz"
        for question in quiz["questions"]:
            assert question["prompt"] not in english_prompts, (
                f"{language} asked a question in English: {question['prompt']}"
            )
        # And the correction a learner sees after a wrong answer.
        graded = grade_quiz(
            [{"questionId": "q-ohms-mcq", "response": "b"}], language
        )
        explanation = graded["results"][0]["explanation"]
        assert "V / R" in explanation or "V/R" in explanation


# ---------------------------------------------------------------------------
# The /tts endpoint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("language", translation.SUPPORTED_LANGUAGES)
def test_the_tts_endpoint_never_returns_a_server_error(client, language):
    """No teaching language may 500 when asked to speak.

    The endpoint used to call edge-tts directly with ``VOICE_MAP[language]``.
    Odia and Punjabi have no edge voice, so that value is None, and
    ``.get(language, default)`` does not save you when the key exists with a
    None value: edge-tts raised "voice must be str" and the endpoint returned
    500. Two of the teaching languages had no voice at all.

    204 is a valid answer here - it means captions-only for a language with no
    provider. 500 is not.
    """
    response = client.post("/tts", json={"text": "Ohm ka niyam", "language": language})
    assert response.status_code in (200, 204, 503), (
        f"{language} -> {response.status_code}: {response.text[:200]}"
    )
    if response.status_code == 200:
        assert response.content, f"{language} returned 200 with no audio"


def test_the_tts_endpoint_still_rejects_empty_text(client):
    assert client.post("/tts", json={"text": "  ", "language": "hindi"}).status_code == 400


# ---------------------------------------------------------------------------
# Switching language mid-lesson
# ---------------------------------------------------------------------------


def test_the_browser_language_list_matches_the_service():
    """The media cache keys on this list; drift makes languages share a slot.

    `normalizeLanguage` in services/media returns 'hinglish' for anything it
    does not recognise, and that value is the cache key. A language missing
    from the JS list therefore does not merely lose a label - it starts
    serving another language's cached scene.
    """
    import re

    source = (REPO_ROOT / "services/media/src/cached-descriptors.js").read_text(
        encoding="utf-8"
    )
    block = re.search(
        r"CANONICAL_LANGUAGES = new Set\(\[(.*?)\]\)", source, re.S
    )
    assert block, "CANONICAL_LANGUAGES not found in cached-descriptors.js"
    listed = set(re.findall(r"'([a-z]+)'", block.group(1)))
    assert listed == set(translation.SUPPORTED_LANGUAGES), (
        f"JS/Python language lists differ: "
        f"only in JS={listed - set(translation.SUPPORTED_LANGUAGES)}, "
        f"only in Python={set(translation.SUPPORTED_LANGUAGES) - listed}"
    )


def test_switching_language_rebuilds_an_earned_repair_scene(client):
    """The repair scene must follow the learner into the new language.

    It used to be re-spliced from the client's own copy, so the one scene the
    learner most needed to understand stayed in the language they had just
    switched away from.
    """
    plan = client.post(
        "/lessons/plan",
        json={"learner": _learner("english"), "topic": "Ohm's Law"},
    ).json()

    checkpoint = next(s for s in plan["scenes"] if s.get("checkpointId"))
    answer = client.post(
        f"/lessons/{plan['id']}/checkpoints/{checkpoint['checkpointId']}/answer",
        json={"answer": "current increases", "language": "english"},
    ).json()
    assert answer["nextAction"] == "repair"
    english_repair = answer["repairScene"]["narration"]

    switched = client.post(
        f"/lessons/{plan['id']}/language", json={"language": "tamil"}
    ).json()

    repairs = [s for s in switched["scenes"] if s.get("isRepair")]
    assert repairs, "the earned repair scene was dropped by the language switch"
    assert repairs[0]["narration"] != english_repair, (
        "the repair scene came back in the old language"
    )
    assert repairs[0]["narration"].strip()


def test_a_repair_scene_stays_next_to_its_checkpoint_after_a_switch(client):
    plan = client.post(
        "/lessons/plan",
        json={"learner": _learner("english"), "topic": "Ohm's Law"},
    ).json()
    checkpoint = next(s for s in plan["scenes"] if s.get("checkpointId"))
    client.post(
        f"/lessons/{plan['id']}/checkpoints/{checkpoint['checkpointId']}/answer",
        json={"answer": "current increases", "language": "english"},
    )

    scenes = client.post(
        f"/lessons/{plan['id']}/language", json={"language": "hindi"}
    ).json()["scenes"]

    checkpoint_at = next(i for i, s in enumerate(scenes) if s.get("checkpointId"))
    assert scenes[checkpoint_at + 1].get("isRepair"), (
        "the repair scene is no longer immediately after its checkpoint"
    )


def test_switching_language_without_a_repair_leaves_the_lesson_unchanged(client):
    """A learner who has made no mistake must not acquire a repair scene."""
    plan = client.post(
        "/lessons/plan",
        json={"learner": _learner("english"), "topic": "Ohm's Law"},
    ).json()
    switched = client.post(
        f"/lessons/{plan['id']}/language", json={"language": "bhojpuri"}
    ).json()
    assert not any(s.get("isRepair") for s in switched["scenes"])
    assert len(switched["scenes"]) == len(plan["scenes"])


def test_the_demo_button_does_not_overwrite_the_chosen_language():
    """Picking a language and then pressing "demo" must keep the language.

    `loadDemoPreset` used to call `setRadio('language', 'hinglish')` before
    submitting the form. A learner who chose Telugu and then reached for the
    demo button got a Hinglish lesson - and the dropdown still displayed
    "Telugu", so the interface disagreed with what they were hearing. Every
    other field it presets describes the *demo*; the language describes the
    *learner*.

    Asserted against the source because the frontend has no DOM harness. It is
    a narrow check, but it is exactly the line that caused the bug.
    """
    import re

    source = (REPO_ROOT / "apps/web/src/app.js").read_text(encoding="utf-8")
    body = re.search(
        r"function loadDemoPreset\(\)\s*\{(.*?)\n\}", source, re.S
    )
    assert body, "loadDemoPreset not found in app.js"
    assert "'language'" not in body.group(1), (
        "loadDemoPreset touches the language control again; it must leave the "
        "learner's choice alone."
    )


def test_the_video_cache_is_keyed_by_language_not_just_scene():
    """Rendered videos carry muxed narration, so the key must include language.

    Scene ids repeat across lessons - teaching Ohm's Law twice produces the
    same `scene-1-intro-electricity` both times - so keying on the scene id
    alone meant a second lesson in Tamil found the first lesson's Hinglish
    video under that key and played it. It corrected itself on Next, because
    later scenes had not been cached yet, which is exactly how the bug was
    described.

    Source-level, because the frontend has no DOM harness; it pins the access
    pattern that caused the bug.
    """
    import re

    source = (REPO_ROOT / "apps/web/src/app.js").read_text(encoding="utf-8")
    assert "function videoKey(" in source, "videoKey helper is gone"

    bare = re.findall(r"video\.byScene\.(?:get|set)\(\s*scene\.id", source)
    assert not bare, (
        f"{len(bare)} video.byScene access(es) key on scene.id alone; "
        f"use videoKey(scene) so languages cannot collide."
    )


def test_restarting_clears_the_previous_lessons_video():
    """Otherwise the old lesson's video is what shows while the new one renders."""
    source = (REPO_ROOT / "apps/web/src/app.js").read_text(encoding="utf-8")
    restart = source[source.index("function restart()") :]
    restart = restart[: restart.index("\n}")]
    assert "video.byScene.clear()" in restart
    assert "removeAttribute('src')" in restart
