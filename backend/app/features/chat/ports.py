"""Consumer-owned outbound ports for Chat.

Decision record:

* ``app.ports.llm.LLMProvider`` is not reused because its prompt/string
  signatures cannot preserve the current grounded response, source metadata,
  profile, or SSE frame contract.
* ``ChatRepository`` is new because no existing Protocol owns room/session
  authorization plus conversation persistence.
* ``AgentRouter`` is intentionally not introduced in Phase 2.  The frozen
  canonical path bypasses RouterAgent; routing it now would be a behavior
  migration.  The legacy Router/RemoteAgent facade remains available.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import Protocol

from app.core.actor import ActorContext
from app.features.chat.domain import ChatGeneration, ChatMessage, ChatStreamEvent


class ChatRepository(Protocol):
    """Authorize Chat ownership and persist completed turns."""

    async def authorize_actor(self, actor: ActorContext) -> ActorContext:
        """Return an owner-bound actor or fail closed before any model call."""

    async def get_user_context(self, actor: ActorContext) -> Mapping[str, object]:
        """Load context belonging only to the already-authorized actor."""

    async def save_message(self, message: ChatMessage) -> None:
        """Persist a completed turn after revalidating ownership at write time."""


class ChatGenerator(Protocol):
    """Generate grounded responses through the configured local provider."""

    async def generate(
        self,
        query: str,
        *,
        profile: str,
        user_context: Mapping[str, object],
    ) -> ChatGeneration:
        """Generate one response without depending on HTTP transport types."""

    def stream(
        self,
        query: str,
        *,
        profile: str,
        user_context: Mapping[str, object],
    ) -> AsyncIterator[ChatStreamEvent]:
        """Yield provider-neutral frames; the inbound adapter owns ``[DONE]``."""
