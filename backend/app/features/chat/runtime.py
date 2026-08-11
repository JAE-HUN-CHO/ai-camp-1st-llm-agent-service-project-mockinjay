"""Application-scoped chat state and context seams.

The feature owns request/session state; API modules only ask for the runtime
attached to the current FastAPI application.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request


class StreamRegistry:
    """Small mapping seam for active stream metadata."""

    def __init__(self) -> None:
        self._streams: dict[str, dict[str, Any]] = {}

    def get(self, session_id: str, default: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return self._streams.get(session_id, default)

    def set(self, session_id: str, metadata: dict[str, Any]) -> None:
        self._streams[session_id] = metadata

    def pop(self, session_id: str, default: Any = None) -> Any:
        return self._streams.pop(session_id, default)

    def __contains__(self, session_id: str) -> bool:
        return session_id in self._streams


def get_stream_registry(request: Request) -> StreamRegistry:
    """Return the registry owned by this FastAPI application instance."""
    registry = getattr(request.app.state, "stream_registry", None)
    if registry is None:
        registry = StreamRegistry()
        request.app.state.stream_registry = registry
    return registry


def get_context_system(request: Any) -> Any:
    """Return the context/session runtime owned by this application."""
    context_system = getattr(request.app.state, "context_system", None)
    if context_system is None:
        try:
            from app.core.context_system import ContextSystem
        except ModuleNotFoundError:  # supports direct repository-root imports
            from backend.app.core.context_system import ContextSystem

        context_system = ContextSystem()
        request.app.state.context_system = context_system
    return context_system
