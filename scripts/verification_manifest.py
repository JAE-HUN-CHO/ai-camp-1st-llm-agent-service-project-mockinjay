#!/usr/bin/env python3
"""Run verification commands and append exact outcomes to one local manifest."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

from sensitive_patterns import SENSITIVE_PATTERN


ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_OPTION = re.compile(
    r"(?i)^--?(?:access[-_]?token|api[-_]?key|authorization|credential|email|password|secret|token)$"
)
SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)^(--?(?:access[-_]?token|api[-_]?key|authorization|credential|email|password|secret|token)=)(.*)$"
)
SENSITIVE_QUERY_VALUE = re.compile(
    r"(?i)([?&](?:access[-_]?token|api[-_]?key|authorization|credential|email|password|secret|token)=)[^&\s]*"
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def worktree_fingerprint(artifact_dir: Path | None = None) -> str:
    tracked = subprocess.check_output(["git", "diff", "--binary", "HEAD"], cwd=ROOT)
    untracked_names = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT
    )
    digest = hashlib.sha256(tracked + b"\0")
    for raw_name in filter(None, untracked_names.split(b"\0")):
        path = ROOT / raw_name.decode("utf-8")
        if artifact_dir is not None:
            try:
                path.resolve().relative_to(artifact_dir.resolve())
                continue
            except ValueError:
                pass
        digest.update(raw_name)
        digest.update(b"\0")
        if path.is_file():
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _validate_existing_manifest(artifact_dir: Path) -> dict | None:
    manifest_path = artifact_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["git_sha"] != git_sha():
        raise RuntimeError("manifest SHA differs from current HEAD")
    return manifest


def _sanitize_argv(argv: list[str]) -> list[str]:
    sanitized = []
    redact_next = False
    for argument in argv:
        if redact_next:
            sanitized.append("<redacted>")
            redact_next = False
            continue
        if SENSITIVE_OPTION.fullmatch(argument):
            sanitized.append(argument)
            redact_next = True
            continue
        assignment = SENSITIVE_ASSIGNMENT.match(argument)
        if assignment:
            sanitized.append(f"{assignment.group(1)}<redacted>")
            continue
        redacted = SENSITIVE_PATTERN.sub("<redacted>", argument)
        redacted = SENSITIVE_QUERY_VALUE.sub(r"\1<redacted>", redacted)
        sanitized.append(redacted)
    return sanitized


def append_command(
    artifact_dir: Path,
    *,
    argv: list[str],
    exit_code: int,
    started_at: str,
    finished_at: str,
    artifacts: list[str],
    cwd: Path | None = None,
) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = artifact_dir / "manifest.json"
    manifest = _validate_existing_manifest(artifact_dir)
    if manifest is None:
        manifest = {
            "schema_version": 1,
            "git_sha": git_sha(),
            "run_id": artifact_dir.name,
            "created_at": started_at,
            "environment": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "hosted_provider_call_count": 0,
            },
            "commands": [],
        }
    fingerprint = worktree_fingerprint(artifact_dir)
    manifest["worktree_fingerprint"] = fingerprint
    manifest["updated_at"] = finished_at
    manifest["commands"].append(
        {
            "argv": _sanitize_argv(argv),
            "cwd": str((cwd or ROOT).resolve()),
            "exit_code": exit_code,
            "started_at": started_at,
            "finished_at": finished_at,
            "artifacts": artifacts,
            "worktree_fingerprint": fingerprint,
        }
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def run_command(
    artifact_dir: Path,
    output: Path,
    command: list[str],
    produced_artifacts: list[Path] | None = None,
    cwd: Path = ROOT,
) -> int:
    artifact_dir = artifact_dir.resolve()
    output = output.resolve()
    try:
        relative_output = output.relative_to(artifact_dir)
    except ValueError as exc:
        raise ValueError("verification output must be inside artifact_dir") from exc
    _validate_existing_manifest(artifact_dir)
    cwd = cwd.resolve()
    try:
        cwd.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("verification cwd must be inside the repository") from exc
    if not cwd.is_dir():
        raise ValueError("verification cwd must be an existing directory")
    artifacts = [str(relative_output)]
    resolved_produced: list[tuple[Path, Path]] = []
    for produced in produced_artifacts or []:
        produced = produced.resolve()
        try:
            relative_produced = produced.relative_to(artifact_dir)
        except ValueError as exc:
            raise ValueError("produced artifact must be inside artifact_dir") from exc
        resolved_produced.append((produced, relative_produced))
        artifacts.append(str(relative_produced))
    started = _now()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        )
    finished = _now()
    append_command(
        artifact_dir,
        argv=command,
        exit_code=completed.returncode,
        started_at=started,
        finished_at=finished,
        artifacts=artifacts,
        cwd=cwd,
    )
    for produced, relative_produced in resolved_produced:
        if not produced.is_file():
            raise RuntimeError(f"expected produced artifact is missing: {relative_produced}")
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--produced-artifact", type=Path, action="append", default=[])
    parser.add_argument("--cwd", type=Path, default=ROOT)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")
    return run_command(
        args.artifact_dir,
        args.output,
        command,
        produced_artifacts=args.produced_artifact,
        cwd=args.cwd,
    )


if __name__ == "__main__":
    raise SystemExit(main())
