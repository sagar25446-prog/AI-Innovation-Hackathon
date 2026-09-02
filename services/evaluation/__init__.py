"""Checkpoint evaluation, mastery tracking and the final learning report.

This is the adaptive half of the product loop. A wrong answer is never met with
"Wrong." -- it produces a diagnosis, supportive feedback and a *different*
teaching scene that attacks the specific misconception, followed by a retry.
"""

from __future__ import annotations

from typing import Any

from services.evaluation.misconceptions import (
    CONSTANT_CURRENT,
    DIRECT_PROPORTIONALITY,
    classify_answer,
    misconception_id,
)
from services.planner.concepts import CHECKPOINT_CONCEPT_ID, NEXT_TOPIC

# Mastery values are fixed by the demo fixtures so the API and
# ``demo-fixtures/`` never disagree.
MASTERY_FIRST_TRY_CORRECT = 0.75
MASTERY_AFTER_REPAIR = 0.6
MASTERY_MISCONCEPTION = 0.35
MASTERY_UNCLEAR = 0.4

_REPAIR_CITATION = {
    "documentId": "ncert-class9-science-ch12",
    "pageOrSlide": 205,
    "excerpt": (
        "It is obvious from Eq. (12.5) that the current through a resistor is "
        "inversely proportional to its resistance."
    ),
}

FEEDBACK = {
    "correct_first": {
        "english": "Exactly right! Increasing resistance lowers the current, because I = V/R.",
        "hindi": "बिल्कुल सही! प्रतिरोध बढ़ने से धारा कम होती है, क्योंकि I = V/R।",
        "hinglish": "Bilkul sahi! Resistance badhne se current kam hota hai kyunki I = V/R.",
    },
    "correct_retry": {
        "english": (
            "Well done! Now you have it - more resistance means less current. "
            "Keep the water pipe picture in mind."
        ),
        "hindi": (
            "बहुत बढ़िया! अब समझ आ गया - प्रतिरोध बढ़ने से धारा कम होती है। "
            "पानी की पाइप वाली तुलना याद रखना।"
        ),
        "hinglish": (
            "Bahut accha! Ab samajh aa gaya - resistance badhne se current kam "
            "hota hai. Water pipe analogy yaad rakhna!"
        ),
    },
    "direct-proportionality": {
        "english": (
            "Almost! But remember - with the voltage fixed, I = V/R, so raising "
            "the resistance makes the current SMALLER, not larger."
        ),
        "hindi": (
            "लगभग सही! लेकिन याद रखो - वोल्टेज स्थिर होने पर I = V/R, इसलिए "
            "प्रतिरोध बढ़ाने से धारा कम होती है, ज़्यादा नहीं।"
        ),
        "hinglish": (
            "Lagbhag sahi! Lekin yaad rakho - voltage fixed hone par, I = V/R, "
            "toh resistance badhne se current KAM hota hai, zyada nahi."
        ),
    },
    "constant-current": {
        "english": (
            "Good thinking, but not quite. The voltage stays fixed, not the "
            "current. Since I = V/R, changing R must change I."
        ),
        "hindi": (
            "अच्छा सोचा, पर पूरी तरह सही नहीं। वोल्टेज स्थिर है, धारा नहीं। "
            "चूँकि I = V/R, R बदलने पर I भी बदलेगी।"
        ),
        "hinglish": (
            "Accha socha, par bilkul sahi nahi. Voltage fixed hai, current nahi. "
            "Kyunki I = V/R, R badlega toh I bhi badlega."
        ),
    },
    "unclear": {
        "english": "Let's try once more. In one line: does the current go up or down?",
        "hindi": "एक बार और कोशिश करो। एक पंक्ति में: धारा बढ़ेगी या घटेगी?",
        "hinglish": "Ek baar aur try karo. Ek line mein: current badhega ya kam hoga?",
    },
}

REPAIR_NARRATION = {
    DIRECT_PROPORTIONALITY: {
        "english": (
            "Think of water flowing through a pipe. If you make the pipe narrower "
            "(that is, raise the resistance), the water flow (the current) gets "
            "SMALLER, not larger! In the same way, in I = V/R, when R goes up, I "
            "comes down."
        ),
        "hindi": (
            "सोचो एक पाइप में पानी बह रहा है। अगर पाइप को पतला कर दो (यानी प्रतिरोध "
            "बढ़ाओ), तो पानी का बहाव (यानी धारा) कम होगा, ज़्यादा नहीं! इसी तरह, "
            "I = V/R में, जब R बढ़ता है तो I घटती है।"
        ),
        "hinglish": (
            "Socho ek pipe mein paani beh raha hai. Agar pipe ko narrow kar do "
            "(matlab resistance badhao), toh paani ka flow (matlab current) KAM "
            "hoga, zyada nahi! Isi tarah, I = V/R mein, jab R badhta hai toh I "
            "GHATTA hai."
        ),
    },
    CONSTANT_CURRENT: {
        "english": (
            "Only the voltage is held fixed here, not the current. Look at the "
            "pipe: the pump pressure stays the same, but a narrower pipe still "
            "slows the flow. In I = V/R, if R changes then I must change too."
        ),
        "hindi": (
            "यहाँ केवल वोल्टेज स्थिर है, धारा नहीं। पाइप देखो: पंप का दबाव वही "
            "रहता है, फिर भी पतला पाइप बहाव को धीमा कर देता है। I = V/R में, "
            "R बदलेगा तो I भी बदलेगी।"
        ),
        "hinglish": (
            "Yahan sirf voltage fixed hai, current nahi. Pipe dekho: pump ka "
            "pressure same rehta hai, phir bhi narrow pipe flow ko slow kar deta "
            "hai. I = V/R mein, R badlega toh I bhi badlega."
        ),
    },
}

