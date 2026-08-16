#!/usr/bin/env python3
"""Derive Phase 3A acceptance counters from JUnit and HTTP evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from smoke_common import write_json


def _cases(path: Path) -> list[tuple[str, bool]]:
    result = []
    for case in ET.parse(path).getroot().iter("testcase"):
        name = " ".join(
            value for value in (case.get("classname"), case.get("name")) if value
        )
        passed = not any(
            case.find(tag) is not None for tag in ("failure", "error", "skipped")
        )
        result.append((name, passed))
    return result


def _selected(cases: list[tuple[str, bool]], fragment: str) -> dict[str, int]:
    matches = [(name, passed) for name, passed in cases if fragment in name]
    return {
        "total": len(matches),
        "passed": sum(passed for _name, passed in matches),
        "failed": sum(not passed for _name, passed in matches),
    }


def _read_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Phase 3A evidence must be a JSON object")
    return payload


COUNTER_PATHS = {
    "unauthorized_write_count": ("smoke", "http", "unauthorized_write_count"),
    "synthetic_leak_count": ("pii", "leak_count"),
    "synthetic_record_leak_count": ("smoke", "http", "synthetic_leak_count"),
    "hosted_provider_call_count": ("hosted_provider_call_count",),
    "schema_migration_count": ("mongodb", "schema_migration_count"),
}


def required_counter_totals(
    selectors: list[dict[str, object]],
) -> tuple[dict[str, int | None], list[str]]:
    totals: dict[str, int | None] = {}
    missing = []
    for counter_name, path in COUNTER_PATHS.items():
        values = []
        for index, selector in enumerate(selectors):
            current: object = selector
            for part in path:
                if not isinstance(current, dict) or part not in current:
                    missing.append(f"selector[{index}].{'.'.join(path)}")
                    break
                current = current[part]
            else:
                if type(current) is not int or current < 0:
                    missing.append(f"selector[{index}].{'.'.join(path)}")
                else:
                    values.append(current)
        totals[counter_name] = sum(values) if len(values) == len(selectors) else None
    return totals, missing


def cross_user_cases(item: dict[str, object]) -> dict[str, object]:
    smoke = item.get("smoke")
    smoke = smoke if isinstance(smoke, dict) else {}
    http = smoke.get("http")
    http = http if isinstance(http, dict) else {}
    cases = http.get("cross_user_cases")
    return cases if isinstance(cases, dict) else {}


def selector_identities_match(
    hex_selector: dict[str, object], rollback_selector: dict[str, object]
) -> bool:
    return (
        hex_selector.get("implementation") == "hex"
        and hex_selector.get("selector")
        == {
            "environment_present": True,
            "configured_value": "hex",
            "expected_default": "legacy",
        }
        and rollback_selector.get("implementation") == "legacy"
        and rollback_selector.get("selector")
        == {
            "environment_present": False,
            "configured_value": None,
            "expected_default": "legacy",
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit-junit", type=Path, required=True)
    parser.add_argument("--integration-junit", type=Path, required=True)
    parser.add_argument("--hex-selector", type=Path, required=True)
    parser.add_argument("--rollback-selector", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    unit = _cases(args.unit_junit)
    integration = _cases(args.integration_junit)
    groups = {
        "frozen_v1_contract": _selected(unit, "test_health_records_v1_contract"),
        "application": _selected(unit, "test_health_records_application"),
        "selector": _selected(unit, "test_health_records_selector"),
        "mongodb_adapter": _selected(unit, "test_mongodb_health_record_repository"),
        "live_mongodb": _selected(integration, "test_health_records_mongodb"),
    }
    hex_selector = _read_object(args.hex_selector)
    rollback_selector = _read_object(args.rollback_selector)
    http_results = [hex_selector, rollback_selector]
    counter_totals, missing_counters = required_counter_totals(http_results)
    owner_case_results = [cross_user_cases(item) for item in http_results]
    result = "pass"
    if any(group["total"] == 0 or group["failed"] for group in groups.values()):
        result = "fail"
    if any(item.get("result") != "pass" for item in http_results):
        result = "fail"
    if not selector_identities_match(hex_selector, rollback_selector):
        result = "fail"
    if missing_counters or any(value != 0 for value in counter_totals.values()):
        result = "fail"
    if any(cases != {"passed": 2, "total": 2} for cases in owner_case_results):
        result = "fail"

    write_json(
        args.output,
        {
            "schema_version": 1,
            "result": result,
            "unit": {
                "total": len(unit),
                "passed": sum(passed for _name, passed in unit),
            },
            "integration": {
                "total": len(integration),
                "passed": sum(passed for _name, passed in integration),
            },
            "groups": groups,
            "http_implementations_passed": sum(
                item.get("result") == "pass" for item in http_results
            ),
            "http_implementations_total": len(http_results),
            "cross_user_cases_passed": sum(
                int(cases.get("passed", 0)) for cases in owner_case_results
            ),
            "cross_user_cases_total": sum(
                int(cases.get("total", 0)) for cases in owner_case_results
            ),
            **counter_totals,
            "counter_evidence_complete": not missing_counters,
            "missing_counter_paths": missing_counters,
            "selector_default": "legacy",
            "rollback_result": rollback_selector.get("result"),
        },
    )
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
