# Agent 시스템 리팩토링 설계 초안

## 1. 현재 상태 분석

### 현재 구조
```
backend/Agent/
├── base_agent.py              # 기본 추상 클래스
├── agent_manager.py           # 에이전트 라우팅 및 관리
├── session_manager.py         # 세션 관리
├── context_tracker.py         # 컨텍스트 추적
├── core/                      # 공통 기능
│   ├── contracts.py          # AgentRequest, AgentResponse
│   └── policies.py           # 정책 엔진
├── api/                       # API 클라이언트
├── nutrition/agent.py         # 영양 에이전트 (복잡한 멀티턴 대화)
├── medical_welfare/agent.py   # 의료복지 에이전트 (간단한 구조)
├── research_paper/agent.py    # 논문 검색 에이전트
├── trend_visualization/agent.py
└── quiz/agent.py
```

### 현재 문제점
1. **일관성 부족**: 각 에이전트마다 다른 응답 구조 (`response` vs `answer`)
2. **중복 코드**:
   - OpenAI 클라이언트 초기화 로직이 각 에이전트에 중복
   - 토큰 추정 로직 중복
   - 에러 처리 로직 분산
3. **확장성 제약**:
   - AgentManager에 에이전트가 하드코딩됨
   - 새 에이전트 추가 시 여러 파일 수정 필요
4. **상태 관리 분산**:
   - NutritionAgent가 자체적으로 conversation_states 관리
   - SessionManager와 중복되는 책임
5. **계약 미사용**: contracts.py에 정의된 AgentRequest/Response를 실제로 사용하지 않음
6. **이질적인 에이전트 타입**:
   - 로컬 에이전트 (Nutrition, Quiz 등): 직접 호출
   - 원격 에이전트 (Parlant 기반): 별도 서버, HTTP 통신 필요
   - 두 타입이 통일되지 않은 인터페이스로 관리됨

---

## 2. 개선된 아키텍처 설계

### 핵심 설계 원칙
1. **플러그인 아키텍처**: 에이전트를 자동 발견하고 등록
2. **의존성 주입**: 공통 서비스(OpenAI, DB 등)를 중앙에서 주입
3. **계약 기반**: AgentRequest/Response를 모든 에이전트가 사용
4. **레이어 분리**: Presentation(API) - Application(Manager) - Domain(Agent) - Infrastructure(Clients)
5. **상태 관리 통일**: 모든 상태를 SessionManager로 통합
6. **어댑터 패턴**: 로컬/원격 에이전트를 동일한 인터페이스로 통합 (LocalAgent, RemoteAgent)

### 새로운 폴더 구조
```
backend/Agent/
├── core/
│   ├── __init__.py
│   ├── contracts.py          # AgentRequest, AgentResponse (개선)
│   ├── base_agent.py         # BaseAgent (개선) - 통일된 추상 클래스
│   ├── local_agent.py        # 🆕 로컬 에이전트 기본 클래스
│   ├── remote_agent.py       # 🆕 원격 에이전트 어댑터 (HTTP 통신)
│   ├── agent_registry.py     # 🆕 에이전트 자동 등록
│   ├── exceptions.py         # 🆕 커스텀 예외
│   └── types.py              # 🆕 공통 타입 정의 (AgentType: LOCAL, REMOTE)
│
├── infrastructure/           # 🆕 인프라 레이어
│   ├── __init__.py
│   ├── services/
│   │   ├── openai_service.py    # OpenAI 클라이언트 (싱글톤)
│   │   ├── mongodb_service.py
│   │   ├── vector_service.py
│   │   ├── pubmed_service.py
│   │   └── http_client.py       # 🆕 원격 에이전트용 HTTP 클라이언트
│   ├── session/
│   │   ├── session_manager.py   # 개선된 세션 관리
│   │   └── context_tracker.py   # 개선된 컨텍스트 추적
│   └── config/
│       └── settings.py          # 통합 설정 관리 (Parlant 서버 URL 포함)
│
├── application/              # 🆕 애플리케이션 레이어
│   ├── __init__.py
│   ├── agent_manager.py      # 개선된 에이전트 매니저
│   ├── router.py             # 🆕 라우팅 로직 분리
│   └── middleware/           # 🆕 미들웨어
│       ├── context_middleware.py
│       ├── logging_middleware.py
│       └── error_middleware.py
│
├── agents/                   # 🆕 도메인 레이어
│   ├── __init__.py
│   │
│   ├── local/                # 로컬 에이전트들 (직접 실행)
│   │   ├── nutrition/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py          # LocalAgent 상속
│   │   │   ├── prompts.py
│   │   │   ├── schemas.py
│   │   │   └── handlers/
│   │   │       ├── image_handler.py
│   │   │       └── dialog_handler.py
│   │   │
│   │   ├── trend_visualization/
│   │   └── quiz/
│   │
│   ├── remote/               # 🆕 원격 에이전트들 (별도 Parlant 서버)
│   │   ├── __init__.py
│   │   │
│   │   ├── common/           # 🆕 공통 도구 모듈 (서버 간 공유)
│   │   │   ├── __init__.py
│   │   │   ├── emergency_tools.py    # check_emergency_keywords
│   │   │   ├── kidney_tools.py       # get_kidney_stage_info, get_symptom_info
│   │   │   └── parlant_utils.py      # get_profile, convert_objectid_to_str
│   │   │
│   │   ├── research_paper/   # 연구논문 검색 에이전트 (독립 서버)
│   │   │   ├── __init__.py
│   │   │   ├── agent.py              # RemoteAgent 상속 (port 8800 프록시)
│   │   │   └── server/
│   │   │       ├── research_server.py    # 🆕 Parlant 서버 (search_medical_qa)
│   │   │       ├── run_server.py         # 🆕 서버 실행 스크립트
│   │   │       ├── parlant_nlp_adapter.py (기존 재사용)
│   │   │       └── nlp_service.py    (기존 재사용)
│   │   │
│   │   ├── medical_welfare/  # 🆕 의료복지 에이전트 (독립 서버)
│   │   │   ├── __init__.py
│   │   │   ├── agent.py              # RemoteAgent 상속 (port 8801 프록시)
│   │   │   └── server/
│   │   │       ├── welfare_server.py     # 🆕 Parlant 서버 (welfare, hospitals)
│   │   │       ├── run_server.py         # 🆕 서버 실행 스크립트
│   │   │       ├── parlant_nlp_adapter.py (공유)
│   │   │       └── nlp_service.py    (공유)
│   │   │
│   │   ├── _deprecated/
│   │   │   └── healthcare_v2_en.py   # 🗑️ 기존 통합 서버 (단계적 폐기)
│   │   │
│   │   └── start_all_servers.sh  # 🆕 모든 Parlant 서버 동시 실행 스크립트
│   │
│   └── _templates/           # 에이전트 템플릿
│       ├── local_agent_template.py
│       └── remote_agent_template.py
│
└── utils/                    # 🆕 유틸리티
    ├── token_estimator.py    # 공통 토큰 추정
    ├── validators.py         # 입력 검증
    └── formatters.py         # 응답 포맷팅
```

