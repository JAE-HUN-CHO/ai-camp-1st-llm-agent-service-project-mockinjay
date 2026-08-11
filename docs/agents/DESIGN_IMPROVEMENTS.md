# 설계 개선 사항

피드백을 반영한 상세 개선안입니다.

---

## 1. RemoteAgent 에러 처리 및 복원력 개선

### 문제점
- HTTP 예외만 처리, 응답 파싱/스키마 오류 미처리
- 무한 루프/조기 종료 위험
- 타임아웃 정책 불명확

### 개선안

```python
# core/remote_agent.py
import httpx
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # 정상
    OPEN = "open"          # 장애 (요청 차단)
    HALF_OPEN = "half_open"  # 복구 시도

class CircuitBreaker:
    """서킷 브레이커 패턴 구현"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    def should_allow_request(self) -> bool:
        """요청 허용 여부 판단"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # 복구 시간이 지났는지 확인
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = CircuitState.HALF_OPEN
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return False

    def record_success(self):
        """성공 기록"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        """실패 기록"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")


class RemoteAgent(BaseAgent):
    """개선된 원격 에이전트 어댑터"""

    def __init__(
        self,
        agent_type: str,
        server_url: str,
        server_port: int = 8800,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        max_polling_duration: float = 120.0,  # 최대 폴링 시간 (2분)
        polling_interval: float = 0.5,  # 초기 폴링 간격
    ):
        super().__init__(agent_type)
        self.server_url = server_url
        self.server_port = server_port
        self.base_url = f"http://{server_url}:{server_port}"
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_polling_duration = max_polling_duration
        self.polling_interval = polling_interval

        # Circuit breaker 초기화
        self.circuit_breaker = CircuitBreaker()

        # HTTP 클라이언트 (재사용)
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

    async def process(self, request: AgentRequest) -> AgentResponse:
        """통일된 계약 기반 처리 (에러 처리 강화)"""

        # Circuit breaker 체크
        if not self.circuit_breaker.should_allow_request():
            raise AgentCircuitOpenError(
                f"{self.agent_type} server is unavailable (circuit open)"
            )

        # 재시도 로직
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                result = await self._execute_with_timeout(request)
                self.circuit_breaker.record_success()
                return result

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = self.backoff_factor ** attempt
                    await asyncio.sleep(wait_time)

            except AgentResponseParseError as e:
                # 파싱 에러는 재시도 안 함 (서버 버그)
                logger.error(f"Response parsing error: {e}")
                self.circuit_breaker.record_failure()
                raise

            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                self.circuit_breaker.record_failure()
                raise

        # 모든 재시도 실패
        self.circuit_breaker.record_failure()
        raise AgentServerUnavailableError(
            f"Failed to connect to {self.agent_type} after {self.max_retries} attempts",
            original_error=last_exception
        )

    async def _execute_with_timeout(self, request: AgentRequest) -> AgentResponse:
        """타임아웃 적용된 실행"""
        try:
            return await asyncio.wait_for(
                self._execute_request(request),
                timeout=self.max_polling_duration
            )
        except asyncio.TimeoutError:
            raise AgentTimeoutError(
                f"{self.agent_type} exceeded max polling duration "
                f"({self.max_polling_duration}s)"
            )

    async def _execute_request(self, request: AgentRequest) -> AgentResponse:
        """실제 요청 실행"""
        # 1. Parlant 세션 관리
        session_id = await self._get_or_create_session(request.session_id)

        # 2. 메시지 전송
        await self._send_message(session_id, request.query)

        # 3. 이벤트 폴링 (개선된 종료 조건)
        events = await self._poll_events_until_ready(session_id)

        # 4. 응답 추출 및 변환
        return self._convert_events_to_response(events, request)

    async def _poll_events_until_ready(self, session_id: str) -> list:
        """
        개선된 이벤트 폴링 (명확한 종료 조건)

        종료 조건:
        1. ready 상태 + 모든 active trace 완료
        2. 타임아웃 (외부에서 처리)
        3. 에러 이벤트 발생
        """
        active_trace_ids = set()
        offset = 0
        all_events = []
        start_time = datetime.now()
        current_interval = self.polling_interval

        while True:
            # 폴링 간격 동적 조정 (adaptive polling)
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > 10:  # 10초 이상 걸리면 간격 늘림
                current_interval = min(2.0, current_interval * 1.2)

            try:
                events = await self._fetch_events(
                    session_id,
                    offset,
                    wait_for_data=int(current_interval)
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    raise AgentServerError(f"Server error: {e}")
                elif e.response.status_code == 404:
                    raise AgentSessionNotFoundError(f"Session {session_id} not found")
                else:
                    raise AgentHTTPError(f"HTTP {e.response.status_code}: {e}")

            # 빈 이벤트 처리
            if not events:
                await asyncio.sleep(current_interval)
                continue

            for event in events:
                all_events.append(event)

                # 에러 이벤트 체크
                if event.get("kind") == "status" and event.get("data", {}).get("status") == "error":
                    error_msg = event.get("data", {}).get("message", "Unknown error")
                    raise AgentExecutionError(f"Agent error: {error_msg}")

                # Trace ID 추출 (안전하게)
                correlation_id = event.get("correlation_id", "")
                if not correlation_id:
                    logger.warning(f"Event without correlation_id: {event.get('kind')}")
                    continue

                trace_id = correlation_id.split("::")[0] if "::" in correlation_id else correlation_id

                # Message 이벤트 추적
                if event.get("kind") == "message" and event.get("source") == "agent":
                    active_trace_ids.add(trace_id)

                # Ready 상태에서 trace 제거
                if event.get("kind") == "status":
                    status = event.get("data", {}).get("status")
                    if status == "ready":
                        active_trace_ids.discard(trace_id)

            # 종료 조건 체크
            has_ready = any(
                e.get("kind") == "status" and e.get("data", {}).get("status") == "ready"
                for e in events
            )

            if has_ready and len(active_trace_ids) == 0:
                logger.info(f"Polling complete: {len(all_events)} events collected")
                break

            # Offset 업데이트
            if events:
                max_offset = max(e.get("offset", offset) for e in events)
                offset = max_offset + 1

            # 다음 폴링까지 대기
            await asyncio.sleep(current_interval)

        return all_events

    def _convert_events_to_response(
        self, events: list, request: AgentRequest
    ) -> AgentResponse:
        """Parlant 이벤트를 AgentResponse로 변환 (안전한 파싱)"""
        try:
            # Message 이벤트 추출
            messages = []
            for e in events:
                if e.get("kind") == "message" and e.get("source") == "agent":
                    data = e.get("data", {})
                    if isinstance(data, dict):
                        msg = data.get("message", "")
                        if msg:
                            messages.append(msg)

            # Tool 이벤트 추출 (논문 검색 등)
            tools = []
            for e in events:
                if e.get("kind") == "tool":
                    tool_data = e.get("data", {})
                    if isinstance(tool_data, dict):
                        tools.append(tool_data)

            # 응답 생성
            answer = "\n".join(messages) if messages else ""

            return AgentResponse(
                answer=answer,
                sources=[],  # Tool 이벤트에서 추출
                papers=tools,  # Parlant 도구 결과
                tokens_used=0,  # Parlant은 토큰 정보 제공 안 함
                status="success",
                agent_type=self.agent_type,
                metadata={
                    "event_count": len(events),
                    "message_count": len(messages),
                    "tool_count": len(tools),
                },
            )

        except Exception as e:
            raise AgentResponseParseError(
                f"Failed to parse Parlant events: {e}",
                events=events
            )

    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/health",
                timeout=5.0
            )
            response.raise_for_status()

            return {
                "status": "healthy",
                "url": self.base_url,
                "circuit_state": self.circuit_breaker.state.value,
                "response_time": response.elapsed.total_seconds(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "url": self.base_url,
                "circuit_state": self.circuit_breaker.state.value,
                "error": str(e),
            }

    async def close(self):
        """리소스 정리"""
        await self.http_client.aclose()


# core/exceptions.py
class AgentError(Exception):
    """에이전트 기본 예외"""
    pass

class AgentServerUnavailableError(AgentError):
    """서버 연결 불가"""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error

class AgentTimeoutError(AgentError):
    """타임아웃"""
    pass

class AgentCircuitOpenError(AgentError):
    """서킷 브레이커 오픈"""
    pass

class AgentResponseParseError(AgentError):
    """응답 파싱 에러"""
    def __init__(self, message: str, events: list = None):
        super().__init__(message)
        self.events = events

class AgentServerError(AgentError):
    """서버 5xx 에러"""
    pass

class AgentSessionNotFoundError(AgentError):
    """세션 없음"""
    pass

class AgentHTTPError(AgentError):
    """기타 HTTP 에러"""
    pass

class AgentExecutionError(AgentError):
    """에이전트 실행 에러"""
    pass
```

