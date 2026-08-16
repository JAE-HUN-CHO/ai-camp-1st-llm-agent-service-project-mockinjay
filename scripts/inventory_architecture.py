#!/usr/bin/env python3
"""Emit an evidence-oriented inventory from the live FastAPI application graph."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _dependency_names(route) -> list[str]:
    dependant = getattr(route, "dependant", None)
    dependencies = getattr(dependant, "dependencies", []) if dependant else []
    names = []
    for dependency in dependencies:
        call = getattr(dependency, "call", None)
        names.append(getattr(call, "__name__", str(call)))
    return sorted(set(names))


def _classification(path: Path) -> str:
    source = path.read_text(encoding="utf-8") if path.is_file() else ""
    if "runtime" in path.name or "Protocol" in source or "class " in source:
        return "in-use" if "features/chat" in str(path) or "features/research" in str(path) else "defined-only"
    return "naming-anchor"


def build_inventory() -> dict:
    from app.main import app

    routes = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if not path:
            continue
        endpoint = getattr(route, "endpoint", None)
        methods = sorted(getattr(route, "methods", []) or [])
        response_model = getattr(route, "response_model", None)
        routes.append(
            {
                "methods": methods,
                "path": path,
                "name": getattr(route, "name", None),
                "endpoint": (
                    f"{getattr(endpoint, '__module__', '')}.{getattr(endpoint, '__name__', '')}"
                ),
                "auth_dependencies": _dependency_names(route),
                "response_model": str(response_model) if response_model else None,
                "content_type": "text/event-stream" if "stream" in path else "application/json",
            }
        )

    seams = []
    for base in (BACKEND / "app" / "features", BACKEND / "app" / "ports", BACKEND / "app" / "adapters"):
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            seams.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "classification": _classification(path),
                }
            )

    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "entrypoint": "backend/app/main.py:app",
        "route_count": len(routes),
        "routes": sorted(routes, key=lambda item: (item["path"], item["methods"])),
        "feature_port_adapter_inventory": seams,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build_inventory()
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
