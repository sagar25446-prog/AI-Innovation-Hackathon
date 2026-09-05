"""On-demand localisation for the extended teaching languages.

``english`` / ``hindi`` / ``hinglish`` are hand-authored across the planner
catalogues, evaluation feedback, flashcards and everything else that is keyed
by language. The twelve additional languages are **not** hand-written
everywhere; they are localised on demand instead:

1. a per-process memory cache, so each string is translated at most once;
2. Gemini Flash when ``GEMINI_API_KEY`` is configured - a real translation,
   produced once and cached;
3. the canonical English string unchanged as a defensive last step, so an
   uncached string never breaks (or lies on) a lesson.

The translation prompt forbids touching numbers, unit symbols, variable
letters and equations, so ``I = V/R`` survives any language exactly. What
localise() returns is fed straight into the existing narration/voice/caption
pipeline, so a learner in Tamil, Bengali or Marathi gets a working lesson and
video even fully offline.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Core languages have hand-authored content; everything else is localised.
CORE_LANGUAGES = ("english", "hindi", "hinglish")

# The full teaching-language matrix. Order drives the contract enum and the
# UI option lists, so keep it stable and alphabetical after the core three.
SUPPORTED_LANGUAGES = CORE_LANGUAGES + (
    "bengali",
    "gujarati",
    "kannada",
    "malayalam",
    "marathi",
    "nepali",
    "odia",
    "punjabi",
    "sinhala",
    "tamil",
    "telugu",
    "urdu",
)

DEFAULT_LANGUAGE = "hinglish"

# Display names used for UI options and in prompts sent to Gemini.
LANGUAGE_NAMES = {
    "english": "English",
    "hindi": "Hindi",
    "hinglish": "Hinglish",
    "bengali": "Bengali",
    "gujarati": "Gujarati",
    "kannada": "Kannada",
    "malayalam": "Malayalam",
    "marathi": "Marathi",
    "nepali": "Nepali",
    "odia": "Odia",
    "punjabi": "Punjabi",
    "sinhala": "Sinhala",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "urdu": "Urdu",
}

_MISSING = object()
# (language, source_text) -> translated | None. A cached None means "Gemini
# was unavailable", so offline runs never re-hit the API for the same string.
_cache: dict[tuple[str, str], str | None] = {}


def language_name(language: str) -> str:
    """Full name of a teaching language for UI/prompt use."""
    return LANGUAGE_NAMES.get(language, "English")


def is_supported(language: str) -> bool:
    return language in SUPPORTED_LANGUAGES


def clear_translation_cache() -> None:
    """Forget cached translations (used by tests to stay hermetic)."""
    _cache.clear()


def localized(mapping: dict[str, str], language: str) -> str:
    """Pick ``mapping[language]``, falling back to a localised English copy.

    This is the drop-in replacement for ``mapping[language]``: it behaves
    identically for the hand-authored languages and localises on demand for
    the extended ones, so no caller needs to branch itself.
    """
    value = mapping.get(language)
    if value:
        return value
    source = mapping.get("english") or next(iter(mapping.values()), "")
    return localize(source, language)


def localize(text: str, language: str) -> str:
    """Localise a canonical string into an extended teaching language.

    Core languages pass through untouched (their catalogues are authored).
    Unsupported languages also pass through, so callers never crash on a
    stray code.
    """
    clean = (text or "").strip()
    if not clean or language in CORE_LANGUAGES or language not in SUPPORTED_LANGUAGES:
        return clean

    key = (language, clean)
    cached = _cache.get(key, _MISSING)
    if cached is not _MISSING:
        return cached if cached else clean

    translated = _gemini_translate(clean, language)
    _cache[key] = translated
    return translated if translated else clean


def _gemini_translate(text: str, language: str) -> str | None:
    """Translate via Gemini Flash. Returns None (source kept) when offline."""
    try:
        from services.llm import _generate_text, gemini_available
    except ImportError:
        return None
    if not gemini_available():
        return None

    prompt = (
        f"You are a professional translator for an Indian school. Translate "
        f"the teacher's narration below into {language_name(language)}. "
        f"Do NOT change numbers, unit symbols, variable letters, or any "
        f"equation such as I = V/R; keep them exactly as written. "
        f"Keep the tone warm, simple and clear for Class 9 students. "
        f"Return only the translation.\n\n"
        f"NARRATION:\n{text}"
    )
    try:
        translated = _generate_text(prompt)
        return translated.strip() if translated and translated.strip() else None
    except Exception as exc:
        logger.warning("Translation to %s failed: %s", language, exc)
        return None


__all__ = [
    "CORE_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "clear_translation_cache",
    "is_supported",
    "language_name",
    "localize",
    "localized",
]