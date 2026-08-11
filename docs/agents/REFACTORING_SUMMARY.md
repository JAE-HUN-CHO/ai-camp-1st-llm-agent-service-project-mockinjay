# 에이전트 시스템 리팩토링 요약

## 📋 작성된 문서

1. **AGENT_REFACTORING_PLAN.md** - 전체 시스템 리팩토링 설계
2. **PARLANT_SERVER_SEPARATION_PLAN.md** - Parlant 서버 분리 상세 계획

---

## 🎯 핵심 설계 결정

### 1. 에이전트 타입 분리
**로컬 에이전트** (LocalAgent)
- Nutrition, Quiz, Trend Visualization
- Python 프로세스 내에서 직접 실행
- OpenAI API 직접 호출

**원격 에이전트** (RemoteAgent)
- Research Paper, Medical Welfare
- 별도 Parlant 서버로 실행 (독립 프로세스)
- HTTP 통신으로 연결

### 2. Parlant 서버 분리 전략
**현재**: 하나의 통합 서버 (`healthcare_v2_en.py`)
```python
@p.tool search_medical_qa        # Research Paper용
@p.tool search_welfare_programs  # Medical Welfare용
@p.tool search_hospitals         # Medical Welfare용
@p.tool check_emergency_keywords # 공통
```

**개선 후**: 에이전트별 독립 서버
```
Research Paper Server (port 8800)
├── search_medical_qa
├── get_kidney_stage_info
└── check_emergency_keywords (공유)

Medical Welfare Server (port 8801)
├── search_welfare_programs
├── search_hospitals
└── check_emergency_keywords (공유)
```

### 3. 통일된 인터페이스
모든 에이전트가 동일한 계약 사용:
```python
class BaseAgent(ABC):
    async def process(self, request: AgentRequest) -> AgentResponse:
        pass

class LocalAgent(BaseAgent):
    # OpenAI 직접 호출
    pass

class RemoteAgent(BaseAgent):
    # HTTP로 Parlant 서버 호출
    # 이벤트 폴링 자동 처리
    pass
```

---

## 📁 새로운 폴더 구조

```
backend/Agent/
├── core/
│   ├── base_agent.py          # 통일된 추상 클래스
│   ├── local_agent.py         # 로컬 에이전트 기본 클래스
│   ├── remote_agent.py        # 원격 에이전트 어댑터 (Parlant 프록시)
│   ├── agent_registry.py      # 플러그인 자동 등록 시스템
│   └── contracts.py           # AgentRequest/Response
│
├── infrastructure/
│   ├── services/
│   │   ├── openai_service.py  # 싱글톤
│   │   ├── http_client.py     # 원격 에이전트용
│   │   └── ...
│   └── session/
│       ├── session_manager.py
│       └── context_tracker.py
│
├── application/
│   ├── agent_manager.py       # 로컬/원격 자동 라우팅
│   └── router.py
│
├── agents/
│   ├── local/                 # 로컬 에이전트들
│   │   ├── nutrition/
│   │   ├── quiz/
│   │   └── trend_visualization/
│   │
│   └── remote/                # 원격 에이전트들 (Parlant)
│       ├── common/            # 공통 도구 모듈
│       │   ├── emergency_tools.py
│       │   ├── kidney_tools.py
│       │   └── parlant_utils.py
│       │
│       ├── research_paper/
│       │   ├── agent.py       # RemoteAgent(port=8800)
│       │   └── server/
│       │       ├── research_server.py  # Parlant 서버
│       │       └── run_server.py
│       │
│       ├── medical_welfare/
│       │   ├── agent.py       # RemoteAgent(port=8801)
│       │   └── server/
│       │       ├── welfare_server.py   # Parlant 서버
│       │       └── run_server.py
│       │
│       └── start_all_servers.sh  # 모든 서버 실행
│
└── utils/
    ├── token_estimator.py
    └── validators.py
```

---

## 🚀 주요 개선점

### 1. 플러그인 아키텍처
**기존**:
```python
# agent_manager.py 수정 필요
self.agents = {
    "nutrition": NutritionAgent(),
    "research_paper": ResearchPaperAgent(),
    # 새 에이전트 추가 시 여기 수정
}
```

**개선**:
```python
# 자동 등록!
@AgentRegistry.register("new_agent")
class NewAgent(LocalAgent):
    pass

# AgentManager는 수정 불필요
agents = AgentRegistry.list_agents()  # 자동 발견
```

### 2. 로컬/원격 통합 관리
```python
# 사용자는 에이전트 타입만 선택
response = await manager.route_request(
    agent_type="research_paper",  # 원격 에이전트
    user_input="CKD 연구 찾아줘",
    session_id="session-123"
)

# AgentManager가 자동 라우팅
# - LocalAgent → 직접 호출
# - RemoteAgent → HTTP 통신 + 이벤트 폴링
```

### 3. Parlant 이벤트 폴링 자동화
```python
class RemoteAgent(BaseAgent):
    async def process(self, request: AgentRequest) -> AgentResponse:
        # 1. Parlant 세션 관리
        # 2. 메시지 전송
        # 3. 이벤트 폴링 (Trace ID 기반 완료 감지)
        # 4. 응답 변환
        # 모두 자동 처리!
```

### 4. 서버 독립성
- Research Paper 서버 장애 → Medical Welfare 정상 동작
- 각 서버 독립적으로 스케일 가능
- 배포 시 각 서버만 재시작 (Zero-downtime)

---

## 📊 기대 효과

### 개발 생산성
| 작업 | 현재 | 개선 후 |
|------|------|---------|
| 새 로컬 에이전트 추가 | 30분 | **5분** |
| 새 원격 에이전트 추가 | 2시간 | **10분** |
| Parlant 이벤트 폴링 구현 | 매번 1시간 | **재사용 (0분)** |

