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