---

## 2. 세션 관리 전략

### 문제점
- 세션 생성/갱신 흐름 불명확
- 기존 API 호환 전략 미정의

### 개선안

```python
# infrastructure/session/session_strategy.py
from enum import Enum
from typing import Protocol

class SessionCreationStrategy(Enum):
    """세션 생성 전략"""
    LAZY = "lazy"          # 요청 시 자동 생성
    EXPLICIT = "explicit"  # 명시적 생성 필요
    HYBRID = "hybrid"      # API 레벨에서 생성, Agent는 재사용

class SessionManager:
    """개선된 세션 관리자"""

    def __init__(self, strategy: SessionCreationStrategy = SessionCreationStrategy.HYBRID):
        self.sessions: Dict[str, Dict] = {}
        self.strategy = strategy

    async def get_or_create_session(self, session_id: Optional[str], user_id: str) -> str:
        """세션 가져오기 또는 생성 (전략 기반)"""

        if session_id:
            session = self.get_session(session_id)
            if session:
                # 세션 갱신
                self.update_session_activity(session_id)
                return session_id

            if self.strategy == SessionCreationStrategy.EXPLICIT:
                raise SessionNotFoundError(f"Session {session_id} not found")

        # 세션 생성
        if self.strategy == SessionCreationStrategy.LAZY or \
           self.strategy == SessionCreationStrategy.HYBRID:
            return self.create_session(user_id)

        raise SessionCreationNotAllowedError(
            "Session creation not allowed with EXPLICIT strategy"
        )


# application/agent_manager.py (개선)
class AgentManager:
    """개선된 에이전트 매니저"""

    async def route_request(
        self,
        agent_type: str,
        user_input: str,
        session_id: Optional[str] = None,  # Optional로 변경
        user_id: str = "anonymous",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """요청 라우팅 (세션 자동 생성 지원)"""

        # 1. 세션 가져오기 또는 생성
        try:
            actual_session_id = await self.session_manager.get_or_create_session(
                session_id, user_id
            )
        except SessionNotFoundError as e:
            return {
                "success": False,
                "error": "session_not_found",
                "message": str(e),
                "should_create_session": True,  # 클라이언트 힌트
            }

        # 2. 에이전트 가져오기
        try:
            agent = self._get_or_create_agent(agent_type)
        except AgentNotFoundException:
            return {
                "success": False,
                "error": "unknown_agent",
                "available_agents": self.registry.list_agents(),
            }

        # 3. 에이전트 처리
        request = AgentRequest(
            query=user_input,
            session_id=actual_session_id,
            context=context or {},
        )

        try:
            response = await agent.process(request)

            # 세션 업데이트
            self.context_tracker.track_usage(
                actual_session_id, agent_type, response.tokens_used
            )
            self.session_manager.update_session_activity(actual_session_id, agent_type)

            return {
                "success": True,
                "session_id": actual_session_id,  # 생성된 세션 ID 반환
                "agent_type": agent_type,
                "result": response.dict(),
            }

        except AgentCircuitOpenError as e:
            return {
                "success": False,
                "error": "agent_unavailable",
                "message": str(e),
                "retry_after": 60,  # 초
            }

        except AgentTimeoutError as e:
            return {
                "success": False,
                "error": "agent_timeout",
                "message": str(e),
            }

        except Exception as e:
            logger.error(f"Agent processing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": "agent_error",
                "message": str(e),
            }
```

