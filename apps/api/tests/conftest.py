"""Shared test configuration.

The suite is a regression guard for GuruFlow's **deterministic** behaviour.
`apps/api/main.py` loads `apps/api/.env` at import time, so once a real
`GEMINI_API_KEY` exists on the machine every planning and evaluation test
starts calling the live model. That is bad in three separate ways:

* **Non-deterministic** - the same suite fails different tests on consecutive
  runs, because the model's wording changes.
* **Slow** - the suite went from about 6 seconds to over 4 minutes.
* **Environment-dependent** - it passes for a teammate without a key and fails
  for one with a key, which is the worst kind of test failure to debug.

So the LLM is disabled for every test by default. Tests that genuinely need the
live model opt in with ``@pytest.mark.live_llm`` and are skipped when no key is
configured.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_KEY_VARS = ("GEMINI_API_KEY", "GURUFLOW_LLM_API_KEY")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live_llm: test needs a real Gemini key; skipped when none is configured.",
    )


def _reset_llm_module_state() -> None:
    """Clear services.llm's cached client and resolved model.

    The module memoises both, so removing the key from the environment is not
    enough on its own once something has already built a client.
    """
    llm = sys.modules.get("services.llm")
    if llm is None:
        return
    llm._gemini_client = None
    llm._model_attempted = False
    if hasattr(llm, "_MODEL_NAME"):
        llm._MODEL_NAME = None


def _has_live_key() -> bool:
    """Whether a real key is reachable, loading .env if pytest has not.

    Only `apps/api/main.py` calls load_dotenv, and a test module that never
    imports it would otherwise report "no key" while apps/api/.env sits right
    there - making @live_llm look broken rather than unconfigured.
    """
    if any(os.environ.get(name) for name in _KEY_VARS):
        return True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    for candidate in (REPO_ROOT / "apps" / "api" / ".env", REPO_ROOT / ".env"):
        if candidate.exists():
            load_dotenv(candidate)
    return any(os.environ.get(name) for name in _KEY_VARS)


@pytest.fixture(autouse=True)
def deterministic_llm(request, monkeypatch):
    """Disable the LLM unless the test is explicitly marked ``live_llm``."""
    if request.node.get_closest_marker("live_llm"):
        if not _has_live_key():
            pytest.skip("no Gemini key configured")
        yield
        return

    for name in _KEY_VARS:
        monkeypatch.delenv(name, raising=False)
    _reset_llm_module_state()
    yield
    # The next test re-resolves from whatever the environment then holds.
    _reset_llm_module_state()


# ---------------------------------------------------------------------------
# Shared API client
# ---------------------------------------------------------------------------
#
# This lived in test_api.py, so any other module that wanted it got
# "fixture 'client' not found". Shared here instead, so endpoint tests can sit
# in whichever module they belong to topically.

from fastapi.testclient import TestClient  # noqa: E402

from apps.api.main import app, repository  # noqa: E402


@pytest.fixture
def client(tmp_path):
    from apps.api import main as m
    from apps.api.student_memory import StudentMemoryStore

    repository.reset()
    # Isolate long-term memory from the shared on-disk store so endpoint tests
    # are hermetic (the real store is file-backed and persists across runs).
    saved_store = m.student_memory
    m.student_memory = StudentMemoryStore(directory=str(tmp_path / "memory"))
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        m.student_memory = saved_store
