"""Teacher personalities: adjust the tone/support of narrations and feedback.

A personality changes *how* the teacher speaks, not *what* is taught. Because
the deterministic narrations are exact contract strings, personalities are only
applied when a learner explicitly opts into one; the default keeps the original
neutral narration so nothing regresses.
"""

from __future__ import annotations

from typing import Any

from services.translation import localize

# Tone framing prepended to each scene narration, per personality and language.
_NARRATION_FRAMING: dict[str, dict[str, dict[str, str]]] = {
    "patient": {
        "english": {
            "beginner": "Let's take it step by step. ",
            "default": "Let's work through this together. ",
        },
        "hindi": {
            "beginner": "आइए इसे कदम-कदम पर समझें। ",
            "default": "आइए इसे एक साथ समझें। ",
        },
        "hinglish": {
            "beginner": "Chalo isse step by step samjhte hain. ",
            "default": "Chalo isse saath mein samjhte hain. ",
        },
    },
    "socratic": {
        "english": {
            "beginner": "Let's think: what do you notice? ",
            "default": "Consider the why behind this. ",
        },
        "hindi": {
            "beginner": "सोचिए: आपको क्या दिखता है? ",
            "default": "इसके पीछे का कारण सोचिए। ",
        },
        "hinglish": {
            "beginner": "Socho: aapko kya notice hota hai? ",
            "default": "Iske peeche ka reason socho. ",
        },
    },
    "coach": {
        "english": {
            "beginner": "Great, let's nail this one. ",
            "default": "Push through — you've got this. ",
        },
        "hindi": {
            "beginner": "बढ़िया, इसे पक्का करें। ",
            "default": "आगे बढ़ें — आप कर सकते हैं। ",
        },
        "hinglish": {
            "beginner": "Great, isko pakka karte hain. ",
            "default": "Aage badho — tum kar sakte ho. ",
        },
    },
}

# Feedback tone applied to a checkpoint verdict.
_FEEDBACK_TONE: dict[str, dict[str, str]] = {
    "patient": {
        "encourage": "That's okay — learning takes practice. ",
        "push": "Good progress — keep it up. ",
    },
    "socratic": {
        "encourage": "Let's revisit that idea. ",
        "push": "What changed, and why? ",
    },
    "coach": {
        "encourage": "No worries — recover and retry. ",
        "push": "Strong! Now make it count. ",
    },
}


def apply_persona_narration(
    narration: str,
    personality: str | None,
    language: str,
    level: str,
) -> str:
    """Prefix a narration with persona tone if a personality is selected."""
    if not personality:
        return narration
    framing_map = _NARRATION_FRAMING.get(personality)
    if not framing_map:
        return narration
    lang_map = framing_map.get(language)
    if lang_map is None:
        base = framing_map.get("english", {})
        prefix = base.get(level) or base.get("default", "")
        prefix = localize(prefix, language) if prefix else ""
        return f"{prefix}{narration}" if prefix else narration
    prefix = lang_map.get(level) or lang_map.get("default", "")
    return f"{prefix}{narration}" if prefix else narration


def persona_feedback(personality: str | None, *, encouraged: bool) -> str:
    """Return a persona-appropriate feedback tone prefix (or empty string)."""
    if not personality:
        return ""
    tone = _FEEDBACK_TONE.get(personality)
    if not tone:
        return ""
    key = "encourage" if encouraged else "push"
    return tone[key]
