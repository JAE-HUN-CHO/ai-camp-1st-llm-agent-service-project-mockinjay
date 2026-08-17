#!/usr/bin/env python3
"""Derive Phase 3B acceptance counters from tests and runtime evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from smoke_common import write_json


def _cases(path: Path) -> list[tuple[str, str]]:
    """Read JUnit cases into normalized names and outcomes."""
    cases = []
    for case in ET.parse(path).getroot().iter(  # noqa: S314 - local JUnit only
        "testcase"
    ):
        name = " ".join(
            value for value in (case.get("classname"), case.get("name")) if value
        )
        if case.find("skipped") is not None:
            status = "skipped"
        elif case.find("failure") is not None or case.find("error") is not None:
            status = "failed"
        else:
            status = "passed"
        cases.append((name, status))
    return cases


def _selected(cases: list[tuple[str, str]], fragment: str) -> dict[str, int]:
    """Summarize the exact test group matching a module fragment."""
    group_pattern = re.compile(rf"(^|[./]){re.escape(fragment)}(?=[./ ]|$)")
    matches = [
        (name, status) for name, status in cases if group_pattern.search(name)
    ]
    return {
        "total": len(matches),
        "passed": sum(status == "passed" for _name, status in matches),
        "failed": sum(status == "failed" for _name, status in matches),
        "skipped": sum(status == "skipped" for _name, status in matches),
    }


def _read_object(path: Path) -> dict[str, object]:
    """Load one required JSON evidence object."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Phase 3B evidence must be a JSON object")
    return payload


def _nested(item: dict[str, object], *path: str) -> object:
    """Read a nested evidence value without accepting a missing path."""
    current: object = item
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _zero(item: dict[str, object], *path: str) -> bool:
    """Accept only integer zero for a required evidence counter."""
    value = _nested(item, *path)
    return type(value) is int and value == 0


def _sum_integer_evidence(
    items: tuple[dict[str, object], ...], *path: str
) -> int | None:
    """Sum integer counters while failing closed on missing evidence."""
    values = [_nested(item, *path) for item in items]
    if not all(type(value) is int for value in values):
        return None
    return sum(int(value) for value in values)


def provider_evidence_passes(item: dict[str, object]) -> bool:
    """Validate derived local-only provider-call evidence."""
    evidence = item.get("provider_call_evidence")
    return (
        isinstance(evidence, dict)
        and evidence.get("measurement") == "derived_not_network_observed"
        and evidence.get("health_profile_provider_port_present") is False
        and evidence.get("ollama_enabled") is False
        and isinstance(
            evidence.get("hosted_credentials_present_before_sanitization"),
            list,
        )
        and evidence.get("hosted_credentials_present_after_sanitization") == []
        and _zero(item, "hosted_provider_call_count")
        and _zero(item, "provider_call_count")
    )


def selector_passes(item: dict[str, object], implementation: str) -> bool:
    """Validate selector identity, telemetry, safety, and storage evidence."""
    expected_selector = {
        "environment_present": implementation == "hex",
        "configured_value": implementation if implementation == "hex" else None,
        "expected_default": "legacy",
    }
    telemetry = item.get("telemetry")
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    opposite = "legacy" if implementation == "hex" else "hex"
    return (
        item.get("result") == "pass"
        and item.get("implementation") == implementation
        and item.get("selector") == expected_selector
        and type(telemetry.get(f"{implementation}.get.success")) is int
        and int(telemetry[f"{implementation}.get.success"]) > 0
        and type(telemetry.get(f"{implementation}.update.success")) is int
        and int(telemetry[f"{implementation}.update.success"]) > 0
        and not any(str(key).startswith(f"{opposite}.") for key in telemetry)
        and provider_evidence_passes(item)
        and _zero(item, "pii", "leak_count")
        and _zero(item, "mongodb", "duplicate_user_id_group_count")
        and _zero(item, "mongodb", "schema_drift_count")
        and _zero(item, "mongodb", "index_drift_count")
        and _zero(item, "mongodb", "schema_migration_count")
        and _zero(item, "mongodb", "index_migration_count")
        and _zero(item, "mongodb", "verification_cleanup_remaining_count")
    )


