"""LLM service for GuruFlow.

Provides Gemini Flash integration for planning, evaluation, and content
generation. All functions return None when the API is unavailable, letting
consumers fall back to deterministic logic.
"""

from __future__ import annotations

import json
import logging
import os
import time
import re
from typing import Any

logger = logging.getLogger(__name__)

# Model candidates, tried in order until one answers.
#
# Google retires models for *new* API keys without removing them from the
# ListModels response, so a hardcoded name silently 404s on a fresh key while
# still appearing available. gemini-2.5-flash did exactly that. Rather than
# swap in another name that will age out the same way, the first candidate that
# responds is used and remembered.
#
# GURUFLOW_GEMINI_MODEL still wins outright when set, and is tried first.
_MODEL_CANDIDATES = [
    "gemini-3.6-flash",     # Google's own replacement recommendation
    "gemini-flash-latest",  # moving alias, survives future retirements
    "gemini-3.5-flash",
    "gemini-2.5-flash",     # legacy; still valid for older keys
]

_CONFIGURED_MODEL = os.environ.get("GURUFLOW_GEMINI_MODEL", "").strip()

# Models this key has already been told it cannot use. A 404 is permanent for
# the life of the process, so retrying one wastes a round-trip on every call
# and, worse, can be the error a transient round ends on - masking the real
# "everything is busy" cause.
_DEAD_MODELS: set[str] = set()

# Why the last model resolution gave up: "quota", "busy", "unavailable", or
# None when the last attempt succeeded. Callers swallow LLM failures and fall
# back deterministically, which is right for the learner but hides *why* from
# operators - and "out of quota" needs a different response from "the model is
# retired". Surfaced in /health.
last_failure_reason: str | None = None

# Resolved lazily on first successful call, then reused.
_MODEL_NAME: str | None = _CONFIGURED_MODEL or None


def _candidate_models() -> list[str]:
    """Model names to try, configured one first, without duplicates."""
    ordered = ([_CONFIGURED_MODEL] if _CONFIGURED_MODEL else []) + _MODEL_CANDIDATES
    seen: list[str] = []
    for name in ordered:
        if name and name not in seen and name not in _DEAD_MODELS:
            seen.append(name)
    return seen


def _is_model_unavailable(error: Exception) -> bool:
    """True when the error means 'this model, not this request' (404/NOT_FOUND)."""
    text = str(error)
    return "404" in text or "NOT_FOUND" in text


def _is_quota_exhausted(error: Exception) -> bool:
    """True for 429 / RESOURCE_EXHAUSTED - a spent quota, not a busy server.

    Worth separating from overload: the free tier's cap is per model per *day*,
    so trying a different model can help but retrying the same set seconds
    later cannot. Saying "quota exhausted" in the log also saves whoever reads
    it from hunting for a bug that is not there.
    """
    text = str(error)
    return "RESOURCE_EXHAUSTED" in text or "429" in text


def _is_transient(error: Exception) -> bool:
    """True for load/quota errors that another model or a retry may survive.

    A 503 on one Flash model does not mean every model is busy, and collapsing
    the lesson to "unsupported topic" because of a momentary spike is a far
    worse outcome than trying the next candidate.
    """
    text = str(error)
    return any(
        marker in text
        for marker in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded")
    )


