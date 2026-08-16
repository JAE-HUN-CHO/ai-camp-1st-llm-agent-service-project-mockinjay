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

from smoke_common import (
    digest_text,
    require_local_http,
    resolve_artifact_path,
    utc_now,
    write_json,
)
from verification_manifest import append_command


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.bootstrap.container import HEALTH_PROFILE_IMPLEMENTATION_ERROR


def run(args: argparse.Namespace) -> int:
    artifact_dir = args.artifact_dir.resolve()
    artifact_path = resolve_artifact_path(artifact_dir, args.artifact_name)
    base_url = require_local_http(f"http://127.0.0.1:{args.port}")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(BACKEND)
    environment["OLLAMA_ENABLED"] = "false"
    environment["CHAT_IMPLEMENTATION"] = "legacy"
    environment["HEALTH_RECORDS_IMPLEMENTATION"] = "legacy"
    environment["HEALTH_PROFILE_IMPLEMENTATION"] = "invalid"
    for name in (
        "ANTHROPIC_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "EMCIE_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "OPENAI_API_KEY",
    ):
        environment.pop(name, None)

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
        except Exception as exc:
            launch_failure = exc
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        exit_code = -1 if process is None else int(process.returncode or 0)
        log_file.seek(0)
        log_text = log_file.read().decode("utf-8", errors="replace")

    expected_error_seen = HEALTH_PROFILE_IMPLEMENTATION_ERROR in log_text
    result = (
        "pass"
        if launch_failure is None
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
                "hosted_credentials_present_after_sanitization": [],
            },
            "failure": (
                {
                    "type": type(launch_failure).__name__,
                    "message": digest_text(str(launch_failure)),
                }
                if launch_failure is not None
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--artifact-name", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8006)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
