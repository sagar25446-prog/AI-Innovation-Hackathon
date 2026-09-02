"""Tests for the LangChain-orchestrated retrieval layer.

These use the fast keyword path on purpose: the LangChain retriever wraps
services.rag.retrieve(), which degrades to keyword scoring when vector RAG is
off, so these tests never trigger the heavy sentence-transformers/ChromaDB load.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from services.rag import rag_status, retrieve  # noqa: E402


def _langchain_present() -> bool:
    try:
        from langchain_core.retrievers import BaseRetriever  # noqa: F401
        return True
    except ImportError:
        return False


def _langchain_ok() -> bool:
    try:
        from services.rag.langchain_layer import GuruFlowRetriever  # noqa: F401
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _langchain_present(), reason="langchain-core not installed"
)

_SECTIONS = [
    {
        "pageOrSlide": 1,
        "heading": "Current",
        "excerpt": "Current is the flow of electric charge in amperes.",
        "keywords": ["current"],
    },
    {
        "pageOrSlide": 2,
        "heading": "Resistance",
        "excerpt": "Resistance opposes current and is measured in ohms.",
        "keywords": ["resistance"],
    },
    {
        "pageOrSlide": 3,
        "heading": "Ohm's Law",
        "excerpt": "Ohm's law states V equals I times R.",
        "keywords": ["voltage"],
    },
]


def _langchain_present() -> bool:
    try:
        from langchain_core.retrievers import BaseRetriever  # noqa: F401
        return True
    except ImportError:
        return False


def test_rag_status_reports_langchain_orchestration():
    status = rag_status()
    assert status["langchain"] is True
    assert "langchain" in status["mode"]


@pytest.mark.skipif(
    not _langchain_ok(), reason="GuruFlowRetriever unavailable"
)
def test_langchain_retriever_returns_ranked_documents():
    from services.rag.langchain_layer import build_retriever

    retriever = build_retriever(_SECTIONS, "mat-doc", top_k=2)
    assert retriever is not None
    docs = retriever.invoke("how does resistance oppose current")
    assert len(docs) == 2
    # Top hit should be the Resistance section.
    assert docs[0].metadata["heading"] == "Resistance"
    assert docs[0].metadata["pageOrSlide"] == 2


@pytest.mark.skipif(
    not _langchain_ok(), reason="GuruFlowRetriever unavailable"
)
def test_langchain_retriever_is_base_retriever_subclass():
    from services.rag.langchain_layer import GuruFlowRetriever
    from langchain_core.retrievers import BaseRetriever

    assert issubclass(GuruFlowRetriever, BaseRetriever)


def test_retrieve_still_returns_grounded_results():
    results = retrieve("resistance opposes the current", _SECTIONS, "mat-doc")
    assert len(results) >= 1
    assert results[0].citation["heading"] == "Resistance"
    assert results[0].grounded is True