def _call_with_model_fallback(call, rounds: int = 2):
    """Run ``call(model_name)``, working around retired and overloaded models.

    ``call`` takes one argument, the model name. A model that reports
    NOT_FOUND is skipped permanently for this process; one that reports 503 or
    429 is skipped for now but stays a candidate. Anything else propagates
    immediately, because it is about the request rather than the model.

    Two rounds with a short pause between them is enough to ride out the brief
    demand spikes Gemini Flash sees, without stalling a lesson for long.
    """
    global _MODEL_NAME, last_failure_reason

    if _MODEL_NAME:
        try:
            return call(_MODEL_NAME)
        except Exception as exc:
            if not (_is_model_unavailable(exc) or _is_transient(exc)):
                raise
            logger.warning(
                "Model %s failed (%s); re-resolving.", _MODEL_NAME, type(exc).__name__
            )
            _MODEL_NAME = None

    # A 404 names a model we deliberately skip, so it is the least useful thing
    # to surface. Prefer the reason we could not use a model we *would* have
    # used - "out of quota" or "busy" - and fall back to the 404 only if
    # nothing else failed.
    last_error: Exception | None = None
    last_skip_error: Exception | None = None
    for round_index in range(max(1, rounds)):
        if round_index:
            time.sleep(1.5)
            logger.info("Retrying Gemini after a transient failure.")
        # Reset per round: a spent daily quota is not worth a second pass.
        every_failure_was_quota = True
        for name in _candidate_models():
            try:
                result = call(name)
            except Exception as exc:
                if _is_model_unavailable(exc):
                    # Permanent for this key: never try it again this process.
                    _DEAD_MODELS.add(name)
                    logger.info("Model %s not available for this key; skipping.", name)
                    last_skip_error = exc
                    continue
                if _is_quota_exhausted(exc):
                    logger.warning(
                        "Model %s: quota exhausted for this key; trying the next.",
                        name,
                    )
                elif _is_transient(exc):
                    every_failure_was_quota = False
                    logger.info("Model %s is busy; trying the next.", name)
                else:
                    raise
                last_error = exc
                continue
            _MODEL_NAME = name
            last_failure_reason = None
            logger.info("Using Gemini model: %s", name)
            return result

        if every_failure_was_quota:
            logger.error(
                "Every Gemini model is out of quota for this key. The free tier "
                "allows 20 requests per model per day. Falling back to the "
                "deterministic path."
            )
            break

    if last_error:
        last_failure_reason = (
            "quota" if _is_quota_exhausted(last_error) else "busy"
        )
        raise last_error
    if last_skip_error:
        last_failure_reason = "unavailable"
        raise last_skip_error
    raise RuntimeError("No Gemini model candidates were configured.")

_gemini_client = None
_model_attempted = False


def _get_api_key() -> str | None:
    """Read the Gemini key lazily so a .env key added later is honoured."""
    return os.environ.get("GEMINI_API_KEY") or os.environ.get(
        "GURUFLOW_LLM_API_KEY"
    )


def _get_gemini_client():
    """Lazy-build the google-genai client. Returns None if unavailable."""
    global _gemini_client, _model_attempted
    if _gemini_client is not None:
        return _gemini_client
    if _model_attempted:
        return None
    _model_attempted = True
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        # Modern, supported SDK: https://github.com/google-gemini/google-genai
        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
        logger.info("Loaded Gemini client (model resolved on first call)")
        return _gemini_client
    except Exception as exc:
        logger.warning("Could not initialise Gemini client: %s", exc)
        return None


def gemini_available() -> bool:
    """Return True if the Gemini API is configured and importable."""
    return _get_gemini_client() is not None


def _generate_json(prompt: str) -> dict[str, Any] | None:
    """Ask the model for strict JSON output. Returns parsed dict or None."""
    client = _get_gemini_client()
    if client is None:
        return None
    try:
        response = _call_with_model_fallback(
            lambda model: client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.4,
                },
            )
        )
        text = (response.text or "").strip()
        return _parse_json_response(text)
    except Exception as exc:
        logger.warning("Gemini JSON call failed: %s", exc)
        return None


def _generate_text(prompt: str) -> str | None:
    """Ask the model for free text. Returns text or None."""
    client = _get_gemini_client()
    if client is None:
        return None
    try:
        response = _call_with_model_fallback(
            lambda model: client.models.generate_content(
                model=model,
                contents=prompt,
                config={"temperature": 0.6},
            )
        )
        text = (response.text or "").strip()
        return text if text else None
    except Exception as exc:
        logger.warning("Gemini text call failed: %s", exc)
        return None


