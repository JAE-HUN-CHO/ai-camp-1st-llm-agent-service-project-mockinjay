"""Application use cases for the approved Phase-2 Chat slice."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass, replace

from app.core.actor import ActorContext
from app.core.emergency_safety import EMERGENCY_RESPONSE
from app.features.chat.domain import (
    ChatGeneration,
    ChatMessage,
    ChatPersistenceError,
    ChatSafetyPolicy,
    ChatStreamEvent,
)
from app.features.chat.ports import ChatGenerator, ChatRepository


@dataclass(frozen=True, slots=True)
class ChatCommand:
    """Carry an actor-bound Chat request into the application layer."""

    actor: ActorContext
    query: str
    profile: str = "general"
    client_message_id: str | None = None


@dataclass(frozen=True, slots=True)
class PreparedChatStream:
    """Hold an authorized stream request without transport-layer state."""

    command: ChatCommand
    actor: ActorContext
    user_context: Mapping[str, object]
    emergency: bool = False


def accumulate_chat_stream_content(
    accumulated: str,
    event: ChatStreamEvent,
) -> str:
    """Apply the frozen v1 content semantics to one provider-neutral event."""
    if event.status == "streaming":
        return accumulated + event.content
    if event.status == "partial":
        return event.content or accumulated
    if event.status == "new_message":
        return f"{accumulated}\n\n{event.content}" if accumulated else event.content
    if event.status in {"complete", "success"}:
        return event.content or accumulated
    return accumulated


class SendChatMessage:
    """Apply safety and ownership gates before non-streaming generation."""

    def __init__(
        self,
        repository: ChatRepository,
        generator: ChatGenerator,
        safety_policy: ChatSafetyPolicy,
    ) -> None:
        self._repository = repository
        self._generator = generator
        self._safety_policy = safety_policy

    async def execute(self, command: ChatCommand) -> ChatGeneration:
        """Execute one request and persist the completed turn when possible.

        Emergency requests return the Phase-0 response without repository or
        provider calls. Non-emergency requests authorize ownership before
        loading context or invoking the local generator.
        """

        decision = self._safety_policy.evaluate(command.query)
        if decision.blocked:
            return ChatGeneration(
                answer=EMERGENCY_RESPONSE,
                metadata={"provider": "emergency_pre_filter", "is_emergency": True},
                agent_type="emergency_safety",
            )

        actor = await self._repository.authorize_actor(command.actor)
        user_context = await self._repository.get_user_context(actor)
        generation = await self._generator.generate(
            command.query,
            profile=command.profile,
            user_context=user_context,
        )
        persisted = True
        try:
            await self._repository.save_message(
                ChatMessage(
                    actor=actor,
                    query=command.query,
                    answer=generation.answer,
                    agent_type=generation.agent_type,
                    client_message_id=command.client_message_id,
                )
            )
        except ChatPersistenceError:
            # Frozen v1 returns a valid provider answer even when optional
            # history persistence fails. Telemetry records the persistence bit.
            persisted = False
        return ChatGeneration(
            answer=generation.answer,
            sources=generation.sources,
            metadata=generation.metadata,
            agent_type=generation.agent_type,
            persisted=persisted,
        )


class StreamChatMessage:
    """Prepare and execute a provider-neutral Chat event stream."""

    def __init__(
        self,
        repository: ChatRepository,
        generator: ChatGenerator,
        safety_policy: ChatSafetyPolicy,
    ) -> None:
        self._repository = repository
        self._generator = generator
        self._safety_policy = safety_policy

    async def prepare(self, command: ChatCommand) -> PreparedChatStream:
        """Apply safety first, then authorize and load owner-scoped context."""

        decision = self._safety_policy.evaluate(command.query)
        if decision.blocked:
            return PreparedChatStream(
                command=command,
                actor=command.actor,
                user_context={},
                emergency=True,
            )
        actor = await self._repository.authorize_actor(command.actor)
        user_context = await self._repository.get_user_context(actor)
        return PreparedChatStream(command, actor, user_context)

    async def events(
        self,
        prepared: PreparedChatStream,
        *,
        is_cancelled: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Yield terminal-aware events and persist only successful content.

        ``error`` and ``cancelled`` are terminal failures. A provider EOF with
        accumulated content is normalized to ``complete``; an empty EOF is an
        ``error``. The HTTP adapter, not this use case, appends ``[DONE]``.
        """

        if prepared.emergency:
            yield ChatStreamEvent(
                status="complete",
                content=EMERGENCY_RESPONSE,
                agent_type="emergency_safety",
                attributes={"is_emergency": True},
            )
            return

        accumulated = ""
        agent_type = "ollama_rag"
        completed = False
        failed = False
        close_failed = False
        terminal_event: ChatStreamEvent | None = None
        provider_stream = self._generator.stream(
            prepared.command.query,
            profile=prepared.command.profile,
            user_context=prepared.user_context,
        )
        try:
            async for event in provider_stream:
                if is_cancelled is not None and await is_cancelled():
                    failed = True
                    yield ChatStreamEvent(
                        status="cancelled",
                        agent_type=agent_type,
                        attributes={"message": "Stream stopped by user"},
                    )
                    break
                if event.agent_type:
                    agent_type = event.agent_type
                if event.status in {"error", "cancelled"}:
                    failed = True
                    yield event
                    break
                if event.status in {"complete", "success"}:
                    accumulated = accumulate_chat_stream_content(accumulated, event)
                    completed = True
                    terminal_event = replace(event, content=accumulated)
                    break
                accumulated = accumulate_chat_stream_content(accumulated, event)
                yield event
        except Exception:
            failed = True
            yield ChatStreamEvent(
                status="error",
                error="local provider stream failed",
                agent_type=agent_type,
            )
        finally:
            close = getattr(provider_stream, "aclose", None)
            if close is not None:
                try:
                    await close()
                except Exception:
                    close_failed = True

        if close_failed and not failed:
            failed = True
            yield ChatStreamEvent(
                status="error",
                error="local provider stream failed",
                agent_type=agent_type,
            )

        if not failed and not completed:
            if accumulated:
                completed = True
                terminal_event = ChatStreamEvent(
                    status="complete",
                    content=accumulated,
                    agent_type=agent_type,
                )
            else:
                failed = True
                yield ChatStreamEvent(
                    status="error",
                    error="local provider stream ended without content",
                    agent_type=agent_type,
                )

        if completed and not failed:
            try:
                await self._repository.save_message(
                    ChatMessage(
                        actor=prepared.actor,
                        query=prepared.command.query,
                        answer=accumulated,
                        agent_type=agent_type,
                        client_message_id=prepared.command.client_message_id,
                    )
                )
            except ChatPersistenceError:
                pass
            except Exception:
                yield ChatStreamEvent(
                    status="error",
                    error="chat history authorization failed",
                    agent_type=agent_type,
                )
                return
            if terminal_event is not None:
                yield terminal_event
