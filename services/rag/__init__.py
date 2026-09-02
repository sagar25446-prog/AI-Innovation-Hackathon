"""Section-aware retrieval over ingested material.

Supports two retrieval modes:
1. Embedding-based (sentence-transformers + ChromaDB) - semantic search
2. Keyword overlap (original) - fallback when embeddings are unavailable

The embedding path is tried first; keyword overlap is always available.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# Below this score we do not claim the answer came from the material.
GROUNDING_THRESHOLD = 0.15

# Lazy-loaded embedding model
_embedding_model = None
_embeddings_checked = False
_embeddings_available = False


def _get_embedding_model():
    """Lazy-load sentence-transformers model."""
    global _embedding_model, _embeddings_checked, _embeddings_available
    if _embeddings_checked:
        return _embedding_model if _embeddings_available else None
    _embeddings_checked = True
    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        _embeddings_available = True
        logger.info("Loaded sentence-transformers model: all-MiniLM-L6-v2")
        return _embedding_model
    except Exception as exc:
        logger.warning("Could not load sentence-transformers: %s. Using keyword fallback.", exc)
        _embeddings_available = False
        return None


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
    return weighted / (len(query_tokens) * 3)


def _embedding_search(
    query: str,
    sections: list[dict[str, Any]],
    document_id: str,
    top_k: int = 2,
) -> list[RetrievalResult]:
    """Semantic search using sentence-transformers embeddings."""
    model = _get_embedding_model()
    if model is None or not sections:
        return []

    try:
        import torch
        excerpts = [s.get("excerpt", "") for s in sections]
        all_texts = [query] + excerpts
        embeddings = model.encode(all_texts, convert_to_tensor=True)

        query_emb = embeddings[0]
        section_embs = embeddings[1:]
        similarities = torch.nn.functional.cosine_similarity(
            query_emb.unsqueeze(0), section_embs
        )

        scored = []
        for i, sim in enumerate(similarities.tolist()):
            section = sections[i]
            citation = {
                "documentId": document_id,
                "pageOrSlide": int(section["pageOrSlide"]),
                "excerpt": section["excerpt"],
            }
            if section.get("heading"):
                citation["heading"] = section["heading"]
            scored.append(RetrievalResult(citation=citation, score=round(sim, 3)))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]
    except Exception as exc:
        logger.warning("Embedding search failed: %s", exc)
        return []


def retrieve(
    query: str,
    sections: Iterable[dict[str, Any]],
    document_id: str,
    top_k: int = 2,
) -> list[RetrievalResult]:
    """Return the ``top_k`` best-matching sections as contract citations.

    Tries embedding search first, falls back to keyword overlap.
    """
    sections_list = list(sections)
    if not sections_list:
        return []

    embedding_results = _embedding_search(query, sections_list, document_id, top_k)
    if embedding_results and embedding_results[0].score > 0.3:
        return embedding_results

    query_tokens = _tokenise(query)
    scored: list[RetrievalResult] = []

    for section in sections_list:
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
    """Describe how well a scene is supported by the source material."""
    if not results:
        return "general_knowledge"
    return "source_grounded" if results[0].grounded else "general_knowledge"


def best_citations(results: list[RetrievalResult]) -> list[dict[str, Any]]:
    """Citations for grounded results only; never cite a weak match."""
    return [result.citation for result in results if result.grounded]
