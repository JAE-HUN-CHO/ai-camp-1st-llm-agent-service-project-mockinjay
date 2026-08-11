"""Check the explicit frontend consolidation parity contract.

This is intentionally a contract check, not a byte-for-byte comparison:
``frontend`` is the canonical feature source and rollback trees may contain aliases or
deprecated screens that are represented by redirects/placeholders.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

FEATURES = {
    "auth": ["/login", "/signup"],
    "chat": ["/chat", "/chat/medical-welfare", "/chat/nutrition", "/chat/research"],
    "diet": ["/diet-care", "/diet-care/nutri-coach", "/diet-care/diet-log"],
    "health": ["/mypage/test-results", "/mypage/test-results/add"],
    "research": ["/trends", "/news/detail/:id"],
    "community": ["/community", "/community/detail/:id"],
    "quiz": ["/quiz", "/quiz/play", "/quiz/completion"],
    "account": ["/mypage", "/mypage/profile", "/notifications"],
    "legal": ["/support", "/terms-and-conditions", "/privacy-policy", "/cookie-consent"],
}

API_CONTRACTS = {
    "chat": [["/api/chat/message"], ["/api/chat/stream"], ["/api/rooms"], ["/api/session"]],
    "diet": [["/api/diet-care"], ["/api/diet-care/nutri-coach", "/api/nutrition/analyze"]],
    "health": [["/api/health-records"]],
    "research": [["/api/trends"], ["/api/clinical-trials"], ["/api/news"]],
    "community": [["/api/community"]],
    "quiz": [["/api/quiz"]],
    "account": [["/api/mypage"], ["/api/bookmarks"], ["/api/mypage/notifications", "/api/notification", "MYPAGE_BASE}/notifications"]],
}


def _route_values(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r'path\s*=\s*["\']([^"\']+)', text))


def _all_text(root: Path) -> str:
    return "\n".join(
        item.read_text(encoding="utf-8", errors="ignore")
        for item in root.rglob("*")
        if item.is_file() and item.suffix in {".ts", ".tsx", ".js", ".jsx"}
    )


def build_report(repo: Path) -> dict[str, object]:
    canonical = repo / "frontend"
    rollback_source = repo / "logs" / "rollback" / "new_frontend-rollback"
    routes_file = canonical / "src/routes/AppRoutes.tsx"
    routes = _route_values(routes_file)
    canonical_text = _all_text(canonical / "src")
    required_routes = {route for values in FEATURES.values() for route in values}
    route_missing = sorted(route for route in required_routes if route not in routes and route not in canonical_text)

    api_missing = {
        feature: [alternatives for alternatives in endpoint_groups if not any(endpoint in canonical_text for endpoint in alternatives)]
        for feature, endpoint_groups in API_CONTRACTS.items()
    }
    api_missing = {feature: endpoints for feature, endpoints in api_missing.items() if endpoints}

    tests = list((canonical / "src").rglob("*.test.*"))
    test_text = "\n".join(path.name.lower() for path in tests)
    feature_test_missing = [] if "approutesparity" in test_text else [
        feature for feature in FEATURES if feature not in test_text and feature != "legal"
    ]

    legacy_assets = {
        str(path.relative_to(rollback_source / "public"))
        for path in (rollback_source / "public").rglob("*")
        if path.is_file()
    }
    canonical_assets = {
        str(path.relative_to(canonical / "public"))
        for path in (canonical / "public").rglob("*")
        if path.is_file()
    }

    return {
        "source": "frontend",
        "legacy_trees": ["logs/rollback/new_frontend-rollback", "logs/rollback/stitch_frontend-rollback"],
        "route_missing": route_missing,
        "api_missing": api_missing,
        "feature_test_missing": feature_test_missing,
        "legacy_public_assets": sorted(legacy_assets),
        "canonical_public_assets": sorted(canonical_assets),
        "legacy_only_public_assets": sorted(legacy_assets - canonical_assets),
        "status": "PASS" if not route_missing and not api_missing and not feature_test_missing else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args.repo)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
