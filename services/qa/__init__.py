"""Follow-up questions asked mid-lesson.

Task 2 requires the teacher to "answer follow-up questions while maintaining
lesson context". This answers from the lesson's own material: the question is
retrieved against the ingested sections, and the answer carries the same
page-level citations the scenes use.

When Gemini is configured the retrieved passages are handed to it and it is
told, in the prompt, to answer only from them. With no key the answer is
extractive - the cited passage plus a framing line - which is less fluent but
cannot hallucinate. Either way, if retrieval finds nothing the system says so
rather than inventing an answer.
"""

from __future__ import annotations

import logging
from typing import Any

from services.rag import GROUNDING_THRESHOLD, retrieve
from services.translation import language_name, localized

logger = logging.getLogger(__name__)

_LEAD_IN = {
    "english": "From your material:",
    "hindi": "आपकी सामग्री से:",
    "hinglish": "Aapke material se:",
}

_UNGROUNDED = {
    "english": (
        "I could not find that in the material you gave me, so I will not "
        "guess. Try rephrasing, or ask about the concepts in this lesson."
    ),
    "hindi": (
        "यह मुझे आपकी सामग्री में नहीं मिला, इसलिए मैं अनुमान नहीं लगाऊँगा। "
        "प्रश्न दोबारा पूछें, या इस पाठ के विषयों के बारे में पूछें।"
    ),
    "hinglish": (
        "Yeh mujhe aapke material mein nahi mila, isliye main guess nahi "
        "karunga. Sawal dobara poochho, ya is lesson ke concepts ke baare mein "
        "poochho."
    ),
}


def _llm_answer(
    question: str,
    passages: list[dict[str, Any]],
    language: str,
    lesson_topic: str,
) -> str | None:
    """Ask Gemini, constrained to the retrieved passages."""
    try:
        from services.llm import _generate_text as generate_text, gemini_available
    except ImportError:
        return None
    if not gemini_available():
        return None

    context = "\n\n".join(
        f"[page {p['pageOrSlide']}] {p['excerpt']}" for p in passages
    )
    prompt = (
        f"You are a school teacher mid-lesson on '{lesson_topic}'. A student "
        f"asked a follow-up question.\n\n"
        f"Answer ONLY from the passages below. If they do not contain the "
        f"answer, say you cannot find it in the material. Never invent facts "
        f"or citations.\n\n"
        f"Reply in {language_name(language)}, in at most three "
        f"short sentences, at a Class 9 level. Keep any formula exactly as "
        f"written.\n\n"
        f"PASSAGES:\n{context}\n\nQUESTION: {question}\n\nANSWER:"
    )
    try:
        return generate_text(prompt)
    except Exception as exc:
        logger.warning("LLM follow-up answer failed: %s", exc)
        return None


def answer_question(
    question: str,
    sections: list[dict[str, Any]],
    document_id: str,
    language: str = "hinglish",
    lesson_topic: str = "this lesson",
) -> dict[str, Any]:
    """Answer a learner's follow-up, grounded in the lesson material."""
    clean = (question or "").strip()
    if not clean:
        return {
            "answer": localized(_UNGROUNDED, language),
            "citations": [],
            "grounded": False,
            "source": "none",
        }

    results = retrieve(clean, sections, document_id, top_k=3)
    strong = [r for r in results if r.score >= GROUNDING_THRESHOLD]

    if not strong:
        return {
            "answer": localized(_UNGROUNDED, language),
            "citations": [],
            "grounded": False,
            "source": "no-match",
        }

    citations = [r.citation for r in strong]

    generated = _llm_answer(clean, citations, language, lesson_topic)
    if generated:
        return {
            "answer": generated.strip(),
            "citations": citations,
            "grounded": True,
            "source": "gemini",
        }

    # Extractive fallback: quote the material rather than paraphrase it badly.
    lead = localized(_LEAD_IN, language)
    best = citations[0]
    answer = f"{lead} \"{best['excerpt']}\" (page {best['pageOrSlide']})"
    return {
        "answer": answer,
        "citations": citations,
        "grounded": True,
        "source": "extractive",
    }
