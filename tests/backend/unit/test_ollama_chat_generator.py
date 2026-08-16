"""Failure sanitization and shape checks for the Chat Ollama adapter."""

from collections.abc import AsyncIterator
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.adapters.ollama.chat_generator import OllamaChatGenerator
from app.features.chat.domain import ChatProviderUnavailable


class Service:
    def __init__(
        self,
        result=None,
        *,
        failure: Exception | None = None,
        stream_event: dict | None = None,
    ) -> None:
        self.result = result
        self.failure = failure
        self.stream_event = stream_event or {"status": "complete", "content": "safe"}
        self.stream_closed = False

    async def generate(self, _query, *, profile, user_context):
        if self.failure is not None:
            raise self.failure
        return self.result

    async def stream(self, _query, *, profile, user_context) -> AsyncIterator[dict]:
        try:
            if self.failure is not None:
                raise self.failure
            yield self.stream_event
        finally:
            self.stream_closed = True


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


@pytest.mark.asyncio
async def test_stream_exposes_only_frozen_attributes_and_sanitizes_error() -> None:
    service = Service(
        stream_event={
            "status": "error",
            "error": "raw provider detail",
            "retrieved_count": 2,
            "private_prompt": "must not escape",
        }
    )
    generator = OllamaChatGenerator(service)

    events = [
        event
        async for event in generator.stream(
            "query",
            profile="general",
            user_context={},
        )
    ]

    assert events[0].error == "local provider stream failed"
    assert events[0].attributes == {"retrieved_count": 2}
    assert service.stream_closed is True


@pytest.mark.asyncio
async def test_stream_closes_delegated_iterator_on_consumer_exit() -> None:
    service = Service()
    stream = OllamaChatGenerator(service).stream(
        "query",
        profile="general",
        user_context={},
    )

    await anext(stream)
    await stream.aclose()

    assert service.stream_closed is True
