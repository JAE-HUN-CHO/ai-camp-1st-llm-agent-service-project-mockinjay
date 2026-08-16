"""Cross-user ownership matrix for chat resources."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.api.dependencies import authorize_chat_actor


class _Rooms:
    def __init__(self):
        self.queries = []

    async def find_one(self, query):
        self.queries.append(query)
        if query == {"room_id": "room-a", "user_id": "user-a", "is_deleted": False}:
            return {"room_id": "room-a", "user_id": "user-a"}
        return None


class _DBManager:
    def __init__(self):
        self.rooms = _Rooms()
        self.connect_count = 0

    async def connect(self):
        self.connect_count += 1

    @property
    def db(self):
        return {"chat_rooms": self.rooms}


def _request(user_id):
    return SimpleNamespace(state=SimpleNamespace(user_id=user_id))


def _context(session):
    manager = _DBManager()
    return (
        SimpleNamespace(
            session_manager=SimpleNamespace(get_session=lambda _session_id: session),
            context_engineer=SimpleNamespace(db_manager=manager),
        ),
        manager,
    )


@pytest.mark.asyncio
async def test_owned_room_and_session_are_bound_before_downstream() -> None:
    context, manager = _context(
        {"session_id": "session-a", "user_id": "user-a", "room_id": "room-a"}
    )
    actor = await authorize_chat_actor(
        _request("user-a"),
        context,
        requested_user_id="user-a",
        room_id="room-a",
        session_id="session-a",
    )
    assert actor.user_id == "user-a"
    assert manager.connect_count == 1


@pytest.mark.asyncio
async def test_persisted_room_authorizes_after_session_cache_restart() -> None:
    context, manager = _context(None)
    actor = await authorize_chat_actor(
        _request("user-a"),
        context,
        requested_user_id="user-a",
        room_id="room-a",
        session_id="room-a",
    )
    assert actor.room_id == "room-a"
    assert actor.session_id == "room-a"
    assert manager.connect_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("request_user", "requested_user", "room_id", "session", "expected_status"),
    [
        ("user-a", "user-b", None, None, 403),
        ("user-a", "user-a", "room-b", None, 404),
        ("user-a", "user-a", None, None, 404),
        ("user-a", "user-a", None, {"user_id": "user-b"}, 403),
        (
            "user-a",
            "user-a",
            "room-a",
            {"user_id": "user-a", "room_id": "room-b"},
            403,
        ),
    ],
)
async def test_cross_user_matrix_rejects_every_unauthorized_case(
    request_user, requested_user, room_id, session, expected_status
) -> None:
    context, _manager = _context(session)
    with pytest.raises(HTTPException) as exc:
        await authorize_chat_actor(
            _request(request_user),
            context,
            requested_user_id=requested_user,
            room_id=room_id,
            session_id="session-a" if session is not None or room_id is None else None,
        )
    assert exc.value.status_code == expected_status
