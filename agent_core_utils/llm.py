"""
Compatibility shim for legacy imports.

Some agents expect `from agent_core_utils.llm import initialize_llm_client`.
This module forwards to `agent_core_utils.services.initialize_llm_client` and
falls back to a minimal dummy client if that import fails.
"""

from __future__ import annotations

try:  # Prefer the real implementation when available
    from .services import initialize_llm_client as _initialize_llm_client  # type: ignore
except Exception:  # pragma: no cover - defensive fallback
    _initialize_llm_client = None  # type: ignore


def initialize_llm_client():  # noqa: D401 - simple forwarder
    """Return an LLM client compatible with the expected interface.

    If the real implementation is available, use it; otherwise provide a
    minimal dummy client exposing `invoke(messages)` and optional `astream`.
    """
    if callable(_initialize_llm_client):
        return _initialize_llm_client()

    class _DummyResponse:
        # Match langchain-like response shape with a `.content` attribute
        def __init__(self, content: str = "") -> None:
            self.content = content

    class _DummyClient:
        def invoke(self, _messages):  # simple echo-ish stub
            return _DummyResponse("")

    return _DummyClient()