### API 레벨 통합 (FastAPI)

```python
# app/api/agents.py
from fastapi import APIRouter, HTTPException, Header
from typing import Optional

router = APIRouter(prefix="/api/v2/agents", tags=["agents"])

@router.post("/{agent_type}/query")
async def query_agent(
    agent_type: str,
    request: AgentQueryRequest,
    x_session_id: Optional[str] = Header(None),  # 헤더에서 세션 ID
    x_user_id: str = Header("anonymous"),
):
    """에이전트 쿼리 (세션 자동 관리)"""

    result = await agent_manager.route_request(
        agent_type=agent_type,
        user_input=request.query,
        session_id=x_session_id,
        user_id=x_user_id,
        context=request.context,
    )

    if not result["success"]:
        # 에러 타입별 HTTP 상태 코드
        error_codes = {
            "session_not_found": 404,
            "unknown_agent": 404,
            "agent_unavailable": 503,
            "agent_timeout": 504,
            "agent_error": 500,
        }
        status_code = error_codes.get(result["error"], 500)
        raise HTTPException(status_code=status_code, detail=result)

    # 응답 헤더에 세션 ID 포함 (클라이언트가 재사용)
    return JSONResponse(
        content=result,
        headers={"X-Session-Id": result["session_id"]}
    )
```

