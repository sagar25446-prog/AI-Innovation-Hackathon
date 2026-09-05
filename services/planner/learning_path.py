"""Learning paths: what to study, in what order, for a topic too big for one lesson.

"Teach me Machine Learning" is not a lesson request. It is a request for a
*curriculum* - eight or ten lessons that have to arrive in the right order,
because gradient descent before calculus teaches nothing. GuruFlow could plan a
single lesson on any topic; it had no answer for the topic that needs twelve.

So a broad topic now produces a path: an ordered list of modules, each one a
teachable lesson, each with its prerequisites named. The learner's progress
moves through it, and the path knows which module is next.

Two sources, in order:

* **Authored paths** for the subjects the demo covers, so the flagship journey
  is deterministic and works with no API key at all.
* **Gemini** for everything else, constrained to the same shape and validated
  before it is trusted - a path whose prerequisites point at modules that do
  not exist is worse than no path.

A path is not a syllabus dump: ``next_module`` reads the learner's mastery and
returns the first module they are not ready to skip, so the sequence responds
to what they already know rather than restarting everyone at module one.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from services.translation import localize

logger = logging.getLogger(__name__)

# A module is "done" once the learner's mastery of it clears this bar.
MASTERY_COMPLETE = 0.7


# ---------------------------------------------------------------------------
# Authored paths
# ---------------------------------------------------------------------------
# Keyed by a normalised topic. Each module is a lesson GuruFlow can actually
# teach, so a learner can walk the path rather than only read it.

AUTHORED_PATHS: dict[str, dict[str, Any]] = {
    "electricity": {
        "title": "Electricity and Circuits",
        "summary": (
            "Build up from what charge is to solving real circuits, one idea at "
            "a time. Each step assumes only the steps before it."
        ),
        "modules": [
            {
                "id": "electric-current",
                "title": "Electric Current",
                "why": "Everything else describes what current does, so it comes first.",
                "requires": [],
                "estimatedMinutes": 10,
            },
            {
                "id": "voltage",
                "title": "Voltage",
                "why": "Current needs a push. Voltage is the push.",
                "requires": ["electric-current"],
                "estimatedMinutes": 10,
            },
            {
                "id": "resistance",
                "title": "Resistance",
                "why": "What opposes the flow, and why thin wires resist more.",
                "requires": ["electric-current"],
                "estimatedMinutes": 10,
            },
            {
                "id": "ohms-law",
                "title": "Ohm's Law",
                "why": "The relationship that ties the first three together: V = I x R.",
                "requires": ["voltage", "resistance"],
                "estimatedMinutes": 15,
            },
            {
                "id": "series-parallel-circuits",
                "title": "Series and Parallel Circuits",
                "why": "Apply Ohm's Law to circuits with more than one component.",
                "requires": ["ohms-law"],
                "estimatedMinutes": 20,
            },
            {
                "id": "electrical-power",
                "title": "Electrical Power and Heating",
                "why": "Where the energy goes, and why a bulb gets hot.",
                "requires": ["ohms-law"],
                "estimatedMinutes": 15,
            },
        ],
    },
}

# Topic phrasings that should resolve to an authored path. Matched on
# whole words, so "current affairs" does not become an electricity course.
_TOPIC_ALIASES: dict[str, str] = {
    "electricity": "electricity",
    "electric current": "electricity",
    "current electricity": "electricity",
    "circuits": "electricity",
    "ohms law": "electricity",
    "ohm law": "electricity",
    "voltage": "electricity",
    "resistance": "electricity",
}


def _normalise(topic: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (topic or "").lower()).strip()


def authored_path_for(topic: str) -> dict[str, Any] | None:
    """Match a topic to an authored path, or None."""
    normalised = _normalise(topic)
    if not normalised:
        return None
    if normalised in _TOPIC_ALIASES:
        return AUTHORED_PATHS[_TOPIC_ALIASES[normalised]]
    words = set(normalised.split())
    for alias, key in _TOPIC_ALIASES.items():
        alias_words = set(alias.split())
        if alias_words and alias_words <= words:
            return AUTHORED_PATHS[key]
    return None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validated(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop anything malformed, and make the ordering actually teachable.

    Two failure modes matter, and both come from generated paths:

    * a module requiring one that does not exist, and
    * a module appearing *before* something it requires.

    Either makes the path worse than none, so unknown prerequisites are
    dropped and the modules are topologically ordered.
    """
    clean: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for module in modules or []:
        if not isinstance(module, dict):
            continue
        module_id = str(module.get("id") or "").strip()
        title = str(module.get("title") or "").strip()
        if not module_id or not title or module_id in seen_ids:
            continue
        seen_ids.add(module_id)
        clean.append(
            {
                "id": module_id,
                "title": title,
                "why": str(module.get("why") or "").strip(),
                "requires": [
                    str(r).strip()
                    for r in (module.get("requires") or [])
                    if str(r).strip()
                ],
                "estimatedMinutes": int(module.get("estimatedMinutes") or 15),
            }
        )

    # Drop prerequisites pointing at modules that are not in the path.
    for module in clean:
        module["requires"] = [r for r in module["requires"] if r in seen_ids]

    return _topological(clean)