---

## 3. 핵심 컴포넌트 설계

### 3.1 통일된 BaseAgent (추상 클래스)
```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from enum import Enum
from ..core.contracts import AgentRequest, AgentResponse

class AgentType(Enum):
    """에이전트 실행 타입"""
    LOCAL = "local"      # 로컬에서 직접 실행
    REMOTE = "remote"    # 원격 서버 (HTTP 통신)

class BaseAgent(ABC):
    """모든 Agent의 기본 추상 클래스"""

    def __init__(self, agent_type: str):
        self.agent_type = agent_type

    @abstractmethod
    async def process(self, request: AgentRequest) -> AgentResponse:
        """통일된 계약 기반 처리"""
        pass

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """에이전트 메타데이터 (자동 등록용)"""
        pass

    @property
    @abstractmethod
    def execution_type(self) -> AgentType:
        """에이전트 실행 타입 (LOCAL or REMOTE)"""
        pass
```

### 3.2 LocalAgent (로컬 에이전트)
```python
from typing import Optional
from ..infrastructure.services.openai_service import OpenAIService

class LocalAgent(BaseAgent):
    """로컬에서 직접 실행되는 에이전트 (기존 방식)"""

    def __init__(
        self,
        agent_type: str,
        openai_service: Optional[OpenAIService] = None,
        # 다른 서비스들도 주입 가능
    ):
        super().__init__(agent_type)
        self.openai_service = openai_service or OpenAIService.get_instance()

    @property
    def execution_type(self) -> AgentType:
        return AgentType.LOCAL

    # process()와 metadata는 각 구체 클래스에서 구현
```

