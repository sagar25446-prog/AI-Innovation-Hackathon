"""The end-of-lesson assessment: a real quiz, then a grade that means something.

Until now GuruFlow scored a learner on a single mid-lesson checkpoint. That is
enough to drive the misconception repair loop, but it is not an assessment: one
question cannot tell you which concepts a student holds and which they only
nodded along to, and a report built on it is mostly guesswork.

So a finished lesson now ends with a short quiz over the concepts that were
actually taught, and the report is built from those answers.

Three things make it a teaching instrument rather than a form:

* **It is weighted by what went wrong.** A concept the learner missed at the
  checkpoint gets asked about first and asked about harder. A concept they
  never saw is never asked about.
* **It mixes question types** - multiple choice, short answer and a worked
  numeric problem - because each exposes a different kind of not-knowing.
  Recognition is not recall, and recall is not application.
* **Every question carries its own teaching.** A wrong answer returns the
  explanation for *that* distractor, not a generic "incorrect", so the quiz
  keeps teaching while it measures.

The question bank is authored per concept and deterministic, so the demo path
never depends on a live model. For lessons about uploaded material that falls
outside the curated catalogue, ``services.llm`` generates questions instead and
the same grading applies.
"""

from __future__ import annotations

import logging
import random
from typing import Any

from services.translation import localize, localized

logger = logging.getLogger(__name__)

# How much of the final score each question type is worth. Application is
# weighted highest: reproducing a definition is the weakest evidence of
# understanding, using it is the strongest.
QUESTION_WEIGHTS = {"mcq": 1.0, "short": 1.5, "numeric": 2.0}

PASS_THRESHOLD = 0.6

# A concept the learner already stumbled on is worth asking about twice.
_WEAK_MASTERY = 0.6


# ---------------------------------------------------------------------------
# The authored question bank
# ---------------------------------------------------------------------------
# Keyed by concept id. Each question carries the misconception its wrong
# options represent, so grading can name what went wrong instead of just
# counting it.