def _parse_json_response(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from LLM response text that may contain markdown fences."""
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM JSON response")
        return None


# ---------------------------------------------------------------------------
# Lesson planning
# ---------------------------------------------------------------------------

def generate_plan(
    learner: dict[str, Any],
    material_sections: list[dict[str, Any]],
    topic: str,
    document_id: str,
) -> dict[str, Any] | None:
    """Ask Gemini Flash to produce a lesson plan as a list of scenes.

    Returns a dict with a ``scenes`` key on success, or None on failure.
    """
    sections_text = "\n".join(
        f"- [{s.get('pageOrSlide', '?')}] {s.get('heading', '')}: {s.get('excerpt', '')[:200]}"
        for s in (material_sections or [])[:15]
    )

    prompt = f"""You are a lesson planner for an AI teacher app called GuruFlow.

Learner profile:
- Language: {learner.get('language', 'english')}
- Level: {learner.get('level', 'beginner')}
- Available minutes: {learner.get('availableMinutes', 5)}

Topic: {topic}

Available material excerpts:
{sections_text or '(none)'}

Produce a JSON object with a "scenes" array. Each scene must have:
- "conceptId": a short slug
- "objective": one sentence teaching goal in the learner's language
- "narration": 2-3 sentences of teacher narration in the learner's language
- "durationSeconds": integer (15-45)
- "visual": {{"type": "diagram"|"equation"|"concept_map"|"graph", "data": {{}}}}
- "citations": [] (leave empty, backend fills this)

For a checkpoint scene include "isCheckpoint": true.
For a lesson-summary scene include "isSummary": true.

Return ONLY the JSON object, no markdown fences."""

    try:
        return _generate_json(prompt)
    except Exception as exc:
        logger.warning("Gemini plan generation failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Answer evaluation
# ---------------------------------------------------------------------------

def evaluate_answer_llm(
    answer: str,
    language: str,
    attempt: int,
) -> dict[str, Any] | None:
    """Use Gemini Flash to classify a free-text answer.

    Returns a dict with ``classification`` and ``feedback`` on success.
    Classification is one of: correct, direct-proportionality,
    constant-current, unclear.
    """
    prompt = f"""You are an evaluation assistant for an Ohm's Law lesson checkpoint.

The question asks: "If the resistance in a circuit increases while voltage stays constant, what happens to the current?"

The learner answered (in {language}, attempt {attempt}): "{answer}"

Classify the answer:
- "correct": The learner correctly states current decreases / goes down
- "direct-proportionality": The learner incorrectly says current increases
- "constant-current": The learner says current stays the same / no change
- "unclear": The answer is ambiguous or unrelated

Return a JSON object:
{{"classification": "<one of the four>", "feedback": "<brief encouraging feedback in {language}>"}}

Return ONLY the JSON object, no markdown fences."""

    try:
        return _generate_json(prompt)
    except Exception as exc:
        logger.warning("Gemini answer evaluation failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Repair narration
# ---------------------------------------------------------------------------

def generate_repair_narration(
    misconception: str,
    language: str,
) -> str | None:
    """Ask Gemini to produce a personalised repair explanation for the misconception.

    Returns the narration string or None on failure.
    """
    prompt = f"""You are an AI teacher correcting a student's misconception about Ohm's Law.

Misconception: {misconception}
Language: {language}

Write 2-3 sentences of clear, encouraging teacher narration that corrects this
misconception. Use the water-pipe analogy. Write in {language}.

Return ONLY the narration text, no JSON."""

    try:
        return _generate_text(prompt)
    except Exception as exc:
        logger.warning("Gemini repair narration failed: %s", exc)
        return None


def generate_quiz_questions(
    scenes: list[dict[str, Any]], language: str, limit: int = 5
) -> list[dict[str, Any]]:
    """Write end-of-lesson questions for a lesson the authored bank misses.

    Curated lessons use ``services.assessment.QUESTION_BANK``, which is
    deterministic and needs no network. This covers the other case: a learner
    uploaded their own material, so the concepts are whatever the planner found
    in it and no bank could have anticipated them.

    Returns ``[]`` on any failure. A lesson with no quiz still produces a report
    from checkpoint evidence, so the degraded path is a smaller report rather
    than a broken one.
    """
    taught = [
        {
            "conceptId": scene.get("conceptId", ""),
            "objective": scene.get("objective", ""),
            "narration": scene.get("narration", ""),
        }
        for scene in (scenes or [])
        if scene.get("conceptId") and not scene.get("isRepair")
    ][:8]
    if not taught:
        return []

    outline = "\n".join(
        f"- {item['conceptId']}: {item['objective']} | {item['narration'][:220]}"
        for item in taught
    )
    prompt = (
        f"You are an experienced school teacher writing a short end-of-lesson "
        f"quiz. The lesson covered these concepts:\n\n{outline}\n\n"
        f"Write at most {limit} questions that test whether the student can "
        f"USE these ideas, not just repeat them. Mix multiple-choice and "
        f"short-answer. For every wrong multiple-choice option, explain why a "
        f"student might pick it and why it is wrong - that explanation is shown "
        f"to the learner, so make it teach.\n"
        f"Do not change numbers, unit symbols, variable letters or equations.\n"
        f"Return ONLY a JSON array. Each element must be either\n"
        f'  {{"id": "...", "type": "mcq", "conceptId": "...", '
        f'"prompt": {{"english": "..."}}, "options": [{{"id": "a", '
        f'"text": {{"english": "..."}}, "correct": true}}, {{"id": "b", '
        f'"text": {{"english": "..."}}, "why": {{"english": "..."}}}}]}}\n'
        f'or {{"id": "...", "type": "short", "conceptId": "...", '
        f'"prompt": {{"english": "..."}}, "keywords": ["..."], '
        f'"model": {{"english": "..."}}}}\n'
        f"Use concept ids exactly as given above."
    )

    try:
        raw = _call_with_model_fallback(lambda model: _generate_text(prompt))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Quiz generation failed: %s", exc)
        return []

    from services.translation import _parse_json_array

    if not raw:
        return []
    import json as _json

    text = raw.strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        parsed = _json.loads(text[start : end + 1])
    except _json.JSONDecodeError:
        logger.warning("Quiz generation returned unparseable JSON")
        return []
    if not isinstance(parsed, list):
        return []

    # Keep only questions this module knows how to grade, so a malformed
    # element cannot reach the grader.
    valid = []
    for item in parsed:
        if not isinstance(item, dict) or item.get("type") not in ("mcq", "short"):
            continue
        if not item.get("id") or not isinstance(item.get("prompt"), dict):
            continue
        if item["type"] == "mcq":
            options = item.get("options")
            if not isinstance(options, list) or not any(
                isinstance(o, dict) and o.get("correct") for o in options
            ):
                continue
        elif not isinstance(item.get("model"), dict):
            continue
        valid.append(item)
    return valid[:limit]


def grade_short_answer(
    question: str, answer: str, language: str
) -> dict[str, Any] | None:
    """Judge a free-text answer semantically, the way a teacher would.

    Keyword matching cannot tell "voltage pushes the charge along" from
    "voltage is pushed by the charge". This can. Returns None when the model is
    unavailable, and the caller falls back to keyword overlap.
    """
    prompt = (
        f"You are marking one short answer from a Class 9 student.\n"
        f"QUESTION: {question}\n"
        f"STUDENT ANSWER: {answer}\n\n"
        f"Decide whether the answer shows real understanding, allowing for "
        f"informal wording and spelling mistakes. Then write one or two "
        f"sentences of feedback addressed to the student, in a warm and "
        f"encouraging voice. Never use the words 'wrong' or 'incorrect'.\n"
        f'Return ONLY JSON: {{"correct": true or false, "feedback": "..."}}'
    )
    try:
        result = _generate_json(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Short-answer grading failed: %s", exc)
        return None
    if not isinstance(result, dict) or "correct" not in result:
        return None
    return {"correct": bool(result["correct"]), "feedback": result.get("feedback", "")}


def generate_learning_path(topic: str, level: str = "beginner") -> dict[str, Any] | None:
    """Design a module sequence for a topic too broad for one lesson.

    Used only when ``services.planner.learning_path`` has no authored path for
    the topic. The caller validates and topologically sorts whatever comes
    back, so a plausible-looking but unteachable ordering cannot reach a
    learner.

    Returns None when the topic does not actually warrant a path - "what is a
    resistor" is a lesson, not a curriculum, and saying so is more useful than
    inventing eight modules for it.
    """
    prompt = (
        f"A {level} student asks to learn: {topic}\n\n"
        f"If this is narrow enough to teach in a single lesson, reply with "
        f'exactly {{"tooNarrow": true}}.\n'
        f"Otherwise design a learning path of 4 to 10 modules. Order matters: "
        f"a module may only require modules that come before it. Each module "
        f"must be a teachable lesson on its own, and 'why' must say what it "
        f"unlocks - not restate the title.\n"
        f"Return ONLY JSON of the form:\n"
        f'{{"title": "...", "summary": "...", "modules": ['
        f'{{"id": "kebab-case-id", "title": "...", "why": "...", '
        f'"requires": ["earlier-module-id"], "estimatedMinutes": 15}}]}}'
    )
    try:
        result = _generate_json(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Learning path generation failed: %s", exc)
        return None
    if not isinstance(result, dict) or result.get("tooNarrow"):
        return None
    if not isinstance(result.get("modules"), list) or not result["modules"]:
        return None
    return result