---

## 3. AgentRequest/Response 호환성 정책

### 문제점
- 확장 방향만 언급, 구체 스키마 없음
- 역호환 정책 불명확

### 개선안

```python
# core/contracts.py (버전 관리 추가)
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

class AgentRequest(BaseModel):
    """통일된 에이전트 요청 (v1.0)"""

    # 필수 필드
    query: str = Field(..., description="사용자 질문")
    session_id: str = Field(..., description="세션 ID")

    # 선택 필드
    context: Dict[str, Any] = Field(default_factory=dict, description="컨텍스트")
    profile: str = Field(default="general", description="사용자 프로필")
    language: str = Field(default="ko", description="언어")

    # v1.1 추가 필드 (하위 호환)
    image_data: Optional[str] = Field(None, description="Base64 인코딩 이미지")
    multi_turn_state: Optional[Dict[str, Any]] = Field(None, description="멀티턴 상태")

    # 메타데이터
    version: str = Field(default="1.0", description="요청 버전")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        # 알 수 없는 필드 허용 (forward compatibility)
        extra = "allow"


class AgentResponse(BaseModel):
    """통일된 에이전트 응답 (v1.0)"""

    # 필수 필드
    answer: str = Field(..., description="생성된 답변")
    agent_type: str = Field(..., description="에이전트 타입")
    status: str = Field(default="success", description="처리 상태")

    # 선택 필드
    sources: List[Dict] = Field(default_factory=list, description="참조 소스")
    papers: List[Dict] = Field(default_factory=list, description="논문 검색 결과")
    tokens_used: int = Field(default=0, description="사용된 토큰 수")
    metadata: Dict = Field(default_factory=dict, description="추가 메타데이터")

    # v1.1 추가 필드
    images: Optional[List[Dict]] = Field(None, description="생성된 이미지")
    follow_up_questions: Optional[List[str]] = Field(None, description="후속 질문 제안")

    # 메타데이터
    version: str = Field(default="1.0", description="응답 버전")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        extra = "allow"


# 기존 API 호환 어댑터
class LegacyResponseAdapter:
    """기존 응답 형식으로 변환"""

    @staticmethod
    def to_legacy_format(response: AgentResponse) -> Dict[str, Any]:
        """AgentResponse → 기존 API 형식"""

        # 기존 형식 (response 필드 사용)
        legacy = {
            "response": response.answer,  # answer → response
            "tokens_used": response.tokens_used,
            "data": {
                "sources": response.sources,
                "papers": response.papers,
            },
            "metadata": {
                "agent_type": response.agent_type,
                "status": response.status,
                **response.metadata,
            }
        }

        return legacy

    @staticmethod
    def from_legacy_format(legacy: Dict[str, Any], agent_type: str) -> AgentResponse:
        """기존 API 형식 → AgentResponse"""

        return AgentResponse(
            answer=legacy.get("response", ""),
            agent_type=agent_type,
            status="success",
            sources=legacy.get("data", {}).get("sources", []),
            papers=legacy.get("data", {}).get("papers", []),
            tokens_used=legacy.get("tokens_used", 0),
            metadata=legacy.get("metadata", {}),
        )
```

