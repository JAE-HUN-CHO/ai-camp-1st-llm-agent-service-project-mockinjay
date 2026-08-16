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
        self.authorize_calls += 1
        if self.reject:
            raise ChatAccessDenied("cross-user")
        return ActorContext(
            user_id=actor.user_id,
            room_id=actor.room_id,
            session_id=actor.room_id or f"default:{actor.user_id}",
        )

    async def get_user_context(self, _actor: ActorContext) -> dict[str, object]:
        self.context_calls += 1
        return {"summary": "redacted", "keywords": []}

    async def save_message(self, message: ChatMessage) -> None:
        self.saved.append(message)


class FakeGenerator:
    def __init__(
        self,
        events: list[ChatStreamEvent] | None = None,
        *,
        close_failure: bool = False,
    ) -> None:
        self.generate_calls = 0
        self.stream_calls = 0
        self.closed = False
        self.close_failure = close_failure
        self._events = (
            events
            if events is not None
            else [
                ChatStreamEvent("streaming", "hello ", "ollama_rag"),
                ChatStreamEvent("streaming", "world", "ollama_rag"),
            ]
        )

    async def generate(self, query, *, profile, user_context) -> ChatGeneration:
        self.generate_calls += 1
        assert query == "일반 질문"
        assert profile == "patient"
        assert user_context["summary"] == "redacted"
        return ChatGeneration(
            answer="answer",
            metadata={"provider": "ollama"},
        )

    async def stream(self, query, *, profile, user_context) -> AsyncIterator[ChatStreamEvent]:
        self.stream_calls += 1
        assert query == "일반 질문"
        assert profile == "patient"
        assert user_context["summary"] == "redacted"
        try:
            for event in self._events:
                yield event
        finally:
            self.closed = True
            if self.close_failure:
                raise RuntimeError("raw close detail")


def command(query: str = "일반 질문") -> ChatCommand:
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
    assert generator.closed is True


@pytest.mark.asyncio
async def test_terminal_without_content_reuses_accumulated_answer() -> None:
    repository = FakeRepository()
    generator = FakeGenerator(
        [
            ChatStreamEvent("streaming", "complete answer", "ollama_rag"),
            ChatStreamEvent("complete", agent_type="ollama_rag"),
        ]
    )
    use_case = StreamChatMessage(repository, generator, emergency_safety_policy)

    prepared = await use_case.prepare(command())
    events = [event async for event in use_case.events(prepared)]

    assert events[-1].status == "complete"
    assert events[-1].content == "complete answer"
    assert repository.saved[0].answer == "complete answer"


@pytest.mark.asyncio
async def test_provider_close_failure_is_terminal_error_and_has_zero_write() -> None:
    repository = FakeRepository()
    generator = FakeGenerator(
        [ChatStreamEvent("complete", "answer", "ollama_rag")],
        close_failure=True,
    )
    use_case = StreamChatMessage(repository, generator, emergency_safety_policy)

    prepared = await use_case.prepare(command())
    events = [event async for event in use_case.events(prepared)]

    assert [event.status for event in events] == ["error"]
    assert events[0].error == "local provider stream failed"
    assert "raw close detail" not in str(events[0].as_payload())
    assert repository.saved == []


@pytest.mark.asyncio
async def test_cancel_emits_terminal_and_has_zero_write() -> None:
    repository = FakeRepository()
    generator = FakeGenerator()
    use_case = StreamChatMessage(repository, generator, emergency_safety_policy)
    prepared = await use_case.prepare(command())

    async def cancelled() -> bool:
        return True

    events = [
        event
        async for event in use_case.events(prepared, is_cancelled=cancelled)
    ]

    assert [event.status for event in events] == ["cancelled"]
    assert repository.saved == []
    assert generator.closed is True


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
