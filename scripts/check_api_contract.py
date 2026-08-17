#!/usr/bin/env python3
"""Verify the small route contract shared by the canonical frontend and API."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # noqa: E402


def route_methods(path: str) -> set[str]:
    return {
        method
        for route in app.routes
        if getattr(route, "path", None) == path
        for method in getattr(route, "methods", set())
    }


REQUIRED = {
    "/api/auth/change-password": {"POST"},
    "/api/mypage/health-profile": {"GET", "PUT"},
    "/api/health-records/": {"GET", "POST"},
    "/api/health-records/{record_id}": {"PUT", "DELETE"},
    "/api/quiz/session/start": {"POST"},
    "/api/quiz/session/submit-answer": {"POST"},
    "/api/quiz/session/complete": {"POST"},
    "/api/chat/message": {"POST"},
    "/api/chat/stream": {"POST"},
    "/api/chat/rooms": {"GET"},
    "/api/chat/rooms/{room_id}/history": {"GET"},
    "/api/chat/history": {"GET"},
    "/api/chat/history/{agent_type}": {"GET"},
    "/api/chat/research/{path:path}": {
        "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"
    },
    "/api/chat/welfare/{path:path}": {
        "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"
    },
    "/api/chat/{path:path}": {
        "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"
    },
}


def main() -> int:
    failures: list[str] = []
    for path, methods in REQUIRED.items():
        missing = methods - route_methods(path)
        if missing:
            failures.append(f"{path}: missing {sorted(missing)}")

    for stale_path in (
        "/api/health",
        "/api/quiz/start",
        "/api/quiz/submit",
        "/api/trends",
    ):
        if route_methods(stale_path):
            failures.append(f"stale route still registered: {stale_path}")
    if any(getattr(route, "path", "").startswith("/api/v2") for route in app.routes):
        failures.append("unapproved /api/v2 route registered")

    if failures:
        print("API contract: FAIL")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1

    print(f"API contract: PASS ({len(REQUIRED)} required paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