### 3.3 RemoteAgent (원격 에이전트 어댑터)
```python
import httpx
from typing import Optional
from ..infrastructure.services.http_client import HTTPClient

class RemoteAgent(BaseAgent):
    """
    별도 서버로 동작하는 에이전트 어댑터 (Parlant 등)

    HTTP를 통해 원격 서버와 통신하며, 동일한 BaseAgent 인터페이스 제공
    """

    def __init__(
        self,
        agent_type: str,
        server_url: str,
        server_port: int = 8800,
        http_client: Optional[HTTPClient] = None,
        timeout: float = 30.0,
    ):
        super().__init__(agent_type)
        self.server_url = server_url
        self.server_port = server_port
        self.base_url = f"http://{server_url}:{server_port}"
        self.http_client = http_client or HTTPClient.get_instance()
        self.timeout = timeout

    @property
    def execution_type(self) -> AgentType:
        return AgentType.REMOTE

    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        원격 서버로 요청 전달 및 응답 변환

        Parlant 서버는 이벤트 기반 스트리밍 방식이므로:
        1. 세션 생성/조회
        2. 메시지 전송
        3. 이벤트 폴링 (typing, message, ready 상태 추적)
        4. 최종 응답 수집
        """
        try:
            # 1. Parlant 세션 관리
            session_id = await self._get_or_create_session(request.session_id)

            # 2. 메시지 전송
            await self._send_message(session_id, request.query)

            # 3. 이벤트 폴링 (trace ID 기반 완료 감지)
            events = await self._poll_events_until_ready(session_id)

            # 4. 응답 추출 및 변환
            return self._convert_events_to_response(events, request)

        except httpx.ConnectError:
            raise AgentServerUnavailableError(
                f"Cannot connect to {self.agent_type} server at {self.base_url}"
            )
        except httpx.TimeoutException:
            raise AgentTimeoutError(
                f"{self.agent_type} server timeout after {self.timeout}s"
            )

    async def _get_or_create_session(self, session_id: str) -> str:
        """Parlant 세션 생성 또는 조회"""
        # GET /sessions/{session_id} or POST /sessions
        pass

    async def _send_message(self, session_id: str, message: str):
        """Parlant 세션에 메시지 전송"""
        # POST /sessions/{session_id}/messages
        pass

    async def _poll_events_until_ready(self, session_id: str) -> list:
        """
        이벤트 폴링 (Trace ID 기반 완료 감지)

        - message 이벤트 발생 시 trace_id 추적
        - ready 상태 + 모든 trace 완료 시 종료
        """
        active_trace_ids = set()
        offset = 0
        all_events = []

        while True:
            # GET /sessions/{session_id}/events
            events = await self._fetch_events(session_id, offset, wait_for_data=60)

            for event in events:
                all_events.append(event)
                trace_id = event.get("correlation_id", "").split("::")[0]

                if event["kind"] == "message" and event["source"] == "agent":
                    active_trace_ids.add(trace_id)

                if event["kind"] == "status" and event["data"]["status"] == "ready":
                    active_trace_ids.discard(trace_id)

            # 종료 조건: ready 상태 + 활성 trace 없음
            has_ready = any(
                e["kind"] == "status" and e["data"]["status"] == "ready"
                for e in events
            )

            if has_ready and len(active_trace_ids) == 0:
                break

            # offset 업데이트
            if events:
                offset = max(e.get("offset", offset) for e in events) + 1

        return all_events

    async def _fetch_events(
        self, session_id: str, offset: int, wait_for_data: int = 60
    ) -> list:
        """이벤트 목록 조회 (Long Polling)"""
        # GET /sessions/{session_id}/events?min_offset=X&wait_for_data=60
        pass

    def _convert_events_to_response(
        self, events: list, request: AgentRequest
    ) -> AgentResponse:
        """Parlant 이벤트를 AgentResponse로 변환"""
        # message 이벤트 추출
        messages = [
            e["data"]["message"]
            for e in events
            if e["kind"] == "message" and e["source"] == "agent"
        ]

        # tool 이벤트 추출 (논문 검색 등)
        tools = [e["data"] for e in events if e["kind"] == "tool"]

        return AgentResponse(
            answer="\n".join(messages) if messages else "",
            sources=[],  # tool 이벤트에서 추출
            papers=tools,  # Parlant 논문 검색 결과
            tokens_used=0,  # Parlant은 토큰 정보 제공 안 함
            status="success",
            agent_type=self.agent_type,
            metadata={"event_count": len(events)},
        )

    @property
    def metadata(self) -> Dict[str, Any]:
        """원격 에이전트 메타데이터"""
        return {
            "name": f"{self.agent_type} (Remote)",
            "description": "Remote agent via Parlant server",
            "execution_type": "remote",
            "server_url": self.base_url,
        }
```

### 3.2 에이전트 레지스트리 (플러그인 시스템)
```python
class AgentRegistry:
    """에이전트 자동 발견 및 등록"""

    _agents: Dict[str, Type[BaseAgent]] = {}

    @classmethod
    def register(cls, agent_type: str):
        """데코레이터로 에이전트 자동 등록"""
        def decorator(agent_class: Type[BaseAgent]):
            cls._agents[agent_type] = agent_class
            return agent_class
        return decorator

    @classmethod
    def get_agent(cls, agent_type: str, **dependencies) -> BaseAgent:
        """팩토리 패턴으로 에이전트 생성"""
        if agent_type not in cls._agents:
            raise AgentNotFoundException(agent_type)
        return cls._agents[agent_type](**dependencies)

    @classmethod
    def list_agents(cls) -> List[str]:
        """등록된 모든 에이전트 목록"""
        return list(cls._agents.keys())
```

### 3.5 사용 예시

