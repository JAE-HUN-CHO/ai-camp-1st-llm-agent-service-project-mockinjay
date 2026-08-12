"""Ollama-only chat and embedding client.

The small compatibility surface intentionally mirrors the subset of the
legacy chat client that CareGuide used, but talks directly to Ollama's native
``/api/chat`` and ``/api/embed`` endpoints. No API key is read or required.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Iterable, Mapping
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import httpx

from .embedding import OllamaEmbeddingProvider, expand_vector_losslessly

OLLAMA_CHAT_MODEL = "qwen3.6:27b-mlx"
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text-v2-moe"


@dataclass
class OllamaUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class OllamaProviderError(RuntimeError):
    """Raised when the local Ollama provider cannot satisfy a request."""


def _content_and_images(content: Any) -> tuple[str, list[str]]:
    if isinstance(content, str):
        return content, []
    if not isinstance(content, Iterable):
        return str(content), []

    text_parts: list[str] = []
    images: list[str] = []
    for part in content:
        if not isinstance(part, Mapping):
            continue
        if part.get("type") == "text":
            text_parts.append(str(part.get("text", "")))
        elif part.get("type") == "image_url":
            image_url = part.get("image_url", {})
            url = image_url.get("url", "") if isinstance(image_url, Mapping) else ""
            if isinstance(url, str) and "," in url and url.startswith("data:"):
                images.append(url.split(",", 1)[1])
    return "\n".join(text_parts), images


def _message_value(message: Any, key: str, default: Any = None) -> Any:
    if isinstance(message, Mapping):
        return message.get(key, default)
    return getattr(message, key, default)


def _normalize_messages(messages: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        text, images = _content_and_images(_message_value(message, "content", ""))
        role = _message_value(message, "role") or _message_value(message, "type", "user")
        if role == "human":
            role = "user"
        elif role == "ai":
            role = "assistant"
        item: dict[str, Any] = {"role": role, "content": text}
        if images:
            item["images"] = images
        normalized.append(item)
    return normalized


def _response(payload: Mapping[str, Any]) -> SimpleNamespace:
    message = payload.get("message") or {}
    usage = OllamaUsage(
        prompt_tokens=int(payload.get("prompt_eval_count") or 0),
        completion_tokens=int(payload.get("eval_count") or 0),
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=message.get("content", "")))],
        usage=usage,
        model=payload.get("model"),
    )


def _chunk(payload: Mapping[str, Any]) -> SimpleNamespace:
    message = payload.get("message") or {}
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=message.get("content", "")))],
        usage=None,
    )


class _AsyncCompletions:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    async def create(self, *, model: str | None = None, messages: list[Mapping[str, Any]],
                     temperature: float = 0.2, max_tokens: int | None = None,
                     stream: bool = False, think: bool = False, **_: Any) -> Any:
        payload = {
            "model": model or self.client.model,
            "messages": _normalize_messages(messages),
            "stream": stream,
            "think": think,
            "options": {"temperature": temperature},
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens
        if stream:
            return self.client._stream(payload)
        response = await self.client._http.post("/api/chat", json=payload)
        response.raise_for_status()
        return _response(response.json())


class _AsyncChat:
    def __init__(self, client: OllamaClient) -> None:
        self.completions = _AsyncCompletions(client)


class _AsyncEmbeddings:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    async def create(self, *, model: str | None = None, input: str | list[str], **_: Any) -> Any:
        texts = [input] if isinstance(input, str) else list(input)
        vectors = await self.client._embedding.embed(texts)
        return SimpleNamespace(data=[SimpleNamespace(embedding=vector) for vector in vectors])


class OllamaClient:
    """Async Ollama client with the legacy chat/embedding call shape."""

    def __init__(self, model: str | None = None, embedding_model: str | None = None,
                 base_url: str | None = None, timeout: float | None = None) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", OLLAMA_CHAT_MODEL)
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        request_timeout = timeout or float(os.getenv("OLLAMA_API_TIMEOUT", "300"))
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=request_timeout)
        self._embedding = OllamaEmbeddingProvider(
            model=embedding_model or os.getenv("OLLAMA_EMBEDDING_MODEL", OLLAMA_EMBEDDING_MODEL),
            dimensions=1536,
            base_url=self.base_url,
            timeout=request_timeout,
        )
        self.chat = _AsyncChat(self)
        self.embeddings = _AsyncEmbeddings(self)

    async def _stream(self, payload: Mapping[str, Any]) -> AsyncIterator[SimpleNamespace]:
        async with self._http.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    yield _chunk(json.loads(line))

    async def close(self) -> None:
        await self._embedding.close()
        await self._http.aclose()


class OllamaSyncClient:
    """Synchronous native Ollama client for legacy sync service methods."""

    def __init__(self, model: str | None = None, base_url: str | None = None,
                 timeout: float | None = None) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", OLLAMA_CHAT_MODEL)
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout or float(os.getenv("OLLAMA_API_TIMEOUT", "300")))
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create_chat))
        self.embeddings = SimpleNamespace(create=self._create_embeddings)
        self.messages = SimpleNamespace(create=self._create_messages)

    def _create_chat(self, *, model: str | None = None, messages: list[Mapping[str, Any]],
                     temperature: float = 0.2, max_tokens: int | None = None,
                     think: bool = False, **_: Any) -> Any:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": _normalize_messages(messages),
            "stream": False,
            "think": think,
            "options": {"temperature": temperature},
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens
        response = self._http.post("/api/chat", json=payload)
        response.raise_for_status()
        return _response(response.json())

    def _create_embeddings(self, *, model: str | None = None, input: str | list[str], **_: Any) -> Any:
        texts = [input] if isinstance(input, str) else list(input)
        response = self._http.post(
            "/api/embed",
            json={"model": model or os.getenv("OLLAMA_EMBEDDING_MODEL", OLLAMA_EMBEDDING_MODEL), "input": texts},
        )
        response.raise_for_status()
        payload = response.json()
        raw_embeddings = payload.get("embeddings")
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(texts):
            raise OllamaProviderError("Ollama returned an invalid embedding batch")
        target_dimensions = int(os.getenv("OLLAMA_EMBEDDING_DIMENSIONS", "1536"))
        embeddings = [expand_vector_losslessly(vector, target_dimensions) for vector in raw_embeddings]
        return SimpleNamespace(data=[SimpleNamespace(embedding=vector) for vector in embeddings])

    def _create_messages(self, *, model: str | None = None, messages: list[Mapping[str, Any]],
                         max_tokens: int | None = None, temperature: float = 0.2,
                         system: str | None = None, **kwargs: Any) -> Any:
        prompt_messages = list(messages)
        if system:
            prompt_messages.insert(0, {"role": "system", "content": system})
        response = self._create_chat(
            model=model,
            messages=prompt_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return SimpleNamespace(content=[SimpleNamespace(text=response.choices[0].message.content)])

    def close(self) -> None:
        self._http.close()
