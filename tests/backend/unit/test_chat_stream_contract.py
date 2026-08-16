"""Provider-independent HTTP contract tests for chat streaming."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.api import chat


class _FakeContextManager:
    def __init__(self) -> None:
        self.saved: list[dict] = []

    async def get_user_context(self, _user_id: str) -> dict:
        return {}

    async def save_conversation(self, user_id: str, session_id: str, agent_type: str, user_input: str, agent_response: str, room_id: str | None = None) -> None:
        self.saved.append(
            {
                "user_id": user_id,
                "session_id": session_id,
                "agent_type": agent_type,
                "user_input": user_input,
                "agent_response": agent_response,
                "room_id": room_id,
            }
        )

    async def analyze_and_update_context(self, _user_id: str) -> None:
        return None

    async def connect(self) -> None:
        return None

    @property
    def db(self):
        class _Collection:
            async def find_one(self, query):
                if query.get("room_id") == "room-1" and query.get("user_id") == "user-1":
                    return {"room_id": "room-1", "user_id": "user-1"}
                return None

        return {"chat_rooms": _Collection()}


class _FakeRouter:
    async def process_stream(self, _request):
        yield {"status": "streaming", "content": "hello ", "agent_type": "test"}
        yield {"status": "complete", "content": "hello world", "agent_type": "test"}


class _FailingRouter:
    async def process_stream(self, _request):
        yield {"status": "streaming", "content": "unsafe partial", "agent_type": "test"}
        raise RuntimeError("provider failed")


class _NaturalCompletionRouter:
    async def process_stream(self, _request):
        yield {"status": "new_message", "content": "first", "agent_type": "research_paper"}
        yield {"status": "new_message", "content": "second", "agent_type": "research_paper"}


class _ErrorFrameRouter:
    async def process_stream(self, _request):
        yield {"status": "streaming", "content": "unsafe partial", "agent_type": "test"}
        yield {"status": "error", "error": "provider failed", "agent_type": "test"}


def _chat_app(manager, router, *, authenticated: bool = True) -> FastAPI:
    context_system = SimpleNamespace(
        session_manager=SimpleNamespace(
            get_session=lambda session_id: {
                "session_id": session_id,
                "user_id": "user-1",
                "room_id": "room-1",
            }
        ),
        context_engineer=SimpleNamespace(
            db_manager=manager,
            get_user_context=manager.get_user_context,
        ),
    )
    app = FastAPI()
    app.state.context_system = context_system
    app.state.agent_runtime = SimpleNamespace(router_agent=router)

    if authenticated:
        @app.middleware("http")
        async def set_authenticated_user(request, call_next):
            request.state.user_id = "user-1"
            return await call_next(request)

    app.include_router(chat.router)
    return app


def test_chat_stream_emits_sse_and_persists_final_response(monkeypatch) -> None:
    manager = _FakeContextManager()
    context_system = SimpleNamespace(
        session_manager=SimpleNamespace(
            get_session=lambda session_id: {
                "session_id": session_id,
                "user_id": "user-1",
                "room_id": "room-1",
            }
        ),
        context_engineer=SimpleNamespace(db_manager=manager, get_user_context=manager.get_user_context),
    )
    runtime = SimpleNamespace(router_agent=_FakeRouter())

    app = FastAPI()
    app.state.context_system = context_system
    app.state.agent_runtime = runtime

    @app.middleware("http")
    async def set_authenticated_user(request, call_next):
        request.state.user_id = "user-1"
        return await call_next(request)

    app.include_router(chat.router)
    monkeypatch.setattr(chat, "get_agent_runtime", lambda _request: runtime)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/stream",
            json={"query": "hello", "session_id": "session-1", "user_id": "user-1", "room_id": "room-1"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"status": "streaming"' in response.text
    assert '"status": "complete"' in response.text
    assert response.text.endswith("data: [DONE]\n\n")
    assert manager.saved == [
        {
            "user_id": "user-1",
            "session_id": "session-1",
            "agent_type": "test",
            "user_input": "hello",
            "agent_response": "hello world",
            "room_id": "room-1",
        }
    ]


def test_chat_stream_requires_query() -> None:
    app = FastAPI()
    app.state.context_system = SimpleNamespace(
        session_manager=SimpleNamespace(get_session=lambda _session_id: None),
        context_engineer=SimpleNamespace(db_manager=_FakeContextManager()),
    )

    @app.middleware("http")
    async def set_authenticated_user(request, call_next):
        request.state.user_id = "user-1"
        return await call_next(request)

    app.include_router(chat.router)

    with TestClient(app) as client:
        response = client.post("/api/chat/stream", json={"session_id": "session-1"})

    assert response.status_code == 400
    assert "Query is required" in response.json()["detail"]


def test_failed_chat_stream_does_not_persist_partial_response(monkeypatch) -> None:
    manager = _FakeContextManager()
    runtime = SimpleNamespace(router_agent=_FailingRouter())
    app = _chat_app(manager, runtime.router_agent)
    monkeypatch.setattr(chat, "get_agent_runtime", lambda _request: runtime)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/stream",
            json={
                "query": "hello",
                "session_id": "session-1",
                "user_id": "user-1",
                "room_id": "room-1",
            },
        )

    assert "unsafe partial" in response.text
    assert response.text.index("unsafe partial") < response.text.index('"status":"error"')
    assert '"status":"error"' in response.text
    assert response.text.endswith("data: [DONE]\n\n")
    assert manager.saved == []


def test_naturally_completed_chat_stream_emits_terminal_and_persists(monkeypatch) -> None:
    manager = _FakeContextManager()
    runtime = SimpleNamespace(router_agent=_NaturalCompletionRouter())
    app = _chat_app(manager, runtime.router_agent)
    monkeypatch.setattr(chat, "get_agent_runtime", lambda _request: runtime)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/stream",
            json={
                "query": "hello",
                "session_id": "default",
                "user_id": "user-1",
                "room_id": "room-1",
            },
        )

    assert '"status": "complete"' in response.text
    assert response.text.index('"status": "complete"') < response.text.index("data: [DONE]")
    assert manager.saved[0]["session_id"] == "room-1"
    assert manager.saved[0]["agent_response"] == "first\n\nsecond"


def test_explicit_error_frame_does_not_emit_success_or_persist(monkeypatch) -> None:
    manager = _FakeContextManager()
    runtime = SimpleNamespace(router_agent=_ErrorFrameRouter())
    app = _chat_app(manager, runtime.router_agent)
    monkeypatch.setattr(chat, "get_agent_runtime", lambda _request: runtime)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/stream",
            json={
                "query": "hello",
                "session_id": "session-1",
                "user_id": "user-1",
                "room_id": "room-1",
            },
        )

    assert '"status": "error"' in response.text
    assert '"status": "complete"' not in response.text
    assert manager.saved == []


def test_proxy_post_authenticates_before_rejecting_invalid_json(monkeypatch) -> None:
    manager = _FakeContextManager()
    app = _chat_app(manager, _FakeRouter(), authenticated=False)

    class _NoForwardClient:
        async def request(self, **_kwargs):
            raise AssertionError("unauthenticated payload must not be forwarded")

    monkeypatch.setattr(chat, "client", _NoForwardClient())
    with TestClient(app) as client:
        response = client.post(
            "/api/chat/research/events",
            content=b"not-json",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 401


def test_proxy_post_rejects_invalid_json_without_forwarding(monkeypatch) -> None:
    manager = _FakeContextManager()
    app = _chat_app(manager, _FakeRouter())

    class _NoForwardClient:
        async def request(self, **_kwargs):
            raise AssertionError("invalid JSON must not be forwarded")

    monkeypatch.setattr(chat, "client", _NoForwardClient())
    with TestClient(app) as client:
        response = client.post(
            "/api/chat/research/events",
            content=b"not-json",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 400
