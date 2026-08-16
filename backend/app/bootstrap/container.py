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
        """선택된 채팅 구현에 대한 텔레메트리 카운터를 초기화합니다.
        
        Parameters:
        	implementation (ChatImplementation): 카운터에 기록할 채팅 구현
        """
        self._implementation = implementation
        self._counters: Counter[tuple[str, str]] = Counter()

    def record(self, operation: str, outcome: str) -> None:
        """
        채팅 구현의 작업 및 결과 조합에 대한 호출 횟수를 기록합니다.
        
        Parameters:
        	operation (str): 기록할 작업 이름
        	outcome (str): 작업 결과
        """
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
        """
        텔레메트리 구현 정보와 정렬된 작업별 결과 카운터의 스냅샷을 생성합니다.
        
        Returns:
        	dict[str, object]: 구현 식별자와 `"operation.outcome"` 형식의 카운터를 포함하는 스냅샷
        """
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
        """구성된 채팅 구현이 `hex`인지 확인합니다.
        
        Returns:
        	bool: 구현이 `hex`이면 `true`, 그렇지 않으면 `false`.
        """
        return self.implementation is ChatImplementation.HEX


def resolve_chat_implementation(
    environment: Mapping[str, str] | None = None,
) -> ChatImplementation:
    """
    CHAT_IMPLEMENTATION 설정에서 사용할 채팅 구현을 결정합니다.
    
    Args:
        environment (Mapping[str, str] | None): 설정을 읽을 환경 매핑입니다. 생략하면 프로세스 환경 변수를 사용합니다.
    
    Returns:
        ChatImplementation: 선택된 채팅 구현입니다.
    
    Raises:
        ChatConfigurationError: 설정값이 `legacy` 또는 `hex`가 아닌 경우 발생합니다.
    """
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
    """
    채팅 구현에 필요한 컨테이너와 의존성을 구성합니다.
    
    Parameters:
    	context_system (Any): MongoDB 채팅 저장소에 사용할 컨텍스트 시스템
    	agent_runtime (Any): Ollama 채팅 서비스 제공 여부를 포함한 에이전트 런타임
    	environment (Mapping[str, str] | None): 채팅 구현 선택에 사용할 환경 변수 매핑
    
    Returns:
    	ChatContainer: 선택된 구현과 텔레메트리, 사용 가능한 채팅 서비스를 담은 컨테이너
    
    Raises:
    	ChatConfigurationError: 선택한 `hex` 구현에 필요한 채팅 서비스가 없을 때
    """
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
    """
    FastAPI 애플리케이션에 캐시된 채팅 컨테이너를 가져오거나 생성합니다.
    
    애플리케이션 상태에 컨테이너가 없으면 현재 요청의 컨텍스트와 에이전트 런타임으로 생성한 뒤 저장합니다.
    
    Parameters:
    	request (Any): 채팅 컨테이너를 조회할 FastAPI 요청
    
    Returns:
    	ChatContainer: 애플리케이션이 사용하는 채팅 컨테이너
    """
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
