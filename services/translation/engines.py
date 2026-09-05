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

    def translate(self, text: str, language: str) -> str | None:
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

        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
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
        return [(p or "").strip() for p in parsed]


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
    "MT_LANGUAGE_CODES",
    "PublicMTEngine",
    "TranslationEngine",
    "default_engines",
]
