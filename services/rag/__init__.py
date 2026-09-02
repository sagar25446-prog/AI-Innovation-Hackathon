"""Section-aware retrieval over ingested material.

Supports three retrieval modes, tried in order:
1. ChromaDB vector index (persistent, on-disk) - semantic search over indexed sections
2. In-memory embedding (sentence-transformers) - semantic search without a DB
3. Keyword overlap (original) - always available fallback

`index_sections()` persists embeddings to a local ChromaDB store. `retrieve()`
uses whichever path is available so the system never hard-fails.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# Below this score we do not claim the answer came from the material.
GROUNDING_THRESHOLD = 0.15

# Lazy-loaded embedding model
_embedding_model = None
_embeddings_checked = False
_embeddings_available = False

# ChromaDB persistent client / collection (lazy)
_chroma_client = None
_chroma_collection = None
_chroma_checked = False
_chroma_available = False

DEFAULT_CHROMA_DIR = os.environ.get(
    "GURUFLOW_CHROMA_DIR",
    str(Path(tempfile.gettempdir()) / "guruflow_chroma"),
)
COLLECTION_NAME = "material_sections"

# Vector RAG (sentence-transformers + ChromaDB) is opt-in via this flag. The
# keyword path stays the fast, always-available default so tests and the core
# demo run quickly. Set GURUFLOW_VECTOR_RAG=1 to engage full semantic search.
VECTOR_RAG_ENABLED = (
    os.environ.get("GURUFLOW_VECTOR_RAG", "0").strip().lower()
    in ("1", "true", "yes", "on")
)


def _get_embedding_model():
    """Lazy-load sentence-transformers model (only when vector RAG is enabled)."""
    global _embedding_model, _embeddings_checked, _embeddings_available
    if not VECTOR_RAG_ENABLED:
        return None
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


def _get_chroma_collection(persist_dir: str | None = None):
    """Lazy-open the persistent ChromaDB collection (only when vector RAG is enabled)."""
    global _chroma_client, _chroma_collection, _chroma_checked, _chroma_available
    if not VECTOR_RAG_ENABLED:
        return None
    if _chroma_available and _chroma_collection is not None:
        return _chroma_collection
    if _chroma_checked:
        return None
    _chroma_checked = True
    try:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=persist_dir or DEFAULT_CHROMA_DIR)
        _chroma_collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        _chroma_available = True
        logger.info("Opened ChromaDB vector index at %s", persist_dir or DEFAULT_CHROMA_DIR)
        return _chroma_collection
    except Exception as exc:
        logger.warning("Could not initialise ChromaDB: %s. Using in-memory/keyword search.", exc)
        return None


def _upsert_sections(sections: list[dict[str, Any]], document_id: str) -> bool:
    """Persist section embeddings into the ChromaDB index. Returns success."""
    model = _get_embedding_model()
    collection = _get_chroma_collection()
    if collection is None or model is None or not sections:
        return False
    try:
        ids: list[str] = []
        docs: list[str] = []
        metadatas: list[dict[str, Any]] = []
        for i, section in enumerate(sections):
            ids.append(f"{document_id}::sec-{i + 1}")
            docs.append(section.get("excerpt", ""))
            metadatas.append({
                "document_id": document_id,
                "page": int(section["pageOrSlide"]),
                "heading": section.get("heading", ""),
                "excerpt": section.get("excerpt", ""),
            })
        embeddings = model.encode(docs).tolist()
        collection.upsert(ids=ids, embeddings=embeddings, documents=docs, metadatas=metadatas)
        return True
    except Exception as exc:
        logger.warning("ChromaDB upsert failed: %s", exc)
        return False


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


def _chroma_search(
    query: str,
    document_id: str,
    top_k: int = 2,
) -> list[RetrievalResult]:
    """Vector search against the persistent ChromaDB index, scoped to a document."""
    collection = _get_chroma_collection()
    if collection is None:
        return []
    try:
        res = collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"document_id": document_id},
        )
        metadatas = (res.get("metadatas") or [[]])[0] or []
        distances = (res.get("distances") or [[]])[0] or []
        scored = []
        for md, dist in zip(metadatas, distances):
            # cosine distance -> similarity
            score = round(1 - float(dist), 3)
            scored.append(RetrievalResult(
                citation={
                    "documentId": md.get("document_id", document_id),
                    "pageOrSlide": int(md.get("page", 0)),
                    "excerpt": md.get("excerpt", ""),
                    "heading": md.get("heading", ""),
                },
                score=score,
            ))
        return scored
    except Exception as exc:
        logger.warning("ChromaDB query failed: %s", exc)
        return []


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


def index_sections(
    sections: Iterable[dict[str, Any]],
    document_id: str,
    persist_dir: str | None = None,
) -> bool:
    """Index extracted sections into the persistent ChromaDB vector store.

    Returns True if the sections were persisted to the vector index.
    """
    sections_list = list(sections)
    if not sections_list:
        return False
    if persist_dir:
        global _chroma_client, _chroma_collection, _chroma_checked, _chroma_available
        _chroma_client = None
        _chroma_collection = None
        _chroma_checked = False
        _chroma_available = False
    return _upsert_sections(sections_list, document_id)


def retrieve(
    query: str,
    sections: Iterable[dict[str, Any]],
    document_id: str,
    top_k: int = 2,
    use_index: bool = True,
) -> list[RetrievalResult]:
    """Return the ``top_k`` best-matching sections as contract citations.

    Retrieval order:
    1. ChromaDB vector index (if previously indexed and available)
    2. In-memory embedding similarity
    3. Keyword overlap (always available)
    """
    sections_list = list(sections)
    if not sections_list:
        return []

    if use_index:
        chroma_results = _chroma_search(query, document_id, top_k)
        if chroma_results and chroma_results[0].score > 0.3:
            return chroma_results

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
