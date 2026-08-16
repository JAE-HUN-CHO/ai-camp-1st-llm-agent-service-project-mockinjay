"""Static canary gate for credential/chat/health browser sinks."""

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


def _console_argument_code(source: str, open_paren: int) -> str | None:
    """Extract executable argument code while ignoring literal/comment text.

    Parentheses are balanced across nested calls, and template interpolation is
    scanned as code while the template's literal portion remains ignored.
    """
    output: list[str] = []
    mode = "code"
    return_stack: list[tuple[str, int | None]] = []
    interpolation_depth: int | None = None
    parenthesis_depth = 1
    index = open_paren + 1

    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""

        if mode == "code":
            if char in ("'", '"'):
                return_stack.append(("code", interpolation_depth))
                mode = char
                output.append(" ")
            elif char == "`":
                return_stack.append(("code", interpolation_depth))
                mode = "template"
                output.append(" ")
            elif char == "/" and next_char == "/":
                return_stack.append(("code", interpolation_depth))
                mode = "line_comment"
                output.append(" ")
                index += 1
            elif char == "/" and next_char == "*":
                return_stack.append(("code", interpolation_depth))
                mode = "block_comment"
                output.append(" ")
                index += 1
            elif interpolation_depth is not None and char == "{":
                interpolation_depth += 1
                output.append(char)
            elif interpolation_depth is not None and char == "}":
                interpolation_depth -= 1
                if interpolation_depth == 0:
                    mode, interpolation_depth = return_stack.pop()
                    output.append(" ")
                else:
                    output.append(char)
            elif char == "(":
                parenthesis_depth += 1
                output.append(char)
            elif char == ")":
                parenthesis_depth -= 1
                if parenthesis_depth == 0:
                    return "".join(output)
                output.append(char)
            else:
                output.append(char)
        elif mode in ("'", '"'):
            if char == "\\":
                index += 1
            elif char == mode:
                mode, interpolation_depth = return_stack.pop()
                output.append(" ")
        elif mode == "template":
            if char == "\\":
                index += 1
            elif char == "`":
                mode, interpolation_depth = return_stack.pop()
                output.append(" ")
            elif char == "$" and next_char == "{":
                return_stack.append(("template", None))
                mode = "code"
                interpolation_depth = 1
                output.append(" ")
                index += 1
        elif mode == "line_comment":
            if char == "\n":
                mode, interpolation_depth = return_stack.pop()
                output.append("\n")
        elif mode == "block_comment" and char == "*" and next_char == "/":
            mode, interpolation_depth = return_stack.pop()
            output.append(" ")
            index += 1

        index += 1
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
