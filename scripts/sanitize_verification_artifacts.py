#!/usr/bin/env python3
"""Remove host identity, raw parametrized fixtures, and token-sized hashes from evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def _digest(value: str) -> dict[str, int | str]:
    encoded = value.encode("utf-8")
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "bytes": len(encoded)}


def sanitize_junit(path: Path) -> dict[str, int]:
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
