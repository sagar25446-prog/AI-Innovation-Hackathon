"""Narration synthesis with a graceful fallback chain.

Order of preference:

1. **edge-tts** - Microsoft neural voices, free, no key, and it reports word
   boundaries, which is what lets the teaching video burn in captions that
   track the speech instead of guessing timings.
2. **gTTS** - lower quality and needs the network, but it keeps voice alive if
   edge-tts is blocked.
3. **Silence** - the caller degrades to captions only; a lesson never fails
   because a voice provider is down.

``edge-tts`` must be >= 7.2: 7.0.x returns HTTP 403 because Microsoft changed
the ``Sec-MS-GEC`` token scheme.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from services.ffmpeg_util import probe_duration_bytes

logger = logging.getLogger(__name__)

# Neural voices per teaching language. Hinglish uses a Hindi voice because it
# pronounces romanised Hindi far better than an English voice does.
VOICE_MAP: dict[str, str] = {
    "english": "en-IN-PrabhatNeural",
    "hindi": "hi-IN-MadhurNeural",
    "hinglish": "hi-IN-MadhurNeural",
}

# gTTS language codes for the fallback path.
GTTS_LANG_MAP: dict[str, str] = {
    "english": "en",
    "hindi": "hi",
    "hinglish": "hi",
}

# edge-tts reports offsets in 100-nanosecond ticks.
_TICKS_PER_SECOND = 10_000_000

# Rough speaking rate used when no provider reports a real duration.
_WORDS_PER_SECOND = 2.5


@dataclass
class SpeechResult:
    """Synthesised narration plus whatever timing the provider gave us."""

    audio: bytes
    duration_seconds: float
    provider: str
    mime_type: str = "audio/mpeg"
    # [{"text": str, "start": float, "end": float}] - empty when unavailable.
    word_boundaries: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_audio(self) -> bool:
        return bool(self.audio)


def estimate_duration(text: str) -> float:
    """Fallback duration estimate from word count."""
    words = len((text or "").split())
    return max(1.0, words / _WORDS_PER_SECOND)


async def _synthesize_edge(text: str, language: str) -> SpeechResult | None:
    """Synthesise with edge-tts, capturing word boundaries for captions."""
    try:
        import edge_tts
    except ImportError:
        logger.info("edge-tts not installed; trying next voice provider.")
        return None

    voice = VOICE_MAP.get(language, VOICE_MAP["hinglish"])
    chunks: list[bytes] = []
    boundaries: list[dict[str, Any]] = []

    try:
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                # edge-tts 7.2 emits SentenceBoundary for the Indian voices and
                # WordBoundary for others; both carry offset+duration ticks.
                start = chunk["offset"] / _TICKS_PER_SECOND
                boundaries.append(
                    {
                        "text": chunk["text"],
                        "start": start,
                        "end": start + chunk["duration"] / _TICKS_PER_SECOND,
                    }
                )
    except Exception as exc:  # network, 403, voice not found, ...
        logger.warning("edge-tts failed (%s); falling back.", exc)
        return None

    if not chunks:
        return None

    audio = b"".join(chunks)
    # Prefer the real decoded length: boundary ticks stop at the last spoken
    # token and the word-count estimate can be out by seconds, either of which
    # desynchronises the teaching video.
    duration = probe_duration_bytes(audio)
    if not duration:
        duration = boundaries[-1]["end"] if boundaries else estimate_duration(text)
    return SpeechResult(
        audio=audio,
        duration_seconds=duration,
        provider="edge-tts",
        word_boundaries=boundaries,
    )


def _synthesize_gtts(text: str, language: str) -> SpeechResult | None:
    """Synthesise with gTTS. No word timings, so captions fall back to even splits."""
    try:
        from gtts import gTTS
    except ImportError:
        return None

    import io

    try:
        buffer = io.BytesIO()
        gTTS(text=text, lang=GTTS_LANG_MAP.get(language, "en")).write_to_fp(buffer)
        audio = buffer.getvalue()
    except Exception as exc:
        logger.warning("gTTS failed (%s); no audio for this scene.", exc)
        return None

    if not audio:
        return None
    return SpeechResult(
        audio=audio,
        duration_seconds=probe_duration_bytes(audio) or estimate_duration(text),
        provider="gtts",
    )


async def synthesize_async(text: str, language: str = "hinglish") -> SpeechResult:
    """Synthesise narration, walking the fallback chain."""
    clean = (text or "").strip()
    if not clean:
        return SpeechResult(audio=b"", duration_seconds=0.0, provider="none")

    result = await _synthesize_edge(clean, language)
    if result is not None:
        return result

    result = await asyncio.to_thread(_synthesize_gtts, clean, language)
    if result is not None:
        return result

    logger.warning("All voice providers failed; the lesson continues with captions only.")
    return SpeechResult(
        audio=b"", duration_seconds=estimate_duration(clean), provider="none"
    )


def synthesize(text: str, language: str = "hinglish") -> SpeechResult:
    """Blocking wrapper around :func:`synthesize_async`."""
    return asyncio.run(synthesize_async(text, language))


def _split_span(text: str, start: float, end: float, max_chars: int) -> list[dict[str, Any]]:
    """Break one timed span into readable caption lines, spreading time by length."""
    words = text.split()
    if not words:
        return []

    grouped: list[str] = []
    current: list[str] = []
    for word in words:
        if current and len(" ".join(current + [word])) > max_chars:
            grouped.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        grouped.append(" ".join(current))

    total_chars = sum(len(line) for line in grouped) or 1
    span = max(0.0, end - start)
    lines: list[dict[str, Any]] = []
    cursor = start
    for line in grouped:
        share = span * (len(line) / total_chars)
        lines.append({"text": line, "start": cursor, "end": cursor + share})
        cursor += share
    if lines:
        lines[-1]["end"] = end
    return lines


def caption_lines(
    result: SpeechResult,
    text: str,
    max_chars: int = 62,
) -> list[dict[str, Any]]:
    """Group narration into timed caption lines for burning into the video.

    edge-tts reports WordBoundary for some voices and a single SentenceBoundary
    for the Indian ones, so a boundary can cover a whole sentence. Long spans
    are subdivided and their time shared out by line length; with no timings at
    all the narration is spread evenly across the measured duration.
    """
    if not text.strip():
        return []

    if result.word_boundaries:
        lines: list[dict[str, Any]] = []
        for boundary in result.word_boundaries:
            lines.extend(
                _split_span(
                    boundary["text"], boundary["start"], boundary["end"], max_chars
                )
            )
        if lines:
            lines[-1]["end"] = max(lines[-1]["end"], result.duration_seconds)
            return lines

    return _split_span(text, 0.0, result.duration_seconds, max_chars)
