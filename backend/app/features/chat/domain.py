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
    """Identify an owner-bound room and its optional backing session."""

    room_id: str
    owner_id: str
    session_id: str | None = None


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Represent one authorized, completed turn ready for persistence."""

    actor: ActorContext
    query: str
    answer: str
    agent_type: str = "ollama_rag"
    client_message_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ChatGeneration:
    """Return a provider-neutral result for a non-streaming Chat request."""

    answer: str
    sources: tuple[Mapping[str, object], ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)
    agent_type: str = "ollama_rag"
    persisted: bool = True


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    """Carry one provider-neutral frame without transport sentinels."""

    status: str
    content: str = ""
    agent_type: str | None = None
    error: str | None = None
    attributes: Mapping[str, object] = field(default_factory=dict)

    def as_payload(self) -> dict[str, object]:
        """Build the frozen v1 SSE payload while omitting empty fields."""

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
    """Reject a request that is not bound to the owning actor."""


class ChatRoomNotFound(ChatError):
    """Report a missing room without disclosing another owner's room."""


class ChatSessionNotFound(ChatError):
    """Report a missing session after owner-scoped authorization."""


class ChatProviderUnavailable(ChatError):
    """Report an unavailable local Chat provider."""


class ChatProviderTimeout(ChatProviderUnavailable):
    """Report that the local Chat provider exceeded its time limit."""


class ChatPersistenceError(ChatError):
    """Report that an authorized completed turn could not be persisted."""