def http_passes(item: dict[str, object], implementation: str) -> bool:
    """Validate one implementation's frozen HTTP and owner contract."""
    return (
        item.get("result") == "pass"
        and item.get("implementation") == implementation
        and item.get("cross_user_cases") == {"passed": 3, "total": 3}
        and _zero(item, "unauthorized_write_count")
        and item.get("null_preserved") is True
        and item.get("unset_preserved") is True
        and item.get("validation_cases") == {"passed": 2, "total": 2}
    )


def invalid_selector_passes(item: dict[str, object]) -> bool:
    """Validate bounded fail-closed behavior for an invalid selector."""
    duration = item.get("duration_seconds")
    maximum = item.get("max_duration_seconds")
    return (
        item.get("result") == "pass"
        and item.get("configured_value") == "invalid"
        and type(item.get("process_exit_code")) is int
        and int(item["process_exit_code"]) != 0
        and item.get("timed_out") is False
        and item.get("shutdown_failure") is None
        and type(duration) in {int, float}
        and type(maximum) in {int, float}
        and float(duration) <= float(maximum)
        and item.get("expected_error_seen") is True
        and _zero(item, "false_ready_count")
        and _zero(item, "hosted_provider_call_count")
        and _nested(item, "provider_call_evidence", "measurement")
        == "derived_not_network_observed"
        and _nested(item, "provider_call_evidence", "basis")
        == "selector_failed_before_http_readiness"
        and isinstance(
            _nested(
                item,
                "provider_call_evidence",
                "hosted_credentials_present_before_sanitization",
            ),
            list,
        )
        and _nested(
            item,
            "provider_call_evidence",
            "hosted_credentials_present_after_sanitization",
        )
        == []
    )


def schema_passes(item: dict[str, object]) -> bool:
    """Validate the additive, zero-drift storage evidence."""
    return (
        item.get("result") == "pass"
        and item.get("collection") == "health_profiles"
        and _nested(item, "mongodb", "loopback_only") is True
        and type(item.get("document_count")) is int
        and item.get("field_audit_applicable")
        == (int(item["document_count"]) > 0)
        and item.get("field_audit_passed") is True
        and item.get("index_audit_applicable") is True
        and _zero(item, "verification_user_count")
        and _zero(item, "verification_document_count")
        and _zero(item, "duplicate_user_id_group_count")
        and _zero(item, "invalid_owner_document_count")
        and _zero(item, "schema_drift_count")
        and _zero(item, "index_drift_count")
        and _zero(item, "schema_migration_count")
        and _zero(item, "index_migration_count")
        and _zero(item, "cleanup_operation_count")
    )


