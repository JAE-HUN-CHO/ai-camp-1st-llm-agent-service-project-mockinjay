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
        """Ollama 채팅 생성에 사용할 서비스 의존성을 초기화합니다.
        
        Parameters:
        	service (Any): 채팅 생성 및 스트리밍을 제공하는 서비스
        """
        self._service = service

    async def generate(
        self,
        query: str,
        *,
        profile: str,
        user_context: Mapping[str, object],
    ) -> ChatGeneration:
        """
        로컬 Ollama 서비스에 질의를 전달하고 채팅 생성 결과로 변환합니다.
        
        Parameters:
        	query (str): 생성할 응답에 대한 사용자 질의
        	profile (str): 응답 생성에 사용할 프로필
        	user_context (Mapping[str, object]): 응답 생성에 필요한 사용자 컨텍스트
        
        Returns:
        	ChatGeneration: 답변, 매핑 형식의 출처, 메타데이터 및 에이전트 유형을 포함한 생성 결과
        
        Raises:
        	ChatProviderTimeout: 로컬 provider의 응답이 시간 제한을 초과한 경우
        	ChatProviderUnavailable: provider 오류가 발생했거나 응답 형식이 잘못되었거나 답변이 비어 있는 경우
        """
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
        """
        로컬 채팅 제공자의 응답을 스트리밍 이벤트로 변환합니다.
        
        Returns:
        	ChatStreamEvent: 제공자 응답의 상태, 콘텐츠, 에이전트 유형, 오류 및 추가 속성을 담은 이벤트
        
        Raises:
        	ChatProviderTimeout: 로컬 제공자 응답이 시간 제한을 초과한 경우
        	ChatProviderUnavailable: 로컬 제공자를 사용할 수 없거나 처리 중 예외가 발생한 경우
        """
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
