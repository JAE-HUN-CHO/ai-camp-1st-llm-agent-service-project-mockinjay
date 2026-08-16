"""Frozen HTTP adapter contract exercised through the hex selection."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.api import chat
from app.bootstrap.container import ChatContainer, ChatImplementation, ChatTelemetry
from app.core.actor import ActorContext
from app.core.emergency_safety import emergency_safety_policy
from app.features.chat.application import SendChatMessage, StreamChatMessage
from app.features.chat.domain import (
    ChatAccessDenied,
    ChatGeneration,
    ChatMessage,
    ChatProviderTimeout,
    ChatStreamEvent,
)


class Repository:
    def __init__(self, *, denied: bool = False) -> None:
        self.denied = denied
        self.calls = 0
        self.saved: list[ChatMessage] = []

    async def authorize_actor(self, actor: ActorContext) -> ActorContext:
        self.calls += 1
        if self.denied:
            raise ChatAccessDenied("cross-user")
        return ActorContext(
            user_id=actor.user_id,
            room_id=actor.room_id,
            session_id=actor.room_id or f"default:{actor.user_id}",
        )

    async def get_user_context(self, _actor: ActorContext):
        return {}

    async def save_message(self, message: ChatMessage) -> None:
        self.saved.append(message)


class Generator:
    def __init__(self, *, timeout: bool = False, stream_error: bool = False) -> None:
        self.timeout = timeout
        self.stream_error = stream_error
        self.calls = 0

    async def generate(self, _query, *, profile, user_context) -> ChatGeneration:
        self.calls += 1
        if self.timeout:
            raise ChatProviderTimeout("timeout")
        return ChatGeneration(
            answer="hex answer",
            sources=({"title": "source"},),
            metadata={"provider": "ollama"},
        )

    async def stream(self, _query, *, profile, user_context) -> AsyncIterator[ChatStreamEvent]:
        self.calls += 1
        yield ChatStreamEvent("processing", "progress", "ollama_rag")
        yield ChatStreamEvent("streaming", "hex ", "ollama_rag")
        if self.stream_error:
            raise RuntimeError("provider secret must not escape")
        yield ChatStreamEvent("streaming", "stream", "ollama_rag")


def app_with(repository: Repository, generator: Generator) -> FastAPI:
    application = FastAPI()
    application.state.context_system = object()
    telemetry = ChatTelemetry(ChatImplementation.HEX)
    application.state.chat_container = ChatContainer(
        implementation=ChatImplementation.HEX,
        telemetry=telemetry,
        send_chat_message=SendChatMessage(
            repository,
            generator,
            emergency_safety_policy,
        ),
        stream_chat_message=StreamChatMessage(
            repository,
            generator,
            emergency_safety_policy,
        ),
    )

    @application.middleware("http")
    async def authenticate(request, call_next):
        request.state.user_id = "user-a"
        return await call_next(request)

    application.include_router(chat.router)
    return application


def test_hex_message_preserves_frozen_json_envelope() -> None:
    repository = Repository()
    generator = Generator()
    with TestClient(app_with(repository, generator)) as client:
        response = client.post(
            "/api/chat/message",
            json={"query": "hello", "session_id": "default", "user_id": "user-a"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "answer": "hex answer",
        "content": "hex answer",
        "status": "success",
        "agent_type": "ollama_rag",
        "sources": [{"title": "source"}],
        "metadata": {"provider": "ollama"},
    }
    assert len(repository.saved) == 1


def test_hex_message_timeout_is_json_504_before_stream_headers() -> None:
    with TestClient(app_with(Repository(), Generator(timeout=True))) as client:
        response = client.post(
            "/api/chat/message",
            json={"query": "hello", "session_id": "default", "user_id": "user-a"},
        )

    assert response.status_code == 504
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "Local chat provider timeout"


def test_hex_stream_preserves_success_terminal_and_done_separation() -> None:
    repository = Repository()
    with TestClient(app_with(repository, Generator())) as client:
        response = client.post(
            "/api/chat/stream",
            json={"query": "hello", "session_id": "default", "user_id": "user-a"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"status": "complete"' in response.text
    assert response.text.index('"status": "complete"') < response.text.index("data: [DONE]")
    assert repository.saved[0].answer == "hex stream"


def test_hex_stream_provider_failure_is_terminal_error_inside_http_200() -> None:
    repository = Repository()
    with TestClient(app_with(repository, Generator(stream_error=True))) as client:
        response = client.post(
            "/api/chat/stream",
            json={"query": "hello", "session_id": "default", "user_id": "user-a"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"status": "error"' in response.text
    assert "provider secret" not in response.text
    assert '"status": "complete"' not in response.text
    assert response.text.endswith("data: [DONE]\n\n")
    assert repository.saved == []


def test_hex_cross_user_rejection_is_json_and_has_zero_generator_or_write() -> None:
    repository = Repository(denied=True)
    generator = Generator()
    with TestClient(app_with(repository, generator)) as client:
        response = client.post(
            "/api/chat/stream",
            json={"query": "hello", "session_id": "foreign", "user_id": "user-a"},
        )

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/json")
    assert generator.calls == 0
    assert repository.saved == []


def test_hex_emergency_has_zero_repository_generator_and_write_calls() -> None:
    repository = Repository()
    generator = Generator()
    with TestClient(app_with(repository, generator)) as client:
        response = client.post(
            "/api/chat/message",
            json={"query": "숨이 안 쉬어져요", "session_id": "default", "user_id": "user-a"},
        )

    assert response.status_code == 200
    assert response.json()["metadata"]["is_emergency"] is True
    assert repository.calls == 0
    assert generator.calls == 0
    assert repository.saved == []
