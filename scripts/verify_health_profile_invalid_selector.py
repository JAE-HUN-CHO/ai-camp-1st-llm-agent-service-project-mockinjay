#!/usr/bin/env python3
"""Prove an invalid Health Profile selector fails before HTTP readiness."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.bootstrap.container import HEALTH_PROFILE_IMPLEMENTATION_ERROR
from smoke_common import (
    digest_text,
    remaining_hosted_credentials,
    require_local_http,
    resolve_artifact_path,
    sanitize_hosted_credentials,
    utc_now,
    write_json,
)
from verification_manifest import append_command


def run(args: argparse.Namespace) -> int:
    """Prove an invalid selector exits before local HTTP readiness."""
    artifact_dir = args.artifact_dir.resolve()
    artifact_path = resolve_artifact_path(artifact_dir, args.artifact_name)
    base_url = require_local_http(f"http://127.0.0.1:{args.port}")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(BACKEND)
    environment["OLLAMA_ENABLED"] = "false"
    environment["CHAT_IMPLEMENTATION"] = "legacy"
    environment["HEALTH_RECORDS_IMPLEMENTATION"] = "legacy"
    environment["HEALTH_PROFILE_IMPLEMENTATION"] = "invalid"
    removed_hosted_credentials = sanitize_hosted_credentials(environment)

    server_argv = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--app-dir",
        "backend",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.port),
    ]
    started_at = utc_now()
    started = time.monotonic()
    false_ready_count = 0
    launch_failure: Exception | None = None
    shutdown_failure: Exception | None = None
    with tempfile.TemporaryFile() as log_file:
        process: subprocess.Popen[bytes] | None = None
        timed_out = False
        try:
            process = subprocess.Popen(
                server_argv,
                cwd=ROOT,
                env=environment,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
            deadline = time.monotonic() + args.timeout
            while process.poll() is None and time.monotonic() < deadline:
                try:
                    response = httpx.get(f"{base_url}/health", timeout=0.2)
                    false_ready_count += int(response.status_code == 200)
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            timed_out = process.poll() is None
        except Exception as exc:  # noqa: BLE001 - persist launch failure evidence
            launch_failure = exc
        finally:
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                except Exception as exc:  # noqa: BLE001 - preserve cleanup evidence
                    shutdown_failure = exc
                    try:
                        if process.poll() is None:
                            process.kill()
                            process.wait(timeout=5)
                    except Exception as fallback_exc:  # noqa: BLE001
                        shutdown_failure = fallback_exc
        exit_code = -1 if process is None else int(process.returncode or 0)
        log_file.seek(0)
        log_text = log_file.read().decode("utf-8", errors="replace")

    expected_error_seen = HEALTH_PROFILE_IMPLEMENTATION_ERROR in log_text
    result = (
        "pass"
        if launch_failure is None
        and shutdown_failure is None
        and not timed_out
        and exit_code != 0
        and expected_error_seen
        and false_ready_count == 0
        else "fail"
    )
    write_json(
        artifact_path,
        {
            "schema_version": 1,
            "result": result,
            "configured_value": "invalid",
            "process_exit_code": exit_code,
            "timed_out": timed_out,
            "duration_seconds": round(time.monotonic() - started, 3),
            "max_duration_seconds": args.timeout,
            "expected_error_seen": expected_error_seen,
            "false_ready_count": false_ready_count,
            "hosted_provider_call_count": 0,
            "provider_call_evidence": {
                "measurement": "derived_not_network_observed",
                "basis": "selector_failed_before_http_readiness",
                "hosted_credentials_present_before_sanitization": (
                    removed_hosted_credentials
                ),
                "hosted_credentials_present_after_sanitization": (
                    remaining_hosted_credentials(environment)
                ),
            },
            "failure": (
                {
                    "type": type(launch_failure).__name__,
                    "message": digest_text(str(launch_failure)),
                }
                if launch_failure is not None
                else None
            ),
            "shutdown_failure": (
                {
                    "type": type(shutdown_failure).__name__,
                    "message": digest_text(str(shutdown_failure)),
                }
                if shutdown_failure is not None
                else None
            ),
            "log": digest_text(log_text),
            "started_at": started_at,
            "finished_at": utc_now(),
        },
    )
    append_command(
        artifact_dir,
        argv=server_argv,
        exit_code=exit_code,
        started_at=started_at,
        finished_at=utc_now(),
        artifacts=[str(artifact_path.relative_to(artifact_dir))],
    )
    return 0 if result == "pass" else 1


def main() -> int:
    """Parse invalid-selector arguments and return the bounded result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--artifact-name", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8006)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