REPAIR_OBJECTIVE = {
    DIRECT_PROPORTIONALITY: "Correct direct-proportionality misconception",
    CONSTANT_CURRENT: "Correct the belief that current stays constant",
}


def build_repair_scene(misconception: str, language: str) -> dict[str, Any]:
    """Build the corrective Scene for a diagnosed misconception.

    The visual deliberately carries all three repair elements the brief asks
    for -- the equation transformation, the water-pipe analogy and the
    descending current-vs-resistance curve -- inside one 30 second scene.
    """
    return {
        "id": f"scene-repair-{'ohms-law' if misconception == DIRECT_PROPORTIONALITY else 'constant-current'}",
        "conceptId": "ohms-law",
        "objective": REPAIR_OBJECTIVE[misconception],
        "narration": REPAIR_NARRATION[misconception][language],
        "visual": {
            "type": "equation",
            "data": {
                "steps": ["I = V / R", "↑ Resistance = ↓ Current"],
                "analogy": "water-pipe",
                "graph": {
                    "xAxis": {"label": "Resistance (ohm)"},
                    "yAxis": {"label": "Current (A)"},
                    "points": [
                        {"x": 1, "y": 10.0},
                        {"x": 2, "y": 5.0},
                        {"x": 5, "y": 2.0},
                        {"x": 10, "y": 1.0},
                    ],
                    "caption": "As R rises, I falls",
                },
            },
        },
        "citations": [dict(_REPAIR_CITATION)],
        "durationSeconds": 30,
        "isRepair": True,
    }


def evaluate_answer(
    answer: str,
    language: str,
    attempt: int,
    option_id: str | None = None,
) -> dict[str, Any]:
    """Evaluate one checkpoint answer into a contract ``EvaluationResult``.

    ``attempt`` is 1-based: attempt 1 is the learner's first try, attempt 2+
    means they are retrying after a repair scene.
    """
    classification = classify_answer(answer, option_id)

    if classification == "correct":
        first_try = attempt <= 1
        return {
            "correct": True,
            "mastery": MASTERY_FIRST_TRY_CORRECT if first_try else MASTERY_AFTER_REPAIR,
            "feedback": FEEDBACK["correct_first" if first_try else "correct_retry"][language],
            "nextAction": "advance",
        }

    if classification == "unclear":
        return {
            "correct": False,
            "mastery": MASTERY_UNCLEAR,
            "feedback": FEEDBACK["unclear"][language],
            "nextAction": "retry",
        }

    misconception = misconception_id(classification)
    return {
        "correct": False,
        "mastery": MASTERY_MISCONCEPTION,
        "misconception": misconception,
        "feedback": FEEDBACK[classification][language],
        "nextAction": "repair",
        "repairScene": build_repair_scene(misconception, language),
    }


def build_report(
    student_id: str,
    lesson_id: str,
    concept_mastery: dict[str, float],
    misconceptions: list[dict[str, Any]],
    scenes_completed: int,
    checkpoints_passed: int,
    checkpoints_failed: int,
    total_time_seconds: int,
) -> dict[str, Any]:
    """Assemble the final learning report from the learner's session state."""
    strong = sorted([c for c, m in concept_mastery.items() if m >= 0.7])
    weak = sorted([c for c, m in concept_mastery.items() if m < 0.7])

    score = (
        round(sum(concept_mastery.values()) / len(concept_mastery), 2)
        if concept_mastery
        else 0.0
    )

    revision_actions: list[str] = []
    if any(m["id"] == DIRECT_PROPORTIONALITY for m in misconceptions):
        revision_actions.append(
            "Practise more I = V/R calculations with different R values"
        )
        revision_actions.append("Try the water pipe simulation")
    if any(m["id"] == CONSTANT_CURRENT for m in misconceptions):
        revision_actions.append(
            "Re-read which quantity is held constant before applying I = V/R"
        )
    if weak:
        revision_actions.append(f"Revisit: {', '.join(weak)}")
    if not revision_actions:
        revision_actions.append("Move on to Series and Parallel Circuits")

    return {
        "studentId": student_id,
        "lessonId": lesson_id,
        "score": score,
        "strongConcepts": strong,
        "weakConcepts": weak,
        "misconceptions": misconceptions,
        "revisionActions": revision_actions,
        "nextTopic": dict(NEXT_TOPIC),
        "totalTimeSeconds": total_time_seconds,
        "scenesCompleted": scenes_completed,
        "checkpointsPassed": checkpoints_passed,
        "checkpointsFailed": checkpoints_failed,
    }


__all__ = [
    "CHECKPOINT_CONCEPT_ID",
    "CONSTANT_CURRENT",
    "DIRECT_PROPORTIONALITY",
    "build_repair_scene",
    "build_report",
    "classify_answer",
    "evaluate_answer",
]
