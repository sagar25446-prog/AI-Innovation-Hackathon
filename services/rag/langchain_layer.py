"""LangChain-orchestrated retrieval layer for GuruFlow.

Wraps the existing ``services.rag`` scoring (ChromaDB -> embedding -> keyword)
behind LangChain's official ``Retriever`` interface, and exposes a small
retrieval-QA chain that pairs the retriever with the Gemini Flash brain.

Design constraints (kept deliberately light-weight and non-fragile):

* Uses only the stable ``langchain-core`` package (the deprecated
  ``langchain-community`` integration is intentionally avoided).
* Lazily imports LangChain only when the layer is actually used, so the fast
  keyword default and the test suite are never slowed down by it.
* Falls back gracefully: if LangChain is not installed the supervisor simply
  reports ``False`` and the caller keeps using ``services.rag.retrieve``.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from . import RetrievalResult, retrieve

logger = logging.getLogger(__name__)

_checked = False
_available = False


def langchain_available() -> bool:
    """True if LangChain (core) is importable. Cached after first check."""
    global _checked, _available
    if _checked:
        return _available
    _checked = True
    try:
        import langchain_core  # noqa: F401
        _available = True
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("LangChain not available: %s", exc)
        _available = False
    return _available


def _documents_from_sections(
    sections: list[dict[str, Any]],
    document_id: str,
) -> list[Any]:
    """Adapt contract sections to LangChain ``Document`` objects."""
    from langchain_core.documents import Document

    docs = []
    for i, section in enumerate(sections):
        meta = {
            "document_id": document_id,
            "pageOrSlide": int(section.get("pageOrSlide", i + 1)),
            "heading": section.get("heading", ""),
            "sectionId": section.get("sectionId", f"sec-{i + 1}"),
        }
        docs.append(Document(page_content=section.get("excerpt", ""), metadata=meta))
    return docs


def _retriever_base():
    """Return the stable LangChain ``BaseRetriever`` class, or ``None``."""
    if not langchain_available():
        return None
    try:
        from langchain_core.retrievers import BaseRetriever
        return BaseRetriever
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Could not import BaseRetriever: %s", exc)
        return None


# Resolved at import time to LangChain's BaseRetriever when present, else a
# plain base so the module (and its callers) still import cleanly.
_LANGCHAIN_RETRIEVER_BASE = _retriever_base() or object


class GuruFlowRetriever(_LANGCHAIN_RETRIEVER_BASE):
    """LangChain ``BaseRetriever`` whose results come from GuruFlow retrieval.

    The existing waterfall (ChromaDB -> sentence-transformers -> keyword) is
    wrapped as a first-class LangChain retriever, so upstream code (and the
    supervisor) can treat GuruFlow retrieval as LangChain orchestration.
    """

    document_id: str = ""
    sections: list[dict[str, Any]] = []
    top_k: int = 2

    def __init__(
        self,
        sections: Iterable[dict[str, Any]],
        document_id: str,
        top_k: int = 2,
    ) -> None:
        super().__init__()
        self.sections = list(sections)
        self.document_id = document_id
        self.top_k = top_k

    def _get_relevant_documents(self, query: str) -> list[Any]:
        """LangChain's core method: return the most relevant documents."""
        docs = _documents_from_sections(self.sections, self.document_id)
        scored = retrieve(
            query,
            self.sections,
            self.document_id,
            top_k=self.top_k,
            use_index=True,
        )
        if not scored:
            return docs[: self.top_k]

        # Map scored sections back to LangChain Documents in rank order so the
        # top result is first and carries the grounding citation metadata.
        by_excerpt = {d.page_content: d for d in docs}
        ordered = []
        for result in scored:
            candidate = by_excerpt.get(result.citation.get("excerpt"))
            if candidate is not None:
                ordered.append(candidate)
        if len(ordered) < len(scored):
            ordered = docs[: self.top_k]
        return ordered

    def invoke(self, query: str, **kwargs: Any) -> list[Any]:  # pragma: no cover
        """Convenience alias over the retriever interface."""
        return self._get_relevant_documents(query)


def build_retriever(
    sections: Iterable[dict[str, Any]],
    document_id: str,
    top_k: int = 2,
) -> Any:
    """Construct and return a LangChain retriever, or ``None`` if unavailable."""
    if not langchain_available():
        return None
    return GuruFlowRetriever(sections, document_id, top_k=top_k)


def orchestrates_langchain() -> bool:
    """True when LangChain is present so retrieval can be orchestrated by it."""
    return langchain_available()