#### 로컬 에이전트 예시
```python
# agents/local/nutrition/agent.py
from ....core.agent_registry import AgentRegistry
from ....core.local_agent import LocalAgent
from ....core.contracts import AgentRequest, AgentResponse

@AgentRegistry.register("nutrition")
class NutritionAgent(LocalAgent):
    """영양 에이전트 - 로컬 실행"""

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Nutrition Agent",
            "description": "CKD 환자를 위한 영양 분석",
            "version": "2.0",
            "capabilities": ["image_analysis", "multi_turn_dialog"],
        }

    async def process(self, request: AgentRequest) -> AgentResponse:
        # 통일된 인터페이스 사용
        user_input = request.query
        session_id = request.session_id
        context = request.context

        # 실제 처리 로직 (OpenAI 직접 호출)
        result = await self._analyze_nutrition(user_input, session_id, context)

        # 통일된 응답 반환
        return AgentResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            tokens_used=result["tokens_used"],
            agent_type=self.agent_type,
            status="success",
        )
```

#### 원격 에이전트 예시
```python
# agents/remote/research_paper/agent.py
from ....core.agent_registry import AgentRegistry
from ....core.remote_agent import RemoteAgent

@AgentRegistry.register("research_paper")
class ResearchPaperAgent(RemoteAgent):
    """논문 검색 에이전트 - Parlant 서버 (원격)"""

    def __init__(self):
        super().__init__(
            agent_type="research_paper",
            server_url="127.0.0.1",
            server_port=8800,
            timeout=60.0,  # 논문 검색은 시간이 오래 걸릴 수 있음
        )

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Research Paper Agent",
            "description": "PubMed 논문 검색 및 의료 QA",
            "version": "2.0",
            "server_type": "parlant",
            "capabilities": ["pubmed_search", "hybrid_search", "medical_qa"],
        }

    # process()는 RemoteAgent에서 자동 처리
    # Parlant 이벤트 폴링 및 응답 변환이 자동으로 수행됨
```

### 3.4 개선된 AgentManager
```python
class AgentManager:
    """에이전트 관리 - 플러그인 아키텍처"""

    def __init__(self):
        self.registry = AgentRegistry
        self.session_manager = SessionManager()
        self.context_tracker = ContextTracker()

        # 공통 서비스 (싱글톤)
        self.openai_service = OpenAIService.get_instance()

        # 에이전트는 lazy loading
        self._agent_instances: Dict[str, BaseAgent] = {}

    def _get_or_create_agent(self, agent_type: str) -> BaseAgent:
        """에이전트 인스턴스 lazy loading"""
        if agent_type not in self._agent_instances:
            self._agent_instances[agent_type] = self.registry.get_agent(
                agent_type,
                openai_service=self.openai_service,
                # 다른 서비스들도 주입
            )
        return self._agent_instances[agent_type]

    async def route_request(
        self,
        agent_type: str,
        user_input: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """요청 라우팅 - 통일된 계약 사용"""

        # 1. 에이전트 가져오기 (자동 발견)
        try:
            agent = self._get_or_create_agent(agent_type)
        except AgentNotFoundException:
            return {
                "success": False,
                "error": f"Unknown agent: {agent_type}",
                "available_agents": self.registry.list_agents(),
            }

        # 2. 세션 검증
        session = self.session_manager.get_session(session_id)
        if not session:
            return {"success": False, "error": "Invalid session"}

        # 3. AgentRequest 생성
        request = AgentRequest(
            query=user_input,
            session_id=session_id,
            context=context or {},
        )

        # 4. 미들웨어 실행 (컨텍스트 체크, 로깅 등)
        # ...

        # 5. 에이전트 처리
        try:
            response = await agent.process(request)

            # 6. 후처리 (컨텍스트 추적, 세션 업데이트)
            self.context_tracker.track_usage(
                session_id, agent_type, response.tokens_used
            )

            return {
                "success": True,
                "agent_type": agent_type,
                "result": response.dict(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "agent_type": agent_type,
            }

    def list_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """사용 가능한 모든 에이전트 메타데이터"""
        return {
            agent_type: self._get_or_create_agent(agent_type).metadata
            for agent_type in self.registry.list_agents()
        }
```

---

## 4. 마이그레이션 전략

### Phase 1: 인프라 레이어 구축
1. `infrastructure/services/` 생성
   - OpenAIService (싱글톤)
   - 기타 공통 서비스
2. `core/agent_registry.py` 구현
3. `core/base_agent.py` 개선 (의존성 주입 지원)

### Phase 2: 계약 강화
1. `contracts.py` 개선
   - AgentRequest에 image_data, multi_turn_state 추가
   - AgentResponse에 더 많은 필드 추가
2. 공통 유틸리티 구현
   - token_estimator.py
   - validators.py

### Phase 3: 에이전트 마이그레이션
1. NutritionAgent 리팩토링 (가장 복잡)
   - handlers/ 분리
   - 통일된 계약 사용
   - @AgentRegistry.register 데코레이터 적용
2. 다른 에이전트들 순차 마이그레이션
3. 기존 코드와 병렬 운영 (하위 호환성)

### Phase 4: AgentManager 개선
1. 플러그인 시스템 적용
2. 미들웨어 추가
3. 기존 하드코딩 제거