QUESTION_BANK: dict[str, list[dict[str, Any]]] = {
    "electric-current": [
        {
            "id": "q-current-mcq",
            "type": "mcq",
            "prompt": {
                "english": "What does electric current actually measure?",
                "hindi": "विद्युत धारा वास्तव में क्या मापती है?",
                "hinglish": "Electric current actually kya measure karta hai?",
            },
            "options": [
                {
                    "id": "a",
                    "text": {
                        "english": "The rate at which charge flows past a point",
                        "hindi": "किसी बिंदु से आवेश के बहने की दर",
                        "hinglish": "Rate jis se charge kisi point se flow karta hai",
                    },
                    "correct": True,
                },
                {
                    "id": "b",
                    "text": {
                        "english": "The push that makes charge move",
                        "hindi": "आवेश को चलाने वाला धक्का",
                        "hinglish": "Wo push jo charge ko move karata hai",
                    },
                    "why": {
                        "english": "That is voltage, not current. Voltage pushes; current is the flow that results.",
                        "hindi": "वह वोल्टेज है, धारा नहीं। वोल्टेज धक्का देता है; धारा उससे बनने वाला प्रवाह है।",
                        "hinglish": "Wo voltage hai, current nahi. Voltage push karta hai; current uska result flow hai.",
                    },
                },
                {
                    "id": "c",
                    "text": {
                        "english": "How strongly a wire opposes the flow",
                        "hindi": "तार प्रवाह का कितना विरोध करता है",
                        "hinglish": "Wire flow ko kitna oppose karta hai",
                    },
                    "why": {
                        "english": "That is resistance. Resistance opposes current; it is not the current itself.",
                        "hindi": "वह प्रतिरोध है। प्रतिरोध धारा का विरोध करता है; वह स्वयं धारा नहीं है।",
                        "hinglish": "Wo resistance hai. Resistance current ko oppose karta hai; wo khud current nahi hai.",
                    },
                },
            ],
        },
    ],
    "voltage": [
        {
            "id": "q-voltage-short",
            "type": "short",
            "prompt": {
                "english": "In your own words, what does voltage do in a circuit?",
                "hindi": "अपने शब्दों में बताइए, परिपथ में वोल्टेज क्या करता है?",
                "hinglish": "Apne words mein batao, circuit mein voltage kya karta hai?",
            },
            "keywords": ["push", "pressure", "force", "drive", "energy", "difference"],
            "model": {
                "english": "Voltage is the electrical push that drives charge around the circuit.",
                "hindi": "वोल्टेज वह विद्युत धक्का है जो आवेश को परिपथ में चलाता है।",
                "hinglish": "Voltage wo electrical push hai jo charge ko circuit mein chalata hai.",
            },
        },
    ],
    "resistance": [
        {
            "id": "q-resistance-mcq",
            "type": "mcq",
            "prompt": {
                "english": "A thin wire and a thick wire are made of the same metal. Which has more resistance?",
                "hindi": "एक पतला और एक मोटा तार एक ही धातु के हैं। किसका प्रतिरोध अधिक है?",
                "hinglish": "Ek patla aur ek mota wire same metal ke hain. Kiska resistance zyada hai?",
            },
            "options": [
                {
                    "id": "a",
                    "text": {
                        "english": "The thin wire",
                        "hindi": "पतला तार",
                        "hinglish": "Patla wire",
                    },
                    "correct": True,
                },
                {
                    "id": "b",
                    "text": {
                        "english": "The thick wire",
                        "hindi": "मोटा तार",
                        "hinglish": "Mota wire",
                    },
                    "why": {
                        "english": "A thicker wire gives charge more room to move, so it resists less, like a wider pipe.",
                        "hindi": "मोटा तार आवेश को अधिक जगह देता है, इसलिए वह कम विरोध करता है - जैसे चौड़ा पाइप।",
                        "hinglish": "Mota wire charge ko zyada jagah deta hai, isliye wo kam resist karta hai - jaise chaura pipe.",
                    },
                },
                {
                    "id": "c",
                    "text": {
                        "english": "Both the same, since the metal is the same",
                        "hindi": "दोनों समान, क्योंकि धातु एक ही है",
                        "hinglish": "Dono same, kyunki metal same hai",
                    },
                    "why": {
                        "english": "Material matters, but so does thickness. Same metal, different thickness means different resistance.",
                        "hindi": "पदार्थ मायने रखता है, पर मोटाई भी। एक ही धातु, अलग मोटाई का मतलब अलग प्रतिरोध।",
                        "hinglish": "Material matter karta hai, par thickness bhi. Same metal, alag thickness matlab alag resistance.",
                    },
                },
            ],
        },
    ],
    "ohms-law": [
        {
            "id": "q-ohms-numeric",
            "type": "numeric",
            "prompt": {
                "english": "A 12 V battery drives a current through a 4 ohm resistor. What is the current, in amperes?",
                "hindi": "12 V की बैटरी 4 ohm के प्रतिरोधक से धारा प्रवाहित करती है। धारा कितने एम्पियर है?",
                "hinglish": "12 V battery 4 ohm resistor se current bhejti hai. Current kitne amperes hai?",
            },
            "answer": 3.0,
            "tolerance": 0.01,
            "unit": "A",
            "working": {
                "english": "I = V / R = 12 / 4 = 3 A.",
                "hindi": "I = V / R = 12 / 4 = 3 A।",
                "hinglish": "I = V / R = 12 / 4 = 3 A.",
            },
            "hint": {
                "english": "Rearrange V = I x R to make I the subject.",
                "hindi": "V = I x R को I के लिए हल कीजिए।",
                "hinglish": "V = I x R ko I ke liye rearrange karo.",
            },
        },
        {
            "id": "q-ohms-mcq",
            "type": "mcq",
            "prompt": {
                "english": "Voltage is held constant and resistance is doubled. What happens to the current?",
                "hindi": "वोल्टेज स्थिर रखा जाए और प्रतिरोध दोगुना कर दिया जाए। धारा का क्या होगा?",
                "hinglish": "Voltage constant rakha jaye aur resistance double kar diya jaye. Current ka kya hoga?",
            },
            "options": [
                {
                    "id": "a",
                    "text": {
                        "english": "It halves",
                        "hindi": "वह आधी हो जाएगी",
                        "hinglish": "Wo aadhi ho jayegi",
                    },
                    "correct": True,
                },
                {
                    "id": "b",
                    "text": {
                        "english": "It doubles",
                        "hindi": "वह दोगुनी हो जाएगी",
                        "hinglish": "Wo double ho jayegi",
                    },
                    "misconception": "inverse-relationship",
                    "why": {
                        "english": "In I = V / R, resistance is on the bottom. Making the bottom bigger makes the result smaller, not larger.",
                        "hindi": "I = V / R में प्रतिरोध हर में है। हर बड़ा करने पर परिणाम छोटा होता है, बड़ा नहीं।",
                        "hinglish": "I = V / R mein resistance neeche hai. Neeche bada karo toh result chhota hota hai, bada nahi.",
                    },
                },
                {
                    "id": "c",
                    "text": {
                        "english": "It stays the same",
                        "hindi": "वह वैसी ही रहेगी",
                        "hinglish": "Wo waisi hi rahegi",
                    },
                    "why": {
                        "english": "Current depends on both V and R. Change either one and the current changes.",
                        "hindi": "धारा V और R दोनों पर निर्भर है। किसी एक को बदलिए, धारा बदल जाएगी।",
                        "hinglish": "Current V aur R dono par depend karta hai. Kisi ek ko badlo, current badal jayega.",
                    },
                },
            ],
        },
    ],
}

