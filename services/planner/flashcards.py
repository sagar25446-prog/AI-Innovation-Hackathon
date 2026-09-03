"""Deterministic flashcard generation from a lesson plan.

Turns the concepts a lesson taught into review flashcards (front -> back),
including the key Ohm's Law formulae, without needing an LLM or network. This
is a self-contained, testable "advanced feature" that works offline.
"""

from __future__ import annotations

from typing import Any

# A compact, language-neutral formula/recall bank keyed by concept id. Backs
# are phrased so a learner can self-test after the lesson.
_FLASH_BANK: dict[str, dict[str, str]] = {
    "electric-current": {
        "english": "Current is the flow of electric charge through a wire, measured in amperes (A).",
        "hindi": "धारा तार में आवेश का प्रवाह है, जिसे एम्पियर (A) में मापा जाता है।",
        "hinglish": "Current charge ka wire mein flow hai, jise amperes (A) mein measure karte hain.",
    },
    "voltage": {
        "english": "Voltage (V) is the electric push between two points that drives current.",
        "hindi": "वोल्टेज (V) दो बिंदुओं के बीच का विद्युत बल है जो धारा चलाता है।",
        "hinglish": "Voltage (V) do points ke beech ka electric push hai jo current chalata hai.",
    },
    "resistance": {
        "english": "Resistance (R) opposes the flow of current and is measured in ohms (Ω).",
        "hindi": "प्रतिरोध (R) धारा के प्रवाह का विरोध करता है, जिसे ओम (Ω) में मापा जाता है।",
        "hinglish": "Resistance (R) current ke flow ko oppose karta hai, ohms (Ω) mein measure hota hai.",
    },
    "ohms-law": {
        "english": "V = I × R. Voltage equals current times resistance.",
        "hindi": "V = I × R। वोल्टेज धारा गुणा प्रतिरोध के बराबर है।",
        "hinglish": "V = I × R. Voltage, current times resistance ke barabar hota hai.",
    },
    "ohms-law-practice": {
        "english": "To find current, divide voltage by resistance: I = V / R.",
        "hindi": "धारा पाने के लिए वोल्टेज को प्रतिरोध से विभाजित करें: I = V / R।",
        "hinglish": "Current nikalne ke liye voltage ko resistance se divide karo: I = V / R.",
    },
    "ohms-law-application": {
        "english": "At constant voltage, if resistance increases, current decreases (I = V / R).",
        "hindi": "स्थिर वोल्टेज पर यदि प्रतिरोध बढ़े तो धारा घटती है (I = V / R)।",
        "hinglish": "Constant voltage par agar resistance badhe to current ghatta hai (I = V / R).",
    },
}


def generate_flashcards(
    scenes: list[dict[str, Any]],
    language: str = "hinglish",
    concept_ids: list[str] | None = None,
) -> list[dict[str, str]]:
    """Build review cards from the scenes a lesson taught.

    ``concept_ids`` optionally filters to specific concepts (e.g. the learner's
    weak spots from long-term memory). Cards are deduplicated by concept and
    always include the core Ohm's Law formula card.
    """
    if language not in _FLASH_BANK.get("ohms-law", {}):
        language = "hinglish"

    wanted = set(concept_ids) if concept_ids else None
    seen: set[str] = set()
    cards: list[dict[str, str]] = []

    # Cards from the actual scenes in teaching order.
    for scene in scenes:
        concept_id = scene.get("conceptId")
        if not concept_id or concept_id in seen:
            continue
        if wanted is not None and concept_id not in wanted:
            continue
        bank = _FLASH_BANK.get(concept_id)
        if bank is None:
            continue
        objective = scene.get("objective") or ""
        front = f"What is {concept_id.replace('-', ' ')}?"
        if objective:
            front = objective
        cards.append({
            "conceptId": concept_id,
            "front": front,
            "back": bank.get(language, bank.get("english", "")),
        })
        seen.add(concept_id)

    # Always ensure the core formula card is present for a complete review.
    if "ohms-law" not in seen and (wanted is None or "ohms-law" in wanted):
        cards.append({
            "conceptId": "ohms-law",
            "front": "State Ohm's Law.",
            "back": _FLASH_BANK["ohms-law"][language],
        })
        seen.add("ohms-law")

    return cards


def flashcard_count(scenes: list[dict[str, Any]], concept_ids: list[str] | None = None) -> int:
    return len(generate_flashcards(scenes, concept_ids=concept_ids))
