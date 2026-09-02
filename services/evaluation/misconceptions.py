"""Answer analysis and misconception diagnosis for the Ohm's Law checkpoint.

Free-text answers arrive in English, Hindi or Hinglish, so classification works
on multilingual cue words rather than exact string matching. The one subtlety
worth naming: an answer like "resistance badhne se current kam hoga" contains
both an increase cue (*badh*) and a decrease cue (*kam*). The increase cue
belongs to the resistance clause, not the current clause, so those clauses are
stripped before the remaining text is scored.
"""

from __future__ import annotations

import re

# Clauses that describe the *premise* (resistance going up), which would
# otherwise be misread as the learner claiming current goes up.
_PREMISE_PATTERNS = [
    r"resistance\s+(?:is\s+)?(?:increase[sd]?|increasing|badh\w*|badha\w*|doubl\w+|zyada)",
    r"(?:increase[sd]?|increasing|doubl\w+)\s+(?:the\s+)?resistance",
    r"agar\s+resistance\s+\w+",
    r"जब\s+प्रतिरोध\s+\S+",
    r"प्रतिरोध\s+(?:को\s+)?बढ़\S*",
    r"resistance\s+badhne\s+se",
    r"\br\s*(?:is\s*)?(?:increase[sd]?|up)\b",
]

_DECREASE_CUES = [
    "decrease", "decreases", "decreased", "decreasing", "less", "lower",
    "lesser", "reduce", "reduces", "reduced", "halve", "halved", "half",
    "drop", "drops", "falls", "fall", "fell", "down", "inversely", "inverse",
    "smaller", "weaker", "kam", "ghat", "ghatega", "ghatta", "aadha", "adha",
    "कम", "घट", "आधी", "आधा", "घटेगी", "घटेगा",
]

_INCREASE_CUES = [
    "increase", "increases", "increased", "increasing", "more", "higher",
    "rise", "rises", "rising", "greater", "bigger", "stronger", "grow",
    "grows", "double", "doubles", "up", "badh", "badhega", "badhegi",
    "badhta", "zyada", "adhik", "बढ़", "ज़्यादा", "ज्यादा", "अधिक", "दोगुनी",
]

_SAME_CUES = [
    "same", "unchanged", "constant", "no change", "not change", "nothing",
    "steady", "waisa hi", "waise hi", "same rahega", "nahi badlega",
    "समान", "नहीं बदलेगी", "नहीं बदलेगा", "अपरिवर्तित",
]

# Diagnosis identifiers shared with the report and the frontend.
DIRECT_PROPORTIONALITY = "direct-proportionality confusion"
CONSTANT_CURRENT = "constant-current confusion"


def _strip_premise(text: str) -> str:
    """Remove the 'resistance increases' clause so only the claim remains."""
    cleaned = text
    for pattern in _PREMISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    return cleaned


def _count_cues(text: str, cues: list[str]) -> int:
    return sum(1 for cue in cues if cue in text)


def classify_answer(answer: str, option_id: str | None = None) -> str:
    """Classify a checkpoint answer.

    Returns one of ``correct``, ``direct-proportionality``, ``constant-current``
    or ``unclear``. ``option_id`` short-circuits the text analysis when the
    learner used the multiple-choice control instead of typing.
    """
    if option_id:
        mapping = {
            "decreases": "correct",
            "increases": "direct-proportionality",
            "no-change": "constant-current",
        }
        if option_id in mapping:
            return mapping[option_id]

    text = (answer or "").strip().lower()
    if not text:
        return "unclear"

    claim = _strip_premise(text)

    decrease_score = _count_cues(claim, _DECREASE_CUES)
    increase_score = _count_cues(claim, _INCREASE_CUES)
    same_score = _count_cues(claim, _SAME_CUES)

    if decrease_score > increase_score and decrease_score > 0:
        return "correct"
    if increase_score > decrease_score and increase_score > 0:
        return "direct-proportionality"
    if same_score > 0:
        return "constant-current"
    return "unclear"


def misconception_id(classification: str) -> str | None:
    """Map a classification to its contract-facing misconception label."""
    if classification == "direct-proportionality":
        return DIRECT_PROPORTIONALITY
    if classification == "constant-current":
        return CONSTANT_CURRENT
    return None
