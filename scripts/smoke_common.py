"""Shared fail-closed helpers for local HTTP verification scripts."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlparse

from sensitive_patterns import SENSITIVE_PATTERN


ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = SENSITIVE_PATTERN


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def require_local_http(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("only loopback HTTP endpoints are allowed: 127.0.0.1, localhost, ::1")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("credentials, query strings and fragments are forbidden in base URLs")
    return url.rstrip("/")


def digest_text(value: str) -> dict[str, int | str]:
    encoded = value.encode("utf-8")
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "bytes": len(encoded)}


def ensure_redacted(payload: object) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    if SENSITIVE.search(serialized):
        raise ValueError("sensitive canary or credential detected in evidence payload")


def write_json(path: Path, payload: object) -> None:
    ensure_redacted(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def default_artifact_dir() -> Path:
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "logs" / "verification" / sha / run_id
