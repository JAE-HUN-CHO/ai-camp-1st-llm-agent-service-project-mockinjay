#!/usr/bin/env python3
"""Fail when a verification artifact contains credential or PII canaries."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


PATTERN = re.compile(
    r"(?i)(?:"
    r"bearer\s+[a-z0-9._~+/=-]+|"
    r"eyJ[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+|"
    r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}|"
    r"(?:pii|health|token)[_-]?canary(?:[-_][a-z0-9.]+)+"
    r")"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()
    matches = []
    for path in args.artifact_dir.rglob("*"):
        if not path.is_file() or path.name == "pii-scan.txt":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if PATTERN.search(text):
            matches.append(str(path.relative_to(args.artifact_dir)))
    print(f"PII artifact matches: {len(matches)}")
    if matches:
        print("\n".join(matches))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
