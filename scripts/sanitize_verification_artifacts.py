#!/usr/bin/env python3
"""Remove host identity, raw parametrized fixtures, and token-sized hashes from evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def _digest(value: str) -> dict[str, int | str]:
    """
    문자열의 SHA-256 해시와 UTF-8 인코딩 기준 바이트 수를 계산합니다.
    
    Parameters:
        value (str): 해시와 바이트 수를 계산할 문자열
    
    Returns:
        dict[str, int | str]: ``sha256`` 해시 문자열과 ``bytes`` 바이트 수를 담은 딕셔너리
    """
    encoded = value.encode("utf-8")
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "bytes": len(encoded)}


def sanitize_junit(path: Path) -> dict[str, int]:
    """
    JUnit XML 파일의 호스트명, 매개변수화된 테스트 이름 및 캡처된 출력을 익명화합니다.
    
    Parameters:
    	path (Path): 처리하고 결과를 덮어쓸 JUnit XML 파일 경로
    
    Returns:
    	dict[str, int]: 익명화한 호스트명, 해시한 매개변수 및 캡처된 출력의 개수
    """
    tree = ET.parse(path)
    root = tree.getroot()
    hostnames = 0
    parameters = 0
    captured_outputs = 0
    for element in root.iter():
        if "hostname" in element.attrib:
            element.set("hostname", "redacted")
            hostnames += 1
        if element.tag == "testcase":
            name = element.get("name", "")
            if "[" in name and name.endswith("]"):
                base, parameter = name.split("[", 1)
                element.set(
                    "name",
                    f"{base}[case-{hashlib.sha256(parameter.encode('utf-8')).hexdigest()[:12]}]",
                )
                parameters += 1
        if element.tag in {"system-out", "system-err"} and element.text:
            element.text = json.dumps(_digest(element.text), sort_keys=True)
            captured_outputs += 1
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return {
        "hostnames_redacted": hostnames,
        "parameters_hashed": parameters,
        "captured_outputs_hashed": captured_outputs,
    }


def sanitize_stream(path: Path) -> dict[str, int]:
    """
    JSONL 스트림에서 콘텐츠 및 오류 객체의 민감한 내용을 제거하고 바이트 수를 보존합니다.
    
    Parameters:
    	path (Path): 정제할 JSONL 파일의 경로
    
    Returns:
    	dict[str, int]: 제거된 비종료 레코드 콘텐츠와 오류 객체의 개수를 담은 결과
    """
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    short_content_hashes = 0
    error_hashes = 0
    for record in records:
        if record.get("status") not in {"complete", "success"}:
            content = record.pop("content", None)
            if isinstance(content, dict) and isinstance(content.get("bytes"), int):
                record["content_bytes"] = content["bytes"]
                short_content_hashes += 1
        error = record.pop("error", None)
        if isinstance(error, dict) and isinstance(error.get("bytes"), int):
            record["error_bytes"] = error["bytes"]
            error_hashes += 1
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return {
        "nonterminal_content_hashes_removed": short_content_hashes,
        "error_hashes_removed": error_hashes,
    }


def main() -> int:
    """
    명령줄 인자로 지정된 JUnit 파일과 채팅 스트림을 정제하고 결과를 JSON으로 출력합니다.
    
    Returns:
    	int: 처리가 완료되었음을 나타내는 종료 상태 코드 0
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, action="append", default=[])
    parser.add_argument("--chat-stream", type=Path, action="append", default=[])
    args = parser.parse_args()
    report = {
        "junit": {str(path): sanitize_junit(path) for path in args.junit},
        "chat_stream": {str(path): sanitize_stream(path) for path in args.chat_stream},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
