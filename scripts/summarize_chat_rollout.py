#!/usr/bin/env python3
"""Validate five local hex canaries and one explicit legacy rollback."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from smoke_common import ensure_redacted, write_json


class RolloutEvidenceError(RuntimeError):
    """Raised when a selector artifact does not prove the expected contract."""


def _read(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RolloutEvidenceError(f"selector artifact must be an object: {path.name}")
    return payload


def validate_selector(path: Path, implementation: str) -> dict[str, object]:
    payload = _read(path)
    smoke = payload.get("smoke")
    smoke = smoke if isinstance(smoke, dict) else {}
    message = smoke.get("message")
    message = message if isinstance(message, dict) else {}
    stream = smoke.get("stream")
    stream = stream if isinstance(stream, dict) else {}
    telemetry = payload.get("telemetry")
    telemetry = telemetry if isinstance(telemetry, dict) else {}

    checks = {
        "result": payload.get("result") == "pass",
        "implementation": payload.get("implementation") == implementation,
        "hosted_provider_calls": payload.get("hosted_provider_call_count") == 0,
        "smoke_exit": smoke.get("exit_code") == 0,
        "scenario": smoke.get("scenario") == "success",
        "message_status": message.get("status_code") == 200,
        "message_content_type": "application/json"
        in str(message.get("content_type", "")),
        "message_provider": message.get("provider") == "ollama",
        "message_agent": message.get("agent_identity") == "ollama_rag",
        "stream_status": stream.get("status_code") == 200,
        "stream_content_type": "text/event-stream"
        in str(stream.get("content_type", "")),
        "stream_provider": stream.get("provider_identity") == "ollama",
        "stream_agent": stream.get("agent_identity") == "ollama_rag",
        "stream_terminal": stream.get("terminal_status") in {"complete", "success"},
        "stream_done": stream.get("transport_done_count") == 1,
        "message_telemetry": telemetry.get(f"{implementation}.message.success") == 1,
        "stream_telemetry": telemetry.get(f"{implementation}.stream.success") == 1,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise RolloutEvidenceError(
            f"{path.name} failed selector evidence checks: {', '.join(failed)}"
        )
    return {
        "artifact": path.name,
        "duration_seconds": smoke.get("duration_seconds"),
        "message_id": message.get("message_id"),
        "stream_message_id": stream.get("message_id"),
        "terminal_status": stream.get("terminal_status"),
        "transport_done_count": stream.get("transport_done_count"),
        "rest_attempts": sum(
            int(value)
            for key, value in telemetry.items()
            if key.startswith(f"{implementation}.message.")
            and isinstance(value, int)
        ),
        "rest_successes": int(telemetry.get(f"{implementation}.message.success", 0)),
        "sse_attempts": sum(
            int(value)
            for key, value in telemetry.items()
            if key.startswith(f"{implementation}.stream.")
            and isinstance(value, int)
        ),
        "sse_successes": int(telemetry.get(f"{implementation}.stream.success", 0)),
        "hosted_provider_call_count": int(payload.get("hosted_provider_call_count", 0)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hex-artifact", type=Path, action="append", required=True)
    parser.add_argument("--rollback-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.hex_artifact) != 5:
        parser.error("exactly five --hex-artifact values are required")
    hex_paths = [path.resolve() for path in args.hex_artifact]
    if len(set(hex_paths)) != len(hex_paths):
        parser.error("each --hex-artifact must identify a distinct run")
    if args.rollback_artifact.resolve() in set(hex_paths):
        parser.error("rollback evidence must be distinct from hex runs")

    hex_runs = [validate_selector(path, "hex") for path in args.hex_artifact]
    rollback = validate_selector(args.rollback_artifact, "legacy")
    payload = {
        "schema_version": 1,
        "result": "pass",
        "default_implementation": "legacy",
        "hex": {
            "run_count": len(hex_runs),
            "rest_attempts": sum(run["rest_attempts"] for run in hex_runs),
            "rest_successes": sum(run["rest_successes"] for run in hex_runs),
            "sse_attempts": sum(run["sse_attempts"] for run in hex_runs),
            "sse_successes": sum(run["sse_successes"] for run in hex_runs),
            "success_rate_percent": round(
                100
                * (
                    sum(run["rest_successes"] for run in hex_runs)
                    + sum(run["sse_successes"] for run in hex_runs)
                )
                / (
                    sum(run["rest_attempts"] for run in hex_runs)
                    + sum(run["sse_attempts"] for run in hex_runs)
                ),
                3,
            ),
            "runs": hex_runs,
        },
        "rollback": {
            "process_restart": True,
            "rest_attempts": rollback["rest_attempts"],
            "rest_successes": rollback["rest_successes"],
            "sse_attempts": rollback["sse_attempts"],
            "sse_successes": rollback["sse_successes"],
            "run": rollback,
        },
        "hosted_provider_call_count": sum(
            run["hosted_provider_call_count"] for run in [*hex_runs, rollback]
        ),
        "terminal_semantic_failures": sum(
            run["terminal_status"] not in {"complete", "success"}
            for run in [*hex_runs, rollback]
        ),
        "done_false_successes": sum(
            run["transport_done_count"] != 1 for run in [*hex_runs, rollback]
        ),
    }
    ensure_redacted(payload)
    write_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
