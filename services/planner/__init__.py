"""Lesson planning: turn a learner profile plus material into Scene objects.

The planner emits ``Scene`` objects, never long chatbot answers. Adaptation
happens on three axes required by the brief:

* **order/breadth** - the time budget selects a tier of concepts
* **depth** - the level appends extra explanation to each narration
* **language** - english / hindi / hinglish narration, formulae unchanged

When GEMINI_API_KEY is set, the planner uses Gemini Flash for richer,
topic-agnostic planning while keeping the deterministic path as fallback.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from services.ingestion import Material
from services.planner.concepts import CONCEPTS_BY_ID
from services.planner.persona import apply_persona_narration
from services.rag import (
    best_citations,
    grounding_status,
    index_sections,
    retrieve,
)

logger = logging.getLogger(__name__)

# Concept order per time budget. Every tier keeps the required teaching order:
# Current -> Voltage -> Resistance -> Ohm's Law -> checkpoint -> assessment.
TIERS: list[tuple[int, str, list[str]]] = [
    (
        5,
        "compact",
        ["electric-current", "ohms-law", "ohms-law-application"],
    ),
    (
        10,
        "standard",
        [
            "intro-electricity",
            "electric-current",
            "resistance",
            "ohms-law",
            "ohms-law-application",
            "lesson-summary",
        ],
    ),
    (
        20,
        "full",
        [
            "intro-electricity",
            "electric-current",
            "voltage",
            "resistance",
            "ohms-law",
            "ohms-law-application",
            "lesson-summary",
        ],
    ),
    (
        10080,
        "deep",
        [
            "intro-electricity",
            "electric-current",
            "voltage",
            "resistance",
            "ohms-law",
            "ohms-law-practice",
            "ohms-law-application",
            "lesson-summary",
        ],
    ),
]

# Higher levels get more words per scene, so scenes run slightly longer.
LEVEL_DURATION_MULTIPLIER = {"beginner": 1.0, "intermediate": 1.15, "advanced": 1.3}

CHECKPOINT_ID = "checkpoint-ohms-law-1"

MIN_SCENE_SECONDS = 15


def select_tier(available_minutes: int) -> tuple[str, list[str]]:
    """Pick the concept set that suits the learner's time budget."""
    for limit, name, concept_ids in TIERS:
        if available_minutes <= limit:
            return name, list(concept_ids)
    _, name, concept_ids = TIERS[-1]
    return name, list(concept_ids)


def build_narration(concept: dict[str, Any], language: str, level: str) -> str:
    """Base narration in the learner's language, deepened for higher levels."""
    narration = concept["narration"][language]
    if level == "beginner":
        return narration
    extra = concept.get("depth", {}).get(language, {}).get(level)
    return f"{narration} {extra}" if extra else narration


def _compress(durations: list[int], budget_seconds: int) -> list[int]:
    """Shrink scene durations proportionally if the plan overruns the budget.

    Scenes are never stretched to fill unused time -- an honest 4-minute lesson
    inside a 60-minute budget is better than padding.
    """
    total = sum(durations)
    if total <= budget_seconds or total == 0:
        return durations
    factor = budget_seconds / total
    return [max(MIN_SCENE_SECONDS, int(round(d * factor))) for d in durations]


def _plan_lesson_deterministic(
    learner: dict[str, Any],
    material: Material,
    topic: str,
    lesson_id: str | None,
) -> dict[str, Any]:
    """Build a contract-shaped LessonPlan using the deterministic path."""
    level = learner["level"]
    language = learner["language"]
    available_minutes = int(learner["availableMinutes"])

    tier_name, concept_ids = select_tier(available_minutes)
    multiplier = LEVEL_DURATION_MULTIPLIER[level]

    raw_durations = [
        max(MIN_SCENE_SECONDS, int(round(CONCEPTS_BY_ID[cid]["baseSeconds"] * multiplier)))
        for cid in concept_ids
    ]
    durations = _compress(raw_durations, available_minutes * 60)

    scenes: list[dict[str, Any]] = []
    for index, concept_id in enumerate(concept_ids):
        concept = CONCEPTS_BY_ID[concept_id]
        results = retrieve(concept["query"], material.sections, material.document_id)

        narration = build_narration(concept, language, level)
        narration = apply_persona_narration(
            narration, learner.get("personality"), language, level
        )

        scene: dict[str, Any] = {
            "id": f"scene-{index + 1}-{concept_id}",
            "conceptId": concept_id,
            "objective": concept["objective"][language],
            "narration": narration,
            "visual": concept["visual"],
            "citations": best_citations(results),
            "durationSeconds": durations[index],
            "groundingStatus": grounding_status(results),
        }
        if concept.get("checkpoint"):
            scene["checkpointId"] = CHECKPOINT_ID
        scenes.append(scene)

    return {
        "id": lesson_id or f"lesson-{uuid.uuid4().hex[:8]}",
        "learner": dict(learner),
        "scenes": scenes,
        "topic": topic,
        "materialId": material.material_id,
        "documentTitle": material.title,
        "tier": tier_name,
        "estimatedSeconds": sum(durations),
    }


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalise_visual(visual: Any) -> dict[str, Any]:
    """Coerce a scene's visual spec to a known type with a valid data payload."""
    if not isinstance(visual, dict):
        return {"type": "concept_map", "data": {}}
    vtype = visual.get("type")
    if vtype not in ("circuit", "equation", "graph", "concept_map",
                     "water_pipe_analogy", "timeline", "diagram", "code_trace"):
        vtype = "concept_map"
    data = visual.get("data")
    if not isinstance(data, dict):
        data = {}
    return {"type": vtype, "data": data}