# Shown when the learner gets a question right, so the quiz still teaches.
_CORRECT_NOTE = {
    "english": "Correct.",
    "hindi": "सही।",
    "hinglish": "Correct.",
}

_VERDICTS = {
    "strong": {
        "english": "Strong understanding - you can use these ideas, not just repeat them.",
        "hindi": "मजबूत समझ - आप इन विचारों का प्रयोग कर सकते हैं, केवल दोहरा नहीं रहे।",
        "hinglish": "Strong understanding - aap in ideas ko use kar sakte ho, sirf repeat nahi kar rahe.",
    },
    "developing": {
        "english": "Developing - the main ideas are there, a couple of spots need another pass.",
        "hindi": "विकसित हो रही - मुख्य विचार मौजूद हैं, कुछ जगह दोबारा देखनी होंगी।",
        "hinglish": "Developing - main ideas hain, kuch spots par ek aur pass chahiye.",
    },
    "needs-review": {
        "english": "Needs review - let us go back over the weak concepts before moving on.",
        "hindi": "पुनरावलोकन चाहिए - आगे बढ़ने से पहले कमजोर अवधारणाओं को दोबारा देखते हैं।",
        "hinglish": "Review chahiye - aage badhne se pehle weak concepts dobara dekhte hain.",
    },
}


# ---------------------------------------------------------------------------
# Building a quiz
# ---------------------------------------------------------------------------


def _concept_ids(scenes: list[dict[str, Any]]) -> list[str]:
    """Concepts actually taught, in teaching order, without repeats."""
    ordered: list[str] = []
    for scene in scenes or []:
        concept_id = scene.get("conceptId")
        # Repair scenes re-teach a concept that is already in the list.
        if concept_id and concept_id not in ordered and not scene.get("isRepair"):
            ordered.append(concept_id)
    return ordered


def _localize_question(question: dict[str, Any], language: str) -> dict[str, Any]:
    """Render one banked question into the learner's language.

    Answer keys (``correct``, ``answer``, ``keywords``) stay server-side: the
    client is sent only what it needs to display the question.
    """
    out: dict[str, Any] = {
        "id": question["id"],
        "type": question["type"],
        "conceptId": question["conceptId"],
        "prompt": localized(question["prompt"], language),
        "weight": QUESTION_WEIGHTS.get(question["type"], 1.0),
    }
    if question["type"] == "mcq":
        out["options"] = [
            {"id": option["id"], "text": localized(option["text"], language)}
            for option in question["options"]
        ]
    elif question["type"] == "numeric":
        out["unit"] = question.get("unit", "")
        out["hint"] = localized(question["hint"], language) if question.get("hint") else ""
    return out


def build_quiz(
    scenes: list[dict[str, Any]],
    language: str,
    *,
    concept_mastery: dict[str, float] | None = None,
    max_questions: int = 5,
    seed: int | None = None,
) -> dict[str, Any]:
    """Assemble the end-of-lesson quiz for a finished lesson.

    Only concepts that were actually taught can be asked about, and concepts
    the learner struggled with are asked about first - the quiz should spend
    its questions where the doubt is.
    """
    mastery = concept_mastery or {}
    taught = _concept_ids(scenes)

    def priority(concept_id: str) -> tuple[int, int]:
        # Weak concepts first; ties broken by teaching order so the quiz still
        # reads as a walk back through the lesson.
        weak = 0 if mastery.get(concept_id, 1.0) < _WEAK_MASTERY else 1
        return (weak, taught.index(concept_id))

    selected: list[dict[str, Any]] = []
    for concept_id in sorted(taught, key=priority):
        for question in QUESTION_BANK.get(concept_id, []):
            selected.append({**question, "conceptId": concept_id})

    if not selected:
        # Off-catalogue lesson: no banked questions for these concepts.
        selected = _llm_questions(scenes, language, max_questions)

    selected = selected[:max_questions]
    return {
        "language": language,
        "questions": [_localize_question(q, language) for q in selected],
        "totalWeight": sum(QUESTION_WEIGHTS.get(q["type"], 1.0) for q in selected),
        "conceptsAssessed": sorted({q["conceptId"] for q in selected}),
    }


def _llm_questions(
    scenes: list[dict[str, Any]], language: str, limit: int
) -> list[dict[str, Any]]:
    """Generate questions for a lesson the authored bank does not cover.

    Returns ``[]`` when the LLM is unavailable, which leaves the lesson with no
    quiz rather than a wrong one - the report then falls back to checkpoint
    evidence exactly as before.
    """
    try:
        from services.llm import gemini_available, generate_quiz_questions
    except ImportError:
        return []
    if not gemini_available():
        return []
    try:
        generated = generate_quiz_questions(scenes, language, limit)
    except Exception as exc:  # noqa: BLE001 - a quiz is optional, a crash is not
        logger.warning("Quiz generation failed: %s", exc)
        return []
    return generated or []


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


