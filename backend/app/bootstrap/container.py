"""Single API-process composition root for the Chat implementation selector."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import logging
import os
from typing import Any

from app.adapters.mongodb.chat_repository import MongoChatRepository
from app.adapters.ollama.chat_generator import OllamaChatGenerator
from app.core.emergency_safety import emergency_safety_policy
from app.features.chat.application import SendChatMessage, StreamChatMessage


logger = logging.getLogger(__name__)


class ChatConfigurationError(RuntimeError):
    pass


class ChatImplementation(StrEnum):
    LEGACY = "legacy"
    HEX = "hex"


class ChatTelemetry:
    """Process-local, non-sensitive counters used for rollback decisions."""

    def __init__(self, implementation: ChatImplementation) -> None:
        self._implementation = implementation
        self._counters: Counter[tuple[str, str]] = Counter()

    def record(self, operation: str, outcome: str) -> None:
        key = (operation, outcome)
        self._counters[key] += 1
        logger.info(
            "Chat implementation call implementation=%s operation=%s outcome=%s count=%d",
            self._implementation.value,
            operation,
            outcome,
            self._counters[key],
        )

    def snapshot(self) -> dict[str, object]:
        return {
            "implementation": self._implementation.value,
            "counters": {
                f"{operation}.{outcome}": count
                for (operation, outcome), count in sorted(self._counters.items())
            },
        }


@dataclass(slots=True)
class ChatContainer:
    implementation: ChatImplementation
    telemetry: ChatTelemetry
    send_chat_message: SendChatMessage | None = None
    stream_chat_message: StreamChatMessage | None = None

    @property
    def is_hex(self) -> bool:
        return self.implementation is ChatImplementation.HEX


def resolve_chat_implementation(
    environment: Mapping[str, str] | None = None,
) -> ChatImplementation:
    """Evaluate ``CHAT_IMPLEMENTATION`` exactly once per container build."""
    environment = os.environ if environment is None else environment
    raw = environment.get("CHAT_IMPLEMENTATION")
    value = "legacy" if raw is None else raw
    try:
        return ChatImplementation(value)
    except ValueError as exc:
        raise ChatConfigurationError(
            "CHAT_IMPLEMENTATION must be exactly 'legacy' or 'hex'"
        ) from exc


def build_chat_container(
    *,
    context_system: Any,
    agent_runtime: Any,
    environment: Mapping[str, str] | None = None,
) -> ChatContainer:
    implementation = resolve_chat_implementation(environment)
    telemetry = ChatTelemetry(implementation)
    if implementation is ChatImplementation.LEGACY:
        return ChatContainer(implementation=implementation, telemetry=telemetry)

    service = agent_runtime.chat_service
    if service is None:
        raise ChatConfigurationError(
            "CHAT_IMPLEMENTATION=hex requires the local Ollama provider to be enabled"
        )
    repository = MongoChatRepository(context_system)
    generator = OllamaChatGenerator(service)
    return ChatContainer(
        implementation=implementation,
        telemetry=telemetry,
        send_chat_message=SendChatMessage(
            repository,
            generator,
            emergency_safety_policy,
        ),
        stream_chat_message=StreamChatMessage(
            repository,
            generator,
            emergency_safety_policy,
        ),
    )


def get_chat_container(request: Any) -> ChatContainer:
    """Return the one container owned by this FastAPI application."""
    container = getattr(request.app.state, "chat_container", None)
    if container is None:
        from app.features.chat.runtime import get_context_system
        from app.services.agent_runtime import get_agent_runtime

        container = build_chat_container(
            context_system=get_context_system(request),
            agent_runtime=get_agent_runtime(request),
        )
        request.app.state.chat_container = container
    return container
