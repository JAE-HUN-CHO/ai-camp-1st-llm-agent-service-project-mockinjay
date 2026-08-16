"""Selector default, invalid configuration, telemetry, and rollback drill."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.bootstrap.container import (
    ChatConfigurationError,
    ChatImplementation,
    build_chat_container,
    resolve_chat_implementation,
)


class Runtime:
    def __init__(self) -> None:
        self.chat_service_reads = 0
        self.service = object()

    @property
    def chat_service(self):
        self.chat_service_reads += 1
        return self.service


def test_missing_selector_defaults_to_legacy_without_provider_construction() -> None:
    runtime = Runtime()
    container = build_chat_container(
        context_system=object(),
        agent_runtime=runtime,
        environment={},
    )

    assert container.implementation is ChatImplementation.LEGACY
    assert container.send_chat_message is None
    assert runtime.chat_service_reads == 0


@pytest.mark.parametrize("value", ["", "LEGACY", "ollama", "fallback", "hex "])
def test_invalid_selector_fails_closed(value: str) -> None:
    with pytest.raises(ChatConfigurationError):
        resolve_chat_implementation({"CHAT_IMPLEMENTATION": value})


def test_hex_is_separate_from_provider_toggle_and_wires_use_cases() -> None:
    runtime = Runtime()
    container = build_chat_container(
        context_system=object(),
        agent_runtime=runtime,
        environment={"CHAT_IMPLEMENTATION": "hex"},
    )

    assert container.implementation is ChatImplementation.HEX
    assert container.send_chat_message is not None
    assert container.stream_chat_message is not None
    assert runtime.chat_service_reads == 1


def test_hex_with_disabled_provider_fails_instead_of_falling_back() -> None:
    runtime = Runtime()
    runtime.service = None
    with pytest.raises(ChatConfigurationError):
        build_chat_container(
            context_system=object(),
            agent_runtime=runtime,
            environment={"CHAT_IMPLEMENTATION": "hex"},
        )


def test_explicit_restart_rollback_from_hex_to_legacy() -> None:
    runtime = Runtime()
    hex_container = build_chat_container(
        context_system=object(),
        agent_runtime=runtime,
        environment={"CHAT_IMPLEMENTATION": "hex"},
    )
    legacy_container = build_chat_container(
        context_system=object(),
        agent_runtime=runtime,
        environment={"CHAT_IMPLEMENTATION": "legacy"},
    )

    assert hex_container.is_hex is True
    assert legacy_container.is_hex is False
    assert legacy_container.send_chat_message is None


def test_telemetry_contains_only_implementation_operation_outcome_and_count() -> None:
    container = build_chat_container(
        context_system=object(),
        agent_runtime=Runtime(),
        environment={},
    )
    container.telemetry.record("message", "success")
    container.telemetry.record("message", "failure")

    assert container.telemetry.snapshot() == {
        "implementation": "legacy",
        "counters": {"message.failure": 1, "message.success": 1},
    }