### 코드 품질
- 중복 코드 제거: **~40%**
- 계약 기반 명확한 인터페이스
- 레이어 분리로 책임 명확화

### 시스템 안정성
- 장애 격리 (한 에이전트 장애가 다른 에이전트에 영향 없음)
- 독립 확장 (트래픽 많은 에이전트만 스케일)
- Zero-downtime 배포

---

## 🛠️ 구현 로드맵

### Phase 1: 인프라 레이어 (1-2일)
- [ ] `infrastructure/services/openai_service.py` (싱글톤)
- [ ] `infrastructure/services/http_client.py` (원격 에이전트용)
- [ ] `core/agent_registry.py` (플러그인 시스템)
- [ ] `core/base_agent.py`, `local_agent.py`, `remote_agent.py`

### Phase 2: Parlant 공통 모듈 추출 (1일)
- [ ] `agents/remote/common/emergency_tools.py`
- [ ] `agents/remote/common/kidney_tools.py`
- [ ] `agents/remote/common/parlant_utils.py`

### Phase 3: Research Paper 서버 분리 (2-3일)
- [ ] `agents/remote/research_paper/server/research_server.py` 생성
- [ ] `search_medical_qa` 도구 이전
- [ ] Guidelines, Journey 설정
- [ ] 테스트 및 검증

### Phase 4: Medical Welfare 서버 생성 (2-3일)
- [ ] `agents/remote/medical_welfare/server/welfare_server.py` 생성
- [ ] `search_welfare_programs`, `search_hospitals` 도구 이전
- [ ] Guidelines, Journey 설정
- [ ] 테스트 및 검증

### Phase 5: RemoteAgent 어댑터 (2일)
- [ ] `core/remote_agent.py` 구현
- [ ] Parlant 이벤트 폴링 로직 (Trace ID 기반)
- [ ] `ResearchPaperAgent(RemoteAgent)`
- [ ] `MedicalWelfareAgent(RemoteAgent)`

### Phase 6: 로컬 에이전트 마이그레이션 (3-4일)
- [ ] NutritionAgent → LocalAgent 리팩토링
- [ ] QuizAgent → LocalAgent
- [ ] TrendVisualizationAgent → LocalAgent
- [ ] 통일된 계약 적용

### Phase 7: AgentManager 개선 (1일)
- [ ] 플러그인 시스템 적용
- [ ] 하드코딩 제거
- [ ] 미들웨어 추가

### Phase 8: 통합 테스트 및 배포 (2-3일)
- [ ] 모든 에이전트 통합 테스트
- [ ] 프론트엔드 연동 테스트
- [ ] `start_all_servers.sh` 스크립트
- [ ] Docker Compose 설정
- [ ] 기존 `healthcare_v2_en.py` 폐기

**총 예상 시간**: 14-18일 (2-3주)

---

## 📝 코드 예시

### 로컬 에이전트 추가 (5분)
```python
# agents/local/new_agent/agent.py
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

### 원격 에이전트 추가 (10분)
```python
# agents/remote/new_parlant_agent/agent.py
from ....core.agent_registry import AgentRegistry
from ....core.remote_agent import RemoteAgent

@AgentRegistry.register("new_parlant_agent")  # 자동 등록!
class NewParlantAgent(RemoteAgent):
    def __init__(self):
        super().__init__(
            agent_type="new_parlant_agent",
            server_url="127.0.0.1",
            server_port=8902,  # 새 포트
        )

    @property
    def metadata(self):
        return {"name": "New Parlant Agent", "server_type": "parlant"}

    # process()는 RemoteAgent가 자동 처리!
```

### 사용 (AgentManager)
```python
# 사용자 코드는 변경 없음
response = await manager.route_request(
    agent_type="new_agent",      # 로컬 or 원격 상관없음
    user_input="질문",
    session_id="session-123"
)
# AgentManager가 자동으로 로컬/원격 판단 및 라우팅
```

---

## ⚠️ 주의사항

### 1. 하위 호환성
- 기존 API 엔드포인트 유지
- Adapter 패턴으로 기존 인터페이스 지원
- 점진적 마이그레이션 (병렬 운영)

### 2. Parlant 서버 관리
- 각 서버를 독립적으로 실행 및 모니터링
- 서버 간 통신 없음 (완전 독립)
- 공통 도구는 Python 모듈로 공유 (코드 레벨)

### 3. 환경 변수
```bash
# Research Paper Server
RESEARCH_PARLANT_HOST=127.0.0.1
RESEARCH_PARLANT_PORT=8800

# Medical Welfare Server
WELFARE_PARLANT_HOST=127.0.0.1
WELFARE_PARLANT_PORT=8801
```

---

## 🎓 참고 문서

1. **AGENT_REFACTORING_PLAN.md** - 전체 시스템 아키텍처
2. **PARLANT_SERVER_SEPARATION_PLAN.md** - Parlant 서버 분리 상세
3. **PARLANT_INTEGRATION.md** - Parlant 이벤트 스트리밍 가이드

---

## 🤝 다음 단계

1. ✅ 설계 리뷰 및 피드백 (완료)
2. ⬜ Phase 1 구현 시작 (인프라 레이어)
3. ⬜ Parlant 공통 모듈 추출
4. ⬜ Research Paper 서버 분리 (PoC)
5. ⬜ 점진적 마이그레이션

**질문이나 변경 사항이 있으면 언제든지 말씀해주세요!**

---

**작성일**: 2025-11-23
**버전**: 1.0
**작성자**: Claude Code
