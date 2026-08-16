"""Fail-closed evidence and SSE contract tests for Phase-1 scripts."""

import json
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
from smoke_parlant_http import _discover, _event_summary, _prepare_error_artifact
from verification_manifest import append_command, run_command


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


def test_pii_scan_excludes_only_the_canonical_report(monkeypatch, tmp_path) -> None:
    artifact_dir = tmp_path / "artifacts"
    canonical_report = artifact_dir / "privacy" / "pii-scan.txt"
    canonical_report.parent.mkdir(parents=True)
    (artifact_dir / "http").mkdir(parents=True)
    canonical_report.write_text("health-canary-ckd3", encoding="utf-8")
    (artifact_dir / "http" / "safe.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["check_artifact_pii.py", str(artifact_dir)])
    assert pii_main() == 0

    disguised_artifact = artifact_dir / "http" / "pii-scan.txt"
    disguised_artifact.write_text("health-canary-ckd3", encoding="utf-8")
    assert pii_main() == 1

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(sys, "argv", ["check_artifact_pii.py", str(empty)])
    assert pii_main() == 1


def test_parlant_smoke_removes_stale_top_level_error_artifact(tmp_path) -> None:
    error_artifact = tmp_path / "http" / "parlant-smoke-error.json"
    error_artifact.parent.mkdir(parents=True)
    error_artifact.write_text('{"error":"previous run"}', encoding="utf-8")

    assert _prepare_error_artifact(tmp_path) == error_artifact
    assert not error_artifact.exists()


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
    marker = tmp_path / "executed"
    command = [
        sys.executable,
        "-c",
        f"from pathlib import Path; Path({str(marker)!r}).write_text('x')",
    ]
    with pytest.raises(ValueError, match="inside artifact_dir"):
        run_command(tmp_path / "artifacts", tmp_path / "outside.txt", command)
    assert not marker.exists()


def test_manifest_sha_mismatch_blocks_command_before_output(tmp_path) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "manifest.json").write_text(
        json.dumps({"git_sha": "different-head"}),
        encoding="utf-8",
    )
    marker = tmp_path / "executed"
    command = [
        sys.executable,
        "-c",
        f"from pathlib import Path; Path({str(marker)!r}).write_text('x')",
    ]

    with pytest.raises(RuntimeError, match="manifest SHA differs"):
        run_command(artifact_dir, artifact_dir / "output.txt", command)

    assert not marker.exists()
    assert not (artifact_dir / "output.txt").exists()


def test_manifest_redacts_sensitive_argv_values(tmp_path) -> None:
    artifact_dir = tmp_path / "artifacts"
    append_command(
        artifact_dir,
        argv=[
            "smoke",
            "--email",
            "patient@example.com",
            "--token=secret-token",
            "--url=http://127.0.0.1:8000/path?api_key=secret&safe=1",
            "Bearer another-secret",
        ],
        exit_code=0,
        started_at="2026-08-16T00:00:00+00:00",
        finished_at="2026-08-16T00:00:01+00:00",
        artifacts=[],
    )

    serialized = (artifact_dir / "manifest.json").read_text(encoding="utf-8")
    assert "patient@example.com" not in serialized
    assert "secret-token" not in serialized
    assert "api_key=secret" not in serialized
    assert "another-secret" not in serialized
    assert serialized.count("<redacted>") >= 4


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

    async def get(self, _url: str) -> _DiscoveryResponse:
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
