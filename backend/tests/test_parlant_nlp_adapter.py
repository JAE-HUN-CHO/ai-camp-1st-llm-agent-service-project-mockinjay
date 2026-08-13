import asyncio

import pytest

from Agent.research_paper.server.parlant_nlp_adapter import (
    ParlantGenerationError,
    ParlantHealthcareNLPService,
    extract_json_payload,
)


@pytest.mark.parametrize(
    "response, expected",
    [
        ('{"answer": "ok"} explanation', {"answer": "ok"}),
        ('```json\n[1, 2]\n```', [1, 2]),
    ],
)
def test_extract_json_payload_accepts_wrapped_and_trailing_text(response, expected):
    assert extract_json_payload(response) == expected


def test_extract_json_payload_rejects_missing_json():
    with pytest.raises(ParlantGenerationError):
        extract_json_payload("no structured response")


def test_streaming_contract_is_explicitly_unsupported():
    service = object.__new__(ParlantHealthcareNLPService)
    assert service.supports_streaming is False
    with pytest.raises(NotImplementedError):
        asyncio.run(service.get_streaming_text_generator())
