"""Owner-scoped MongoDB adapter contract with zero unauthorized writes."""

import asyncio
import logging
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.adapters.mongodb.chat_repository import MongoChatRepository
from app.core.actor import ActorContext
from app.db.context_manager import ContextManager
from app.features.chat.domain import ChatAccessDenied, ChatMessage, ChatRoomNotFound


class Rooms:
    def __init__(self) -> None:
        self.queries = []

    async def find_one(self, query):
        self.queries.append(query)
        if query == {"room_id": "room-a", "user_id": "user-a", "is_deleted": False}:
            return {"room_id": "room-a", "user_id": "user-a"}
        return None


class Manager:
    def __init__(self) -> None:
        self.rooms = Rooms()
        self.writes = []

    async def connect(self):
        return None

    @property
    def db(self):
        return {"chat_rooms": self.rooms}

    async def save_conversation(self, *args):
        self.writes.append(args)
        return True


def repository(manager: Manager, *, session_user_id: str = "user-a") -> MongoChatRepository:
    engineer = SimpleNamespace(
        db_manager=manager,
        get_user_context=lambda _user_id: None,
        analyze_and_update_context=lambda _user_id: None,
    )

    async def get_context(_user_id):
        return {}

    async def analyze(_user_id):
        return None

    engineer.get_user_context = get_context
    engineer.analyze_and_update_context = analyze
    context = SimpleNamespace(
        session_manager=SimpleNamespace(
            get_session=lambda session_id: {
                "session_id": session_id,
                "user_id": session_user_id,
                "room_id": "room-a",
            }
        ),
        context_engineer=engineer,
    )
    return MongoChatRepository(context)


def repository_with_analyzer(manager: Manager, analyzer) -> MongoChatRepository:
    adapter = repository(manager)
    adapter._context_system.context_engineer.analyze_and_update_context = analyzer
    return adapter


@pytest.mark.asyncio
async def test_owned_room_write_revalidates_owner_in_query() -> None:
    manager = Manager()
    adapter = repository(manager)
    actor = await adapter.authorize_actor(
        ActorContext(user_id="user-a", room_id="room-a", session_id="room-a")
    )
    await adapter.save_message(ChatMessage(actor, "query", "answer"))

    assert manager.rooms.queries == [
        {"room_id": "room-a", "user_id": "user-a", "is_deleted": False},
        {"room_id": "room-a", "user_id": "user-a", "is_deleted": False},
    ]
    assert len(manager.writes) == 1


@pytest.mark.asyncio
async def test_cross_user_room_has_zero_writes() -> None:
    manager = Manager()
    adapter = repository(manager)

    with pytest.raises(ChatRoomNotFound):
        await adapter.save_message(
            ChatMessage(
                ActorContext(
                    user_id="user-b",
                    room_id="room-a",
                    session_id="room-a",
                ),
                "query",
                "answer",
            )
        )

    assert manager.writes == []


@pytest.mark.asyncio
async def test_cross_user_session_has_zero_writes() -> None:
    manager = Manager()
    adapter = repository(manager, session_user_id="user-b")

    with pytest.raises(ChatAccessDenied):
        await adapter.save_message(
            ChatMessage(
                ActorContext(
                    user_id="user-a",
                    room_id="room-a",
                    session_id="room-a",
                ),
                "query",
                "answer",
            )
        )

    assert manager.writes == []


@pytest.mark.asyncio
async def test_background_analysis_failure_is_consumed_and_sanitized(caplog) -> None:
    async def fail_analysis(_user_id):
        raise RuntimeError("raw health context")

    manager = Manager()
    adapter = repository_with_analyzer(manager, fail_analysis)
    actor = await adapter.authorize_actor(
        ActorContext(user_id="user-a", room_id="room-a", session_id="room-a")
    )

    with caplog.at_level(logging.WARNING):
        await adapter.save_message(ChatMessage(actor, "query", "answer"))
        while adapter._background_tasks:
            await asyncio.sleep(0)

    assert "Chat context analysis task failed" in caplog.text
    assert "raw health context" not in caplog.text


@pytest.mark.asyncio
async def test_concurrent_deterministic_id_race_is_an_idempotent_replay() -> None:
    class DuplicateCollection:
        async def update_one(self, *_args, **_kwargs):
            raise DuplicateKeyError("concurrent retry won")

    manager = ContextManager()
    manager.db = SimpleNamespace(conversation_history=DuplicateCollection())

    created = await manager.save_conversation(
        "user-a",
        "room-a",
        "ollama_rag",
        "query",
        "answer",
        "room-a",
        "client-message-a",
    )

    assert created is False