### Phase 5: 테스트 및 정리
1. 통합 테스트
2. 문서 업데이트
3. 기존 코드 제거

---

## 5. 새 에이전트 추가 방법 (개선 후)

### 현재 방식 (복잡함)
1. `agents/new_agent/agent.py` 생성
2. `agent_manager.py` 수정 (import, self.agents 딕셔너리)
3. BaseAgent 상속 및 구현

### 개선된 방식 - 로컬 에이전트 (간단함)
1. `agents/local/new_agent/agent.py` 생성
2. 템플릿 복사 및 수정
```python
from ....core.agent_registry import AgentRegistry
from ....core.local_agent import LocalAgent

@AgentRegistry.register("new_agent")  # 자동 등록!
class NewAgent(LocalAgent):
    @property
    def metadata(self):
        return {"name": "New Agent", "description": "..."}

    async def process(self, request: AgentRequest) -> AgentResponse:
        # OpenAI 직접 사용
        result = await self.openai_service.generate(request.query)
        return AgentResponse(answer=result, agent_type=self.agent_type)
```
3. 끝! (AgentManager 수정 불필요)

### 개선된 방식 - 원격 에이전트 (더 간단함!)
1. `agents/remote/new_parlant_agent/agent.py` 생성
2. 서버 정보만 설정
```python
from ....core.agent_registry import AgentRegistry
from ....core.remote_agent import RemoteAgent

@AgentRegistry.register("new_parlant_agent")  # 자동 등록!
class NewParlantAgent(RemoteAgent):
    def __init__(self):
        super().__init__(
            agent_type="new_parlant_agent",
            server_url="127.0.0.1",
            server_port=8900,  # 다른 포트
        )

    @property
    def metadata(self):
        return {"name": "New Parlant Agent", "server_type": "parlant"}

    # process()는 RemoteAgent가 자동 처리!
    # Parlant 이벤트 폴링 로직 재사용
```
3. 별도 서버 실행 (`agents/remote/new_parlant_agent/server/run_server.py`)
4. 끝! (복잡한 HTTP 통신 로직 작성 불필요)

---

## 6. 기대 효과

### 개발 생산성
- 새 로컬 에이전트 추가: **30분 → 5분**
- 새 원격 에이전트 추가: **2시간 → 10분** (HTTP 통신 로직 재사용)
- 중복 코드 제거: **~40%**
- 테스트 용이성 향상

### 유지보수성
- 계약 기반 명확한 인터페이스
- 의존성 주입으로 테스트 가능
- 레이어 분리로 책임 명확화
- 로컬/원격 에이전트 통일된 관리

### 확장성
- 플러그인 아키텍처로 무한 확장
- 미들웨어로 공통 기능 추가 용이
- 서비스 계층 분리로 재사용성 향상
- **Parlant 에이전트 무한 추가 가능** (RemoteAgent 재사용)

### 일관성
- 로컬/원격 에이전트 모두 동일한 `AgentRequest/Response` 사용
- 사용자 입장에서는 에이전트 타입 구분 불필요
- AgentManager가 자동으로 로컬/원격 라우팅

---

## 7. 리스크 및 대응

### 리스크
1. **하위 호환성**: 기존 API가 깨질 수 있음
   - 대응: Adapter 패턴으로 기존 인터페이스 유지

2. **마이그레이션 시간**: 전체 마이그레이션에 시간 소요
   - 대응: Phase별 점진적 마이그레이션, 병렬 운영

3. **복잡도 증가**: 레이어가 많아져 초기 학습 곡선
   - 대응: 명확한 문서화, 템플릿 제공

### 검증 방법
- 각 Phase마다 기존 테스트 통과 확인
- 성능 벤치마크 비교
- 점진적 롤아웃 (Canary 배포)

---

## 8. 복합 질문 처리 시스템 (Multi-Query Router)

### 8.1 요구사항
- **복합 질문 처리**: 여러 에이전트 관련 질문이 동시에 들어올 경우 분해하여 처리
- **의도 분류**: 사용자 입력에서 가장 적합한 에이전트 자동 선택
- **응답 통합**: 여러 에이전트의 답변을 하나의 일관된 응답으로 조합

### 8.2 Router 아키텍처

