#!/usr/bin/env python3
"""Fail when a verification artifact contains credential or PII canaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sensitive_patterns import SENSITIVE_PATTERN

PATTERN = SENSITIVE_PATTERN


def main() -> int:
    """
    명령줄 인자로 지정한 아티팩트 디렉터리에서 민감 정보 패턴을 검사하고 결과를 출력합니다.
    
    JSON 출력 경로가 지정되면 검사 결과를 해당 파일에 기록합니다.
    
    Returns:
    	int: 검사 성공 시 0, 디렉터리가 없거나 검사할 파일이 없거나 일치 항목이 발견되면 1
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    if not args.artifact_dir.is_dir():
        print("PII artifact scan failed: artifact directory does not exist")
        return 1
    matches = []
    scanned = 0
    excluded_paths = {args.artifact_dir / "privacy" / "pii-scan.txt"}
    if args.json_output is not None:
        excluded_paths.add(args.json_output)
    for path in args.artifact_dir.rglob("*"):
        if not path.is_file() or path in excluded_paths:
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        if PATTERN.search(text):
            matches.append(str(path.relative_to(args.artifact_dir)))
    print(f"PII artifact matches: {len(matches)}")
    print(f"PII artifact files scanned: {scanned}")
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "files_scanned": scanned,
                    "canary_matches": len(matches),
                    "matching_files": matches,
                    "result": "pass" if scanned > 0 and not matches else "fail",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if scanned == 0:
        print("PII artifact scan failed: no evidence files found")
        return 1
    if matches:
        print("\n".join(matches))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
