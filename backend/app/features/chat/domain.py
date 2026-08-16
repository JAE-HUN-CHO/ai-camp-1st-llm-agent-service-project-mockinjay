"""Framework-free values and failures for the Chat vertical slice.

``ChatSafetyPolicy`` deliberately aliases the Phase-0
``EmergencySafetyPolicy``.  Chat does not own a second keyword list or a second
policy instance; every composition root injects the existing singleton.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping, TypeAlias

from app.core.actor import ActorContext
from app.core.emergency_safety import EmergencySafetyPolicy


ChatSafetyPolicy: TypeAlias = EmergencySafetyPolicy


@dataclass(frozen=True, slots=True)
class ChatRoom:
    room_id: str
    owner_id: str
    session_id: str | None = None


@dataclass(frozen=True, slots=True)
class ChatMessage:
    actor: ActorContext
    query: str
    answer: str
    agent_type: str = "ollama_rag"
    client_message_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ChatGeneration:
    answer: str
    sources: tuple[Mapping[str, object], ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)
    agent_type: str = "ollama_rag"
    persisted: bool = True


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    status: str
    content: str = ""
    agent_type: str | None = None
    error: str | None = None
    attributes: Mapping[str, object] = field(default_factory=dict)

    def as_payload(self) -> dict[str, object]:
        """
        스트림 이벤트를 직렬화 가능한 페이로드로 변환합니다.
        
        Returns:
        	dict[str, object]: 이벤트 속성에 상태와 설정된 콘텐츠, 에이전트 유형, 오류를 포함한 페이로드
        """
        payload: dict[str, object] = dict(self.attributes)
        payload["status"] = self.status
        if self.content:
            payload["content"] = self.content
        if self.agent_type:
            payload["agent_type"] = self.agent_type
        if self.error:
            payload["error"] = self.error
        return payload


class ChatError(Exception):
    """Base failure mapped by the inbound adapter."""


class ChatAccessDenied(ChatError):
    pass


class ChatRoomNotFound(ChatError):
    pass


class ChatSessionNotFound(ChatError):
    pass


class ChatProviderUnavailable(ChatError):
    pass


class ChatProviderTimeout(ChatProviderUnavailable):
    pass


class ChatPersistenceError(ChatError):
    pass
