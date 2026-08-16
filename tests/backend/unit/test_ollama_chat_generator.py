"""Failure sanitization and shape checks for the Chat Ollama adapter."""

from collections.abc import AsyncIterator
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.adapters.ollama.chat_generator import OllamaChatGenerator
from app.features.chat.domain import ChatProviderUnavailable


class Service:
    def __init__(self, result=None, *, failure: Exception | None = None) -> None:
        """
        테스트 서비스의 반환 결과 또는 발생시킬 예외를 설정합니다.
        
        Parameters:
            result: 생성 요청에 사용할 결과입니다.
            failure (Exception | None): 생성 요청에서 발생시킬 예외입니다.
        """
        self.result = result
        self.failure = failure

    async def generate(self, _query, *, profile, user_context):
        """
        설정된 결과를 반환하거나 구성된 예외를 발생시킵니다.
        
        Parameters:
        	_query: 생성 요청입니다.
        	profile: 생성 프로필입니다.
        	user_context: 사용자 컨텍스트입니다.
        
        Returns:
        	구성된 생성 결과입니다.
        """
        if self.failure is not None:
            raise self.failure
        return self.result

    async def stream(self, _query, *, profile, user_context) -> AsyncIterator[dict]:
        """
        안전한 완료 응답을 스트리밍합니다.
        
        Parameters:
        	_query: 스트리밍할 질의입니다.
        	profile: 생성에 사용할 프로필입니다.
        	user_context: 사용자 관련 컨텍스트입니다.
        
        Returns:
        	dict: 완료 상태와 콘텐츠를 포함한 응답입니다.
        """
        if self.failure is not None:
            raise self.failure
        yield {"status": "complete", "content": "safe"}


@pytest.mark.asyncio
async def test_generate_rejects_malformed_or_empty_provider_results() -> None:
    for result in (None, {}, {"answer": ""}):
        generator = OllamaChatGenerator(Service(result))
        with pytest.raises(ChatProviderUnavailable):
            await generator.generate("query", profile="general", user_context={})


@pytest.mark.asyncio
async def test_generate_sanitizes_unexpected_metadata_shape() -> None:
    generator = OllamaChatGenerator(
        Service({"answer": "safe", "sources": [], "metadata": ["not", "mapping"]})
    )

    result = await generator.generate("query", profile="general", user_context={})

    assert result.answer == "safe"
    assert result.metadata == {}


@pytest.mark.asyncio
async def test_unexpected_provider_exception_is_mapped_without_raw_message() -> None:
    generator = OllamaChatGenerator(Service(failure=ValueError("raw provider detail")))

    with pytest.raises(ChatProviderUnavailable) as error:
        await generator.generate("query", profile="general", user_context={})
    assert "raw provider detail" not in str(error.value)

    with pytest.raises(ChatProviderUnavailable) as stream_error:
        async for _event in generator.stream(
            "query", profile="general", user_context={}
        ):
            pass
    assert "raw provider detail" not in str(stream_error.value)