### API 버전 관리

```python
# app/api/agents_v1.py (기존 API - 유지)
@router.post("/api/agents/{agent_type}/query")
async def query_agent_v1(agent_type: str, request: LegacyQueryRequest):
    """기존 API (v1) - 하위 호환성"""

    # 새 시스템 호출
    result = await agent_manager.route_request(
        agent_type=agent_type,
        user_input=request.query,
        session_id=request.session_id,
    )

    # 기존 형식으로 변환
    if result["success"]:
        response = AgentResponse.parse_obj(result["result"])
        return LegacyResponseAdapter.to_legacy_format(response)

    return result  # 에러는 그대로


# app/api/agents_v2.py (새 API)
@router.post("/api/v2/agents/{agent_type}/query")
async def query_agent_v2(agent_type: str, request: AgentRequest):
    """새 API (v2) - AgentRequest/Response 사용"""

    result = await agent_manager.route_request(
        agent_type=agent_type,
        user_input=request.query,
        session_id=request.session_id,
        context=request.context,
    )

    return result  # AgentResponse 그대로 반환
```

---

## 4. 모니터링 및 헬스 체크

```python
# application/middleware/monitoring_middleware.py
import time
from prometheus_client import Counter, Histogram, Gauge

# 메트릭 정의
agent_requests_total = Counter(
    "agent_requests_total",
    "Total agent requests",
    ["agent_type", "status"]
)

agent_request_duration = Histogram(
    "agent_request_duration_seconds",
    "Agent request duration",
    ["agent_type"]
)

agent_circuit_state = Gauge(
    "agent_circuit_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["agent_type"]
)

class MonitoringMiddleware:
    """모니터링 미들웨어"""

    async def __call__(
        self,
        agent_type: str,
        request: AgentRequest,
        call_next
    ) -> AgentResponse:
        """요청 처리 및 메트릭 수집"""

        start_time = time.time()

        try:
            response = await call_next(request)

            # 성공 메트릭
            agent_requests_total.labels(
                agent_type=agent_type,
                status="success"
            ).inc()

            duration = time.time() - start_time
            agent_request_duration.labels(agent_type=agent_type).observe(duration)

            return response

        except Exception as e:
            # 실패 메트릭
            status = type(e).__name__
            agent_requests_total.labels(
                agent_type=agent_type,
                status=status
            ).inc()

            raise


# 헬스 체크 엔드포인트
@router.get("/health")
async def health_check():
    """전체 시스템 헬스 체크"""

    agents_health = {}
    for agent_type in agent_manager.registry.list_agents():
        agent = agent_manager._get_or_create_agent(agent_type)

        if hasattr(agent, 'health_check'):
            agents_health[agent_type] = await agent.health_check()
        else:
            agents_health[agent_type] = {"status": "healthy", "type": "local"}

    all_healthy = all(
        h.get("status") == "healthy"
        for h in agents_health.values()
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "agents": agents_health,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

---

## 5. Import 및 패키징 전략

### 문제점
- 상대 경로 import, PYTHONPATH 전략 불명확

### 개선안

```python
# pyproject.toml 또는 setup.py
[tool.poetry]
name = "agent-system"
version = "1.0.0"
packages = [
    { include = "Agent", from = "backend" }
]

# backend/Agent/__init__.py
"""Agent 패키지 최상위"""
__version__ = "1.0.0"

# 공통 import 제공
from .core import (
    BaseAgent,
    LocalAgent,
    RemoteAgent,
    AgentRegistry,
    AgentRequest,
    AgentResponse,
)