```python
# application/router.py
from typing import List, Dict, Any
from enum import Enum

class QueryIntent(Enum):
    """질문 의도 타입"""
    NUTRITION = "nutrition"
    RESEARCH = "research_paper"
    WELFARE = "medical_welfare"
    QUIZ = "quiz"
    TREND = "trend_visualization"
    MULTI = "multi"  # 복합 질문

class IntentClassifier:
    """의도 분류기 (GPT-4o 사용)"""

    async def classify(self, user_input: str) -> Dict[str, Any]:
        """
        사용자 입력에서 의도 분류

        Returns:
            {
                "intent_type": "single" | "multi",
                "primary_intent": QueryIntent,
                "sub_intents": List[QueryIntent],
                "decomposed_queries": [
                    {"intent": QueryIntent, "query": "분해된 질문"}
                ]
            }
        """
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": INTENT_CLASSIFICATION_PROMPT
            }, {
                "role": "user",
                "content": user_input
            }],
            temperature=0.3
        )

        return self._parse_intent_result(response)

class QueryRouter:
    """복합 질문 라우팅 및 응답 통합"""

    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.intent_classifier = IntentClassifier()

    async def route_and_process(
        self,
        user_input: str,
        session_id: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        복합 질문 처리 메인 플로우

        1. 의도 분류
        2. 단일/복합 질문 판단
        3. 적절한 처리 방식 선택
        4. 응답 통합
        """
        # 1. 의도 분류
        intent_result = await self.intent_classifier.classify(user_input)

        # 2. 단일 질문 처리
        if intent_result["intent_type"] == "single":
            return await self._process_single_intent(
                intent_result["primary_intent"],
                user_input,
                session_id,
                context
            )

        # 3. 복합 질문 처리
        return await self._process_multi_intent(
            intent_result["decomposed_queries"],
            session_id,
            context
        )

    async def _process_single_intent(
        self,
        intent: QueryIntent,
        query: str,
        session_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """단일 의도 처리 (기존 route_request)"""
        agent_type = intent.value

        result = await self.agent_manager.route_request(
            agent_type=agent_type,
            user_input=query,
            session_id=session_id,
            context=context
        )

        return {
            "type": "single",
            "intent": intent.value,
            "result": result
        }

    async def _process_multi_intent(
        self,
        decomposed_queries: List[Dict],
        session_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        복합 의도 처리

        여러 에이전트를 병렬/순차 호출하고 응답 통합
        """
        # 1. 에이전트별 쿼리 그룹화
        agent_queries = self._group_by_agent(decomposed_queries)

        # 2. 병렬 처리 (독립적인 질문)
        tasks = []
        for agent_type, queries in agent_queries.items():
            for query_info in queries:
                task = self.agent_manager.route_request(
                    agent_type=agent_type,
                    user_input=query_info["query"],
                    session_id=session_id,
                    context=context
                )
                tasks.append((agent_type, query_info["query"], task))

        # 3. 모든 응답 수집
        results = await asyncio.gather(*[task for _, _, task in tasks])

        # 4. 응답 통합
        aggregated_response = await self._aggregate_responses(
            [(agent_type, query, result) for (agent_type, query, _), result in zip(tasks, results)]
        )

        return {
            "type": "multi",
            "intents": list(agent_queries.keys()),
            "individual_results": [
                {"agent": agent, "query": query, "result": result}
                for (agent, query, _), result in zip(tasks, results)
            ],
            "aggregated_response": aggregated_response
        }

    async def _aggregate_responses(
        self,
        agent_results: List[Tuple[str, str, Dict]]
    ) -> str:
        """
        여러 에이전트 응답을 하나의 통합 응답으로 조합

        GPT-4o를 사용하여 자연스러운 통합 답변 생성
        """
        # 1. 각 에이전트 응답 추출
        formatted_results = []
        for agent_type, query, result in agent_results:
            if result.get("success"):
                answer = result["result"].get("answer", "")
                formatted_results.append({
                    "agent": agent_type,
                    "query": query,
                    "answer": answer
                })

        # 2. GPT-4o로 통합 답변 생성
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

### 8.3 프롬프트 설계

**의도 분류 프롬프트**:
```python
INTENT_CLASSIFICATION_PROMPT = """
당신은 만성 신장 질환(CKD) 환자를 돕는 AI 어시스턴트의 의도 분류기입니다.

사용자 질문을 분석하여 다음 카테고리로 분류하세요:
- nutrition: 음식, 영양, 식단 관련
- research_paper: 의학 논문, 연구 자료 검색
- medical_welfare: 복지 제도, 병원 정보
- quiz: 퀴즈, 학습, 테스트
- trend_visualization: 통계, 트렌드, 시각화

복합 질문의 경우, 각 의도별로 분해하여 반환하세요.

예시 1 (단일):
입력: "당근의 칼륨 함량이 얼마나 되나요?"
출력: {
  "intent_type": "single",
  "primary_intent": "nutrition",
  "sub_intents": [],
  "decomposed_queries": []
}

예시 2 (복합):
입력: "저염식 레시피 알려주고, 관련 논문도 찾아줘"
출력: {
  "intent_type": "multi",
  "primary_intent": "nutrition",
  "sub_intents": ["nutrition", "research_paper"],
  "decomposed_queries": [
    {"intent": "nutrition", "query": "저염식 레시피를 추천해주세요"},
    {"intent": "research_paper", "query": "저염식 식이요법 관련 의학 논문을 검색해주세요"}
  ]
}

JSON 형식으로만 응답하세요.
"""
```

**응답 통합 프롬프트**:
```python
RESPONSE_AGGREGATION_PROMPT = """
당신은 여러 AI 에이전트의 답변을 하나의 일관된 응답으로 통합하는 전문가입니다.

각 에이전트의 답변을 받아 다음 원칙으로 통합하세요:
1. **자연스러운 흐름**: 답변 간 자연스러운 연결
2. **정보 보존**: 각 에이전트의 핵심 정보 유지
3. **중복 제거**: 겹치는 내용 통합
4. **사용자 중심**: 질문에 대한 완전한 답변 제공

예시:
입력: [
  {
    "agent": "nutrition",
    "query": "저염식 레시피",
    "answer": "저염식 레시피로는 무염 버터를 사용한 감자 샐러드를 추천합니다..."
  },
  {
    "agent": "research_paper",
    "query": "저염식 식이요법 논문",
    "answer": "2023년 'Journal of Renal Nutrition' 연구에 따르면 저염식이 CKD 환자의 혈압 조절에..."
  }
]

출력:
"저염식 레시피로는 무염 버터를 사용한 감자 샐러드를 추천드립니다.

또한, 최신 연구에 따르면 저염식이 CKD 환자의 혈압 조절에 효과적이라는 결과가 있습니다. 2023년 'Journal of Renal Nutrition' 연구에서는..."

통합된 답변만 반환하세요.
"""
```

### 8.4 API 통합

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
    """
    context_dict = json.loads(context) if context else {}

    result = await query_router.route_and_process(
        user_input=user_input,
        session_id=session_id,
        context=context_dict
    )

    return result
```

