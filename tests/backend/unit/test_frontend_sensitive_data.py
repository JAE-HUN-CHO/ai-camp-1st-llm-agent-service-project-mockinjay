"""Static canary gate for credential/chat/health browser sinks."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend" / "src"
CONSOLE_CALL = re.compile(
    r"console\.(?:log|info|warn|error|debug)\s*\((.*?)\)",
    re.DOTALL,
)
STRING_LITERAL = re.compile(
    r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)''',
    re.DOTALL,
)
RAW_CONSOLE_VALUE = re.compile(
    r"\b(?:error|err|e|user|data|buffer|query|message|profile|record|health|"
    r"token|session|response|payload|content)\b|\.substring\s*\(",
    re.IGNORECASE,
)


def _find_raw_console_sink_lines(source: str) -> list[int]:
    violations = []
    for match in CONSOLE_CALL.finditer(source):
        arguments_without_literals = STRING_LITERAL.sub("", match.group(1))
        if RAW_CONSOLE_VALUE.search(arguments_without_literals):
            violations.append(source.count("\n", 0, match.start()) + 1)
    return violations


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
    violations = []
    for path in sensitive_paths:
        assert path.is_file(), f"sensitive sink inventory path is missing: {path.relative_to(ROOT)}"
        source = path.read_text(encoding="utf-8")
        for line_no in _find_raw_console_sink_lines(source):
            violations.append(f"{path.relative_to(ROOT)}:{line_no}")
    assert violations == [], "raw sensitive console sinks found:\n" + "\n".join(violations)


def test_console_sink_detector_covers_single_argument_and_multiline_calls() -> None:
    source = """console.error(error)
console.log(user)
console.info(data)
console.log(
  buffer
)
console.error('safe generic message')
"""

    assert _find_raw_console_sink_lines(source) == [1, 2, 3, 4]
