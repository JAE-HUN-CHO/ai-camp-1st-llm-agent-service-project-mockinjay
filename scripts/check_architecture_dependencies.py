#!/usr/bin/env python3
"""AST dependency gate for the approved Phase-0 seams.

Existing legacy observations are inventoried but do not become a destructive
cleanup gate before an approved slice migration. New domain/application/port seams fail
when they import framework, SDK, database, or sibling-feature implementations.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "backend" / "app"
FORBIDDEN = ("fastapi", "motor", "pymongo", "parlant", "ollama", "app.db", "app.adapters")


def _relative_import(path: Path, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    module_parts = ["app", *path.relative_to(APP).with_suffix("").parts]
    package_parts = module_parts[:-1]
    keep = len(package_parts) - (node.level - 1)
    base = package_parts[: max(0, keep)]
    return ".".join([*base, *((node.module or "").split("."))]).rstrip(".")


def _matches_module(imported: str, prefix: str) -> bool:
    return imported == prefix or imported.startswith(f"{prefix}.")


def imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            result.append((node.lineno, _relative_import(path, node)))
    return result


def scan() -> dict:
    violations = []
    checked = []
    candidates = list((APP / "ports").glob("*.py"))
    candidates += list((APP / "features").glob("*/domain.py"))
    candidates += list((APP / "features").glob("*/application.py"))
    candidates += list((APP / "features").glob("*/ports.py"))
    for path in sorted(set(candidates)):
        checked.append(str(path.relative_to(ROOT)))
        feature = path.parent.name if "features" in path.parts else None
        for line, imported in imports(path):
            reason = None
            if any(_matches_module(imported, prefix) for prefix in FORBIDDEN):
                reason = "infrastructure import in inner seam"
            own_feature = f"app.features.{feature}" if feature else None
            if (
                feature
                and _matches_module(imported, "app.features")
                and own_feature
                and not _matches_module(imported, own_feature)
            ):
                reason = "cross-feature implementation import"
            if reason:
                violations.append(
                    {
                        "path": str(path.relative_to(ROOT)),
                        "line": line,
                        "import": imported,
                        "reason": reason,
                    }
                )
    return {
        "schema_version": 1,
        "checked": checked,
        "enforced_violation_count": len(violations),
        "enforced_violations": violations,
        "legacy_scope": "inventory-only until each file enters an approved slice migration",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = scan()
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 1 if payload["enforced_violation_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