### 8.5 예상 시나리오

**시나리오 1: 단일 질문**
```
User: "당근의 칼륨 함량은?"
→ Intent: nutrition (단일)
→ NutritionAgent 호출
→ 응답 반환
```

**시나리오 2: 복합 질문 (2개 에이전트)**
```
User: "저칼륨 식단 추천하고, 관련 논문도 찾아줘"
→ Intent: multi [nutrition, research_paper]
→ 병렬 처리:
   - NutritionAgent: 저칼륨 식단 추천
   - ResearchPaperAgent: 저칼륨 식이 논문 검색
→ GPT-4o로 응답 통합
→ 통합 답변 반환
```

**시나리오 3: 복합 질문 (3개 에이전트)**
```
User: "CKD 3기 환자 식단 추천하고, 근처 병원 알려주고, 관련 퀴즈 풀고 싶어"
→ Intent: multi [nutrition, medical_welfare, quiz]
→ 병렬 처리:
   - NutritionAgent: CKD 3기 식단
   - MedicalWelfareAgent: 병원 검색
   - QuizAgent: 퀴즈 세션 생성
→ 응답 통합
→ 통합 답변 + 각 에이전트 결과 반환
```

### 8.6 성능 최적화

1. **병렬 처리**: `asyncio.gather()`로 독립적인 에이전트 동시 호출
2. **타임아웃**: 각 에이전트 최대 30초 제한
3. **우선순위**: primary_intent 에이전트를 먼저 처리
4. **캐싱**: 동일 세션 내 유사 질문 캐싱

### 8.7 에러 처리

```python
async def _process_multi_intent(self, decomposed_queries, session_id, context):
    results = []

    for query_info in decomposed_queries:
        try:
            result = await asyncio.wait_for(
                self.agent_manager.route_request(...),
                timeout=30.0
            )
            results.append(result)
        except asyncio.TimeoutError:
            results.append({
                "success": False,
                "error": "timeout",
                "agent": query_info["intent"]
            })
        except Exception as e:
            results.append({
                "success": False,
                "error": str(e),
                "agent": query_info["intent"]
            })

    # 부분 성공도 허용 (최소 1개 성공 시 통합 응답 생성)
    successful_results = [r for r in results if r.get("success")]

    if not successful_results:
        return {"success": False, "error": "All agents failed"}

    return await self._aggregate_responses(successful_results)
```

---

## 9. 다음 단계

1. ✅ 설계 리뷰 및 피드백
2. ⬜ Phase 1 구현 시작
3. ⬜ IntentClassifier 구현 (GPT-4o 프롬프트 테스트)
4. ⬜ QueryRouter 구현 (병렬 처리 및 응답 통합)
5. ⬜ NutritionAgent 리팩토링 (PoC)
6. ⬜ 나머지 에이전트 마이그레이션
7. ⬜ 통합 테스트 및 문서화

---

## 참고: 코드 예시

### 현재 AgentManager (하드코딩)
```python
self.agents: Dict[str, BaseAgent] = {
    "medical_welfare": MedicalWelfareAgent(),
    "nutrition": NutritionAgent(),
    "research_paper": ResearchPaperAgent(),
    # 새 에이전트 추가 시마다 수정 필요!
}
```

### 개선된 AgentManager (자동 발견)
```python
# 등록된 모든 에이전트 자동 사용
available_agents = AgentRegistry.list_agents()
# ['nutrition', 'medical_welfare', 'research_paper', 'new_agent', ...]

agent = AgentRegistry.get_agent("nutrition", openai_service=self.openai_service)
```