def _topological(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order modules so every prerequisite comes before its dependant.

    Falls back to the given order for anything caught in a cycle, so a
    self-referential path still renders instead of vanishing.
    """
    by_id = {m["id"]: m for m in modules}
    ordered: list[dict[str, Any]] = []
    placed: set[str] = set()

    remaining = list(modules)
    while remaining:
        ready = [m for m in remaining if all(r in placed for r in m["requires"])]
        if not ready:
            # A cycle. Emit the rest in their original order rather than looping.
            ordered.extend(remaining)
            break
        for module in ready:
            ordered.append(module)
            placed.add(module["id"])
        remaining = [m for m in remaining if m["id"] not in placed]

    return [by_id.get(m["id"], m) for m in ordered]


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


def build_learning_path(
    topic: str,
    language: str = "english",
    *,
    concept_mastery: dict[str, float] | None = None,
    level: str = "beginner",
) -> dict[str, Any] | None:
    """Build an ordered learning path for a broad topic.

    Returns None when the topic is not broad enough to warrant a path and no
    model is available to judge otherwise - the caller then plans a single
    lesson exactly as before.
    """
    mastery = concept_mastery or {}

    authored = authored_path_for(topic)
    source = "authored"
    if authored:
        title = authored["title"]
        summary = authored["summary"]
        modules = _validated(authored["modules"])
    else:
        generated = _llm_path(topic, level)
        if not generated:
            return None
        source = "generated"
        title = generated.get("title") or topic
        summary = generated.get("summary") or ""
        modules = _validated(generated.get("modules", []))

    if not modules:
        return None

    for module in modules:
        score = mastery.get(module["id"])
        module["mastery"] = round(score, 2) if score is not None else None
        module["status"] = (
            "complete"
            if score is not None and score >= MASTERY_COMPLETE
            else "available"
            if all(
                mastery.get(r, 0.0) >= MASTERY_COMPLETE for r in module["requires"]
            )
            else "locked"
        )
        module["title"] = localize(module["title"], language)
        if module["why"]:
            module["why"] = localize(module["why"], language)

    current = next((m for m in modules if m["status"] != "complete"), None)
    completed = sum(1 for m in modules if m["status"] == "complete")

    return {
        "topic": topic,
        "title": localize(title, language),
        "summary": localize(summary, language) if summary else "",
        "source": source,
        "language": language,
        "modules": modules,
        "moduleCount": len(modules),
        "completedCount": completed,
        "progress": round(completed / len(modules), 4),
        "nextModuleId": current["id"] if current else None,
        "totalMinutes": sum(m["estimatedMinutes"] for m in modules),
    }


def _llm_path(topic: str, level: str) -> dict[str, Any] | None:
    """Ask Gemini for a path when no authored one matches."""
    try:
        from services.llm import gemini_available, generate_learning_path
    except ImportError:
        return None
    if not gemini_available():
        return None
    try:
        return generate_learning_path(topic, level)
    except Exception as exc:  # noqa: BLE001 - a missing path is not a failure
        logger.warning("Learning path generation failed for %r: %s", topic, exc)
        return None


def next_module(path: dict[str, Any]) -> dict[str, Any] | None:
    """The module the learner should study now."""
    if not path:
        return None
    return next(
        (m for m in path.get("modules", []) if m["id"] == path.get("nextModuleId")),
        None,
    )


__all__ = [
    "AUTHORED_PATHS",
    "MASTERY_COMPLETE",
    "authored_path_for",
    "build_learning_path",
    "next_module",
]
