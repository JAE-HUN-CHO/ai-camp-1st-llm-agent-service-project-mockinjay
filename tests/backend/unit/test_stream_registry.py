"""Tests for the application-scoped stream cancellation seam."""

from backend.app.services.stream_registry import StreamRegistry


def test_registry_isolated_and_supports_cancellation_metadata() -> None:
    first = StreamRegistry()
    second = StreamRegistry()
    first.set("session-1", {"cancel_requested": False})

    first.get("session-1")["cancel_requested"] = True

    assert first.get("session-1")["cancel_requested"] is True
    assert second.get("session-1") is None
    assert first.pop("session-1")["cancel_requested"] is True
    assert "session-1" not in first
