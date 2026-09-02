"""Material ingestion: turn an upload or a topic into cited sections.

Deterministic by design. A real parser (PDF/PPTX) can replace
``extract_sections`` later without changing the returned shape, which is what
the planner and the RAG service consume.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from services.ingestion.corpus import DEMO_DOCUMENT_ID, DEMO_SECTIONS

# Words that carry no retrieval signal; dropped when deriving keywords.
_STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "is", "are", "in", "on", "for",
    "it", "that", "this", "with", "as", "by", "be", "or", "from", "at",
}


@dataclass
class Material:
    """An ingested source document plus its extracted sections."""

    material_id: str
    document_id: str
    title: str
    status: str
    sections: list[dict[str, Any]] = field(default_factory=list)
    origin: str = "builtin"

    @property
    def page_count(self) -> int:
        if not self.sections:
            return 0
        return len({section["pageOrSlide"] for section in self.sections})

    def to_dict(self) -> dict[str, Any]:
        return {
            "materialId": self.material_id,
            "documentId": self.document_id,
            "title": self.title,
            "status": self.status,
            "origin": self.origin,
            "sectionCount": len(self.sections),
            "pageCount": self.page_count,
            "sections": self.sections,
        }


def _derive_keywords(text: str) -> list[str]:
    """Pull lowercase content words out of raw text for keyword retrieval."""
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    seen: list[str] = []
    for word in words:
        if word not in _STOPWORDS and word not in seen:
            seen.append(word)
    return seen[:12]


def extract_sections(raw_text: str, document_id: str) -> list[dict[str, Any]]:
    """Split pasted/uploaded text into page-numbered sections.

    Splits on blank lines so each paragraph becomes one citable section. Page
    numbers are synthesised sequentially because pasted text carries none; a
    real PDF parser would supply the true page here instead.
    """
    blocks = [block.strip() for block in re.split(r"\n\s*\n", raw_text) if block.strip()]
    sections: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        lines = block.splitlines()
        heading = lines[0].strip()[:80] if lines else f"Section {index + 1}"
        sections.append(
            {
                "sectionId": f"{document_id}-sec-{index + 1}",
                "pageOrSlide": index + 1,
                "heading": heading,
                "excerpt": block[:400],
                "keywords": _derive_keywords(block),
            }
        )
    return sections


def ingest_topic(topic: str) -> Material:
    """Ingest by topic name, falling back to the built-in Electricity corpus.

    Any Electricity-adjacent topic resolves to the bundled NCERT chapter so the
    demo is source-grounded without an upload.
    """
    normalised = (topic or "").strip().lower()
    electricity_terms = ("electric", "ohm", "current", "voltage", "resistance", "circuit")
    if any(term in normalised for term in electricity_terms) or not normalised:
        return Material(
            material_id=f"material-{DEMO_DOCUMENT_ID}",
            document_id=DEMO_DOCUMENT_ID,
            title="NCERT Class 9 Science - Chapter 12: Electricity",
            status="ready",
            sections=list(DEMO_SECTIONS),
            origin="builtin",
        )

    # Unknown topic: return an empty, explicitly-ungrounded material so the RAG
    # layer reports low confidence instead of inventing citations.
    return Material(
        material_id=f"material-{uuid.uuid4().hex[:8]}",
        document_id=f"topic-{re.sub(r'[^a-z0-9]+', '-', normalised).strip('-')}",
        title=topic.strip(),
        status="ready",
        sections=[],
        origin="topic-only",
    )


def ingest_text(raw_text: str, title: str = "Uploaded material") -> Material:
    """Ingest raw pasted or uploaded text into citable sections."""
    material_id = f"material-{uuid.uuid4().hex[:8]}"
    document_id = material_id
    return Material(
        material_id=material_id,
        document_id=document_id,
        title=title,
        status="ready",
        sections=extract_sections(raw_text, document_id),
        origin="upload",
    )
