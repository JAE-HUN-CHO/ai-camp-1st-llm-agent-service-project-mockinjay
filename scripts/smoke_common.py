"""Shared fail-closed helpers for local HTTP verification scripts."""

from __future__ import annotations

from collections.abc import MutableMapping
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlparse

from sensitive_patterns import SENSITIVE_PATTERN


ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = SENSITIVE_PATTERN
HOSTED_SECRET_NAMES = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "EMCIE_API_KEY",
        "GNEWS_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "NCBI_API_KEY",
        "NEWSDATA_API_KEY",
        "NEWSAPI_KEY",
        "OPENAI_API_KEY",
    }
)


def sanitize_hosted_credentials(environment: MutableMapping[str, str]) -> list[str]:
    """Remove hosted-provider credentials and return names only, never values."""
    removed_names = sorted(
        name for name in HOSTED_SECRET_NAMES if name in environment
    )
    for name in removed_names:
        environment.pop(name)
    return removed_names


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


def resolve_artifact_path(artifact_dir: Path, relative_path: Path) -> Path:
    """Resolve a verification artifact without allowing path traversal."""
    artifact_root = artifact_dir.resolve()
    if relative_path.is_absolute() or ".." in relative_path.parts or not relative_path.name:
        raise ValueError("verification artifact path must stay inside artifact_dir")
    resolved = (artifact_root / relative_path).resolve()
    try:
        resolved.relative_to(artifact_root)
    except ValueError as exc:
        raise ValueError("verification artifact path must stay inside artifact_dir") from exc
    return resolved


def write_json(path: Path, payload: object) -> None:
    ensure_redacted(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def default_artifact_dir() -> Path:
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "logs" / "verification" / sha / run_id
