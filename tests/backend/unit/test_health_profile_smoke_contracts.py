"""Fail-closed checks for Phase 3B verification tooling."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest


SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_health_profiles_http_verification import (
    _telemetry,
    read_schema_audit,
    resolve_artifact_path,
    telemetry_failures,
    validate_selector_contract,
    verification_exit_code,
)
from smoke_common import (
    HOSTED_SECRET_NAMES,
    remaining_hosted_credentials,
    resolve_artifact_path as shared_resolve_artifact_path,
    sanitize_hosted_credentials,
)
import verify_health_profile_invalid_selector as invalid_selector


def test_health_profile_artifact_path_stays_inside_run(tmp_path: Path) -> None:
    """Verify health profile artifact path stays inside run."""
    assert resolve_artifact_path is shared_resolve_artifact_path
    assert resolve_artifact_path(tmp_path, Path("http/profile.json")) == (
        tmp_path / "http/profile.json"
    ).resolve()

    with pytest.raises(ValueError):
        resolve_artifact_path(tmp_path, Path("../profile.json"))
    with pytest.raises(ValueError):
        resolve_artifact_path(tmp_path, Path("/tmp/profile.json"))


def test_health_profile_child_environment_removes_all_hosted_credentials() -> None:
    """Verify health profile child environment removes all hosted credentials."""
    required_names = {
        "ANTHROPIC_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "EMCIE_API_KEY",
        "GNEWS_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "NCBI_API_KEY",
        "NEWSDATA_API_KEY",
        "NEWSAPI_KEY",
        "OPENAI_API_KEY",
    }
    assert required_names <= HOSTED_SECRET_NAMES
    environment = dict.fromkeys(HOSTED_SECRET_NAMES, "synthetic-secret")
    environment["FUTURE_PROVIDER_API_KEY"] = "synthetic-secret"
    environment["FUTURE_PROVIDER_API_TOKEN"] = "synthetic-secret"
    environment["CAREGUIDE_SMOKE_TOKEN"] = "preserved-local-token"
    environment["SAFE_SETTING"] = "preserved"

    assert sanitize_hosted_credentials(environment) == sorted(
        {
            *HOSTED_SECRET_NAMES,
            "FUTURE_PROVIDER_API_KEY",
            "FUTURE_PROVIDER_API_TOKEN",
        }
    )
    assert not HOSTED_SECRET_NAMES.intersection(environment)
    assert environment == {
        "CAREGUIDE_SMOKE_TOKEN": "preserved-local-token",
        "SAFE_SETTING": "preserved",
    }
    assert remaining_hosted_credentials(environment) == []
    assert remaining_hosted_credentials(
        {
            "EMPTY_PROVIDER_API_KEY": "",
            "FUTURE_PROVIDER_API_KEY": "synthetic-secret",
        }
    ) == ["FUTURE_PROVIDER_API_KEY"]


def test_health_profile_schema_audit_requires_all_zero_counters(tmp_path: Path) -> None:
    """Verify health profile schema audit requires all zero counters."""
    path = tmp_path / "schema.json"
    payload = {
        "result": "pass",
        "duplicate_user_id_group_count": 0,
        "schema_drift_count": 0,
        "index_drift_count": 0,
        "schema_migration_count": 0,
        "index_migration_count": 0,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert read_schema_audit(path) == {key: 0 for key in payload if key != "result"}

    payload["duplicate_user_id_group_count"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        read_schema_audit(path)


def test_health_profile_telemetry_rejects_missing_and_opposite_calls() -> None:
    """Verify health profile telemetry rejects missing and opposite calls."""
    log_text = "\n".join(
        [
            "INFO Health Profile implementation call implementation=hex "
            "operation=get outcome=success count=1",
            "INFO Health Profile implementation call implementation=hex "
            "operation=update outcome=success count=1",
        ]
    )
    assert _telemetry(log_text) == {
        "hex.get.success": 1,
        "hex.update.success": 1,
    }

    assert telemetry_failures(
        {"hex.get.success": 2, "hex.update.success": 3}, "hex"
    ) == []

    failures = telemetry_failures(
        {"hex.get.success": 1, "legacy.update.success": 1}, "hex"
    )
    assert "missing hex.update.success" in failures
    assert "opposite implementation telemetry present: legacy.update.success" in failures


def test_health_profile_verification_exit_code_handles_list_only_failure() -> None:
    """Verify health profile verification exit code handles list only failure."""
    assert verification_exit_code(False, [], 0) == 0
    assert verification_exit_code(False, ["missing hex.update.success"], 0) == 1


def test_health_profile_selector_evidence_requires_default_legacy_or_explicit_hex() -> None:
    """Verify health profile selector evidence requires default legacy or explicit hex."""
    validate_selector_contract("legacy", True)
    validate_selector_contract("hex", False)

    with pytest.raises(ValueError, match="legacy verification"):
        validate_selector_contract("legacy", False)
    with pytest.raises(ValueError, match="hex verification"):
        validate_selector_contract("hex", True)


def test_invalid_selector_launch_failure_writes_fail_closed_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify invalid selector launch failure writes fail closed artifact."""
    real_popen = invalid_selector.subprocess.Popen

    def fail_to_launch(argv: list[str], *args: object, **kwargs: object) -> object:
        """Simulate failure only when the local verification server starts."""
        if "uvicorn" in argv:
            raise OSError("synthetic launch failure")
        return real_popen(argv, *args, **kwargs)

    monkeypatch.setattr(invalid_selector.subprocess, "Popen", fail_to_launch)
    args = argparse.Namespace(
        artifact_dir=tmp_path,
        artifact_name=Path("selector/invalid.json"),
        port=65001,
        timeout=0.1,
    )

    assert invalid_selector.run(args) == 1
    payload = json.loads((tmp_path / "selector/invalid.json").read_text())
    assert payload["result"] == "fail"
    assert payload["process_exit_code"] == -1
    assert payload["failure"]["type"] == "OSError"


def test_invalid_selector_shutdown_failure_is_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify shutdown failures still produce fail-closed selector evidence."""
    process = Mock(returncode=None)
    process.poll.return_value = None
    process.wait.side_effect = OSError("synthetic shutdown failure")
    append_command = Mock()
    monkeypatch.setattr(
        invalid_selector.subprocess,
        "Popen",
        Mock(return_value=process),
    )
    monkeypatch.setattr(invalid_selector, "append_command", append_command)
    args = argparse.Namespace(
        artifact_dir=tmp_path,
        artifact_name=Path("selector/invalid.json"),
        port=65001,
        timeout=0.0,
    )

    assert invalid_selector.run(args) == 1
    payload = json.loads((tmp_path / "selector/invalid.json").read_text())
    assert payload["result"] == "fail"
    assert payload["shutdown_failure"]["type"] == "OSError"
    process.kill.assert_called_once()
    append_command.assert_called_once()
