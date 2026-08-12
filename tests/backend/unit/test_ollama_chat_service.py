from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from backend.app.services.ollama_chat import EMERGENCY_RESPONSE, OllamaChatService


class _Cursor:
    async def to_list(self, length: int):
        return [
            {
                "_id": "paper-1",
                "title": "CKD guidance",
                "chunk_text": "혈압과 단백뇨를 정기적으로 확인합니다.",
                "score": 0.91,
            }
        ][:length]


class _Collection:
    def __init__(self):
        self.pipeline = None

    def aggregate(self, pipeline):
        self.pipeline = pipeline
        return _Cursor()


class _Database:
    def __init__(self):
        self.collection = _Collection()

    def __getitem__(self, name):
        assert name == "pubmed_embeddings"
        return self.collection


class _Completions:
    def __init__(self):
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            async def chunks():
                for text in ("근거에 ", "따르면 안내합니다."):
                    yield SimpleNamespace(
                        choices=[SimpleNamespace(delta=SimpleNamespace(content=text))]
                    )

            return chunks()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="근거 기반 답변"))]
        )


class _Client:
    def __init__(self):
        self.chat = SimpleNamespace(completions=_Completions())
        self.embeddings = SimpleNamespace(create=self.create_embedding)
        self.embedding_calls = []

    async def create_embedding(self, **kwargs):
        self.embedding_calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1] * 1536)])


@pytest.mark.asyncio
async def test_generate_embeds_retrieves_and_calls_real_chat_model():
    client = _Client()
    database = _Database()
    service = OllamaChatService(client=client, database=database)

    result = await service.generate("신장병 혈압 관리", profile="patient")

    assert result["answer"] == "근거 기반 답변"
    assert result["metadata"]["embedding_dimensions"] == 1536
    assert result["metadata"]["retrieved_count"] == 1
    assert database.collection.pipeline[0]["$vectorSearch"]["path"] == "embedding"
    assert len(database.collection.pipeline[0]["$vectorSearch"]["queryVector"]) == 1536
    assert client.chat.completions.calls[0]["messages"][1]["content"].find("혈압") >= 0


@pytest.mark.asyncio
async def test_emergency_filter_bypasses_embedding_and_model():
    client = _Client()
    service = OllamaChatService(client=client, database=_Database())

    result = await service.generate("갑자기 흉통이 있어요")

    assert result["answer"] == EMERGENCY_RESPONSE
    assert result["metadata"]["is_emergency"] is True
    assert client.embedding_calls == []
    assert client.chat.completions.calls == []


@pytest.mark.asyncio
async def test_stream_emits_processing_and_model_chunks():
    service = OllamaChatService(client=_Client(), database=_Database())

    events = [event async for event in service.stream("CKD 식단")]

    assert events[0]["status"] == "processing"
    assert [event["content"] for event in events[1:]] == ["근거에 ", "따르면 안내합니다."]
