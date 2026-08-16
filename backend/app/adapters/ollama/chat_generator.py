"""Ollama/Mongo-grounded implementation of the Chat generator port."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx

from app.adapters.ollama.client import OllamaProviderError
from app.features.chat.domain import (
    ChatGeneration,
    ChatProviderTimeout,
    ChatProviderUnavailable,
    ChatStreamEvent,
)


class OllamaChatGenerator:
    """Translate the existing local service into the consumer-owned port."""

    def __init__(self, service: Any) -> None:
        self._service = service

    async def generate(
        self,
        query: str,
        *,
        profile: str,
        user_context: Mapping[str, object],
    ) -> ChatGeneration:
        try:
            result = await self._service.generate(
                query,
                profile=profile,
                user_context=user_context,
            )
        except (TimeoutError, asyncio.TimeoutError, httpx.TimeoutException) as exc:
            raise ChatProviderTimeout("local provider timed out") from exc
        except (OllamaProviderError, httpx.HTTPError, RuntimeError) as exc:
            raise ChatProviderUnavailable("local provider is unavailable") from exc
        except Exception as exc:
            raise ChatProviderUnavailable("local provider is unavailable") from exc

        if not isinstance(result, Mapping):
            raise ChatProviderUnavailable("local provider returned an invalid response")
        answer = str(result.get("answer") or "")
        if not answer:
            raise ChatProviderUnavailable("local provider returned an empty response")
        sources = result.get("sources") or []
        metadata = result.get("metadata")
        return ChatGeneration(
            answer=answer,
            sources=tuple(source for source in sources if isinstance(source, Mapping)),
            metadata=metadata if isinstance(metadata, Mapping) else {},
            agent_type="ollama_rag",
        )

    async def stream(
        self,
        query: str,
        *,
        profile: str,
        user_context: Mapping[str, object],
    ) -> AsyncIterator[ChatStreamEvent]:
        try:
            async for raw in self._service.stream(
                query,
                profile=profile,
                user_context=user_context,
            ):
                if isinstance(raw, Mapping):
                    status = str(raw.get("status") or "streaming")
                    content = str(
                        raw.get("content")
                        or raw.get("answer")
                        or raw.get("response")
                        or ""
                    )
                    attributes = {
                        key: value
                        for key, value in raw.items()
                        if key
                        not in {
                            "status",
                            "content",
                            "answer",
                            "response",
                            "agent_type",
                            "error",
                        }
                    }
                    yield ChatStreamEvent(
                        status=status,
                        content=content,
                        agent_type=str(raw.get("agent_type") or "ollama_rag"),
                        error=str(raw["error"]) if raw.get("error") else None,
                        attributes=attributes,
                    )
                else:
                    yield ChatStreamEvent(
                        status="streaming",
                        content=str(raw),
                        agent_type="ollama_rag",
                    )
        except (TimeoutError, asyncio.TimeoutError, httpx.TimeoutException) as exc:
            raise ChatProviderTimeout("local provider timed out") from exc
        except (OllamaProviderError, httpx.HTTPError, RuntimeError) as exc:
            raise ChatProviderUnavailable("local provider is unavailable") from exc
        except Exception as exc:
            raise ChatProviderUnavailable("local provider is unavailable") from exc