__all__ = [
    "BaseAgent",
    "LocalAgent",
    "RemoteAgent",
    "AgentRegistry",
    "AgentRequest",
    "AgentResponse",
]
```

### 서버 실행 스크립트 개선

```python
# agents/remote/research_paper/server/run_server.py
import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

# 이제 절대 경로로 import 가능
from Agent.agents.remote.common.emergency_tools import check_emergency_keywords
from Agent.agents.remote.research_paper.server.research_server import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### start_all_servers.sh 개선

```bash
#!/bin/bash
set -euo pipefail  # 에러 시 즉시 종료

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# PID 파일 저장 경로
PID_DIR="/tmp/agent_servers"
mkdir -p "$PID_DIR"

# 시그널 핸들러 (정리)
cleanup() {
    echo -e "${RED}Stopping all servers...${NC}"

    if [ -f "$PID_DIR/research_paper.pid" ]; then
        kill $(cat "$PID_DIR/research_paper.pid") 2>/dev/null || true
        rm "$PID_DIR/research_paper.pid"
    fi

    if [ -f "$PID_DIR/medical_welfare.pid" ]; then
        kill $(cat "$PID_DIR/medical_welfare.pid") 2>/dev/null || true
        rm "$PID_DIR/medical_welfare.pid"
    fi

    echo -e "${GREEN}All servers stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Starting all Parlant servers..."

# Research Paper Server
python -m Agent.agents.remote.research_paper.server.run_server &
echo $! > "$PID_DIR/research_paper.pid"
echo -e "${GREEN}Research Paper Server started (PID: $!)${NC}"

# Medical Welfare Server
python -m Agent.agents.remote.medical_welfare.server.run_server &
echo $! > "$PID_DIR/medical_welfare.pid"
echo -e "${GREEN}Medical Welfare Server started (PID: $!)${NC}"

echo ""
echo -e "${GREEN}All servers running${NC}"
echo "Press Ctrl+C to stop all servers"

# 포그라운드에서 대기
wait
```

---

## 6. 복합 질문 처리를 위한 Router 개선

### 문제점
- 현재 `AgentManager.route_request()`는 단일 에이전트로만 라우팅
- 복합 질문 (예: "저염식 레시피 추천하고, 관련 논문도 찾아줘")을 처리할 수 없음
- 사용자가 agent_type을 명시해야 하므로 UX 저하

### 개선안

#### 6.1 의도 분류 계층 추가

```python
# application/router.py
class IntentClassifier:
    """
    GPT-4o를 사용한 의도 분류기

    사용자 입력을 분석하여:
    1. 단일 의도 vs 복합 의도 판단
    2. 각 의도에 해당하는 에이전트 매핑
    3. 복합 질문을 서브 쿼리로 분해
    """

    async def classify(self, user_input: str) -> IntentClassificationResult:
        """
        의도 분류 및 쿼리 분해

        Returns:
            IntentClassificationResult {
                intent_type: "single" | "multi",
                primary_intent: QueryIntent,
                sub_intents: List[QueryIntent],
                decomposed_queries: List[SubQuery]
            }
        """
        # GPT-4o 프롬프트 기반 분류
        # INTENT_CLASSIFICATION_PROMPT 사용
```

**프롬프트 예시**:
```
당신은 사용자 질문을 분석하여 적절한 AI 에이전트를 선택하는 라우터입니다.

사용자 질문: "저염식 레시피 알려주고, 관련 논문도 찾아줘"

분석 결과 (JSON):
{
  "intent_type": "multi",
  "primary_intent": "nutrition",
  "sub_intents": ["nutrition", "research_paper"],
  "decomposed_queries": [
    {"intent": "nutrition", "query": "저염식 레시피를 추천해주세요"},
    {"intent": "research_paper", "query": "저염식 식이요법 관련 의학 논문을 검색해주세요"}
  ]
}
```

#### 6.2 QueryRouter 구현