def build_summary(
    *,
    unit: list[tuple[str, str]],
    integration: list[tuple[str, str]],
    frontend: list[tuple[str, str]],
    legacy_selector: dict[str, object],
    hex_selector: dict[str, object],
    invalid_selector: dict[str, object],
    legacy_http: dict[str, object],
    hex_http: dict[str, object],
    schema: dict[str, object],
    imports: dict[str, object],
    pii: dict[str, object],
) -> dict[str, object]:
    """Combine test and runtime evidence into the Phase 3B acceptance result."""
    groups = {
        "frozen_v1_contract": _selected(unit, "test_health_profile_v1_contract"),
        "application": _selected(unit, "test_health_profile_application"),
        "selector": _selected(unit, "test_health_profile_selector"),
        "mongodb_adapter": _selected(
            unit, "test_mongodb_health_profile_repository"
        ),
        "verification_tooling": _selected(
            unit, "test_health_profile_smoke_contracts"
        ),
        "live_mongodb": _selected(integration, "test_health_profiles_mongodb"),
        "frontend_client": _selected(frontend, "healthProfileApi"),
    }
    selectors_ok = selector_passes(
        legacy_selector, "legacy"
    ) and selector_passes(hex_selector, "hex")
    http_ok = http_passes(legacy_http, "legacy") and http_passes(hex_http, "hex")
    invalid_ok = invalid_selector_passes(invalid_selector)
    schema_ok = schema_passes(schema)
    imports_ok = _zero(
        imports, "enforced_violation_count"
    ) and imports.get("enforced_violations") == []
    pii_ok = pii.get("result") == "pass" and _zero(pii, "canary_matches")
    groups_ok = all(
        group["total"] > 0 and group["failed"] == 0 and group["skipped"] == 0
        for group in groups.values()
    )
    unauthorized_write_count = _sum_integer_evidence(
        (legacy_http, hex_http), "unauthorized_write_count"
    )
    hosted_provider_call_count = _sum_integer_evidence(
        (legacy_selector, hex_selector, invalid_selector),
        "hosted_provider_call_count",
    )
    result = (
        "pass"
        if all((groups_ok, selectors_ok, http_ok, invalid_ok, schema_ok, imports_ok, pii_ok))
        else "fail"
    )
    return {
        "schema_version": 1,
        "result": result,
        "unit": {
            "total": len(unit),
            "passed": sum(status == "passed" for _, status in unit),
            "failed": sum(status == "failed" for _, status in unit),
            "skipped": sum(status == "skipped" for _, status in unit),
        },
        "integration": {
            "total": len(integration),
            "passed": sum(status == "passed" for _, status in integration),
            "failed": sum(status == "failed" for _, status in integration),
            "skipped": sum(status == "skipped" for _, status in integration),
        },
        "frontend": {
            "total": len(frontend),
            "passed": sum(status == "passed" for _, status in frontend),
            "failed": sum(status == "failed" for _, status in frontend),
            "skipped": sum(status == "skipped" for _, status in frontend),
        },
        "groups": groups,
        "selector_default": "legacy",
        "selectors_passed": 2 if selectors_ok else 0,
        "selectors_total": 2,
        "invalid_selector_fail_closed": invalid_ok,
        "http_implementations_passed": 2 if http_ok else 0,
        "http_implementations_total": 2,
        "cross_user_cases_passed": 6 if http_ok else 0,
        "cross_user_cases_total": 6,
        "unauthorized_write_count": unauthorized_write_count,
        "sensitive_artifact_match_count": pii.get("canary_matches"),
        "import_violation_count": imports.get("enforced_violation_count"),
        "hosted_provider_call_count": hosted_provider_call_count,
        "hosted_provider_call_count_basis": "derived_not_network_observed",
        "schema_migration_count": schema.get("schema_migration_count"),
        "index_migration_count": schema.get("index_migration_count"),
        "schema_preserved": schema_ok,
    }


def main() -> int:
    """Parse evidence paths and write the final acceptance summary."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit-junit", type=Path, required=True)
    parser.add_argument("--integration-junit", type=Path, required=True)
    parser.add_argument("--frontend-junit", type=Path, required=True)
    parser.add_argument("--legacy-selector", type=Path, required=True)
    parser.add_argument("--hex-selector", type=Path, required=True)
    parser.add_argument("--invalid-selector", type=Path, required=True)
    parser.add_argument("--legacy-http", type=Path, required=True)
    parser.add_argument("--hex-http", type=Path, required=True)
    parser.add_argument("--schema-audit", type=Path, required=True)
    parser.add_argument("--import-rules", type=Path, required=True)
    parser.add_argument("--pii", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    summary = build_summary(
        unit=_cases(args.unit_junit),
        integration=_cases(args.integration_junit),
        frontend=_cases(args.frontend_junit),
        legacy_selector=_read_object(args.legacy_selector),
        hex_selector=_read_object(args.hex_selector),
        invalid_selector=_read_object(args.invalid_selector),
        legacy_http=_read_object(args.legacy_http),
        hex_http=_read_object(args.hex_http),
        schema=_read_object(args.schema_audit),
        imports=_read_object(args.import_rules),
        pii=_read_object(args.pii),
    )
    write_json(args.output, summary)
    return 0 if summary["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
