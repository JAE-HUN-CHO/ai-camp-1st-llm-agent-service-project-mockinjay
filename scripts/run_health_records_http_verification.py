#!/usr/bin/env python3
"""Run one local Health Records implementation and collect redacted HTTP evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
import uuid

import httpx
from jose import jwt


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import settings
from smoke_common import digest_text, ensure_redacted, require_local_http, utc_now, write_json
from verification_manifest import append_command


HOSTED_SECRET_NAMES = {
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "EMCIE_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
}
TELEMETRY_PATTERN = re.compile(
    r"Health Records implementation call implementation=(legacy|hex) "
    r"operation=(list|create|update|delete) outcome=(success|failure) count=(\d+)"
)


@dataclass(frozen=True)
class ShutdownResult:
    controlled: bool
    exit_code: int
    method: str


def _require_local_mongodb(uri: str) -> None:
    parsed = urlsplit(uri)
    if parsed.scheme != "mongodb" or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("live Health Records verification requires loopback MongoDB")


def resolve_artifact_path(artifact_dir: Path, relative_path: Path) -> Path:
    if relative_path.is_absolute() or ".." in relative_path.parts or not relative_path.name:
        raise ValueError("Health Records artifact path must stay inside artifact_dir")
    resolved = (artifact_dir / relative_path).resolve()
    try:
        resolved.relative_to(artifact_dir)
    except ValueError as exc:
        raise ValueError("Health Records artifact path must stay inside artifact_dir") from exc
    return resolved


def read_schema_audit(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("result") != "pass":
        raise ValueError("Health Records schema audit did not pass")
    counters = {}
    for name in ("schema_migration_count", "index_migration_count"):
        value = payload.get(name)
        if type(value) is not int or value != 0:
            raise ValueError(f"Health Records schema audit has invalid {name}")
        counters[name] = value
    return counters


def _token(secret_key: str, owner: str) -> str:
    return jwt.encode(
        {
            "user_id": owner,
            "username": "phase3a-verifier",
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        secret_key,
        algorithm="HS256",
    )


def _wait_ready(base_url: str, process: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("CareGuide exited before Health Records readiness")
        try:
            response = httpx.get(f"{base_url}/health", timeout=1.0)
            if response.status_code == 200 and response.json().get("status") == "healthy":
                return
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(0.2)
    raise TimeoutError("CareGuide Health Records readiness timed out")


def _stop_process(process: subprocess.Popen[bytes]) -> ShutdownResult:
    if process.poll() is not None:
        return ShutdownResult(False, int(process.returncode or 0), "already_exited")
    process.terminate()
    try:
        process.wait(timeout=20)
        return ShutdownResult(True, int(process.returncode or 0), "terminate")
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            return ShutdownResult(False, int(process.returncode or -9), "kill_timeout")
        return ShutdownResult(False, int(process.returncode or -9), "kill")


def _telemetry(log_text: str) -> dict[str, int]:
    counters: dict[str, int] = {}
    for implementation, operation, outcome, count in TELEMETRY_PATTERN.findall(log_text):
        counters[f"{implementation}.{operation}.{outcome}"] = int(count)
    return counters


def telemetry_failures(counters: dict[str, int], implementation: str) -> list[str]:
    failures = []
    for operation in ("list", "create", "update", "delete"):
        key = f"{implementation}.{operation}.success"
        if counters.get(key, 0) < 1:
            failures.append(f"missing {key}")
    opposite = "legacy" if implementation == "hex" else "hex"
    opposite_keys = sorted(key for key in counters if key.startswith(f"{opposite}."))
    failures.extend(
        f"opposite implementation telemetry present: {key}" for key in opposite_keys
    )
    return failures


def run(args: argparse.Namespace) -> int:
    artifact_dir = args.artifact_dir.resolve()
    selector_path = resolve_artifact_path(artifact_dir, args.selector_artifact)
    http_path = resolve_artifact_path(artifact_dir, args.http_artifact)
    schema_audit_path = resolve_artifact_path(artifact_dir, args.schema_audit_artifact)
    schema_audit = read_schema_audit(schema_audit_path)
    base_url = require_local_http(f"http://127.0.0.1:{args.port}")
    _require_local_mongodb(settings.mongodb_uri)

    environment = os.environ.copy()
    removed_hosted_credentials = sorted(
        name for name in HOSTED_SECRET_NAMES if environment.pop(name, None)
    )
    environment["PYTHONPATH"] = str(BACKEND)
    environment["OLLAMA_ENABLED"] = "false"
    environment["CHAT_IMPLEMENTATION"] = "legacy"
    verification_secret = secrets.token_urlsafe(48)
    owner = f"phase3a-owner-{uuid.uuid4()}"
    other_owner = f"phase3a-other-{uuid.uuid4()}"
    canary = f"health-canary-phase3a-{uuid.uuid4()}"
    environment["SECRET_KEY"] = verification_secret
    environment["CAREGUIDE_SMOKE_TOKEN"] = _token(verification_secret, owner)
    environment["CAREGUIDE_OTHER_SMOKE_TOKEN"] = _token(
        verification_secret, other_owner
    )
    environment["CAREGUIDE_HEALTH_CANARY"] = canary
    if args.unset_selector:
        environment.pop("HEALTH_RECORDS_IMPLEMENTATION", None)
    else:
        environment["HEALTH_RECORDS_IMPLEMENTATION"] = args.implementation

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
    smoke_argv = [
        sys.executable,
        "scripts/smoke_api_health_records.py",
        "--base-url",
        base_url,
        "--timeout",
        str(args.smoke_timeout),
        "--implementation",
        args.implementation,
        "--artifact-dir",
        str(artifact_dir),
        "--artifact-name",
        str(args.http_artifact),
    ]
    started_at = utc_now()
    server_started_at = utc_now()
    process: subprocess.Popen[bytes] | None = None
    shutdown = ShutdownResult(False, -1, "not_started")
    smoke_exit = -1
    smoke_duration = 0.0
    failure: Exception | None = None
    log_text = ""
    with tempfile.TemporaryFile() as log_file:
        try:
            process = subprocess.Popen(
                server_argv,
                cwd=ROOT,
                env=environment,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
            _wait_ready(base_url, process, args.startup_timeout)
            smoke_started = time.monotonic()
            completed = subprocess.run(
                smoke_argv,
                cwd=ROOT,
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=args.max_duration,
            )
            smoke_duration = time.monotonic() - smoke_started
            smoke_exit = completed.returncode
        except Exception as exc:
            failure = exc
        finally:
            if process is not None:
                shutdown = _stop_process(process)
            log_file.seek(0)
            log_text = log_file.read().decode("utf-8", errors="ignore")

    result = "pass"
    if failure is not None or smoke_exit != 0 or not http_path.is_file():
        result = "fail"
        if failure is None:
            failure = RuntimeError("Health Records HTTP smoke failed")
    if process is not None and not shutdown.controlled:
        result = "fail"
        if failure is None:
            failure = RuntimeError("Health Records server shutdown was not controlled")
    pii_leak_count = int(canary in log_text)
    if pii_leak_count:
        result = "fail"
        failure = RuntimeError("Health Records canary appeared in application logs")

    telemetry = _telemetry(log_text)
    telemetry_errors = telemetry_failures(telemetry, args.implementation)
    if telemetry_errors:
        result = "fail"
        if failure is None:
            failure = RuntimeError(
                "Health Records telemetry validation failed: "
                + "; ".join(telemetry_errors)
            )

    http_summary: dict[str, object] | None = None
    if http_path.is_file():
        loaded = json.loads(http_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            http_summary = {
                "result": loaded.get("result"),
                "cross_user_cases": loaded.get("cross_user_cases"),
                "unauthorized_write_count": loaded.get("unauthorized_write_count"),
                "synthetic_leak_count": loaded.get("synthetic_leak_count"),
                "null_clear_preserved": loaded.get("null_clear_preserved"),
                "unset_fields_preserved": loaded.get("unset_fields_preserved"),
                "list_order_preserved": loaded.get("list_order_preserved"),
                "error_contract_preserved": loaded.get("error_contract_preserved"),
            }

    summary: dict[str, object] = {
        "schema_version": 1,
        "result": result,
        "implementation": args.implementation,
        "selector": {
            "environment_present": not args.unset_selector,
            "configured_value": None if args.unset_selector else args.implementation,
            "expected_default": "legacy",
        },
        "mongodb": {
            "host": urlsplit(settings.mongodb_uri).hostname,
            "loopback_only": True,
            "collection": "health_records",
            **schema_audit,
        },
        "provider_call_count": 0,
        "hosted_provider_call_count": 0,
        "removed_hosted_credential_names": removed_hosted_credentials,
        "smoke": {
            "exit_code": smoke_exit,
            "duration_seconds": round(smoke_duration, 3),
            "max_duration_seconds": args.max_duration,
            "http": http_summary,
        },
        "telemetry": telemetry,
        "pii": {"synthetic_canary_count": 1, "leak_count": pii_leak_count},
        "server": {
            "controlled_shutdown": shutdown.controlled,
            "shutdown_method": shutdown.method,
            "exit_code": shutdown.exit_code,
            "log": digest_text(log_text),
        },
        "failure": (
            {"type": type(failure).__name__, "message": digest_text(str(failure))}
            if failure is not None
            else None
        ),
        "started_at": started_at,
        "finished_at": utc_now(),
    }
    ensure_redacted(summary)
    write_json(selector_path, summary)
    append_command(
        artifact_dir,
        argv=server_argv,
        exit_code=0 if result == "pass" else 1,
        started_at=server_started_at,
        finished_at=utc_now(),
        artifacts=[
            str(selector_path.relative_to(artifact_dir)),
            *(
                [str(http_path.relative_to(artifact_dir))]
                if http_path.is_file()
                else []
            ),
        ],
    )
    return 0 if result == "pass" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--selector-artifact", type=Path, required=True)
    parser.add_argument("--http-artifact", type=Path, required=True)
    parser.add_argument("--schema-audit-artifact", type=Path, required=True)
    parser.add_argument("--implementation", choices=("legacy", "hex"), required=True)
    parser.add_argument("--unset-selector", action="store_true")
    parser.add_argument("--startup-timeout", type=float, default=60.0)
    parser.add_argument("--smoke-timeout", type=float, default=15.0)
    parser.add_argument("--max-duration", type=float, default=60.0)
    parser.add_argument("--port", type=int, default=8003)
    args = parser.parse_args()
    if args.unset_selector and args.implementation != "legacy":
        parser.error("an unset selector must resolve to legacy")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
