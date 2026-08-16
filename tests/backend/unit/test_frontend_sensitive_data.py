"""Static canary gate for credential/chat/health browser sinks."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend" / "src"


def test_sensitive_state_is_never_written_or_restored_from_local_storage() -> None:
    violations = []
    pattern = re.compile(
        r"localStorage\.(?:getItem|setItem)\([^\n]*(?:token|user|chat|session|health)",
        re.IGNORECASE,
    )
    for path in FRONTEND.rglob("*.ts*"):
        if "__tests__" in path.parts or path.name.endswith(".example.tsx"):
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if pattern.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{line_no}")
    assert violations == []


def test_chat_auth_health_console_calls_do_not_include_raw_values() -> None:
    sensitive_paths = [
        FRONTEND / "components" / "ChatInterface.tsx",
        FRONTEND / "components" / "Layout.tsx",
        FRONTEND / "contexts" / "AuthContext.tsx",
        FRONTEND / "contexts" / "SessionContext.tsx",
        FRONTEND / "features" / "chat" / "ChatPage.tsx",
        FRONTEND / "features" / "health" / "HealthRecordsPage.tsx",
        FRONTEND / "hooks" / "useChatSession.ts",
    ]
    forbidden = re.compile(r"console\.(?:log|warn|error|debug)\([^\n]*(?:,\s*(?:error|err|e|user|data|buffer)|substring\()")
    violations = []
    for path in sensitive_paths:
        assert path.is_file(), f"sensitive sink inventory path is missing: {path.relative_to(ROOT)}"
        source = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(source.splitlines(), start=1):
            if forbidden.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{line_no}")
    assert violations == [], "raw sensitive console sinks found:\n" + "\n".join(violations)
