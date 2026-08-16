"""Explicit local MongoDB integration for the Phase-2 Chat repository."""

import asyncio
from pathlib import Path
import os
import sys
from types import SimpleNamespace
import uuid

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.adapters.mongodb.chat_repository import MongoChatRepository
from app.core.actor import ActorContext
from app.db.context_manager import ContextManager
from app.features.chat.domain import ChatMessage


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_repository_round_trip_is_owner_scoped() -> None:
    """사용자와 채팅방 소유권 범위에서 메시지 저장 및 조회 결과를 검증한다."""
    uri = os.getenv("MONGODB_URI")
    if not uri:
        pytest.skip("MONGODB_URI is required for the live Mongo integration smoke")

    suffix = uuid.uuid4().hex
    user_id = f"phase2-user-{suffix}"
    room_id = f"phase2-room-{suffix}"
    manager = ContextManager(uri=uri, db_name=os.getenv("DB_NAME", "careguide"))
    await manager.connect()

    async def get_context(_user_id):
        return {}

    async def analyze(_user_id):
        return None

    context_system = SimpleNamespace(
        session_manager=SimpleNamespace(get_session=lambda _session_id: None),
        context_engineer=SimpleNamespace(
            db_manager=manager,
            get_user_context=get_context,
            analyze_and_update_context=analyze,
        ),
    )
    repository = MongoChatRepository(context_system)
    try:
        await manager.db.chat_rooms.insert_one(
            {
                "room_id": room_id,
                "user_id": user_id,
                "is_deleted": False,
            }
        )
        actor = await repository.authorize_actor(
            ActorContext(user_id=user_id, room_id=room_id, session_id=room_id)
        )
        client_message_id = f"phase2-message-{suffix}"
        await repository.save_message(
            ChatMessage(
                actor=actor,
                query="synthetic query",
                answer="synthetic answer",
                client_message_id=client_message_id,
            )
        )

        document = await manager.db.conversation_history.find_one(
            {"room_id": room_id, "user_id": user_id}
        )
        assert document is not None
        assert document["session_id"] == room_id
        assert document["agent_type"] == "ollama_rag"
        assert document["client_message_id"] == client_message_id
    finally:
        await manager.db.conversation_history.delete_many(
            {"room_id": room_id, "user_id": user_id}
        )
        await manager.db.chat_rooms.delete_many(
            {"room_id": room_id, "user_id": user_id}
        )
        await manager.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_client_message_id_prevents_sequential_and_concurrent_duplicate_writes() -> None:
    """
    동일한 클라이언트 메시지 ID를 사용한 순차 및 동시 저장이 중복 기록을 생성하지 않는지 검증합니다.
    """
    uri = os.getenv("MONGODB_URI")
    if not uri:
        pytest.skip("MONGODB_URI is required for the live Mongo integration smoke")

    suffix = uuid.uuid4().hex
    user_id = f"phase2-idempotency-user-{suffix}"
    room_id = f"phase2-idempotency-room-{suffix}"
    manager = ContextManager(uri=uri, db_name=os.getenv("DB_NAME", "careguide"))
    await manager.connect()

    async def get_context(_user_id):
        return {}

    async def analyze(_user_id):
        return None

    context_system = SimpleNamespace(
        session_manager=SimpleNamespace(get_session=lambda _session_id: None),
        context_engineer=SimpleNamespace(
            db_manager=manager,
            get_user_context=get_context,
            analyze_and_update_context=analyze,
        ),
    )
    repository = MongoChatRepository(context_system)
    try:
        await manager.db.chat_rooms.insert_one(
            {
                "room_id": room_id,
                "user_id": user_id,
                "is_deleted": False,
            }
        )
        actor = await repository.authorize_actor(
            ActorContext(user_id=user_id, room_id=room_id, session_id=room_id)
        )

        sequential_id = f"phase2-sequential-{suffix}"
        sequential_message = ChatMessage(
            actor=actor,
            query="synthetic sequential query",
            answer="synthetic sequential answer",
            client_message_id=sequential_id,
        )
        await repository.save_message(sequential_message)
        await repository.save_message(sequential_message)

        concurrent_id = f"phase2-concurrent-{suffix}"
        await asyncio.gather(
            repository.save_message(
                ChatMessage(
                    actor=actor,
                    query="synthetic concurrent query",
                    answer="synthetic concurrent answer a",
                    client_message_id=concurrent_id,
                )
            ),
            repository.save_message(
                ChatMessage(
                    actor=actor,
                    query="synthetic concurrent query",
                    answer="synthetic concurrent answer b",
                    client_message_id=concurrent_id,
                )
            ),
        )

        assert await manager.db.conversation_history.count_documents(
            {"user_id": user_id, "client_message_id": sequential_id}
        ) == 1
        assert await manager.db.conversation_history.count_documents(
            {"user_id": user_id, "client_message_id": concurrent_id}
        ) == 1
    finally:
        await manager.db.conversation_history.delete_many(
            {"room_id": room_id, "user_id": user_id}
        )
        await manager.db.chat_rooms.delete_many(
            {"room_id": room_id, "user_id": user_id}
        )
        await manager.close()
