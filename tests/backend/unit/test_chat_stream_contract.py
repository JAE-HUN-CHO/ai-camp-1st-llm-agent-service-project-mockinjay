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


class _FakeRouter:
    async def process_stream(self, _request):
        yield {"status": "streaming", "content": "hello ", "agent_type": "test"}
        yield {"status": "complete", "content": "hello world", "agent_type": "test"}


def test_chat_stream_emits_sse_and_persists_final_response(monkeypatch) -> None:
    manager = _FakeContextManager()
    context_system = SimpleNamespace(
        session_manager=SimpleNamespace(get_session=lambda _session_id: None),
        context_engineer=SimpleNamespace(db_manager=manager, get_user_context=manager.get_user_context),
    )
    runtime = SimpleNamespace(router_agent=_FakeRouter())

    app = FastAPI()
    app.state.context_system = context_system
    app.state.agent_runtime = runtime
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
    app.include_router(chat.router)

    with TestClient(app) as client:
        response = client.post("/api/chat/stream", json={"session_id": "session-1"})

    assert response.status_code == 400
    assert "Query is required" in response.json()["detail"]
