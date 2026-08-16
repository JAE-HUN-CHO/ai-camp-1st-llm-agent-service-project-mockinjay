"""Fail-closed evidence and SSE contract tests for Phase-1 scripts."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_architecture_dependencies
from check_architecture_dependencies import _matches_module, imports
from check_artifact_pii import main as pii_main
from smoke_api_chat import parse_sse_line, serialize_stream_evidence
from smoke_common import ensure_redacted, require_local_http
from smoke_parlant_http import _discover, _event_summary
from verification_manifest import run_command


@pytest.mark.parametrize(
    "url",
    ["https://127.0.0.1:8000", "http://example.com:8000", "http://user:pass@127.0.0.1:8000"],
)
def test_smoke_rejects_nonlocal_or_credentialed_urls(url: str) -> None:
    with pytest.raises(ValueError):
        require_local_http(url)


def test_sse_done_is_distinct_from_terminal_success() -> None:
    assert parse_sse_line('data: {"status":"complete","agent_type":"ollama_rag"}') == (
        "frame",
        {"status": "complete", "agent_type": "ollama_rag"},
    )
    assert parse_sse_line("data: [DONE]") == ("done", None)
    assert parse_sse_line("data:[DONE]") == ("done", None)


def test_stream_evidence_keeps_terminal_and_done_on_separate_lines() -> None:
    evidence = serialize_stream_evidence(
        [{"status": "complete", "agent_identity": "ollama_rag"}]
    )

    assert evidence.splitlines() == [
        '{"status": "complete", "agent_identity": "ollama_rag"}',
        '{"transport_done": true}',
    ]


def test_event_evidence_hashes_content_without_storing_raw_text() -> None:
    summary = _event_summary(
        {"id": "evt-1", "offset": 2, "kind": "message", "source": "ai_agent", "data": {"message": "private response"}}
    )
    assert summary["id"] == "evt-1"
    assert summary["content"]["bytes"] == len("private response")
    assert "private response" not in str(summary)


def test_evidence_writer_rejects_pii_canaries_and_credentials() -> None:
    for value in ("health-canary-ckd3", "patient@example.com", "Bearer secret-token"):
        with pytest.raises(ValueError):
            ensure_redacted({"value": value})


def test_pii_scan_fails_closed_for_missing_and_empty_directories(
    monkeypatch, tmp_path
) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setattr(sys, "argv", ["check_artifact_pii.py", str(missing)])
    assert pii_main() == 1

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(sys, "argv", ["check_artifact_pii.py", str(empty)])
    assert pii_main() == 1


def test_relative_imports_and_module_boundaries_are_enforced(
    monkeypatch, tmp_path
) -> None:
    app = tmp_path / "app"
    module = app / "features" / "chat" / "domain.py"
    module.parent.mkdir(parents=True)
    module.write_text("from ...db import connection\n", encoding="utf-8")
    monkeypatch.setattr(check_architecture_dependencies, "APP", app)

    assert imports(module) == [(1, "app.db")]
    assert _matches_module("fastapi", "fastapi") is True
    assert _matches_module("fastapi.routing", "fastapi") is True
    assert _matches_module("fastapi_helpers", "fastapi") is False


def test_verification_output_must_be_inside_artifact_directory(tmp_path) -> None:
    with pytest.raises(ValueError, match="inside artifact_dir"):
        run_command(tmp_path / "artifacts", tmp_path / "outside.txt", ["true"])


class _DiscoveryResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _DiscoveryClient:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.call_count = 0

    async def get(self, _url):
        self.call_count += 1
        return next(self._responses)


@pytest.mark.asyncio
async def test_parlant_discovery_requires_health_json_and_agent_identity() -> None:
    client = _DiscoveryClient(
        [
            _DiscoveryResponse(200, {"status": "healthy"}),
            _DiscoveryResponse(200, [{"id": "agent-1", "name": "CareGuide_v2"}]),
        ]
    )
    prefix, agent = await _discover(client, "http://127.0.0.1:8800", "CareGuide_v2")
    assert prefix == ""
    assert agent == {"id": "agent-1", "name": "CareGuide_v2"}
    assert client.call_count == 2


@pytest.mark.asyncio
async def test_parlant_discovery_rejects_non_json_health() -> None:
    class _NonJSONResponse(_DiscoveryResponse):
        def json(self):
            raise ValueError("not json")

    with pytest.raises(RuntimeError, match="healthz did not return JSON"):
        await _discover(
            _DiscoveryClient([_NonJSONResponse(200, None)]),
            "http://127.0.0.1:8800",
            "CareGuide_v2",
        )