```python
class QueryRouter:
    """
    복합 질문 처리를 위한 고급 라우터

    기능:
    1. 의도 분류 (IntentClassifier)
    2. 단일/복합 질문 자동 판단
    3. 병렬 에이전트 호출 (asyncio.gather)
    4. 응답 통합 (GPT-4o)
    """

    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.intent_classifier = IntentClassifier()
        self.response_aggregator = ResponseAggregator()

    async def route_and_process(
        self,
        user_input: str,
        session_id: str,
        context: Optional[Dict] = None
    ) -> RouterResult:
        """
        통합 라우팅 메인 플로우

        1. 의도 분류
        2. 단일/복합 처리 분기
        3. 에이전트 호출
        4. 응답 통합 (복합의 경우)
        """
        # 1. 의도 분류
        intent_result = await self.intent_classifier.classify(user_input)

        # 2. 단일 질문 처리
        if intent_result.intent_type == "single":
            return await self._process_single_intent(
                intent_result.primary_intent,
                user_input,
                session_id,
                context
            )

        # 3. 복합 질문 처리
        return await self._process_multi_intent(
            intent_result.decomposed_queries,
            session_id,
            context
        )

    async def _process_multi_intent(
        self,
        decomposed_queries: List[SubQuery],
        session_id: str,
        context: Optional[Dict]
    ) -> RouterResult:
        """
        복합 의도 처리

        여러 에이전트를 병렬로 호출하고 응답 통합
        """
        # 1. 에이전트별 작업 생성
        tasks = []
        for sub_query in decomposed_queries:
            task = self.agent_manager.route_request(
                agent_type=sub_query.intent,
                user_input=sub_query.query,
                session_id=session_id,
                context=context
            )
            tasks.append((sub_query.intent, sub_query.query, task))

        # 2. 병렬 실행 (최대 30초 타임아웃)
        results = await asyncio.gather(
            *[task for _, _, task in tasks],
            return_exceptions=True
        )

        # 3. 에러 처리 (부분 성공 허용)
        successful_results = []
        for (agent_type, query, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agent_type} failed: {result}")
                continue
            if result.get("success"):
                successful_results.append({
                    "agent": agent_type,
                    "query": query,
                    "result": result["result"]
                })

        # 4. 응답 통합 (GPT-4o)
        aggregated_response = await self.response_aggregator.aggregate(
            successful_results
        )

        return RouterResult(
            type="multi",
            intents=[r["agent"] for r in successful_results],
            individual_results=successful_results,
            aggregated_response=aggregated_response
        )
```

#### 6.3 응답 통합 (Response Aggregator)

```python
class ResponseAggregator:
    """
    여러 에이전트의 응답을 하나의 일관된 답변으로 통합

    GPT-4o를 사용하여:
    1. 각 에이전트 응답 요약
    2. 중복 제거
    3. 자연스러운 흐름으로 연결
    """

    async def aggregate(
        self,
        agent_results: List[Dict]
    ) -> str:
        """
        응답 통합

        Args:
            agent_results: [
                {
                    "agent": "nutrition",
                    "query": "저염식 레시피",
                    "result": {...}
                },
                ...
            ]

        Returns:
            통합된 자연스러운 답변
        """
        # 1. 각 에이전트 응답 추출
        formatted_results = []
        for item in agent_results:
            answer = item["result"].get("answer", "")
            formatted_results.append({
                "agent": item["agent"],
                "query": item["query"],
                "answer": answer
            })

        # 2. GPT-4o로 통합
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": RESPONSE_AGGREGATION_PROMPT
            }, {
                "role": "user",
                "content": json.dumps(formatted_results, ensure_ascii=False)
            }],
            temperature=0.7
        )

        return response.choices[0].message.content
```

