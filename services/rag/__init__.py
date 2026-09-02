"""Section-aware retrieval over ingested material.

Deliberately simple: keyword overlap scoring over the sections produced by
``services.ingestion``. This is the "simple path" the reuse decision table
asks for -- no vector database is deployed for the MVP. The scoring function is
the only thing an embedding-backed retriever would need to replace.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

# Below this score we do not claim the answer came from the material.
GROUNDING_THRESHOLD = 0.15


@dataclass
class RetrievalResult:
    """A retrieved section plus how confident we are that it is relevant."""

    citation: dict[str, Any]
    score: float

    @property
    def grounded(self) -> bool:
        return self.score >= GROUNDING_THRESHOLD


def _tokenise(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z]{3,}", (text or "").lower()))


def score_section(section: dict[str, Any], query_tokens: set[str]) -> float:
    """Score one section against the query by keyword and excerpt overlap.

    Keyword hits are weighted more heavily than incidental excerpt hits because
    keywords are the curated signal for the section.
    """
    if not query_tokens:
        return 0.0

    keywords = {str(k).lower() for k in section.get("keywords", [])}
    excerpt_tokens = _tokenise(section.get("excerpt", ""))
    heading_tokens = _tokenise(section.get("heading", ""))

    keyword_hits = len(query_tokens & keywords)
    heading_hits = len(query_tokens & heading_tokens)
    excerpt_hits = len(query_tokens & excerpt_tokens)

    weighted = (keyword_hits * 3) + (heading_hits * 2) + excerpt_hits
    # Normalise against the query length so short queries cannot score higher
    # simply by matching fewer terms.
    return weighted / (len(query_tokens) * 3)


def retrieve(
    query: str,
    sections: Iterable[dict[str, Any]],
    document_id: str,
    top_k: int = 2,
) -> list[RetrievalResult]:
    """Return the ``top_k`` best-matching sections as contract citations."""
    query_tokens = _tokenise(query)
    scored: list[RetrievalResult] = []

    for section in sections:
        score = score_section(section, query_tokens)
        if score <= 0:
            continue
        citation = {
            "documentId": document_id,
            "pageOrSlide": int(section["pageOrSlide"]),
            "excerpt": section["excerpt"],
        }
        if section.get("heading"):
            citation["heading"] = section["heading"]
        scored.append(RetrievalResult(citation=citation, score=round(score, 3)))

    scored.sort(key=lambda result: result.score, reverse=True)
    return scored[:top_k]


def grounding_status(results: list[RetrievalResult]) -> str:
    """Describe how well a scene is supported by the source material.

    Returning ``general_knowledge`` is what keeps the product honest: when the
    material does not cover a concept we say so rather than attaching a
    plausible-looking citation to invented content.
    """
    if not results:
        return "general_knowledge"
    return "source_grounded" if results[0].grounded else "general_knowledge"


def best_citations(results: list[RetrievalResult]) -> list[dict[str, Any]]:
    """Citations for grounded results only; never cite a weak match."""
    return [result.citation for result in results if result.grounded]
