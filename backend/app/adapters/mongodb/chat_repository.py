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


class MongoChatRepository:
    """Adapt the existing context/session stores without changing schemas."""

    def __init__(self, context_system: Any) -> None:
        """채팅 컨텍스트 시스템을 저장하고 백그라운드 작업 추적을 초기화합니다.
        
        Parameters:
        	context_system (Any): 채팅 컨텍스트와 데이터베이스 관리자를 제공하는 시스템
        """
        self._context_system = context_system
        self._background_tasks: set[asyncio.Task[Any]] = set()

    @property
    def _manager(self) -> Any:
        """컨텍스트 시스템의 데이터베이스 관리자를 제공합니다.
        
        Returns:
        	Any: 컨텍스트 시스템에 연결된 데이터베이스 관리자
        """
        return self._context_system.context_engineer.db_manager

    async def authorize_actor(self, actor: ActorContext) -> ActorContext:
        """
        액터의 사용자·방·세션 접근 권한을 검증하고 정규화된 컨텍스트를 반환합니다.
        
        Parameters:
            actor (ActorContext): 사용자, 방, 세션 식별자를 포함한 액터 컨텍스트
        
        Returns:
            ActorContext: 기본값이 보완된 정규화된 액터 컨텍스트
        
        Raises:
            ChatAccessDenied: 사용자 인증 정보가 없거나 세션 소유권 또는 방 일치 검증에 실패한 경우
            ChatRoomNotFound: 지정한 방을 찾을 수 없거나 사용자가 소유하지 않은 경우
            ChatSessionNotFound: 지정한 세션을 찾을 수 없는 경우
        """
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
        """
        사용자에 대한 컨텍스트 정보를 조회합니다.
        
        Parameters:
            actor (ActorContext): 컨텍스트를 조회할 사용자 정보
        
        Returns:
            Mapping[str, object]: 사용자의 컨텍스트 매핑 또는 유효한 매핑이 없을 때 빈 매핑
        """
        context = await self._context_system.context_engineer.get_user_context(
            actor.user_id
        )
        return context if isinstance(context, Mapping) else {}

    async def save_message(self, message: ChatMessage) -> None:
        """
        메시지를 저장하고 사용자 컨텍스트 업데이트를 예약합니다.
        
        Raises:
            ChatAccessDenied: 액터의 접근 권한이 없는 경우.
            ChatRoomNotFound: 지정된 채팅방을 찾을 수 없는 경우.
            ChatSessionNotFound: 지정된 세션을 찾을 수 없는 경우.
            ChatPersistenceError: 메시지 저장 중 예기치 않은 오류가 발생한 경우.
        """
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
            task.add_done_callback(self._background_tasks.discard)
        except (ChatAccessDenied, ChatRoomNotFound, ChatSessionNotFound):
            raise
        except Exception as exc:
            logger.warning("Chat history persistence failed")
            raise ChatPersistenceError("chat history persistence failed") from exc
