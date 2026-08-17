"""Single API-process composition root for incremental implementation selectors."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import logging
import os
from threading import Lock
from typing import Any

from fastapi import Request

from app.adapters.mongodb.health_profile_repository import MongoHealthProfileRepository
from app.adapters.mongodb.health_record_repository import MongoHealthRecordRepository
from app.adapters.mongodb.chat_repository import MongoChatRepository
from app.adapters.ollama.chat_generator import OllamaChatGenerator
from app.core.emergency_safety import emergency_safety_policy
from app.db.connection import get_health_profiles_collection, get_health_records_collection
from app.features.chat.application import SendChatMessage, StreamChatMessage
from app.features.health.application import (
    CreateHealthRecord,
    DeleteHealthRecord,
    GetHealthProfile,
    ListHealthRecords,
    UpdateHealthProfile,
    UpdateHealthRecord,
)
from app.services.health_profile_legacy import LegacyHealthProfileFacade
from app.services.health_records_legacy import LegacyHealthRecordsFacade


logger = logging.getLogger(__name__)


class ChatConfigurationError(RuntimeError):
    pass


class ChatImplementation(StrEnum):
    LEGACY = "legacy"
    HEX = "hex"


class HealthRecordsConfigurationError(RuntimeError):
    pass


class HealthRecordsImplementation(StrEnum):
    LEGACY = "legacy"
    HEX = "hex"


class HealthProfileConfigurationError(RuntimeError):
    pass


HEALTH_PROFILE_IMPLEMENTATION_ERROR = (
    "HEALTH_PROFILE_IMPLEMENTATION must be exactly 'legacy' or 'hex'"
)


class HealthProfileImplementation(StrEnum):
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


class HealthRecordsTelemetry:
    """Process-local counters containing no record IDs or health values."""

    def __init__(self, implementation: HealthRecordsImplementation) -> None:
        self._implementation = implementation
        self._counters: Counter[tuple[str, str]] = Counter()

    def record(self, operation: str, outcome: str) -> None:
        key = (operation, outcome)
        self._counters[key] += 1
        logger.info(
            "Health Records implementation call implementation=%s operation=%s "
            "outcome=%s count=%d",
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


class HealthProfileTelemetry:
    """Process-local counters containing no actor or health values."""

    def __init__(self, implementation: HealthProfileImplementation) -> None:
        """Initialize thread-safe health-profile implementation counters."""
        self._implementation = implementation
        self._counters: Counter[tuple[str, str]] = Counter()
        self._lock = Lock()

    def record(self, operation: str, outcome: str) -> None:
        """Record one non-sensitive implementation outcome."""
        key = (operation, outcome)
        with self._lock:
            self._counters[key] += 1
            count = self._counters[key]
        logger.info(
            "Health Profile implementation call implementation=%s operation=%s "
            "outcome=%s count=%d",
            self._implementation.value,
            operation,
            outcome,
            count,
        )

    def snapshot(self) -> dict[str, object]:
        """Return a stable copy of the current telemetry counters."""
        with self._lock:
            counters = {
                f"{operation}.{outcome}": count
                for (operation, outcome), count in sorted(self._counters.items())
            }
        return {
            "implementation": self._implementation.value,
            "counters": counters,
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


@dataclass(slots=True)
class HealthRecordsContainer:
    implementation: HealthRecordsImplementation
    telemetry: HealthRecordsTelemetry
    legacy: LegacyHealthRecordsFacade | None = None
    list_health_records: ListHealthRecords | None = None
    create_health_record: CreateHealthRecord | None = None
    update_health_record: UpdateHealthRecord | None = None
    delete_health_record: DeleteHealthRecord | None = None

    @property
    def is_hex(self) -> bool:
        return self.implementation is HealthRecordsImplementation.HEX


@dataclass(slots=True)
class HealthProfileContainer:
    implementation: HealthProfileImplementation
    telemetry: HealthProfileTelemetry
    legacy: LegacyHealthProfileFacade | None = None
    get_health_profile: GetHealthProfile | None = None
    update_health_profile: UpdateHealthProfile | None = None

    @property
    def is_hex(self) -> bool:
        """Report whether the composition root selected the hex implementation."""
        return self.implementation is HealthProfileImplementation.HEX


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


def resolve_health_records_implementation(
    environment: Mapping[str, str] | None = None,
) -> HealthRecordsImplementation:
    """Evaluate ``HEALTH_RECORDS_IMPLEMENTATION`` once per container build."""
    environment = os.environ if environment is None else environment
    raw = environment.get("HEALTH_RECORDS_IMPLEMENTATION")
    value = "legacy" if raw is None else raw
    try:
        return HealthRecordsImplementation(value)
    except ValueError as exc:
        raise HealthRecordsConfigurationError(
            "HEALTH_RECORDS_IMPLEMENTATION must be exactly 'legacy' or 'hex'"
        ) from exc


def resolve_health_profile_implementation(
    environment: Mapping[str, str] | None = None,
) -> HealthProfileImplementation:
    """Evaluate ``HEALTH_PROFILE_IMPLEMENTATION`` once per container build."""
    environment = os.environ if environment is None else environment
    raw = environment.get("HEALTH_PROFILE_IMPLEMENTATION")
    value = "legacy" if raw is None else raw
    try:
        return HealthProfileImplementation(value)
    except ValueError as exc:
        raise HealthProfileConfigurationError(HEALTH_PROFILE_IMPLEMENTATION_ERROR) from exc


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


def build_health_records_container(
    *, environment: Mapping[str, str] | None = None
) -> HealthRecordsContainer:
    """Build exactly one selected Health Records implementation."""
    implementation = resolve_health_records_implementation(environment)
    telemetry = HealthRecordsTelemetry(implementation)
    if implementation is HealthRecordsImplementation.LEGACY:
        return HealthRecordsContainer(
            implementation=implementation,
            telemetry=telemetry,
            legacy=LegacyHealthRecordsFacade(get_health_records_collection),
        )

    repository = MongoHealthRecordRepository(get_health_records_collection)
    return HealthRecordsContainer(
        implementation=implementation,
        telemetry=telemetry,
        list_health_records=ListHealthRecords(repository),
        create_health_record=CreateHealthRecord(repository),
        update_health_record=UpdateHealthRecord(repository),
        delete_health_record=DeleteHealthRecord(repository),
    )


def build_health_profile_container(
    *, environment: Mapping[str, str] | None = None
) -> HealthProfileContainer:
    """Build exactly one selected MyPage Health Profile implementation."""
    implementation = resolve_health_profile_implementation(environment)
    telemetry = HealthProfileTelemetry(implementation)
    if implementation is HealthProfileImplementation.LEGACY:
        return HealthProfileContainer(
            implementation=implementation,
            telemetry=telemetry,
            legacy=LegacyHealthProfileFacade(),
        )

    repository = MongoHealthProfileRepository(get_health_profiles_collection)
    return HealthProfileContainer(
        implementation=implementation,
        telemetry=telemetry,
        get_health_profile=GetHealthProfile(repository),
        update_health_profile=UpdateHealthProfile(repository),
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


def get_health_records_container(request: Request) -> HealthRecordsContainer:
    """Return the Health Records container owned by this FastAPI application."""
    container = getattr(request.app.state, "health_records_container", None)
    if container is None:
        container = build_health_records_container()
        request.app.state.health_records_container = container
    return container


def get_health_profile_container(request: Request) -> HealthProfileContainer:
    """Return the Health Profile container owned by this FastAPI application."""
    container = getattr(request.app.state, "health_profile_container", None)
    if container is None:
        container = build_health_profile_container()
        request.app.state.health_profile_container = container
    return container
