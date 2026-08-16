"""Fail-closed acceptance summary tests for Phase 3B."""

from __future__ import annotations

from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from summarize_health_profiles_phase3b import (
    _selected,
    http_passes,
    invalid_selector_passes,
    schema_passes,
    selector_passes,
)


def _selector(implementation: str) -> dict[str, object]:
    return {
        "result": "pass",
        "implementation": implementation,
        "selector": {
            "environment_present": implementation == "hex",
            "configured_value": implementation if implementation == "hex" else None,
            "expected_default": "legacy",
        },
        "telemetry": {
            f"{implementation}.get.success": 3,
            f"{implementation}.update.success": 4,
        },
        "provider_call_count": 0,
        "hosted_provider_call_count": 0,
        "provider_call_evidence": {
            "measurement": "derived_not_network_observed",
            "basis": "health_profile_has_no_provider_port_and_runtime_providers_are_disabled",
            "health_profile_provider_port_present": False,
            "ollama_enabled": False,
            "hosted_credentials_present_after_sanitization": [],
        },
        "pii": {"leak_count": 0},
        "mongodb": {
            "duplicate_user_id_group_count": 0,
            "schema_drift_count": 0,
            "index_drift_count": 0,
            "schema_migration_count": 0,
            "index_migration_count": 0,
            "verification_cleanup_remaining_count": 0,
        },
    }


def test_selector_summary_requires_identity_telemetry_and_provider_evidence() -> None:
    legacy = _selector("legacy")
    assert selector_passes(legacy, "legacy")

    legacy["provider_call_evidence"] = None
    assert not selector_passes(legacy, "legacy")


def test_http_summary_requires_all_owner_and_preservation_cases() -> None:
    http = {
        "result": "pass",
        "implementation": "hex",
        "cross_user_cases": {"passed": 3, "total": 3},
        "unauthorized_write_count": 0,
        "null_preserved": True,
        "unset_preserved": True,
        "validation_cases": {"passed": 2, "total": 2},
    }
    assert http_passes(http, "hex")

    http["unauthorized_write_count"] = None
    assert not http_passes(http, "hex")


def test_invalid_selector_summary_requires_bounded_nonzero_exit() -> None:
    invalid = {
        "result": "pass",
        "configured_value": "invalid",
        "process_exit_code": 3,
        "timed_out": False,
        "duration_seconds": 0.5,
        "max_duration_seconds": 15.0,
        "expected_error_seen": True,
        "false_ready_count": 0,
        "hosted_provider_call_count": 0,
        "provider_call_evidence": {
            "measurement": "derived_not_network_observed",
            "basis": "selector_failed_before_http_readiness",
            "hosted_credentials_present_after_sanitization": [],
        },
    }
    assert invalid_selector_passes(invalid)

    invalid["process_exit_code"] = 0
    assert not invalid_selector_passes(invalid)


def test_schema_summary_requires_loopback_and_all_zero_drift() -> None:
    schema = {
        "result": "pass",
        "collection": "health_profiles",
        "mongodb": {"loopback_only": True},
        "document_count": 0,
        "field_audit_applicable": False,
        "field_audit_passed": True,
        "verification_user_count": 0,
        "verification_document_count": 0,
        "duplicate_user_id_group_count": 0,
        "invalid_owner_document_count": 0,
        "schema_drift_count": 0,
        "index_drift_count": 0,
        "schema_migration_count": 0,
        "index_migration_count": 0,
        "cleanup_operation_count": 0,
    }
    assert schema_passes(schema)

    schema["index_migration_count"] = None
    assert not schema_passes(schema)


def test_selected_reports_skips_separately_and_keeps_them_nonpassing() -> None:
    cases = [
        ("target passes", "passed"),
        ("target skips", "skipped"),
        ("target fails", "failed"),
        ("target_extra must not overlap", "passed"),
    ]

    assert _selected(cases, "target") == {
        "total": 3,
        "passed": 1,
        "failed": 1,
        "skipped": 1,
    }
