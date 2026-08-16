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
        """채팅 메시지 생성에 필요한 저장소, 생성기 및 안전성 정책을 초기화합니다.
        
        Parameters:
        	repository (ChatRepository): 채팅 메시지 저장소
        	generator (ChatGenerator): 채팅 응답 생성기
        	safety_policy (ChatSafetyPolicy): 질의 안전성 평가 정책
        """
        self._repository = repository
        self._generator = generator
        self._safety_policy = safety_policy

    async def execute(self, command: ChatCommand) -> ChatGeneration:
        """
        쿼리를 안전성 정책에 따라 평가하고 채팅 응답을 생성합니다.
        
        차단된 쿼리에는 긴급 응답을 반환하며, 그 외의 응답은 대화 기록 저장을 시도합니다. 선택적 저장에 실패해도 생성된 응답을 반환하고 저장 상태를 결과에 표시합니다.
        
        Parameters:
        	command (ChatCommand): 행위자, 쿼리, 프로필 및 선택적 클라이언트 메시지 식별자를 포함한 채팅 명령
        
        Returns:
        	ChatGeneration: 생성된 답변, 출처, 메타데이터, 에이전트 유형 및 메시지 저장 성공 여부
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
    def __init__(
        self,
        repository: ChatRepository,
        generator: ChatGenerator,
        safety_policy: ChatSafetyPolicy,
    ) -> None:
        """채팅 메시지 생성에 필요한 저장소, 생성기 및 안전성 정책을 초기화합니다.
        
        Parameters:
        	repository (ChatRepository): 채팅 메시지 저장소
        	generator (ChatGenerator): 채팅 응답 생성기
        	safety_policy (ChatSafetyPolicy): 질의 안전성 평가 정책
        """
        self._repository = repository
        self._generator = generator
        self._safety_policy = safety_policy

    async def prepare(self, command: ChatCommand) -> PreparedChatStream:
        """
        채팅 스트리밍을 시작하기 위한 요청 상태를 준비합니다.
        
        Parameters:
        	command (ChatCommand): 행위자, 질의, 프로필 및 선택적 클라이언트 메시지 식별자를 포함하는 채팅 명령
        
        Returns:
        	PreparedChatStream: 안전성 평가 결과와 인증된 행위자 및 사용자 컨텍스트를 포함하는 스트리밍 준비 상태
        """
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
        """
        채팅 응답 생성 과정을 스트리밍 이벤트로 전달합니다.
        
        안전성 차단 요청은 긴급 완료 이벤트로 처리하며, 그 외 요청은 생성기 이벤트를
        전달하고 응답을 완료한 경우 채팅 기록을 저장합니다. 생성기 오류, 취소, 콘텐츠
        없이 종료된 스트림 및 복구할 수 없는 저장 오류는 오류 이벤트로 나타냅니다.
        
        Parameters:
        	prepared (PreparedChatStream): 인증 및 사용자 컨텍스트가 준비된 채팅 스트림 상태
        	is_cancelled (Callable[[], Awaitable[bool]] | None): 스트림 취소 여부를 확인하는 비동기 콜백
        
        Returns:
        	AsyncIterator[ChatStreamEvent]: 채팅 생성 상태와 콘텐츠를 나타내는 스트리밍 이벤트
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
