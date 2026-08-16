#!/usr/bin/env python3
"""Run one local Health Profile implementation and collect redacted HTTP evidence."""

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

from bson import ObjectId
import httpx
from jose import jwt
from pymongo import MongoClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import settings
from smoke_common import (
    HOSTED_SECRET_NAMES,
    digest_text,
    ensure_redacted,
    require_local_http,
    resolve_artifact_path,
    sanitize_hosted_credentials,
    utc_now,
    write_json,
)
from verification_manifest import append_command


TELEMETRY_PATTERN = re.compile(
    r"Health Profile implementation call implementation=(legacy|hex) "
    r"operation=(get|update) outcome=(success|failure) count=(\d+)"
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
        raise ValueError("live Health Profile verification requires loopback MongoDB")


def read_schema_audit(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("result") != "pass":
        raise ValueError("Health Profile schema audit did not pass")
    counters: dict[str, int] = {}
    for name in (
        "duplicate_user_id_group_count",
        "schema_drift_count",
        "index_drift_count",
        "schema_migration_count",
        "index_migration_count",
    ):
        value = payload.get(name)
        if type(value) is not int or value != 0:
            raise ValueError(f"Health Profile schema audit has invalid {name}")
        counters[name] = value
    return counters


def _token(secret_key: str, owner: str) -> str:
    return jwt.encode(
        {
            "user_id": owner,
            "username": "phase3b-verifier",
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        secret_key,
        algorithm="HS256",
    )


def _wait_ready(base_url: str, process: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("CareGuide exited before Health Profile readiness")
        try:
            response = httpx.get(f"{base_url}/health", timeout=1.0)
            if response.status_code == 200 and response.json().get("status") == "healthy":
                return
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(0.2)
    raise TimeoutError("CareGuide Health Profile readiness timed out")


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
    for operation in ("get", "update"):
        key = f"{implementation}.{operation}.success"
        if counters.get(key, 0) < 1:
            failures.append(f"missing {key}")
    opposite = "legacy" if implementation == "hex" else "hex"
    failures.extend(
        f"opposite implementation telemetry present: {key}"
        for key in sorted(counters)
        if key.startswith(f"{opposite}.")
    )
    return failures


def verification_exit_code(*failure_signals: object) -> int:
    """Normalize every failure signal to a bounded process exit code."""
    return int(any(bool(signal) for signal in failure_signals))


def validate_selector_contract(implementation: str, unset_selector: bool) -> None:
    """Keep runtime evidence aligned with the default/explicit selector contract."""
    if implementation == "legacy" and not unset_selector:
        raise ValueError("legacy verification must leave the selector unset")
    if implementation == "hex" and unset_selector:
        raise ValueError("hex verification must set the selector explicitly")


def record_server_command(
    artifact_dir: Path,
    *,
    server_argv: list[str],
    shutdown: ShutdownResult,
    server_started_at: str,
    finished_at: str,
    artifacts: list[str],
) -> None:
    append_command(
        artifact_dir,
        argv=server_argv,
        exit_code=shutdown.exit_code,
        started_at=server_started_at,
        finished_at=finished_at,
        artifacts=artifacts,
    )


def run(args: argparse.Namespace) -> int:
    artifact_dir = args.artifact_dir.resolve()
    selector_path = resolve_artifact_path(artifact_dir, args.selector_artifact)
    http_path = resolve_artifact_path(artifact_dir, args.http_artifact)
    schema_path = resolve_artifact_path(artifact_dir, args.schema_audit_artifact)
    schema_audit = read_schema_audit(schema_path)
    base_url = require_local_http(f"http://127.0.0.1:{args.port}")
    _require_local_mongodb(settings.mongodb_uri)

    environment = os.environ.copy()
    removed_hosted_credentials = sanitize_hosted_credentials(environment)
    environment["PYTHONPATH"] = str(BACKEND)
    environment["OLLAMA_ENABLED"] = "false"
    environment["CHAT_IMPLEMENTATION"] = "legacy"
    environment["HEALTH_RECORDS_IMPLEMENTATION"] = "legacy"
    verification_secret = secrets.token_urlsafe(48)
    owner_object_id = ObjectId()
    other_object_id = ObjectId()
    owner = str(owner_object_id)
    other_owner = str(other_object_id)
    canary = f"health-canary-phase3b-{uuid.uuid4()}"
    environment["SECRET_KEY"] = verification_secret
    environment["CAREGUIDE_SMOKE_TOKEN"] = _token(verification_secret, owner)
    environment["CAREGUIDE_OTHER_SMOKE_TOKEN"] = _token(
        verification_secret, other_owner
    )
    environment["CAREGUIDE_HEALTH_PROFILE_CANARY"] = canary
    if args.unset_selector:
        environment.pop("HEALTH_PROFILE_IMPLEMENTATION", None)
    else:
        environment["HEALTH_PROFILE_IMPLEMENTATION"] = args.implementation

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
        "scripts/smoke_api_health_profiles.py",
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
    smoke_output = ""
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    database = mongo[settings.db_name]
    cleanup_remaining_count = 2
    cleanup_failure: Exception | None = None

    try:
        mongo.admin.command("ping")
        suffix = uuid.uuid4().hex
        database.users.insert_many(
            [
                {
                    "_id": owner_object_id,
                    "username": f"phase3b-owner-{suffix}",
                    "email": f"phase3b-owner-{suffix}@invalid.example",
                },
                {
                    "_id": other_object_id,
                    "username": f"phase3b-other-{suffix}",
                    "email": f"phase3b-other-{suffix}@invalid.example",
                },
            ]
        )
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
                    timeout=args.max_duration,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                smoke_duration = time.monotonic() - smoke_started
                smoke_exit = completed.returncode
                smoke_output = completed.stdout.decode("utf-8", errors="replace")
            except Exception as exc:
                failure = exc
            finally:
                if process is not None:
                    shutdown = _stop_process(process)
                log_file.seek(0)
                log_text = log_file.read().decode("utf-8", errors="replace")
    except Exception as exc:
        failure = exc
    finally:
        try:
            database.health_profiles.delete_many(
                {"userId": {"$in": [owner, other_owner]}}
            )
            database.users.delete_many(
                {"_id": {"$in": [owner_object_id, other_object_id]}}
            )
            cleanup_remaining_count = (
                database.health_profiles.count_documents(
                    {"userId": {"$in": [owner, other_owner]}}
                )
                + database.users.count_documents(
                    {"_id": {"$in": [owner_object_id, other_object_id]}}
                )
            )
        except Exception as exc:
            cleanup_failure = exc
        mongo.close()

    telemetry = _telemetry(log_text)
    telemetry_errors = telemetry_failures(telemetry, args.implementation)
    pii_leak_count = int(canary in log_text or canary in smoke_output)
    exit_code = verification_exit_code(
        failure is not None
        or cleanup_failure is not None,
        smoke_exit != 0,
        not http_path.is_file(),
        telemetry_errors,
        pii_leak_count != 0,
        cleanup_remaining_count != 0,
        not shutdown.controlled,
    )
    result = "pass" if exit_code == 0 else "fail"
    summary: dict[str, object] = {
        "schema_version": 1,
        "result": result,
        "verification_exit_code": exit_code,
        "implementation": args.implementation,
        "selector": {
            "environment_present": not args.unset_selector,
            "configured_value": None if args.unset_selector else args.implementation,
            "expected_default": "legacy",
        },
        "mongodb": {
            "host": urlsplit(settings.mongodb_uri).hostname,
            "loopback_only": True,
            "collection": "health_profiles",
            **schema_audit,
            "verification_cleanup_remaining_count": cleanup_remaining_count,
        },
        "provider_call_count": 0,
        "hosted_provider_call_count": 0,
        "provider_call_evidence": {
            "measurement": "derived_not_network_observed",
            "basis": "health_profile_has_no_provider_port_and_runtime_providers_are_disabled",
            "health_profile_provider_port_present": False,
            "ollama_enabled": False,
            "hosted_credentials_present_before_sanitization": (
                removed_hosted_credentials
            ),
            "hosted_credentials_present_after_sanitization": sorted(
                name for name in HOSTED_SECRET_NAMES if environment.get(name)
            ),
        },
        "removed_hosted_credential_names": removed_hosted_credentials,
        "smoke": {
            "exit_code": smoke_exit,
            "duration_seconds": round(smoke_duration, 3),
            "max_duration_seconds": args.max_duration,
            "output": digest_text(smoke_output),
        },
        "telemetry": telemetry,
        "telemetry_failures": telemetry_errors,
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
        "cleanup_failure": (
            {
                "type": type(cleanup_failure).__name__,
                "message": digest_text(str(cleanup_failure)),
            }
            if cleanup_failure is not None
            else None
        ),
        "started_at": started_at,
        "finished_at": utc_now(),
    }
    ensure_redacted(summary)
    write_json(selector_path, summary)
    record_server_command(
        artifact_dir,
        server_argv=server_argv,
        shutdown=shutdown,
        server_started_at=server_started_at,
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
    return exit_code


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
    parser.add_argument("--port", type=int, default=8004)
    args = parser.parse_args()
    try:
        validate_selector_contract(args.implementation, args.unset_selector)
    except ValueError as exc:
        parser.error(str(exc))
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
