"""Translation engines, tried in quality order until one answers.

GuruFlow used to have exactly one way to reach a non-core language: a live
Gemini Flash call at lesson time. Gemini's free tier allows 20 requests per
model per day, and a single Tamil lesson spends one of them on the batch plus
one per uncached string afterwards. The day that budget ran out, every one of
the twelve extended languages silently served English - the documented
"defensive last step" doing exactly what it promised, and looking to a learner
like the feature had never worked at all.

So translation is now a stack rather than a single call:

1. ``GeminiEngine``     - best quality, understands "keep I = V/R intact",
                          but rate-limited and needs an API key;
2. ``PublicMTEngine``   - a key-free machine-translation endpoint. Lower
                          quality than Gemini and occasionally leaves an
                          English word behind, but it has no daily budget and
                          needs no configuration, so the twelve extended
                          languages keep working when Gemini is exhausted;
3. the caller's English source, unchanged - never a crash, never a blank.

The shipped translation pack (see ``services.translation.pack``) sits in front
of all of this, so the curated demo lesson is fully translated offline and
never depends on either engine being reachable.

Every engine returns ``None`` rather than raising, so the chain degrades one
step at a time instead of failing.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from typing import Protocol

logger = logging.getLogger(__name__)

# Formulae, units and variable letters must survive translation exactly, or the
# lesson teaches the wrong physics. Both engines are told so; the pack builder
# additionally verifies it.
_PRESERVE_RULE = (
    "Do NOT change numbers, unit symbols, variable letters, or any equation "
    "such as I = V/R; keep them exactly as written."
)

# ISO-639-1 codes for the public MT endpoint. Keyed by GuruFlow language id.
MT_LANGUAGE_CODES = {
    "bengali": "bn",
    "bhojpuri": "bho",
    "gujarati": "gu",
    "kannada": "kn",
    "malayalam": "ml",
    "marathi": "mr",
    "nepali": "ne",
    "odia": "or",
    "punjabi": "pa",
    "sinhala": "si",
    "tamil": "ta",
    "telugu": "te",
    "urdu": "ur",
    "hindi": "hi",
}


# ---------------------------------------------------------------------------
# Formula masking
# ---------------------------------------------------------------------------
# A translator has no idea it is handling a physics lesson. Asked for Nepali,
# it renders "a 12 V battery" as "१२ वी ब्याट्री" - correct Nepali, and wrong
# physics teaching, because the learner is about to substitute that number
# into I = V / R. Politely asking the model not to (which is all the prompt
# could do) worked for Gemini and not for a general MT endpoint.
#
# So the protected spans are lifted out before translation and put back
# afterwards. The translator never sees them and cannot localise what it never
# saw. Sentinels are pure ASCII letters: digits get converted to local
# numerals by exactly the engines this is defending against.

PROTECTED_PATTERN = re.compile(
    r"""
      \b[A-Za-z]\s*=\s*[A-Za-z0-9.^]+                      # V = IR, I = V
        (?:\s*[-+*/x×]\s*[A-Za-z0-9.^]+)*                  #   ... x R, / R
        (?:\s*=\s*[A-Za-z0-9.^]+(?:\s*[-+*/x×]\s*[A-Za-z0-9.^]+)*)*  # ... = 12 / 4 = 3
        (?:\s*[A-ZΩ]\b)?                                 # trailing unit: 3 A
    | \b\d+(?:\.\d+)?\s*(?:ohms?|volts?|amperes?|amps?)\b  # 4 ohm
    | \b\d+(?:\.\d+)?\s*[A-ZΩ]\b                           # 12 V
    | \b\d+(?:\.\d+)?\b                                    # a bare quantity
    """,
    re.VERBOSE,
)

def _sentinel(index: int) -> str:
    """A translator-proof placeholder: {{0}}, {{1}}, ...

    An ASCII-letter marker was tried first and does not survive: asked for
    Bhojpuri, the engine helpfully transliterates "ZQXA" into Devanagari as
    "जेडक्यूएक्सए", the sentinel is gone, and the translation is discarded.
    Double braces are left alone by every engine tested, digits included.
    """
    return "{{" + str(index) + "}}"


def mask_protected(text: str) -> tuple[str, list[str]]:
    """Replace equations, quantities and bare numbers with sentinels."""
    tokens: list[str] = []

    def swap(match: re.Match) -> str:
        whole = match.group(0)
        # Trailing whitespace and sentence-final full stops stay in the text:
        # a decimal point inside 3.5 belongs to the number, but the one ending
        # "V = I x R." belongs to the sentence, and swallowing it leaves the
        # translator with no punctuation to work from.
        token = whole.rstrip(" .")
        tokens.append(token)
        # Keep any trailing space the match swallowed, so the sentence still
        # reads correctly to the translator.
        return _sentinel(len(tokens) - 1) + whole[len(token) :]

    return PROTECTED_PATTERN.sub(swap, text), tokens


def restore_protected(text: str, tokens: list[str]) -> str:
    """Put the original spans back, exactly as they were written.

    Longest sentinel first, so restoring ZQXA cannot corrupt ZQXAA.
    """
    for index in sorted(range(len(tokens)), key=lambda i: -len(_sentinel(i))):
        text = text.replace(_sentinel(index), tokens[index])
    return text


def _translate_masked(translate, text: str, language: str) -> str | None:
    """Run one translation with the protected spans lifted out and restored.

    Returns None when a sentinel did not survive the round trip: the engine
    dropped or mangled it, so the result cannot be trusted to carry the
    formula and the next engine should get a turn.
    """
    masked, tokens = mask_protected(text)
    if not tokens:
        return translate(masked)

    result = translate(masked)
    if not result:
        return None
    if any(_sentinel(i) not in result for i in range(len(tokens))):
        logger.debug("Sentinel lost translating to %s; discarding", language)
        return None
    return restore_protected(result, tokens)


class TranslationEngine(Protocol):
    """Anything that can turn one English string into another language."""

    name: str

    def available(self) -> bool: ...

    def translate(self, text: str, language: str) -> str | None: ...


class GeminiEngine:
    """Gemini Flash. Highest quality, lowest daily budget."""

    name = "gemini"

    def available(self) -> bool:
        try:
            from services.llm import gemini_available
        except ImportError:
            return False
        return bool(gemini_available())

    def _translate_raw(self, text: str, language: str) -> str | None:
        try:
            from services.llm import _generate_text
        except ImportError:
            return None

        from services.translation import language_name

        prompt = (
            f"You are a professional translator for an Indian school. Translate "
            f"the teacher's narration below into {language_name(language)}. "
            f"{_PRESERVE_RULE} "
            f"Keep the tone warm, simple and clear for Class 9 students. "
            f"Return only the translation.\n\nNARRATION:\n{text}"
        )
        try:
            out = _generate_text(prompt)
        except Exception as exc:  # noqa: BLE001 - next engine gets a turn
            logger.debug("Gemini translation to %s failed: %s", language, exc)
            return None
        out = (out or "").strip()
        return out or None

    def translate(self, text: str, language: str) -> str | None:
        return _translate_masked(
            lambda masked: self._translate_raw(masked, language), text, language
        )

    def translate_batch(self, texts: list[str], language: str) -> list[str] | None:
        """Translate many strings in one request.

        Worth a dedicated path: localising a lesson one string at a time cost
        ~14 serial round trips, which is most of a free-tier day for a single
        lesson.
        """
        try:
            from services.llm import _generate_text
        except ImportError:
            return None

        from services.translation import _parse_json_array, language_name

        masks = {}
        masked_texts = []
        for source in texts:
            masked, tokens = mask_protected(source)
            masks[source] = tokens
            masked_texts.append(masked)

        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(masked_texts))
        prompt = (
            f"You are a professional translator for an Indian school. Translate "
            f"each numbered line below into {language_name(language)}.\n"
            f"{_PRESERVE_RULE}\n"
            f"Keep the tone warm, simple and clear for Class 9 students.\n"
            f"Return ONLY a JSON array of {len(texts)} strings, in the same "
            f"order, with no numbering and no commentary.\n\n{numbered}"
        )
        try:
            parsed = _parse_json_array(_generate_text(prompt))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Gemini batch to %s failed: %s", language, exc)
            return None

        # A short or long reply would shift every translation onto the wrong
        # source string, which is worse than not translating at all.
        if not parsed or len(parsed) != len(texts):
            logger.warning(
                "Gemini batch to %s returned %s items for %s inputs; discarding.",
                language,
                len(parsed) if parsed else 0,
                len(texts),
            )
            return None

        # Put each string's protected spans back, and drop any reply that lost
        # one rather than letting a localised numeral through.
        restored: list[str] = []
        for source, candidate in zip(texts, parsed):
            tokens = masks[source]
            value = (candidate or "").strip()
            if tokens and any(_sentinel(i) not in value for i in range(len(tokens))):
                value = ""
            restored.append(restore_protected(value, tokens) if value else "")
        return restored


class PublicMTEngine:
    """A key-free machine-translation endpoint - the always-available tier.

    This is deliberately the *fallback*, not the default: it is a general
    translator with no idea it is handling a physics lesson, so it is weaker
    than Gemini on tone and occasionally leaves an English word in place. What
    it does have is no API key, no daily quota and no setup, which is what the
    twelve extended languages need in order to work on a judge's machine.

    Disabled by setting ``GURUFLOW_PUBLIC_MT=0`` (for fully air-gapped runs,
    where the shipped pack and the English fallback still apply).
    """

    name = "public-mt"
    endpoint = "https://translate.googleapis.com/translate_a/single"
    timeout = 20

    def available(self) -> bool:
        return os.environ.get("GURUFLOW_PUBLIC_MT", "1").strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        )

    def translate(self, text: str, language: str) -> str | None:
        if language not in MT_LANGUAGE_CODES:
            return None
        return _translate_masked(
            lambda masked: self._translate_raw(masked, language), text, language
        )

    def _translate_raw(self, text: str, language: str) -> str | None:
        code = MT_LANGUAGE_CODES.get(language)
        if not code:
            return None

        query = urllib.parse.urlencode(
            {"client": "gtx", "sl": "en", "tl": code, "dt": "t", "q": text}
        )
        request = urllib.request.Request(
            f"{self.endpoint}?{query}",
            headers={"User-Agent": "Mozilla/5.0 (compatible; GuruFlow/1.0)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except Exception as exc:  # noqa: BLE001 - fall through to English
            logger.debug("Public MT to %s failed: %s", language, exc)
            return None

        # Shape: [[[chunk, source, ...], [chunk, source, ...]], ...]
        try:
            out = "".join(seg[0] for seg in payload[0] if seg and seg[0])
        except (IndexError, TypeError):
            return None
        out = out.strip()
        return out or None


def default_engines() -> list[TranslationEngine]:
    """The engine chain, best quality first."""
    return [GeminiEngine(), PublicMTEngine()]


__all__ = [
    "GeminiEngine",
    "PROTECTED_PATTERN",
    "MT_LANGUAGE_CODES",
    "PublicMTEngine",
    "TranslationEngine",
    "default_engines",
    "mask_protected",
    "restore_protected",
]
