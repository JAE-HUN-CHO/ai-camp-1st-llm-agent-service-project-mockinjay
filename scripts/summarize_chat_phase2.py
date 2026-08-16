#!/usr/bin/env python3
"""Derive Phase-2 safety counters from completed JUnit evidence."""

from __future__ import annotations

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

from smoke_common import write_json


def _cases(path: Path) -> list[tuple[str, bool]]:
    """
    JUnit XML 파일에서 테스트 케이스 이름과 통과 여부를 추출합니다.
    
    Parameters:
    	path (Path): 파싱할 JUnit XML 파일 경로
    
    Returns:
    	list[tuple[str, bool]]: 각 테스트 케이스의 클래스명과 테스트명, 통과 여부를 담은 목록
    """
    root = ET.parse(path).getroot()
    result = []
    for case in root.iter("testcase"):
        name = " ".join(
            value for value in (case.get("classname"), case.get("name")) if value
        )
        passed = not any(case.find(tag) is not None for tag in ("failure", "error", "skipped"))
        result.append((name, passed))
    return result


def _group(cases: list[tuple[str, bool]], fragments: tuple[str, ...]) -> dict[str, int]:
    """
    지정된 문자열 조각을 포함하는 테스트 케이스를 선택하고 결과를 집계합니다.
    
    Parameters:
    	cases (list[tuple[str, bool]]): 테스트 케이스 이름과 통과 여부의 목록
    	fragments (tuple[str, ...]): 테스트 케이스 이름을 검색할 문자열 조각
    
    Returns:
    	dict[str, int]: 선택된 테스트의 전체 수, 통과 수, 실패 수를 담은 딕셔너리
    """
    selected = [(name, passed) for name, passed in cases if any(fragment in name for fragment in fragments)]
    return {
        "total": len(selected),
        "passed": sum(passed for _name, passed in selected),
        "failed": sum(not passed for _name, passed in selected),
    }


def main() -> int:
    """
    JUnit 테스트 결과를 검증하고 안전성 요약을 JSON 파일로 저장합니다.
    
    Returns:
    	int: 모든 필수 테스트 조건을 충족하면 0, 그렇지 않으면 1
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit-junit", type=Path, required=True)
    parser.add_argument("--integration-junit", type=Path, required=True)
    parser.add_argument("--frontend-junit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    unit = _cases(args.unit_junit)
    integration = _cases(args.integration_junit)
    frontend = _cases(args.frontend_junit)
    groups = {
        "emergency_gold_set": _group(unit, ("test_emergency_gold_set_has_zero_false_negatives",)),
        "emergency_downstream_zero": _group(
            unit,
            (
                "test_emergency_has_zero_repository_model_and_write_calls",
                "test_emergency_stream_has_zero_repository_provider_and_write_calls",
                "test_hex_emergency_has_zero_repository_generator_and_write_calls",
                "test_remote_agents_block_before_initialize_or_provider",
            ),
        ),
        "cross_user_room_session": _group(
            unit,
            (
                "test_cross_user_matrix_rejects_every_unauthorized_case",
                "test_cross_user_failure_has_zero_generator_and_write_calls",
                "test_hex_cross_user_rejection_is_json_and_has_zero_generator_or_write",
                "test_cross_user_room_has_zero_writes",
                "test_cross_user_session_has_zero_writes",
            ),
        ),
        "sse_terminal_semantics": _group(
            unit,
            (
                "test_stream_natural_eof_emits_success_terminal_and_saves",
                "test_error_frame_stops_later_complete_and_never_saves",
                "test_cancel_emits_terminal_and_has_zero_write",
                "test_disconnect_after_partial_emits_cancelled_and_has_zero_write",
                "test_empty_provider_eof_is_terminal_error_and_has_zero_write",
                "test_hex_stream_preserves_success_terminal_and_done_separation",
                "test_hex_stream_provider_failure_is_terminal_error_inside_http_200",
            ),
        ),
        "done_false_success": {
            **_group(
                [*unit, *frontend],
                (
                    "test_error_done_and_done_without_terminal_are_not_success_scenarios",
                    "does not promote error followed by [DONE] to success",
                    "does not convert a terminal backend error into a successful fallback response",
                    "error_done_then_transport_done",
                    "transport_done_without_terminal",
                ),
            )
        },
    }
    minimums = {
        "emergency_gold_set": 18,
        "emergency_downstream_zero": 5,
        "cross_user_room_session": 9,
        "sse_terminal_semantics": 7,
        "done_false_success": 3,
    }
    result = "pass"
    for name, minimum in minimums.items():
        group = groups[name]
        if group["total"] < minimum or group["failed"]:
            result = "fail"
    if not integration or any(not passed for _name, passed in integration):
        result = "fail"
    if not frontend or any(not passed for _name, passed in frontend):
        result = "fail"

    payload = {
        "schema_version": 1,
        "result": result,
        "emergency_false_negatives": groups["emergency_gold_set"]["failed"],
        "emergency_blocked_downstream_calls": 0 if groups["emergency_downstream_zero"]["failed"] == 0 else None,
        "cross_user_suite": groups["cross_user_room_session"],
        "cross_user_pass_rate_percent": (
            round(
                groups["cross_user_room_session"]["passed"]
                / groups["cross_user_room_session"]["total"]
                * 100,
                2,
            )
            if groups["cross_user_room_session"]["total"]
            else 0
        ),
        "unauthorized_writes": 0 if groups["cross_user_room_session"]["failed"] == 0 else None,
        "done_false_successes": groups["done_false_success"]["failed"],
        "groups": groups,
        "unit": {"total": len(unit), "passed": sum(passed for _name, passed in unit)},
        "integration": {
            "total": len(integration),
            "passed": sum(passed for _name, passed in integration),
        },
        "frontend": {
            "total": len(frontend),
            "passed": sum(passed for _name, passed in frontend),
        },
    }
    write_json(args.output, payload)
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
