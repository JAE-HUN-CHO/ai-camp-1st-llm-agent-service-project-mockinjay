"""Static canary gate for credential/chat/health browser sinks."""

from dataclasses import dataclass, field
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend" / "src"
CONSOLE_CALL = re.compile(
    r"console\.(?:log|info|warn|error|debug)\s*\(",
)
RAW_CONSOLE_VALUE = re.compile(
    r"\b(?:error|err|e|user|data|buffer|query|message|profile|record|health|"
    r"token|session|response|payload|content)\b|\.substring\s*\(",
    re.IGNORECASE,
)


@dataclass
class _ConsoleScanState:
    output: list[str] = field(default_factory=list)
    mode: str = "code"
    return_stack: list[tuple[str, int | None]] = field(default_factory=list)
    interpolation_depth: int | None = None
    parenthesis_depth: int = 1


def _enter_ignored_mode(state: _ConsoleScanState, mode: str) -> None:
    state.return_stack.append(("code", state.interpolation_depth))
    state.mode = mode
    state.output.append(" ")


def _resume_mode(state: _ConsoleScanState) -> None:
    state.mode, state.interpolation_depth = state.return_stack.pop()
    state.output.append(" ")


def _scan_code(
    state: _ConsoleScanState, char: str, next_char: str
) -> tuple[int, bool]:
    if char in ("'", '"'):
        _enter_ignored_mode(state, char)
    elif char == "`":
        _enter_ignored_mode(state, "template")
    elif char == "/" and next_char in ("/", "*"):
        comment_mode = "line_comment" if next_char == "/" else "block_comment"
        _enter_ignored_mode(state, comment_mode)
        return 2, False
    elif state.interpolation_depth is not None and char == "{":
        state.interpolation_depth += 1
        state.output.append(char)
    elif state.interpolation_depth is not None and char == "}":
        state.interpolation_depth -= 1
        if state.interpolation_depth == 0:
            _resume_mode(state)
        else:
            state.output.append(char)
    elif char == "(":
        state.parenthesis_depth += 1
        state.output.append(char)
    elif char == ")":
        state.parenthesis_depth -= 1
        if state.parenthesis_depth == 0:
            return 1, True
        state.output.append(char)
    else:
        state.output.append(char)
    return 1, False


def _scan_string(state: _ConsoleScanState, char: str) -> int:
    if char == "\\":
        return 2
    if char == state.mode:
        _resume_mode(state)
    return 1


def _scan_template(state: _ConsoleScanState, char: str, next_char: str) -> int:
    if char == "\\":
        return 2
    if char == "`":
        _resume_mode(state)
        return 1
    if char == "$" and next_char == "{":
        state.return_stack.append(("template", None))
        state.mode = "code"
        state.interpolation_depth = 1
        state.output.append(" ")
        return 2
    return 1


def _scan_comment(state: _ConsoleScanState, char: str, next_char: str) -> int:
    if state.mode == "line_comment" and char == "\n":
        _resume_mode(state)
        state.output.append("\n")
    elif state.mode == "block_comment" and char == "*" and next_char == "/":
        _resume_mode(state)
        return 2
    return 1


def _console_argument_code(source: str, open_paren: int) -> str | None:
    """Extract executable argument code while ignoring literal/comment text.

    Parentheses are balanced across nested calls, and template interpolation is
    scanned as code while the template's literal portion remains ignored.
    """
    state = _ConsoleScanState()
    index = open_paren + 1

    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if state.mode == "code":
            advance, complete = _scan_code(state, char, next_char)
            if complete:
                return "".join(state.output)
        elif state.mode in ("'", '"'):
            advance = _scan_string(state, char)
        elif state.mode == "template":
            advance = _scan_template(state, char, next_char)
        else:
            advance = _scan_comment(state, char, next_char)
        index += advance
    return None


def _find_raw_console_sink_lines(source: str) -> list[int]:
    violations = []
    for match in CONSOLE_CALL.finditer(source):
        argument_code = _console_argument_code(source, match.end() - 1)
        if argument_code is not None and RAW_CONSOLE_VALUE.search(argument_code):
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


def test_console_sink_detector_covers_nested_multiline_and_template_calls() -> None:
    source = """console.error(error)
console.log(user)
console.info(data)
console.log(
  buffer
)
console.log(JSON.stringify(safe), user)
console.log(`token=${token}`)
console.error('safe generic message')
console.log(JSON.stringify({ label: 'user' }), safe)
console.log(`token literal only`)
"""

    assert _find_raw_console_sink_lines(source) == [1, 2, 3, 4, 7, 8]
