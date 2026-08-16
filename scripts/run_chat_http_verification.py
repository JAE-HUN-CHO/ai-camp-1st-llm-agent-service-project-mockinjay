#!/usr/bin/env python3
"""Start one local Chat implementation, run HTTP smoke, and record redacted evidence."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import threading
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
    r"Chat implementation call implementation=(legacy|hex) "
    r"operation=(message|stream) outcome=([a-z_]+) count=(\d+)"
)


def _is_loopback_host(hostname: str | None) -> bool:
    return hostname in {"localhost", "127.0.0.1", "::1"}


def _require_local_mongodb(uri: str) -> None:
    parsed = urlsplit(uri)
    if parsed.scheme not in {"mongodb", "mongodb+srv"} or not _is_loopback_host(parsed.hostname):
        raise ValueError("live Chat verification requires loopback MongoDB")
    if parsed.scheme == "mongodb+srv":
        raise ValueError("SRV/hosted MongoDB is forbidden for live Chat verification")


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path.name}")
    return value


def _stream_summary(path: Path) -> dict[str, object]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    identifiers = next(record for record in records if record.get("contract") == "chat_stream_identifiers")
    terminal = next(
        (record for record in records if record.get("status") in {"complete", "success"}),
        None,
    )
    return {
        "status_code": identifiers.get("status_code"),
        "content_type": identifiers.get("content_type"),
        "provider_identity": identifiers.get("provider_identity"),
        "agent_identity": terminal.get("agent_identity") if terminal else None,
        "terminal_status": terminal.get("status") if terminal else None,
        "transport_done_count": sum(record.get("transport_done") is True for record in records),
        "room_id": identifiers.get("room_id"),
        "session_id": identifiers.get("session_id"),
        "message_id": identifiers.get("message_id"),
    }


def _telemetry(log_text: str) -> dict[str, int]:
    counters: dict[str, int] = {}
    for implementation, operation, outcome, count in TELEMETRY_PATTERN.findall(log_text):
        counters[f"{implementation}.{operation}.{outcome}"] = int(count)
    return counters


class _StallHandler(BaseHTTPRequestHandler):
    stall_seconds = 3.0

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        content_length = int(self.headers.get("content-length", "0"))
        if content_length:
            self.rfile.read(content_length)
        time.sleep(self.stall_seconds)
        try:
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, _format: str, *_args: object) -> None:
        return


def _start_stall_server(stall_seconds: float) -> tuple[ThreadingHTTPServer, threading.Thread, str]:
    handler = type("ConfiguredStallHandler", (_StallHandler,), {"stall_seconds": stall_seconds})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, thread, f"http://{host}:{port}"


def _wait_ready(base_url: str, process: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"CareGuide exited before readiness ({process.returncode})")
        try:
            response = httpx.get(f"{base_url}/health", timeout=1.0)
            if response.status_code == 200 and response.json().get("status") == "healthy":
                return
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
        time.sleep(0.2)
    raise TimeoutError("CareGuide readiness timed out") from last_error


def _stop_process(process: subprocess.Popen[bytes]) -> int:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    return int(process.returncode or 0)


def _token(secret_key: str) -> str:
    subject = f"phase2-{uuid.uuid4()}"
    expiration = datetime.now(UTC) + timedelta(minutes=30)
    return jwt.encode(
        {"user_id": subject, "username": "phase2-verifier", "exp": expiration},
        secret_key,
        algorithm="HS256",
    )


def run(args: argparse.Namespace) -> int:
    artifact_dir = args.artifact_dir.resolve()
    selector_path = artifact_dir / args.selector_artifact
    base_url = require_local_http(f"http://127.0.0.1:{args.port}")
    _require_local_mongodb(settings.mongodb_uri)

    environment = os.environ.copy()
    removed_hosted_credentials = sorted(name for name in HOSTED_SECRET_NAMES if environment.pop(name, None))
    environment["PYTHONPATH"] = str(BACKEND)
    environment["OLLAMA_ENABLED"] = "true"
    environment["OLLAMA_MAX_TOKENS"] = str(args.max_tokens)
    verification_secret = secrets.token_urlsafe(48)
    environment["SECRET_KEY"] = verification_secret
    environment["CAREGUIDE_SMOKE_TOKEN"] = _token(verification_secret)
    if args.unset_selector:
        environment.pop("CHAT_IMPLEMENTATION", None)
    else:
        environment["CHAT_IMPLEMENTATION"] = args.implementation

    stall_server = None
    stall_thread = None
    provider_url = environment.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    if args.stall_provider:
        stall_server, stall_thread, provider_url = _start_stall_server(args.stall_seconds)
        environment["OLLAMA_API_TIMEOUT"] = str(args.provider_timeout)
    elif args.ollama_base_url:
        provider_url = args.ollama_base_url
    provider_url = require_local_http(provider_url)
    environment["OLLAMA_BASE_URL"] = provider_url
    environment["OLLAMA_HOST"] = provider_url

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
        "scripts/smoke_api_chat.py",
        "--base-url",
        base_url,
        "--timeout",
        str(args.smoke_timeout),
        "--scenario",
        args.scenario,
        "--artifact-dir",
        str(artifact_dir),
    ]
    started_at = utc_now()
    server_started = utc_now()
    process: subprocess.Popen[bytes] | None = None
    smoke_exit = -1
    smoke_duration = 0.0
    server_exit = -1
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
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=args.max_duration,
            )
            smoke_duration = time.monotonic() - smoke_started
            smoke_exit = completed.returncode
        except Exception as exc:
            failure = exc
        finally:
            if process is not None:
                server_exit = _stop_process(process)
            if stall_server is not None:
                stall_server.shutdown()
                stall_server.server_close()
            if stall_thread is not None:
                stall_thread.join(timeout=5)
            log_file.seek(0)
            log_text = log_file.read().decode("utf-8", errors="ignore")

    expected_smoke_exit = "nonzero" if args.expect_smoke_failure else 0
    result = "pass"
    if failure is not None:
        result = "fail"
    elif args.expect_smoke_failure and smoke_exit == 0:
        result = "fail"
        failure = RuntimeError("failure smoke unexpectedly succeeded")
    elif not args.expect_smoke_failure and smoke_exit != 0:
        result = "fail"
        failure = RuntimeError("success smoke failed")
    elif smoke_duration > args.max_duration:
        result = "fail"
        failure = TimeoutError("smoke exceeded bounded duration")

    expected_status = {"provider-failure": 503, "timeout": 504}.get(args.scenario)
    error_artifact = artifact_dir / "http" / f"chat-{args.scenario}-error.json"
    failure_http: dict[str, object] | None = None
    failure_stream: dict[str, object] | None = None
    if args.expect_smoke_failure:
        if not error_artifact.is_file():
            result = "fail"
            failure = RuntimeError("expected failure artifact is missing")
        else:
            failure_http = _read_json(error_artifact)
            if failure_http.get("status_code") != expected_status:
                result = "fail"
                failure = RuntimeError("failure smoke returned unexpected HTTP status")
            failure_stream_path = (
                artifact_dir / "http" / f"chat-{args.scenario}-stream.ndjson"
            )
            if not failure_stream_path.is_file():
                result = "fail"
                failure = RuntimeError("expected stream failure artifact is missing")
            else:
                failure_records = [
                    json.loads(line)
                    for line in failure_stream_path.read_text(encoding="utf-8").splitlines()
                ]
                header = failure_records[0]
                failure_stream = {
                    "status_code": header.get("status_code"),
                    "content_type": header.get("content_type"),
                    "terminal_error_count": sum(
                        record.get("status") == "error" for record in failure_records
                    ),
                    "terminal_success_count": sum(
                        record.get("status") in {"complete", "success"}
                        for record in failure_records
                    ),
                    "transport_done_count": sum(
                        record.get("transport_done") is True for record in failure_records
                    ),
                }
                if failure_stream != {
                    "status_code": 200,
                    "content_type": header.get("content_type"),
                    "terminal_error_count": 1,
                    "terminal_success_count": 0,
                    "transport_done_count": 1,
                } or "text/event-stream" not in str(header.get("content_type", "")):
                    result = "fail"
                    failure = RuntimeError("stream failure evidence is invalid")

    message_summary = None
    stream_summary = None
    if not args.expect_smoke_failure and result == "pass":
        message_summary = _read_json(artifact_dir / "http" / "chat-message.json")
        stream_summary = _stream_summary(artifact_dir / "http" / "chat-stream.ndjson")

    log_digest = digest_text(log_text)
    summary: dict[str, object] = {
        "schema_version": 1,
        "result": result,
        "implementation": args.implementation,
        "selector": {
            "environment_present": not args.unset_selector,
            "configured_value": None if args.unset_selector else args.implementation,
            "expected_default": "legacy",
        },
        "provider": {
            "identity": "ollama",
            "base_url_host": urlsplit(provider_url).hostname,
            "base_url_port": urlsplit(provider_url).port,
            "max_tokens": args.max_tokens,
            "loopback_only": True,
        },
        "mongodb": {"host": urlsplit(settings.mongodb_uri).hostname, "loopback_only": True},
        "hosted_provider_call_count": 0,
        "removed_hosted_credential_names": removed_hosted_credentials,
        "smoke": {
            "scenario": args.scenario,
            "exit_code": smoke_exit,
            "expected_exit_code": expected_smoke_exit,
            "duration_seconds": round(smoke_duration, 3),
            "max_duration_seconds": args.max_duration,
            "message": message_summary,
            "stream": stream_summary,
            "failure_http": failure_http,
            "failure_stream": failure_stream,
        },
        "telemetry": _telemetry(log_text),
        "readiness_only": False if not args.expect_smoke_failure and smoke_exit == 0 else None,
        "server": {
            "controlled_shutdown": True,
            "exit_code": server_exit,
            "log": log_digest,
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
        exit_code=server_exit,
        started_at=server_started,
        finished_at=utc_now(),
        artifacts=[str(selector_path.relative_to(artifact_dir))],
    )
    return 0 if result == "pass" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--selector-artifact", type=Path, required=True)
    parser.add_argument("--implementation", choices=("legacy", "hex"), required=True)
    parser.add_argument("--unset-selector", action="store_true")
    parser.add_argument("--scenario", choices=("success", "provider-failure", "timeout"), default="success")
    parser.add_argument("--expect-smoke-failure", action="store_true")
    parser.add_argument("--ollama-base-url")
    parser.add_argument("--stall-provider", action="store_true")
    parser.add_argument("--stall-seconds", type=float, default=3.0)
    parser.add_argument("--provider-timeout", type=float, default=1.0)
    parser.add_argument("--startup-timeout", type=float, default=60.0)
    parser.add_argument("--smoke-timeout", type=float, default=180.0)
    parser.add_argument("--max-duration", type=float, default=300.0)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()
    if args.unset_selector and args.implementation != "legacy":
        parser.error("an unset selector must resolve to legacy")
    if args.expect_smoke_failure != (args.scenario != "success"):
        parser.error("failure scenarios require --expect-smoke-failure")
    if args.stall_provider and args.ollama_base_url:
        parser.error("choose either --stall-provider or --ollama-base-url")
    if args.max_tokens < 1:
        parser.error("--max-tokens must be positive")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
