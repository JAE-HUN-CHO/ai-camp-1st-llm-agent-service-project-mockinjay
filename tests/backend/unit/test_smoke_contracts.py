"""Fail-closed evidence and SSE contract tests for Phase-1 scripts."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_architecture_dependencies
import run_health_records_http_verification as health_records_verification
from audit_health_records_schema import BASELINE_INDEXES, evaluate_schema_audit
from check_architecture_dependencies import _matches_module, imports
from check_artifact_pii import main as pii_main
from smoke_api_chat import SmokeContractError, parse_sse_line, serialize_stream_evidence
from smoke_common import ensure_redacted, require_local_http
from smoke_parlant_http import _discover, _event_summary, _prepare_error_artifact
from run_chat_http_verification import _readiness_only, _stream_summary
from run_health_records_http_verification import (
    _stop_process,
    read_schema_audit,
    resolve_artifact_path,
    telemetry_failures,
)
from summarize_chat_rollout import RolloutEvidenceError, main as rollout_main, validate_selector
from summarize_health_records_phase3a import (
    cross_user_cases,
    required_counter_totals,
    selector_identities_match,
)
from sanitize_verification_artifacts import sanitize_junit, sanitize_stream
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


def test_chat_smoke_error_carries_only_transport_metadata() -> None:
    error = SmokeContractError(
        "provider failed",
        status_code=503,
        content_type="application/json",
    )

    assert error.status_code == 503
    assert error.content_type == "application/json"


def test_health_records_telemetry_requires_selected_crud_and_rejects_opposite() -> None:
    selected = {
        "hex.list.success": 2,
        "hex.create.success": 2,
        "hex.update.success": 1,
        "hex.delete.success": 1,
    }
    assert telemetry_failures(selected, "hex") == []

    selected.pop("hex.update.success")
    selected["legacy.list.success"] = 1
    assert telemetry_failures(selected, "hex") == [
        "missing hex.update.success",
        "opposite implementation telemetry present: legacy.list.success",
    ]


def test_health_records_artifacts_cannot_escape_the_run_directory(tmp_path) -> None:
    assert resolve_artifact_path(tmp_path, Path("selector/hex.json")) == (
        tmp_path / "selector/hex.json"
    )
    with pytest.raises(ValueError, match="artifact_dir"):
        resolve_artifact_path(tmp_path, Path("../outside.json"))
    with pytest.raises(ValueError, match="artifact_dir"):
        resolve_artifact_path(tmp_path, tmp_path / "absolute.json")


def test_health_records_schema_audit_counters_are_observed(tmp_path) -> None:
    audit = tmp_path / "schema.json"
    audit.write_text(
        json.dumps(
            {
                "result": "pass",
                "schema_migration_count": 0,
                "index_migration_count": 0,
            }
        ),
        encoding="utf-8",
    )
    assert read_schema_audit(audit) == {
        "schema_migration_count": 0,
        "index_migration_count": 0,
    }

    audit.write_text(
        json.dumps(
            {
                "result": "pass",
                "schema_migration_count": 1,
                "index_migration_count": 0,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="schema_migration_count"):
        read_schema_audit(audit)


def test_health_records_shutdown_distinguishes_terminate_and_kill() -> None:
    graceful = Mock()
    graceful.poll.return_value = None
    graceful.returncode = -15
    graceful.wait.return_value = -15
    graceful_result = _stop_process(graceful)
    assert graceful_result.controlled is True
    assert graceful_result.method == "terminate"
    assert graceful_result.exit_code == -15

    forced = Mock()
    forced.poll.return_value = None
    forced.returncode = -9
    forced.wait.side_effect = [subprocess.TimeoutExpired("uvicorn", 20), -9]
    forced_result = _stop_process(forced)
    assert forced_result.controlled is False
    assert forced_result.method == "kill"
    assert forced_result.exit_code == -9


def test_health_records_server_manifest_keeps_process_exit_code(
    monkeypatch, tmp_path
) -> None:
    recorded: list[dict[str, object]] = []

    def capture_append_command(_artifact_dir, **kwargs) -> None:
        recorded.append(kwargs)

    monkeypatch.setattr(
        health_records_verification,
        "append_command",
        capture_append_command,
    )
    health_records_verification.record_server_command(
        tmp_path,
        server_argv=["python", "-m", "uvicorn"],
        shutdown=health_records_verification.ShutdownResult(True, -15, "terminate"),
        server_started_at="2026-08-16T00:00:00+00:00",
        finished_at="2026-08-16T00:00:01+00:00",
        artifacts=["selector/health-records-hex.json"],
    )

    assert recorded == [
        {
            "argv": ["python", "-m", "uvicorn"],
            "exit_code": -15,
            "started_at": "2026-08-16T00:00:00+00:00",
            "finished_at": "2026-08-16T00:00:01+00:00",
            "artifacts": ["selector/health-records-hex.json"],
        }
    ]


def test_health_records_summary_counters_are_derived_and_fail_closed() -> None:
    selector = {
        "hosted_provider_call_count": 0,
        "mongodb": {"schema_migration_count": 0},
        "pii": {"leak_count": 0},
        "smoke": {
            "http": {
                "unauthorized_write_count": 0,
                "synthetic_leak_count": 0,
            }
        },
    }

    totals, missing = required_counter_totals([selector, selector])
    assert totals == {
        "unauthorized_write_count": 0,
        "synthetic_leak_count": 0,
        "synthetic_record_leak_count": 0,
        "hosted_provider_call_count": 0,
        "schema_migration_count": 0,
    }
    assert missing == []

    incomplete = json.loads(json.dumps(selector))
    del incomplete["pii"]["leak_count"]
    totals, missing = required_counter_totals([selector, incomplete])
    assert totals["synthetic_leak_count"] is None
    assert missing == ["selector[1].pii.leak_count"]


def test_health_records_cross_user_summary_handles_null_http() -> None:
    assert cross_user_cases({"smoke": {"http": None}}) == {}


def test_health_records_summary_rejects_substituted_selector_artifacts() -> None:
    hex_selector = {
        "implementation": "hex",
        "selector": {
            "environment_present": True,
            "configured_value": "hex",
            "expected_default": "legacy",
        },
    }
    rollback_selector = {
        "implementation": "legacy",
        "selector": {
            "environment_present": False,
            "configured_value": None,
            "expected_default": "legacy",
        },
    }
    assert selector_identities_match(hex_selector, rollback_selector) is True

    substituted = json.loads(json.dumps(hex_selector))
    substituted["implementation"] = "legacy"
    assert selector_identities_match(substituted, rollback_selector) is False


def test_health_records_schema_audit_distinguishes_empty_and_drift() -> None:
    empty = evaluate_schema_audit(
        document_count=0,
        verification_document_count=0,
        observed_field_names=[],
        indexes=BASELINE_INDEXES,
    )
    assert empty == {
        "result": "pass",
        "schema_observed": False,
        "schema_migration_count": 0,
        "index_migration_count": 0,
    }

    schema_drift = evaluate_schema_audit(
        document_count=1,
        verification_document_count=0,
        observed_field_names=["_id", "unexpected"],
        indexes=BASELINE_INDEXES,
    )
    assert schema_drift["result"] == "fail"
    assert schema_drift["schema_migration_count"] == 1

    index_drift = evaluate_schema_audit(
        document_count=0,
        verification_document_count=0,
        observed_field_names=[],
        indexes=[],
    )
    assert index_drift["result"] == "fail"
    assert index_drift["index_migration_count"] == 1


def test_rollout_summary_requires_successful_json_sse_and_telemetry(tmp_path) -> None:
    artifact = tmp_path / "hex.json"
    payload = {
        "result": "pass",
        "implementation": "hex",
        "hosted_provider_call_count": 0,
        "smoke": {
            "scenario": "success",
            "exit_code": 0,
            "duration_seconds": 1.0,
            "message": {
                "status_code": 200,
                "content_type": "application/json",
                "provider": "ollama",
                "agent_identity": "ollama_rag",
                "message_id": {"sha256": "message", "bytes": 1},
            },
            "stream": {
                "status_code": 200,
                "content_type": "text/event-stream; charset=utf-8",
                "provider_identity": "ollama",
                "agent_identity": "ollama_rag",
                "terminal_status": "complete",
                "transport_done_count": 1,
                "message_id": {"sha256": "stream", "bytes": 1},
            },
        },
        "telemetry": {"hex.message.success": 1, "hex.stream.success": 1},
    }
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    assert validate_selector(artifact, "hex")["terminal_status"] == "complete"

    payload["smoke"]["stream"]["transport_done_count"] = 0
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RolloutEvidenceError, match="stream_done"):
        validate_selector(artifact, "hex")


def test_evidence_sanitizer_removes_host_parameters_and_token_sized_hashes(
    tmp_path,
) -> None:
    junit = tmp_path / "unit.xml"
    junit.write_text(
        '<testsuite hostname="private-host"><testcase name="test_case[raw health text]">'
        '<failure message="private failure">private traceback</failure>'
        "<system-out>private output</system-out></testcase></testsuite>",
        encoding="utf-8",
    )
    stream = tmp_path / "stream.ndjson"
    stream.write_text(
        json.dumps(
            {
                "status": "streaming",
                "content": {"sha256": "recoverable", "bytes": 2},
            }
        )
        + "\n"
        + json.dumps(
            {
                "status": "complete",
                "content": {"sha256": "full-answer", "bytes": 2000},
            }
        )
        + "\n"
        + json.dumps(
            {
                "status": "complete",
                "content": "raw terminal answer",
                "error": "raw terminal error",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    sanitize_junit(junit)
    sanitize_stream(stream)

    junit_text = junit.read_text(encoding="utf-8")
    stream_records = [json.loads(line) for line in stream.read_text().splitlines()]
    assert "private-host" not in junit_text
    assert "raw health text" not in junit_text
    assert "private output" not in junit_text
    assert "private failure" not in junit_text
    assert "private traceback" not in junit_text
    assert stream_records[0] == {"status": "streaming", "content_bytes": 2}
    assert stream_records[1]["content"]["sha256"] == "full-answer"
    assert stream_records[2] == {
        "status": "complete",
        "content_bytes": len("raw terminal answer".encode()),
        "error_bytes": len("raw terminal error".encode()),
    }


def test_http_summary_fails_closed_for_empty_or_identifierless_stream(tmp_path) -> None:
    stream = tmp_path / "stream.ndjson"
    stream.write_text("", encoding="utf-8")
    with pytest.raises(RuntimeError, match="empty"):
        _stream_summary(stream)

    stream.write_text('{"status":"complete"}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="identifier"):
        _stream_summary(stream)


@pytest.mark.parametrize(
    ("readiness", "evidence", "expected"),
    [(False, False, None), (True, False, True), (True, True, False)],
)
def test_readiness_only_reflects_smoke_evidence(
    readiness: bool,
    evidence: bool,
    expected: bool | None,
) -> None:
    assert _readiness_only(readiness, evidence) is expected


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


def test_rollout_rejects_reused_hex_artifacts(monkeypatch, tmp_path) -> None:
    reused = tmp_path / "hex.json"
    rollback = tmp_path / "rollback.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "summarize_chat_rollout.py",
            *sum((["--hex-artifact", str(reused)] for _ in range(5)), []),
            "--rollback-artifact",
            str(rollback),
            "--output",
            str(tmp_path / "rollout.json"),
        ],
    )

    with pytest.raises(SystemExit) as error:
        rollout_main()
    assert error.value.code == 2


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


def test_verification_records_declared_produced_artifact(tmp_path) -> None:
    artifact_dir = tmp_path / "artifacts"
    output = artifact_dir / "command.txt"
    junit = artifact_dir / "unit.junit.xml"
    command = [
        sys.executable,
        "-c",
        f"from pathlib import Path; Path({str(junit)!r}).write_text('<testsuite/>')",
    ]

    assert run_command(artifact_dir, output, command, [junit]) == 0
    manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["commands"][-1]["artifacts"] == ["command.txt", "unit.junit.xml"]


def test_missing_produced_artifact_is_still_recorded(tmp_path) -> None:
    artifact_dir = tmp_path / "artifacts"
    output = artifact_dir / "command.txt"
    missing = artifact_dir / "missing.xml"

    with pytest.raises(RuntimeError, match="expected produced artifact is missing"):
        run_command(
            artifact_dir,
            output,
            [sys.executable, "-c", "print('executed')"],
            [missing],
        )

    manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["commands"][-1]["artifacts"] == ["command.txt", "missing.xml"]


def test_verification_runs_from_repository_subdirectory(tmp_path) -> None:
    artifact_dir = tmp_path / "artifacts"
    output = artifact_dir / "command.txt"
    frontend = Path(__file__).resolve().parents[3] / "frontend"

    assert run_command(
        artifact_dir,
        output,
        [sys.executable, "-c", "from pathlib import Path; print(Path.cwd().name)"],
        cwd=frontend,
    ) == 0
    assert output.read_text(encoding="utf-8").strip() == "frontend"
    manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["commands"][-1]["cwd"] == str(frontend)


@pytest.mark.parametrize("cwd_kind", ["outside", "missing"])
def test_verification_rejects_invalid_cwd_before_command(tmp_path, cwd_kind) -> None:
    artifact_dir = tmp_path / "artifacts"
    marker = tmp_path / "executed"
    cwd = tmp_path if cwd_kind == "outside" else Path(__file__).parents[3] / "missing-cwd"
    command = [
        sys.executable,
        "-c",
        f"from pathlib import Path; Path({str(marker)!r}).write_text('x')",
    ]

    with pytest.raises(ValueError, match="verification cwd"):
        run_command(artifact_dir, artifact_dir / "output.txt", command, cwd=cwd)
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
