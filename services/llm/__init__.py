"""LLM service for GuruFlow.

Provides Gemini Flash integration for planning, evaluation, and content
generation. All functions return None when the API is unavailable, letting
consumers fall back to deterministic logic.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# Model read from env. Default to a current, widely-available Flash model.
_MODEL_NAME = os.environ.get("GURUFLOW_GEMINI_MODEL", "gemini-2.5-flash").strip()

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
        logger.info("Loaded Gemini client, model: %s", _MODEL_NAME)
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
        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.4,
            },
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
        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config={"temperature": 0.6},
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
