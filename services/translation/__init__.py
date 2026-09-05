"""On-demand localisation for the extended teaching languages.

``english`` / ``hindi`` / ``hinglish`` are hand-authored across the planner
catalogues, evaluation feedback, flashcards and everything else that is keyed
by language. The twelve additional languages are **not** hand-written
everywhere; they are resolved through a four-tier stack, cheapest first:

1. a per-process memory cache, so each string is resolved at most once;
2. the **shipped translation pack** in ``data/translations`` - every fixed
   string in the curated lessons, translated ahead of time and committed, so a
   Tamil lesson is instant, offline and identical on every machine;
3. a **translation engine**: Gemini Flash for quality, falling back to a
   key-free public MT endpoint when Gemini is rate-limited or absent. Anything
   an engine produces is written back into the pack, so it is paid for once;
4. the canonical English string unchanged as a defensive last step, so an
   unreachable network never breaks (or blanks) a lesson.

Tier 2 exists because tier 3 alone was not enough. Gemini's free tier allows
20 requests per model per day; once a day's budget was gone, all twelve
extended languages quietly served English and the multilingual feature looked
broken. The pack removes the demo path from the network entirely, and the MT
fallback keeps *off-catalogue* lessons working after that.

The translation prompt forbids touching numbers, unit symbols, variable
letters and equations, so ``I = V/R`` survives any language exactly; the pack
builder verifies this rather than trusting it. What ``localize()`` returns is
fed straight into the existing narration/voice/caption pipeline, so a learner
in Tamil, Bengali or Marathi gets a working lesson and video even fully
offline.
"""

from __future__ import annotations

import logging

from services.translation import engines, pack

logger = logging.getLogger(__name__)

# Core languages have hand-authored content; everything else is localised.
CORE_LANGUAGES = ("english", "hindi", "hinglish")

# The full teaching-language matrix. Order drives the contract enum and the
# UI option lists, so keep it stable and alphabetical after the core three.
SUPPORTED_LANGUAGES = CORE_LANGUAGES + (
    "bengali",
    "bhojpuri",
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
    "bhojpuri": "Bhojpuri",
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
    pack.reset_cache()


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

    # Tier 2: a pre-translated string costs nothing and needs no network.
    shipped = pack.lookup(clean, language)
    if shipped:
        _cache[key] = shipped
        return shipped

    # Tier 3: ask the engines, best quality first.
    translated = _translate_via_engines(clean, language)
    if translated:
        _cache[key] = translated
        pack.remember(clean, translated, language)
        return translated

    # Tier 4. A failed lookup is deliberately NOT cached. Caching the miss used
    # to pin the language to English for the rest of the process: one lesson
    # planned while Gemini was rate-limited left every later lesson in that
    # process English too, even after quota reset. The engines' own
    # ``available()`` checks are local and cheap, so retrying costs nothing
    # when they are genuinely down.
    return clean


def localize_batch(texts: list[str], language: str) -> None:
    """Resolve many strings at once and prime the cache.

    Localising a lesson one string at a time meant ~14 serial round trips per
    lesson: about two minutes on the plan screen, and 14 of Gemini's 20 daily
    free requests spent on a single lesson. This resolves the whole lesson in
    one pass instead.

    Nothing is returned - callers keep using ``localize``/``localized``, which
    now hit a warm cache. Failure is silent by design: the per-string path
    still works, it is just slower.
    """
    if language in CORE_LANGUAGES or language not in SUPPORTED_LANGUAGES:
        return

    pending = []
    for text in texts:
        clean = (text or "").strip()
        if not clean or (language, clean) in _cache or clean in pending:
            continue
        # Tier 2 first: anything the shipped pack knows needs no engine at all.
        shipped = pack.lookup(clean, language)
        if shipped:
            _cache[(language, clean)] = shipped
        else:
            pending.append(clean)
    if not pending:
        return

    # Gemini can do the whole batch in one request, which is the difference
    # between one free-tier call per lesson and one per string.
    gemini = engines.GeminiEngine()
    if gemini.available():
        try:
            translated = gemini.translate_batch(pending, language)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Batch translation to %s failed: %s", language, exc)
            translated = None
        if translated:
            leftover = []
            for source, result in zip(pending, translated):
                cleaned = (result or "").strip()
                if cleaned:
                    _cache[(language, source)] = cleaned
                    pack.remember(source, cleaned, language)
                else:
                    leftover.append(source)
            pending = leftover

    # Whatever Gemini could not do - because it is absent, rate-limited, or
    # returned a malformed batch - the public MT engine picks up one string at
    # a time. Slower, but it has no daily budget, so the lesson still ships in
    # the learner's language.
    if not pending:
        return
    mt = engines.PublicMTEngine()
    if not mt.available():
        # Nothing can translate right now. Do NOT cache the miss: the engines
        # may be reachable again in a minute, and a cached None used to pin a
        # language to English for the rest of the process lifetime.
        return
    for source in pending:
        try:
            result = mt.translate(source, language)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Public MT to %s failed: %s", language, exc)
            continue
        if result:
            _cache[(language, source)] = result
            pack.remember(source, result, language)


def _parse_json_array(raw: str) -> list[str] | None:
    """Pull a JSON array of strings out of a model reply."""
    import json
    import re

    if not raw:
        return None
    text = raw.strip()
    # Models often wrap JSON in a fenced block.
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    return [item if isinstance(item, str) else str(item) for item in parsed]


def _translate_via_engines(text: str, language: str) -> str | None:
    """Walk the engine chain until one produces a translation.

    Returns None when every engine declines, which leaves the caller with the
    English source - degraded, but never blank and never a crash.
    """
    for engine in engines.default_engines():
        try:
            if not engine.available():
                continue
            result = engine.translate(text, language)
        except Exception as exc:  # noqa: BLE001 - an engine may not break the chain
            logger.warning("Translation engine %s raised: %s", engine.name, exc)
            continue
        if result:
            logger.debug("Translated to %s via %s", language, engine.name)
            return result
    return None


def translation_health(language: str) -> dict[str, object]:
    """What a learner in this language will actually get - surfaced in /health.

    The old failure was invisible: the API reported a healthy service while
    every Tamil string quietly came back in English. This makes the degraded
    state legible before a lesson starts.
    """
    if language in CORE_LANGUAGES:
        return {"language": language, "tier": "authored", "packEntries": 0}
    if language not in SUPPORTED_LANGUAGES:
        return {"language": language, "tier": "unsupported", "packEntries": 0}

    live = [e.name for e in engines.default_engines() if e.available()]
    entries = pack.coverage(language)
    if entries and live:
        tier = "pack+live"
    elif entries:
        tier = "pack"
    elif live:
        tier = "live"
    else:
        tier = "english-fallback"
    return {
        "language": language,
        "tier": tier,
        "packEntries": entries,
        "engines": live,
    }


__all__ = [
    "CORE_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "clear_translation_cache",
    "is_supported",
    "language_name",
    "localize",
    "localize_batch",
    "localized",
    "translation_health",
]