**통합 프롬프트 예시**:
```
당신은 여러 AI 에이전트의 답변을 하나의 일관된 응답으로 통합하는 전문가입니다.

각 에이전트의 답변을 받아 다음 원칙으로 통합하세요:
1. 자연스러운 흐름으로 연결
2. 각 에이전트의 핵심 정보 보존
3. 중복 제거
4. 사용자 질문에 대한 완전한 답변 제공

입력 예시:
[
  {
    "agent": "nutrition",
    "query": "저염식 레시피",
    "answer": "저염식 레시피로는 무염 버터를 사용한 감자 샐러드를 추천합니다..."
  },
  {
    "agent": "research_paper",
    "query": "저염식 식이요법 논문",
    "answer": "2023년 'Journal of Renal Nutrition' 연구에 따르면..."
  }
]

통합 답변:
"저염식 레시피로는 무염 버터를 사용한 감자 샐러드를 추천드립니다. [레시피 상세]

또한, 최신 연구 결과를 보면 저염식이 CKD 환자의 혈압 조절에 효과적입니다. 2023년 'Journal of Renal Nutrition' 연구에서는..."
```

#### 6.4 API 통합

```python
# app/main.py
from Agent.application.router import QueryRouter

query_router = QueryRouter(agent_manager)

@app.post("/api/agents/query")
async def query_agents(
    user_input: str = Form(...),
    session_id: str = Form(...),
    context: Optional[str] = Form(None)
):
    """
    복합 질문 지원 통합 API

    자동으로 의도를 분류하고 적절한 에이전트(들)로 라우팅

    예시:
    - 단일 질문: "당근의 칼륨 함량은?" → nutrition
    - 복합 질문: "저염식 레시피 추천하고, 관련 논문도 찾아줘"
      → nutrition + research_paper (병렬 호출 + 응답 통합)
    """
    context_dict = json.loads(context) if context else {}

    result = await query_router.route_and_process(
        user_input=user_input,
        session_id=session_id,
        context=context_dict
    )

    return result
```

### 6.5 성능 최적화

1. **병렬 처리**: `asyncio.gather()`로 여러 에이전트 동시 호출
2. **타임아웃**: 각 에이전트 30초 제한, 초과 시 건너뛰기
3. **캐싱**: 동일 세션 내 유사 질문 캐싱 (Redis)
4. **우선순위**: primary_intent 에이전트를 먼저 처리

### 6.6 에러 처리

```python
# 부분 성공 허용
# 예: 3개 에이전트 중 2개만 성공해도 통합 응답 생성
if not successful_results:
    return {
        "success": False,
        "error": "All agents failed",
        "failed_intents": [r["agent"] for r in failed_results]
    }

# 부분 성공 시 경고 포함
if len(successful_results) < len(decomposed_queries):
    return {
        "success": True,
        "partial": True,
        "warning": f"{len(failed_results)}개 에이전트 실패",
        "aggregated_response": aggregated_response
    }
```

### 6.7 예상 시나리오

**시나리오 1: 단일 질문**
```
User: "당근의 칼륨 함량은?"
→ IntentClassifier: single, nutrition
→ NutritionAgent 호출
→ 응답 반환
```

**시나리오 2: 복합 질문 (2개 에이전트)**
```
User: "저칼륨 식단 추천하고, 관련 논문도 찾아줘"
→ IntentClassifier: multi, [nutrition, research_paper]
→ 병렬 처리:
   - NutritionAgent: 저칼륨 식단 추천
   - ResearchPaperAgent: 저칼륨 식이 논문 검색
→ ResponseAggregator: GPT-4o로 통합
→ 통합 답변 반환
```

**시나리오 3: 복합 질문 (3개 에이전트)**
```
User: "CKD 3기 환자 식단 추천하고, 근처 병원 알려주고, 관련 퀴즈 풀고 싶어"
→ IntentClassifier: multi, [nutrition, medical_welfare, quiz]
→ 병렬 처리 (3개 동시)
→ 응답 통합 + 개별 결과 반환
```

### 6.8 기대 효과

1. **UX 개선**: agent_type 명시 불필요, 자연스러운 대화
2. **복합 질문 지원**: 한 번에 여러 작업 처리
3. **성능 향상**: 병렬 처리로 응답 시간 단축
4. **유연성**: 새 에이전트 추가 시 자동 인식

---

**작성일**: 2025-11-23
**버전**: 1.1 (복합 질문 처리 추가)
**관련 문서**: AGENT_REFACTORING_PLAN.md
