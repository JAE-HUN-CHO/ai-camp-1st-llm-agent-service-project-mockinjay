"""Regression checks for the public API contract used by the frontend."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.main import app


def _route_methods(path: str) -> set[str]:
    return {
        method
        for route in app.routes
        if getattr(route, "path", None) == path
        for method in getattr(route, "methods", set())
    }


def test_frontend_account_and_health_routes_are_registered() -> None:
    assert "POST" in _route_methods("/api/auth/change-password")
    assert _route_methods("/api/auth/change-password") <= {"POST"}
    assert {"GET", "POST"} <= _route_methods("/api/health-records/")
    assert {"PUT", "DELETE"} <= _route_methods("/api/health-records/{record_id}")


def test_quiz_contract_uses_session_endpoints() -> None:
    assert "POST" in _route_methods("/api/quiz/session/start")
    assert "POST" in _route_methods("/api/quiz/session/submit-answer")
    assert "POST" in _route_methods("/api/quiz/session/complete")


def test_frozen_chat_v1_routes_are_registered_without_v2_alias() -> None:
    assert _route_methods("/api/chat/message") == {"POST"}
    assert _route_methods("/api/chat/stream") == {"POST"}
    assert _route_methods("/api/chat/rooms") == {"GET"}
    assert _route_methods("/api/chat/rooms/{room_id}/history") == {"GET"}
    assert _route_methods("/api/chat/history") == {"GET"}
    assert _route_methods("/api/chat/history/{agent_type}") == {"GET"}
    proxy_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}
    assert _route_methods("/api/chat/research/{path:path}") == proxy_methods
    assert _route_methods("/api/chat/welfare/{path:path}") == proxy_methods
    assert _route_methods("/api/chat/{path:path}") == proxy_methods
    assert not any(
        getattr(route, "path", "").startswith("/api/v2") for route in app.routes
    )
