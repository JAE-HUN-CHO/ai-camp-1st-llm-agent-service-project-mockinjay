"""Application use cases for the approved Phase-2 Chat slice."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass

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
    actor: ActorContext
    query: str
    profile: str = "general"
    client_message_id: str | None = None


@dataclass(frozen=True, slots=True)
class PreparedChatStream:
    command: ChatCommand
    actor: ActorContext
    user_context: Mapping[str, object]
    emergency: bool = False


class SendChatMessage:
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
        terminal_event: ChatStreamEvent | None = None
        try:
            async for event in self._generator.stream(
                prepared.command.query,
                profile=prepared.command.profile,
                user_context=prepared.user_context,
            ):
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
                    accumulated = event.content or accumulated
                    completed = True
                    terminal_event = event
                    break
                elif event.status == "streaming":
                    accumulated += event.content
                elif event.status == "partial":
                    accumulated = event.content or accumulated
                elif event.status == "new_message":
                    accumulated = (
                        f"{accumulated}\n\n{event.content}"
                        if accumulated
                        else event.content
                    )
                yield event
        except Exception:
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
