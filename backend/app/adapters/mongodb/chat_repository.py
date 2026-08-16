"""MongoDB implementation of the Chat-owned repository port."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

from app.core.actor import ActorContext
from app.features.chat.domain import (
    ChatAccessDenied,
    ChatMessage,
    ChatPersistenceError,
    ChatRoomNotFound,
    ChatSessionNotFound,
)


logger = logging.getLogger(__name__)


def _consume_background_task(task: asyncio.Task[Any]) -> None:
    """Retrieve task failures without exposing context or chat content."""
    if task.cancelled():
        return
    try:
        failure = task.exception()
    except Exception:
        logger.warning("Chat context analysis task failed")
        return
    if failure is not None:
        logger.warning("Chat context analysis task failed")


class MongoChatRepository:
    """Adapt the existing context/session stores without changing schemas."""

    def __init__(self, context_system: Any) -> None:
        self._context_system = context_system
        self._background_tasks: set[asyncio.Task[Any]] = set()

    @property
    def _manager(self) -> Any:
        return self._context_system.context_engineer.db_manager

    async def authorize_actor(self, actor: ActorContext) -> ActorContext:
        if not actor.user_id:
            raise ChatAccessDenied("authenticated actor is required")

        manager = self._manager
        await manager.connect()
        owned_room = None
        if actor.room_id:
            owned_room = await manager.db["chat_rooms"].find_one(
                {
                    "room_id": actor.room_id,
                    "user_id": actor.user_id,
                    "is_deleted": False,
                }
            )
            if not owned_room:
                raise ChatRoomNotFound("room not found")

        session_id = actor.session_id
        if session_id in {None, "default"}:
            session_id = actor.room_id or f"default:{actor.user_id}"

        if session_id:
            session = self._context_system.session_manager.get_session(session_id)
            compatibility_session = session_id == f"default:{actor.user_id}"
            if not session and not (
                compatibility_session
                or (owned_room and session_id == actor.room_id)
            ):
                raise ChatSessionNotFound("session not found")
            if session and str(session.get("user_id")) != actor.user_id:
                raise ChatAccessDenied("session ownership mismatch")
            if (
                actor.room_id
                and session
                and session.get("room_id") not in {None, actor.room_id}
            ):
                raise ChatAccessDenied("session room mismatch")

        return ActorContext(
            user_id=actor.user_id,
            room_id=actor.room_id,
            session_id=session_id,
            health_record_id=actor.health_record_id,
        )

    async def get_user_context(self, actor: ActorContext) -> Mapping[str, object]:
        context = await self._context_system.context_engineer.get_user_context(
            actor.user_id
        )
        return context if isinstance(context, Mapping) else {}

    async def save_message(self, message: ChatMessage) -> None:
        try:
            # Revalidate immediately before the write so a room deletion or
            # owner mismatch during generation cannot create an unauthorized
            # conversation document.
            actor = await self.authorize_actor(message.actor)
            created = await self._manager.save_conversation(
                actor.user_id,
                actor.session_id,
                message.agent_type,
                message.query,
                message.answer,
                actor.room_id,
                message.client_message_id,
            )
            if created is False:
                return
            task = asyncio.create_task(
                self._context_system.context_engineer.analyze_and_update_context(
                    actor.user_id
                )
            )
            self._background_tasks.add(task)
            task.add_done_callback(_consume_background_task)
            task.add_done_callback(self._background_tasks.discard)
        except (ChatAccessDenied, ChatRoomNotFound, ChatSessionNotFound):
            raise
        except Exception as exc:
            logger.warning("Chat history persistence failed")
            raise ChatPersistenceError("chat history persistence failed") from exc