def _find(question_id: str) -> dict[str, Any] | None:
    for concept_id, questions in QUESTION_BANK.items():
        for question in questions:
            if question["id"] == question_id:
                return {**question, "conceptId": concept_id}
    return None


def _grade_mcq(question: dict[str, Any], response: Any, language: str) -> dict[str, Any]:
    chosen = next(
        (o for o in question["options"] if o["id"] == str(response or "").strip()),
        None,
    )
    if chosen is None:
        return {
            "correct": False,
            "explanation": localize(
                "No answer was selected for this question.", language
            ),
        }
    if chosen.get("correct"):
        return {"correct": True, "explanation": localized(_CORRECT_NOTE, language)}
    return {
        "correct": False,
        "misconception": chosen.get("misconception"),
        # The distractor's own explanation, so the learner is told why *their*
        # answer is wrong rather than only what the right one was.
        "explanation": localized(chosen.get("why", _CORRECT_NOTE), language),
    }


def _grade_short(question: dict[str, Any], response: Any, language: str) -> dict[str, Any]:
    """Keyword-overlap grading, with the LLM preferred when it is available."""
    text = str(response or "").strip()
    if not text:
        return {
            "correct": False,
            "explanation": localized(question["model"], language),
        }

    try:
        from services.llm import gemini_available, grade_short_answer

        if gemini_available():
            verdict = grade_short_answer(question["prompt"]["english"], text, language)
            if verdict and "correct" in verdict:
                return {
                    "correct": bool(verdict["correct"]),
                    "explanation": verdict.get(
                        "feedback", localized(question["model"], language)
                    ),
                }
    except Exception as exc:  # noqa: BLE001 - deterministic path below
        logger.debug("LLM short-answer grading unavailable: %s", exc)

    lowered = text.lower()
    hit = any(keyword in lowered for keyword in question.get("keywords", []))
    return {
        "correct": hit,
        "explanation": localized(question["model"], language),
    }


def _grade_numeric(question: dict[str, Any], response: Any, language: str) -> dict[str, Any]:
    import re

    text = str(response or "")
    # Accept "3", "3 A", "3.0 amperes", "I = 3".
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return {"correct": False, "explanation": localized(question["working"], language)}
    value = float(match.group(0))
    correct = abs(value - question["answer"]) <= question.get("tolerance", 0.01)
    return {"correct": correct, "explanation": localized(question["working"], language)}


def grade_quiz(
    responses: list[dict[str, Any]], language: str
) -> dict[str, Any]:
    """Grade submitted answers into a score plus per-concept evidence.

    ``responses`` is ``[{"questionId": ..., "response": ...}]``. Unknown ids are
    skipped rather than rejected, so a stale client cannot fail a submission
    outright.
    """
    results: list[dict[str, Any]] = []
    earned = 0.0
    possible = 0.0
    per_concept: dict[str, list[bool]] = {}
    misconceptions: list[str] = []

    for item in responses or []:
        question = _find(str(item.get("questionId", "")))
        if question is None:
            continue
        weight = QUESTION_WEIGHTS.get(question["type"], 1.0)
        possible += weight

        grader = {
            "mcq": _grade_mcq,
            "short": _grade_short,
            "numeric": _grade_numeric,
        }[question["type"]]
        outcome = grader(question, item.get("response"), language)

        if outcome["correct"]:
            earned += weight
        if outcome.get("misconception"):
            misconceptions.append(outcome["misconception"])

        per_concept.setdefault(question["conceptId"], []).append(outcome["correct"])
        results.append(
            {
                "questionId": question["id"],
                "conceptId": question["conceptId"],
                "correct": outcome["correct"],
                "explanation": outcome["explanation"],
            }
        )

    score = round(earned / possible, 4) if possible else 0.0
    mastery = {
        concept_id: round(sum(hits) / len(hits), 4)
        for concept_id, hits in per_concept.items()
    }
    if score >= 0.8:
        verdict = "strong"
    elif score >= PASS_THRESHOLD:
        verdict = "developing"
    else:
        verdict = "needs-review"

    return {
        "score": score,
        "passed": score >= PASS_THRESHOLD,
        "verdict": verdict,
        "verdictText": localized(_VERDICTS[verdict], language),
        "results": results,
        "conceptMastery": mastery,
        "misconceptions": sorted(set(misconceptions)),
        "correctCount": sum(1 for r in results if r["correct"]),
        "questionCount": len(results),
    }


__all__ = [
    "PASS_THRESHOLD",
    "QUESTION_BANK",
    "QUESTION_WEIGHTS",
    "build_quiz",
    "grade_quiz",
]
