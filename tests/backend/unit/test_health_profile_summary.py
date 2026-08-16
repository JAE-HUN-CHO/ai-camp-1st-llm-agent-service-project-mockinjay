"""Fail-closed acceptance summary tests for Phase 3B."""

from __future__ import annotations

from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from summarize_health_profiles_phase3b import (
    _selected,
    build_summary,
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
            "hosted_credentials_present_before_sanitization": [],
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


def _http(implementation: str) -> dict[str, object]:
    return {
        "result": "pass",
        "implementation": implementation,
        "cross_user_cases": {"passed": 3, "total": 3},
        "unauthorized_write_count": 0,
        "null_preserved": True,
        "unset_preserved": True,
        "validation_cases": {"passed": 2, "total": 2},
    }


def _invalid_selector() -> dict[str, object]:
    return {
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
            "hosted_credentials_present_before_sanitization": [],
            "hosted_credentials_present_after_sanitization": [],
        },
    }


def _schema() -> dict[str, object]:
    return {
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


def _passing_unit_cases() -> list[tuple[str, str]]:
    return [
        (f"tests.backend.unit.{module} test_case", "passed")
        for module in (
            "test_health_profile_v1_contract",
            "test_health_profile_application",
            "test_health_profile_selector",
            "test_mongodb_health_profile_repository",
            "test_health_profile_smoke_contracts",
        )
    ]


def _build_summary(
    unit: list[tuple[str, str]],
    *,
    import_count: object = 0,
    pii_count: object = 0,
) -> dict[str, object]:
    return build_summary(
        unit=unit,
        integration=[
            (
                "tests.backend.integration.test_health_profiles_mongodb test_case",
                "passed",
            )
        ],
        frontend=[
            (
                "src/services/__tests__/healthProfileApi.test.ts client contract",
                "passed",
            )
        ],
        legacy_selector=_selector("legacy"),
        hex_selector=_selector("hex"),
        invalid_selector=_invalid_selector(),
        legacy_http=_http("legacy"),
        hex_http=_http("hex"),
        schema=_schema(),
        imports={
            "enforced_violation_count": import_count,
            "enforced_violations": [],
        },
        pii={"result": "pass", "canary_matches": pii_count},
    )


def test_selector_summary_requires_identity_telemetry_and_provider_evidence() -> None:
    legacy = _selector("legacy")
    assert selector_passes(legacy, "legacy")

    legacy["provider_call_evidence"] = None
    assert not selector_passes(legacy, "legacy")


def test_http_summary_requires_all_owner_and_preservation_cases() -> None:
    http = _http("hex")
    assert http_passes(http, "hex")

    http["unauthorized_write_count"] = None
    assert not http_passes(http, "hex")


def test_invalid_selector_summary_requires_bounded_nonzero_exit() -> None:
    invalid = _invalid_selector()
    assert invalid_selector_passes(invalid)

    invalid["process_exit_code"] = 0
    assert not invalid_selector_passes(invalid)


def test_schema_summary_requires_loopback_and_all_zero_drift() -> None:
    schema = _schema()
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


def test_build_summary_passes_with_complete_evidence_and_derived_counters() -> None:
    unit = _passing_unit_cases()
    summary = _build_summary(unit)

    assert summary["result"] == "pass"
    assert summary["selectors_passed"] == 2
    assert summary["cross_user_cases_passed"] == 6
    assert summary["unauthorized_write_count"] == 0
    assert _build_summary(unit, import_count=False)["result"] == "fail"
    assert _build_summary(unit, pii_count=False)["result"] == "fail"


def test_build_summary_fails_closed_when_a_required_group_is_skipped() -> None:
    unit = _passing_unit_cases()
    unit[0] = (unit[0][0], "skipped")

    summary = _build_summary(unit)

    assert summary["result"] == "fail"
    assert summary["unauthorized_write_count"] == 0
    assert summary["hosted_provider_call_count"] == 0
    assert summary["groups"]["frozen_v1_contract"] == {
        "total": 1,
        "passed": 0,
        "failed": 0,
        "skipped": 1,
    }
