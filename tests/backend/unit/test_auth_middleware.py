import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.middleware.auth import is_public_path


def test_chat_info_is_the_only_public_chat_path() -> None:
    assert is_public_path("/api/chat/info")
    assert not is_public_path("/api/chat/history")
    assert not is_public_path("/api/chat/rooms/room-1/history")
    assert not is_public_path("/api/chat/stream")


def test_session_routes_are_protected() -> None:
    assert not is_public_path("/api/session/create")
    assert not is_public_path("/api/session/session-1/history")
