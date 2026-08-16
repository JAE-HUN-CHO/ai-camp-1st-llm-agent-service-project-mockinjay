"""Fake-adapter tests for the Phase-2 Chat application core."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.core.actor import ActorContext
from app.core.emergency_safety import emergency_safety_policy
from app.features.chat.application import ChatCommand, SendChatMessage, StreamChatMessage
from app.features.chat.domain import (
    ChatAccessDenied,
    ChatGeneration,
    ChatMessage,
    ChatStreamEvent,
)


class FakeRepository:
    def __init__(self, *, reject: bool = False) -> None:
        self.reject = reject
        self.authorize_calls = 0
        self.context_calls = 0
        self.saved: list[ChatMessage] = []

    async def authorize_actor(self, actor: ActorContext) -> ActorContext:
        """
        행위자의 접근 권한을 확인하고 정규화된 컨텍스트를 반환합니다.
        
        Parameters:
        	actor (ActorContext): 권한을 확인할 행위자의 컨텍스트
        
        Returns:
        	ActorContext: 세션 식별자가 정규화된 행위자 컨텍스트
        
        Raises:
        	ChatAccessDenied: 행위자의 접근이 거부된 경우
        """
        self.authorize_calls += 1
        if self.reject:
            raise ChatAccessDenied("cross-user")
        return ActorContext(
            user_id=actor.user_id,
            room_id=actor.room_id,
            session_id=actor.room_id or f"default:{actor.user_id}",
        )

    async def get_user_context(self, _actor: ActorContext) -> dict[str, object]:
        """
        사용자에게 제공할 수 있도록 제한된 사용자 컨텍스트를 반환합니다.
        
        Returns:
        	dict[str, object]: 요약 정보와 키워드를 포함한 비식별화된 사용자 컨텍스트
        """
        self.context_calls += 1
        return {"summary": "redacted", "keywords": []}

    async def save_message(self, message: ChatMessage) -> None:
        """저장할 채팅 메시지를 기록합니다.
        
        Parameters:
        	message (ChatMessage): 저장할 채팅 메시지
        """
        self.saved.append(message)


class FakeGenerator:
    def __init__(self, events: list[ChatStreamEvent] | None = None) -> None:
        """스트리밍 응답에 사용할 이벤트를 설정하고 생성 및 스트리밍 호출 횟수를 초기화합니다.
        
        Parameters:
        	events (list[ChatStreamEvent] | None): 스트리밍 시 반환할 이벤트 목록입니다. 지정하지 않으면 기본 이벤트를 사용합니다.
        """
        self.generate_calls = 0
        self.stream_calls = 0
        self._events = events or [
            ChatStreamEvent("streaming", "hello ", "ollama_rag"),
            ChatStreamEvent("streaming", "world", "ollama_rag"),
        ]

    async def generate(self, query, *, profile, user_context) -> ChatGeneration:
        """
        일반 채팅 요청에 대한 고정된 생성 결과를 반환합니다.
        
        Parameters:
        	query: 생성할 질문입니다.
        	profile: 사용자 프로필입니다.
        	user_context: 생성에 사용할 사용자 컨텍스트입니다.
        
        Returns:
        	ChatGeneration: `"answer"`와 Ollama 제공자 메타데이터를 포함한 생성 결과입니다.
        """
        self.generate_calls += 1
        assert query == "일반 질문"
        assert profile == "patient"
        assert user_context["summary"] == "redacted"
        return ChatGeneration(
            answer="answer",
            metadata={"provider": "ollama"},
        )

    async def stream(self, query, *, profile, user_context) -> AsyncIterator[ChatStreamEvent]:
        """
        구성된 채팅 스트리밍 이벤트를 순서대로 제공합니다.
        
        Parameters:
        	query: 스트리밍 생성에 사용할 질문입니다.
        	profile: 사용자 프로필입니다.
        	user_context: 생성에 사용할 사용자 컨텍스트입니다.
        
        Returns:
        	ChatStreamEvent: 구성된 스트리밍 이벤트입니다.
        """
        self.stream_calls += 1
        assert query == "일반 질문"
        assert profile == "patient"
        assert user_context["summary"] == "redacted"
        for event in self._events:
            yield event


def command(query: str = "일반 질문") -> ChatCommand:
    """
    고정된 테스트 사용자와 환자 프로필을 사용하는 채팅 명령을 생성합니다.
    
    Parameters:
    	query (str): 채팅 질문입니다. 기본값은 "일반 질문"입니다.
    
    Returns:
    	ChatCommand: 고정된 사용자, 방, 세션 및 환자 프로필을 포함한 채팅 명령입니다.
    """
    return ChatCommand(
        actor=ActorContext(user_id="user-a", room_id="room-a", session_id="room-a"),
        query=query,
        profile="patient",
    )


@pytest.mark.asyncio
async def test_send_success_authorizes_before_generator_and_saves() -> None:
    repository = FakeRepository()
    generator = FakeGenerator()
    use_case = SendChatMessage(repository, generator, emergency_safety_policy)

    result = await use_case.execute(command())

    assert result.answer == "answer"
    assert result.metadata["provider"] == "ollama"
    assert repository.authorize_calls == 1
    assert repository.context_calls == 1
    assert generator.generate_calls == 1
    assert repository.saved[0].actor.session_id == "room-a"


@pytest.mark.asyncio
async def test_emergency_has_zero_repository_model_and_write_calls() -> None:
    repository = FakeRepository()
    generator = FakeGenerator()
    use_case = SendChatMessage(repository, generator, emergency_safety_policy)

    result = await use_case.execute(command("숨이 안 쉬어져요"))

    assert result.metadata["is_emergency"] is True
    assert repository.authorize_calls == 0
    assert repository.context_calls == 0
    assert generator.generate_calls == 0
    assert repository.saved == []


@pytest.mark.asyncio
async def test_cross_user_failure_has_zero_generator_and_write_calls() -> None:
    repository = FakeRepository(reject=True)
    generator = FakeGenerator()
    use_case = SendChatMessage(repository, generator, emergency_safety_policy)

    with pytest.raises(ChatAccessDenied):
        await use_case.execute(command())

    assert repository.authorize_calls == 1
    assert repository.context_calls == 0
    assert generator.generate_calls == 0
    assert repository.saved == []


@pytest.mark.asyncio
async def test_stream_natural_eof_emits_success_terminal_and_saves() -> None:
    repository = FakeRepository()
    generator = FakeGenerator()
    use_case = StreamChatMessage(repository, generator, emergency_safety_policy)

    prepared = await use_case.prepare(command())
    events = [event async for event in use_case.events(prepared)]

    assert [event.status for event in events] == ["streaming", "streaming", "complete"]
    assert events[-1].content == "hello world"
    assert repository.saved[0].answer == "hello world"


@pytest.mark.asyncio
async def test_partial_snapshot_is_preserved_when_provider_reaches_natural_eof() -> None:
    repository = FakeRepository()
    generator = FakeGenerator(
        [ChatStreamEvent("partial", "latest snapshot", "ollama_rag")]
    )
    use_case = StreamChatMessage(repository, generator, emergency_safety_policy)

    prepared = await use_case.prepare(command())
    events = [event async for event in use_case.events(prepared)]

    assert [event.status for event in events] == ["partial", "complete"]
    assert events[-1].content == "latest snapshot"
    assert repository.saved[0].answer == "latest snapshot"


@pytest.mark.asyncio
async def test_error_frame_stops_later_complete_and_never_saves() -> None:
    repository = FakeRepository()
    generator = FakeGenerator(
        [
            ChatStreamEvent("streaming", "partial", "ollama_rag"),
            ChatStreamEvent("error", error="local failure", agent_type="ollama_rag"),
            ChatStreamEvent("complete", "must not win", "ollama_rag"),
        ]
    )
    use_case = StreamChatMessage(repository, generator, emergency_safety_policy)

    prepared = await use_case.prepare(command())
    events = [event async for event in use_case.events(prepared)]

    assert [event.status for event in events] == ["streaming", "error"]
    assert repository.saved == []


@pytest.mark.asyncio
async def test_cancel_emits_terminal_and_has_zero_write() -> None:
    repository = FakeRepository()
    generator = FakeGenerator()
    use_case = StreamChatMessage(repository, generator, emergency_safety_policy)
    prepared = await use_case.prepare(command())

    async def cancelled() -> bool:
        """취소 상태를 나타내는 값을 생성합니다.
        
        Returns:
        	bool: 항상 `True`.
        """
        return True

    events = [
        event
        async for event in use_case.events(prepared, is_cancelled=cancelled)
    ]

    assert [event.status for event in events] == ["cancelled"]
    assert repository.saved == []


@pytest.mark.asyncio
async def test_disconnect_after_partial_emits_cancelled_and_has_zero_write() -> None:
    repository = FakeRepository()
    generator = FakeGenerator()
    use_case = StreamChatMessage(repository, generator, emergency_safety_policy)
    prepared = await use_case.prepare(command())
    checks = 0

    async def disconnected() -> bool:
        nonlocal checks
        checks += 1
        return checks > 1

    events = [
        event
        async for event in use_case.events(prepared, is_cancelled=disconnected)
    ]

    assert [event.status for event in events] == ["streaming", "cancelled"]
    assert repository.saved == []


@pytest.mark.asyncio
async def test_empty_provider_eof_is_terminal_error_and_has_zero_write() -> None:
    repository = FakeRepository()
    generator = FakeGenerator([])
    generator._events = []
    use_case = StreamChatMessage(repository, generator, emergency_safety_policy)

    prepared = await use_case.prepare(command())
    events = [event async for event in use_case.events(prepared)]

    assert [event.status for event in events] == ["error"]
    assert repository.saved == []


@pytest.mark.asyncio
async def test_emergency_stream_has_zero_repository_provider_and_write_calls() -> None:
    repository = FakeRepository()
    generator = FakeGenerator()
    use_case = StreamChatMessage(repository, generator, emergency_safety_policy)

    prepared = await use_case.prepare(command("죽고 싶어요"))
    events = [event async for event in use_case.events(prepared)]

    assert [event.status for event in events] == ["complete"]
    assert events[0].attributes["is_emergency"] is True
    assert repository.authorize_calls == 0
    assert repository.context_calls == 0
    assert generator.stream_calls == 0
    assert repository.saved == []