def _normalise_citations(citations: Any) -> list[dict[str, Any]]:
    """Coerce an LLM-supplied citations list to the contract citation shape.

    Gemini sometimes emits free-form JSON (bare numbers/strings where a
    citation object belongs). We drop anything that is not a dict and keep only
    the fields the contract understands, so a stray token never becomes a 422.
    """
    if not isinstance(citations, list):
        return []
    normalised: list[dict[str, Any]] = []
    for item in citations:
        if not isinstance(item, dict):
            continue
        citation: dict[str, Any] = {}
        if isinstance(item.get("documentId"), str):
            citation["documentId"] = item["documentId"]
        if item.get("pageOrSlide") is not None:
            page = _as_int(item.get("pageOrSlide"), 0)
            if page > 0:
                citation["pageOrSlide"] = page
        if isinstance(item.get("heading"), str):
            citation["heading"] = item["heading"]
        if isinstance(item.get("excerpt"), str):
            citation["excerpt"] = item["excerpt"]
        if citation:
            normalised.append(citation)
    return normalised


def _normalise_llm_scenes(scenes: Any) -> list[dict[str, Any]]:
    """Coerce LLM-produced scenes into the contract shape.

    Gemini may return free-form JSON. We defensively normalise every scene so
    Pydantic never rejects a valid plan because of one malformed field, and the
    caller falls back to the deterministic engine when the outline is unusable.
    """
    normalised: list[dict[str, Any]] = []
    for i, scene in enumerate(scenes or []):
        if not isinstance(scene, dict):
            continue
        citations = _normalise_citations(scene.get("citations"))
        grounding = scene.get("groundingStatus")
        if not isinstance(grounding, str) or grounding not in (
            "source_grounded", "general_knowledge",
        ):
            grounding = "source_grounded" if citations else "general_knowledge"
        normalised_scene: dict[str, Any] = {
            "id": scene.get("id") or f"scene-{i + 1}-llm",
            "conceptId": scene.get("conceptId") or f"concept-{i + 1}",
            "objective": scene.get("objective", ""),
            "narration": scene.get("narration", ""),
            "durationSeconds": _as_int(scene.get("durationSeconds"), 30) or 30,
            "visual": _normalise_visual(scene.get("visual")),
            "citations": citations,
            "groundingStatus": grounding,
        }
        if scene.get("checkpointId"):
            normalised_scene["checkpointId"] = str(scene["checkpointId"])
        normalised.append(normalised_scene)
    return normalised


def _plan_lesson_llm(
    learner: dict[str, Any],
    material: Material,
    topic: str,
    lesson_id: str | None,
) -> dict[str, Any] | None:
    """Try Gemini Flash to generate a richer, topic-agnostic plan.

    Returns None if the LLM call fails so the caller can fall back.
    """
    try:
        from services.llm import generate_plan
        llm_result = generate_plan(
            learner=learner,
            material_sections=material.sections,
            topic=topic,
            document_id=material.document_id,
        )
        if not llm_result or not llm_result.get("scenes"):
            return None

        scenes = _normalise_llm_scenes(llm_result["scenes"])
        if not scenes:
            return None

        total_seconds = sum(s.get("durationSeconds", 30) for s in scenes)
        return {
            "id": lesson_id or f"lesson-{uuid.uuid4().hex[:8]}",
            "learner": dict(learner),
            "scenes": scenes,
            "topic": topic,
            "materialId": material.material_id,
            "documentTitle": material.title,
            "tier": "llm-generated",
            "estimatedSeconds": total_seconds,
        }
    except Exception as exc:
        logger.warning("LLM plan generation failed, falling back to deterministic: %s", exc)
        return None


def plan_lesson(
    learner: dict[str, Any],
    material: Material,
    topic: str = "Ohm's Law",
    lesson_id: str | None = None,
) -> dict[str, Any]:
    """Build a contract-shaped ``LessonPlan`` for this learner and material.

    Tries Gemini Flash first (for richer, topic-agnostic content), falls back
    to the deterministic path if the LLM is unavailable or fails.
    """
    # Vector-index the material so retrieval can use the persistent ChromaDB
    # store (falls back silently to in-memory/keyword search if unavailable).
    try:
        index_sections(material.sections, material.document_id)
    except Exception as exc:
        logger.warning("Vector indexing skipped: %s", exc)

    llm_plan = _plan_lesson_llm(learner, material, topic, lesson_id)
    if llm_plan is not None:
        return llm_plan

    return _plan_lesson_deterministic(learner, material, topic, lesson_id)
