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


_STUDY_MODE_SETS: dict[str, list[str]] = {
    # Assessment-heavy drill: core + extra practice + the real checkpoint + review.
    "exam": [
        "electric-current",
        "ohms-law",
        "ohms-law-practice",
        "ohms-law-application",
        "lesson-summary",
    ],
    # Quick spaced recap: the key law, the checkpoint and the takeaway.
    "revision": [
        "ohms-law",
        "ohms-law-application",
        "lesson-summary",
    ],
}


def _apply_study_mode(concept_ids: list[str], study_mode: str) -> list[str]:
    """Return the concept order to teach for the requested study mode.

    ``lesson`` (default) keeps the time-based tier order untouched so existing
    behaviour and tests are stable. ``exam`` and ``revision`` pick a curated,
    assessment-focused set regardless of the full tier.
    """
    if study_mode not in _STUDY_MODE_SETS:
        return list(concept_ids)
    return list(_STUDY_MODE_SETS[study_mode])


def _tier_name_for(concept_ids: list[str]) -> str:
    """Rename the tier sensibly when a study mode rewrites the concept set."""
    if "ohms-law-practice" in concept_ids:
        return "exam-drill"
    if len(concept_ids) <= 4:
        return "revision"
    return "lesson"


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
    study_mode: str = "lesson",
) -> dict[str, Any]:
    """Build a contract-shaped LessonPlan using the deterministic path."""
    level = learner["level"]
    language = learner["language"]
    available_minutes = int(learner["availableMinutes"])

    _, concept_ids = select_tier(available_minutes)
    concept_ids = _apply_study_mode(concept_ids, study_mode)
    tier_name = study_mode if study_mode != "lesson" else _tier_name_for(concept_ids)
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


def _unsupported_topic_narration(language: str) -> str:
    """Honest, help-not-mislead message for a topic we cannot yet teach offline."""
    return {
        "english": (
            "I don't have curated, source-grounded material for this topic in "
            "offline mode yet. Upload a document, or switch on an LLM API key, "
            "and I'll teach it properly."
        ),
        "hinglish": (
            "Is topic ke liye mere paas abhi offline mode mein curated, "
            "source-grounded content nahi hai. Ek document upload karo, ya LLM "
            "API key on karo, tab main ise sahi tarike se padha sakta hoon."
        ),
        "hindi": (
            "इस विषय के लिए मेरे पास अभी offline मोड में curated, "
            "source-grounded सामग्री नहीं है। कोई document अपलोड करें, या LLM "
            "API key चालू करें, तब मैं इसे सही तरीके से पढ़ा सकता हूँ।"
        ),
    }.get(language, "english")


def _plan_unsupported_topic(
    learner: dict[str, Any],
    material: Material,
    topic: str,
    lesson_id: str | None,
    study_mode: str = "lesson",
) -> dict[str, Any]:
    """Return an honest, contract-shaped plan admitting we lack grounded content.

    Served instead of teaching the wrong subject: when a learner asks for a
    topic that resolves to no source material (no upload, no built-in corpus)
    and no LLM is available, we say so instead of silently teaching Electricity.
    The single scene never fabricates a citation, never transforms into another
    subject, and tells the learner exactly how to proceed.
    """
    language = learner["language"]
    level = learner["level"]
    available_minutes = int(learner.get("availableMinutes", 10))
    narration = _unsupported_topic_narration(language)
    if level != "beginner":
        narration = (
            f"{narration} "
            + {
                "beginner": "",
                "intermediate": (
                    "(Note: offline mode covers the built-in Electricity corpus "
                    "and any document you upload.)"
                    if language == "english"
                    else "(Note: offline mode mein built-in Electricity corpus aur "
                    "aapke upload kiye document hi available hain.)"
                    if language == "hinglish"
                    else "(ध्यान दें: offline मोड में built-in Electricity corpus और "
                    "आपके upload किए document ही उपलब्ध हैं।)"
                ),
                "advanced": (
                    "(Tip: paste the source text or upload a PDF/PPTX from any "
                    "syllabus and this becomes a grounded lesson.)"
                    if language == "english"
                    else "(Tip: koi bhi syllabus ka source text paste karo ya "
                    "PDF/PPTX upload karo, yah grounded lesson ban jayega.)"
                    if language == "hinglish"
                    else "(टिप: किसी भी syllabus का source text पेस्ट करें या "
                    "PDF/PPTX अपलोड करें, यह grounded lesson बन जाएगा।)"
                ),
            }[level]
        )

    scenes = [
        {
            "id": f"scene-1-unsupported-topic",
            "conceptId": "unsupported-topic",
            "objective": f"Understanding {topic or 'this topic'}",
            "narration": narration,
            "visual": {"type": "concept_map", "data": {}},
            "citations": [],
            "durationSeconds": max(MIN_SCENE_SECONDS, int(round(30 * available_minutes / 10))),
            "groundingStatus": "general_knowledge",
            "unsupportedTopic": True,
        }
    ]

    return {
        "id": lesson_id or f"lesson-{uuid.uuid4().hex[:8]}",
        "learner": dict(learner),
        "scenes": scenes,
        "topic": topic,
        "materialId": material.material_id,
        "documentTitle": material.title,
        "tier": "unsupported-topic",
        "estimatedSeconds": scenes[0]["durationSeconds"],
        "studyMode": study_mode,
        "unsupportedTopic": True,
    }


def _has_groundable_content(material: Material) -> bool:
    """True when the material can actually ground a lesson.

    An uploaded document or the built-in Electricity corpus has sections. A
    topic-only request for an unknown subject resolves to an empty Material
    (``origin == "topic-only"`` with no sections).
    """
    if material.sections:
        return True
    # The empty-topic default still maps to the built-in Electricity corpus,
    # which carries sections -- so reaching here genuinely means "unknown topic".
    return False


def plan_lesson(
    learner: dict[str, Any],
    material: Material,
    topic: str = "Ohm's Law",
    lesson_id: str | None = None,
    study_mode: str = "lesson",
) -> dict[str, Any]:
    """Build a contract-shaped ``LessonPlan`` for this learner and material.

    Tries Gemini Flash first (for richer, topic-agnostic content), falls back
    to the deterministic path if the LLM is unavailable or fails.

    ``study_mode`` changes which study style is served:
      * ``lesson``   - a normal teaching lesson (default)
      * ``exam``     - assessment-heavy drill, centred on the checkpoint/practice
      * ``revision`` - a quick spaced recap, centred on core + summary

    When the material carries no grounded content (an unknown topic with no
    upload and no built-in corpus) the deterministic fallback returns an honest
    "unsupported topic" plan instead of silently teaching the wrong subject.
    """
    # Vector-index the material so retrieval can use the persistent ChromaDB
    # store (falls back silently to in-memory/keyword search if unavailable).
    try:
        index_sections(material.sections, material.document_id)
    except Exception as exc:
        logger.warning("Vector indexing skipped: %s", exc)

    llm_plan = _plan_lesson_llm(learner, material, topic, lesson_id)
    if llm_plan is not None:
        llm_plan["studyMode"] = study_mode
        return llm_plan

    # Honest refusal over wrong content: with no LLM and nothing to ground on,
    # never silently teach the Electricity default to a learner who asked for
    # Photosynthesis or Newton's Laws.
    if not _has_groundable_content(material):
        return _plan_unsupported_topic(
            learner, material, topic, lesson_id, study_mode
        )

    plan = _plan_lesson_deterministic(learner, material, topic, lesson_id, study_mode)
    plan["studyMode"] = study_mode
    return plan
