"""Validate relative links in the current normative document set."""

from __future__ import annotations

import re
from pathlib import Path

NORMATIVE = (
    Path("AGENTS.md"),
    Path("docs/AGENTS.md"),
    Path("docs/README.md"),
    Path("docs/agents/domain.md"),
    Path("docs/agents/BOUNDARY_MAP.md"),
    Path("docs/agents/CACHE_POLICY.md"),
    Path("docs/agents/DOCUMENT_CONSISTENCY_MATRIX.md"),
    Path("docs/adr/README.md"),
    Path("docs/adr/ADR-004-clinical-trials-scope.md"),
    Path("docs/adr/ADR-005-vector-db.md"),
    Path("docs/adr/ADR-006-payment-mvp-scope.md"),
    Path("docs/adr/ADR-008-single-frontend-root.md"),
    Path("docs/adr/ADR-009-local-first-runtime.md"),
    Path("docs/adr/ADR-010-local-embedding-dimension-policy.md"),
    Path("docs/adr/ADR-011-current-runtime-contract.md"),
)
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def main() -> int:
    missing: list[str] = []
    for relative_path in NORMATIVE:
        path = Path(relative_path)
        if not path.is_file():
            missing.append(str(path))
            continue
        for target in MARKDOWN_LINK.findall(path.read_text(encoding="utf-8")):
            target = target.split("#", 1)[0].strip().strip("<>")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.is_file():
                missing.append(f"{path}: {target}")

    if missing:
        print("Documentation links: FAIL")
        print("\n".join(missing))
        return 1
    print(f"Documentation links: PASS ({len(NORMATIVE)} normative files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
