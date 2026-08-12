from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.api import chat


class _Context:
    def __init__(self):
        self.saved = []
        self.db_manager = self

    async def get_user_context(self, _user_id):
        return {}

    async def save_conversation(self, *args):
        self.saved.append(args)

    async def analyze_and_update_context(self, _user_id):
        return None


class _Service:
    async def generate(self, query, *, profile, user_context):
        assert query == "혈압 관리"
        assert profile == "patient"
        return {
            "answer": "실제 Ollama 답변",
            "sources": [{"title": "근거"}],
            "metadata": {"provider": "ollama", "retrieved_count": 1},
        }

    async def stream(self, query, *, profile, user_context):
        yield {"status": "processing", "content": "검색 중"}
        yield {"status": "streaming", "content": "실제 "}
        yield {"status": "streaming", "content": "스트림"}


def _app(context):
    app = FastAPI()
    app.state.context_system = SimpleNamespace(
        session_manager=SimpleNamespace(get_session=lambda _session_id: None),
        context_engineer=context,
    )

    @app.middleware("http")
    async def authenticate(request, call_next):
        request.state.user_id = "user-1"
        return await call_next(request)

    app.include_router(chat.router)
    return app


def test_message_uses_application_ollama_service(monkeypatch):
    context = _Context()
    runtime = SimpleNamespace(chat_service=_Service())
    monkeypatch.setattr(chat, "get_agent_runtime", lambda _request: runtime)

    with TestClient(_app(context)) as client:
        response = client.post(
            "/api/chat/message",
            json={"query": "혈압 관리", "session_id": "s1", "user_profile": "patient"},
        )

    assert response.status_code == 200
    assert response.json()["content"] == "실제 Ollama 답변"
    assert response.json()["metadata"]["retrieved_count"] == 1
    assert context.saved[0][3:5] == ("혈압 관리", "실제 Ollama 답변")


def test_stream_uses_application_ollama_service(monkeypatch):
    context = _Context()
    runtime = SimpleNamespace(chat_service=_Service())
    monkeypatch.setattr(chat, "get_agent_runtime", lambda _request: runtime)

    with TestClient(_app(context)) as client:
        response = client.post(
            "/api/chat/stream",
            json={"query": "혈압 관리", "session_id": "s1", "user_profile": "patient"},
        )

    assert response.status_code == 200
    assert '"status": "processing"' in response.text
    assert '"content": "실제 "' in response.text
    assert response.text.endswith("data: [DONE]\n\n")
    assert context.saved[0][3:5] == ("혈압 관리", "실제 스트림")
