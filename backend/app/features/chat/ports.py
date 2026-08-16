"""Consumer-owned outbound ports for Chat.

Decision record:

* ``app.ports.llm.LLMProvider`` is not reused because its prompt/string
  signatures cannot preserve the current grounded response, source metadata,
  profile, or SSE frame contract.
* ``ChatRepository`` is new because no existing Protocol owns room/session
  authorization plus conversation persistence.
* ``AgentRouter`` is intentionally not introduced in Phase 2.  The frozen
  canonical path bypasses RouterAgent; routing it now would be a behavior
  migration.  The legacy Router/RemoteAgent facade remains available.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import Protocol

from app.core.actor import ActorContext
from app.features.chat.domain import ChatGeneration, ChatMessage, ChatStreamEvent


class ChatRepository(Protocol):
    async def authorize_actor(self, actor: ActorContext) -> ActorContext:
        """
        행위자의 접근 권한을 확인하고 소유자에 연결된 컨텍스트를 제공합니다.
        
        Parameters:
        	actor (ActorContext): 권한을 확인할 행위자 컨텍스트
        
        Returns:
        	ActorContext: 권한이 확인된 소유자 연결 행위자 컨텍스트
        """

    async def get_user_context(self, actor: ActorContext) -> Mapping[str, object]:
        """
        승인된 행위자에게 속한 사용자 컨텍스트를 조회합니다.
        
        Parameters:
            actor (ActorContext): 컨텍스트 소유권이 확인된 행위자
        
        Returns:
            Mapping[str, object]: 행위자에게 속한 사용자 컨텍스트
        """

    async def save_message(self, message: ChatMessage) -> None:
        """
        소유권을 다시 확인한 후 완료된 대화 턴을 저장합니다.
        
        Parameters:
        	message (ChatMessage): 저장할 완료된 대화 메시지
        """


class ChatGenerator(Protocol):
    async def generate(
        self,
        query: str,
        *,
        profile: str,
        user_context: Mapping[str, object],
    ) -> ChatGeneration:
        """
        쿼리와 사용자 컨텍스트를 바탕으로 프로필에 맞는 근거 기반 응답을 생성합니다.
        
        Parameters:
        	query (str): 응답을 생성할 사용자의 질의
        	profile (str): 응답 생성에 사용할 프로필
        	user_context (Mapping[str, object]): 응답 생성에 사용할 사용자 컨텍스트
        
        Returns:
        	ChatGeneration: 생성된 응답과 관련 메타데이터
        """

    def stream(
        self,
        query: str,
        *,
        profile: str,
        user_context: Mapping[str, object],
    ) -> AsyncIterator[ChatStreamEvent]:
        """
        사용자 컨텍스트와 프로필을 반영한 응답 스트림을 생성합니다.
        
        Parameters:
        	query (str): 응답을 생성할 사용자 질의
        	profile (str): 응답 생성에 사용할 프로필
        	user_context (Mapping[str, object]): 응답 생성에 사용할 사용자 컨텍스트
        
        Returns:
        	AsyncIterator[ChatStreamEvent]: 전송 계층에 종속되지 않는 스트림 이벤트
        """