---

## 9. Parlant 원격 에이전트 통합 상세

### 9.1 아키텍처
```
┌─────────────────┐
│  FastAPI 서버   │
│  (backend/app)  │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│ AgentManager    │  ← 로컬/원격 자동 라우팅
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌──────┐  ┌──────────────────┐
│Local │  │ RemoteAgent      │
│Agent │  │ (HTTP Adapter)   │
└──────┘  └─────────┬────────┘
                    │ HTTP (Parlant API)
                    ▼
          ┌──────────────────┐
          │ Parlant Server   │
          │ (port 8800)      │
          └──────────────────┘
```

### 9.2 RemoteAgent의 주요 장점

1. **Parlant 이벤트 스트리밍 자동 처리**
   - Trace ID 기반 완료 감지
   - Long Polling 최적화
   - 분할 메시지 자동 수집

2. **통일된 인터페이스**
   - 로컬 에이전트와 동일한 `AgentRequest/Response`
   - AgentManager가 차이를 인지하지 못함

3. **재사용성**
   - 새로운 Parlant 에이전트 추가 시 코드 재사용
   - 서버 URL/포트만 변경하면 됨

### 9.3 Parlant 서버 관리

#### 서버 실행
```bash
# 기존 방식 유지
python backend/Agent/research_paper/run_server.py
```

#### 환경 변수
```bash
# .env
PARLANT_HOST=127.0.0.1
PARLANT_PORT=8800

# 추가 Parlant 서버가 있다면
PARLANT_MEDICAL_PORT=8801
PARLANT_WELFARE_PORT=8802
```

#### 서버 상태 확인
```python
# RemoteAgent에 헬스체크 기능 추가
@router.get("/agents/{agent_type}/health")
async def check_agent_health(agent_type: str):
    agent = manager._get_or_create_agent(agent_type)

    if agent.execution_type == AgentType.REMOTE:
        # Parlant 서버 ping
        return await agent.health_check()

    return {"status": "local", "available": True}
```

### 9.4 마이그레이션 전략 (Parlant 관련)

**⚠️ 중요**: 현재 `healthcare_v2_en.py`에 모든 도구가 통합되어 있음
- Research Paper 도구: `search_medical_qa`
- Medical Welfare 도구: `search_welfare_programs`, `search_hospitals`
- 공통 도구: `check_emergency_keywords`, `get_kidney_stage_info` 등

**Phase 1**: 공통 모듈 추출 (코드 재사용)
- `agents/remote/common/emergency_tools.py` 생성
- `agents/remote/common/kidney_tools.py` 생성
- `agents/remote/common/parlant_utils.py` 생성
- 각 서버에서 import로 재사용

**Phase 2**: Research Paper 서버 분리
- `agents/remote/research_paper/server/research_server.py` 생성
- `search_medical_qa` 도구 이전
- 공통 도구 import (emergency, kidney)
- Guidelines, Journey 설정 (기존 로직 재사용)
- 포트 8800에서 독립 실행
- 테스트 및 검증

**Phase 3**: Medical Welfare 서버 생성
- `agents/remote/medical_welfare/server/welfare_server.py` 생성
- `search_welfare_programs`, `search_hospitals` 도구 이전
- 공통 도구 import
- Welfare 전용 Guidelines, Journey 설정
- 포트 8801에서 독립 실행
- 테스트 및 검증

**Phase 4**: RemoteAgent 어댑터 구현
- `core/remote_agent.py` 작성 (Parlant 이벤트 폴링)
- `ResearchPaperAgent(RemoteAgent)` - port 8800
- `MedicalWelfareAgent(RemoteAgent)` - port 8801

**Phase 5**: 기존 healthcare_v2_en.py 단계적 폐기
- 새 서버들이 안정화되면
- `_deprecated/` 폴더로 이동
- 프론트엔드 전환 완료 후 삭제

**상세 계획**: `PARLANT_SERVER_SEPARATION_PLAN.md` 참조

### 9.5 비교: 현재 vs 개선 후

#### 현재 (Parlant 에이전트 추가 시)
```python
# 1. backend/app/api/chat.py에 프록시 추가
@router.api_route("/{path:path}", ...)
async def proxy_to_parlant(...):
    # 복잡한 프록시 로직 복사-붙여넣기
    ...

# 2. Parlant 서버 별도 실행
# 3. 프론트엔드에서 특수 처리 필요
```

#### 개선 후 (Parlant 에이전트 추가 시)
```python
# 1. RemoteAgent 상속 (10줄)
@AgentRegistry.register("new_agent")
class NewAgent(RemoteAgent):
    def __init__(self):
        super().__init__("new_agent", "127.0.0.1", 8801)

# 2. Parlant 서버 별도 실행
# 3. 끝! (프록시, 프론트엔드 수정 불필요)
```

---

**작성일**: 2025-11-23
**작성자**: Claude Code
**버전**: 2.0 (Parlant 원격 에이전트 지원 추가)
