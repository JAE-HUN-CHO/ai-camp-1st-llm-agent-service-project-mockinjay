#!/usr/bin/env python3
"""Fail when a verification artifact contains credential or PII canaries."""

from __future__ import annotations

import argparse
from pathlib import Path

from sensitive_patterns import SENSITIVE_PATTERN

PATTERN = SENSITIVE_PATTERN


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()
    if not args.artifact_dir.is_dir():
        print("PII artifact scan failed: artifact directory does not exist")
        return 1
    matches = []
    scanned = 0
    report_path = args.artifact_dir / "privacy" / "pii-scan.txt"
    for path in args.artifact_dir.rglob("*"):
        if not path.is_file() or path == report_path:
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        if PATTERN.search(text):
            matches.append(str(path.relative_to(args.artifact_dir)))
    print(f"PII artifact matches: {len(matches)}")
    print(f"PII artifact files scanned: {scanned}")
    if scanned == 0:
        print("PII artifact scan failed: no evidence files found")
        return 1
    if matches:
        print("\n".join(matches))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
