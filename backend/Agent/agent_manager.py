"""
Agent Manager - Refactored with AgentRegistry
모든 Agent 조율, 라우팅 및 컨텍스트 관리
"""

from typing import Dict, Any, Optional
import logging

from .base_agent import BaseAgent
from .context_tracker import ContextTracker
from .session_manager import SessionManager
from .core.agent_registry import AgentRegistry
from .core.contracts import AgentRequest, AgentResponse
from app.core.emergency_safety import EMERGENCY_RESPONSE, emergency_safety_policy

# 에이전트 자동 import (자동 등록됨)
from .medical_welfare import agent as _medical_welfare_agent  # noqa: F401
from .nutrition import agent as _nutrition_agent  # noqa: F401
from .research_paper import agent as _research_paper_agent  # noqa: F401
from .trend_visualization import agent as _trend_visualization_agent  # noqa: F401
from .quiz import agent as _quiz_agent  # noqa: F401
from .router import agent as _router_agent  # noqa: F401

logger = logging.getLogger(__name__)


class AgentManager:
    """Agent 관리 및 라우팅 시스템 (AgentRegistry 통합)"""

    def __init__(self):
        self.context_tracker = ContextTracker()
        self.session_manager = SessionManager()

        # ✅ 새로운 방식: AgentRegistry에서 자동 발견
        logger.info("🔧 Initializing AgentManager with AgentRegistry...")
        self.agents: Dict[str, BaseAgent] = {}
        
        # 등록된 모든 에이전트 자동 생성
        for agent_type in AgentRegistry.list_agents():
            try:
                self.agents[agent_type] = AgentRegistry.create_agent(agent_type)
                logger.info(f"   ✅ Registered: {agent_type}")
            except Exception as e:
                logger.error(f"   ❌ Failed to register {agent_type}: {e}")
        
        logger.info(f"🎉 AgentManager initialized with {len(self.agents)} agents")

    async def route_request(
        self,
        agent_type: str,
        user_input: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Agent로 요청 라우팅 (새 계약 지원)

        Args:
            agent_type: Agent 타입
            user_input: 사용자 입력
            session_id: 세션 ID
            context: 추가 컨텍스트

        Returns:
            Dict[str, Any]: Agent 응답 또는 에러
        """
        if emergency_safety_policy.evaluate(user_input).blocked:
            return {
                "success": True,
                "answer": EMERGENCY_RESPONSE,
                "status": "success",
                "agent_type": "emergency_safety",
                "metadata": {"is_emergency": True, "provider": "emergency_pre_filter"},
            }

        # 1. Agent 유효성 확인
        if agent_type not in self.agents:
            return {
                "success": False,
                "error": f"Unknown agent type: {agent_type}",
                "available_agents": list(self.agents.keys()),
            }

        # 2. 세션 확인
        session = self.session_manager.get_session(session_id)
        if not session:
            return {
                "success": False,
                "error": "Invalid or expired session",
            }

        agent = self.agents[agent_type]

        # 3. 컨텍스트 사용량 예측
        estimated_tokens = agent.estimate_context_usage(user_input)
        limit_check = self.context_tracker.check_limit(session_id, estimated_tokens)

        # 4. 컨텍스트 제한 확인
        if limit_check["would_exceed"]:
            return {
                "success": False,
                "error": "Context limit exceeded",
                "limit_info": {
                    "current_usage": limit_check["current_usage"],
                    "max_limit": limit_check["max_limit"],
                    "remaining": limit_check["remaining"],
                    "estimated_tokens": estimated_tokens,
                },
                "message": f"세션 컨텍스트 제한({limit_check['max_limit']} 토큰)을 초과합니다. "
                          f"현재 사용량: {limit_check['current_usage']} 토큰, "
                          f"예상 추가 사용량: {estimated_tokens} 토큰",
            }

        # 5. Agent 처리 실행 (새 계약 사용)
        try:
            # 새 AgentRequest 생성
            request = AgentRequest(
                query=user_input,
                session_id=session_id,
                context=context or {},
                profile=session.get("user_profile", "general"),
                language=session.get("language", "ko")
            )
            
            # 새 process 메서드 호출
            response: AgentResponse = await agent.process(request)

            # 6. 실제 사용량 추적
            actual_tokens = response.tokens_used
            self.context_tracker.track_usage(session_id, agent_type, actual_tokens)

            # 7. 세션 업데이트
            self.session_manager.update_session_activity(session_id, agent_type)
            self.session_manager.add_to_history(
                session_id,
                agent_type,
                user_input,
                response.answer
            )

            # 8. 컨텍스트 정보 추가
            context_info = self.context_tracker.check_limit(session_id)

            # 9. 응답 변환 (기존 형식 호환)
            return {
                "success": response.status != "error",
                "agent_type": agent_type,
                "result": {
                    "response": response.answer,
                    "answer": response.answer,  # 역호환성
                    "sources": response.sources,
                    "papers": response.papers,
                    "tokens_used": response.tokens_used,
                    "status": response.status,
                    "metadata": response.metadata,
                    "context_info": context_info
                },
            }

        except Exception as e:
            logger.error(f"❌ Agent processing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Agent processing failed: {str(e)}",
                "agent_type": agent_type,
            }

    def create_user_session(self, user_id: str) -> str:
        """
        사용자 세션 생성

        Args:
            user_id: 사용자 ID

        Returns:
            str: 세션 ID
        """
        return self.session_manager.create_session(user_id)

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 정보 조회

        Args:
            session_id: 세션 ID

        Returns:
            Optional[Dict]: 세션 정보
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return None

        context_summary = self.context_tracker.get_session_summary(session_id)

        return {
            "session": session,
            "context": context_summary,
        }

    def reset_session_context(self, session_id: str) -> bool:
        """
        세션 컨텍스트 초기화

        Args:
            session_id: 세션 ID

        Returns:
            bool: 초기화 성공 여부
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return False

        self.context_tracker.reset_session(session_id)
        return True

    def get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        사용 가능한 Agent 목록 반환 (새 metadata 사용)

        Returns:
            Dict: Agent 정보
        """
        available = {}
        for agent_type, agent in self.agents.items():
            try:
                # 새 metadata property 사용
                if hasattr(agent, 'metadata'):
                    metadata = agent.metadata
                    available[agent_type] = {
                        "name": metadata.get("name", agent_type),
                        "description": metadata.get("description", ""),
                        "version": metadata.get("version", "1.0"),
                        "capabilities": metadata.get("capabilities", []),
                        "execution_type": agent.execution_type.value if hasattr(agent, 'execution_type') else "unknown"
                    }
                else:
                    # 레거시 get_agent_info 사용
                    available[agent_type] = agent.get_agent_info()
            except Exception as e:
                logger.error(f"Failed to get info for {agent_type}: {e}")
                available[agent_type] = {"error": str(e)}
        
        return available
