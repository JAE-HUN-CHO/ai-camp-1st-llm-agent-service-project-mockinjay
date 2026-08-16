# 📚 문서 읽는 가이드

현재 기준 문서와 과거 4개 설계 문서를 **어떻게 구분해 읽는지** 설명합니다.

> 아래 `REFACTORING_SUMMARY`, `AGENT_REFACTORING_PLAN`,
> `PARLANT_SERVER_SEPARATION_PLAN`, `DESIGN_IMPROVEMENTS`는 historical reference다.
> OpenAI, `new_frontend`, 과거 Agent 수·포트를 현재 구현 지시로 사용하지 않는다.

## 현재 아키텍처 트랙

```text
DOCUMENT_CONSISTENCY_MATRIX
  → domain.md + Accepted ADR-004/005/006/011
  → ARCHITECTURE_CURRENT_STATE
  → ARCHITECTURE_GAP_ANALYSIS
  → ARCHITECTURE_REFERENCE_ALIGNMENT
  → Accepted ADR-013 + ARCHITECTURE_REFACTORING_DESIGN
  → ARCHITECTURE_REFACTORING_PLAN
  → ARCHITECTURE_MULTI_AGENT_REVIEW
```

현재 상태는 사실, gap은 미해결 문제, reference alignment는 적용 근거다. ADR-013은 binding
결정이고 설계/계획은 그 결정을 실행하는 가이드다. Phase 0~1은 검증됐으며 현재는 Phase 2 Chat
vertical slice만 다음 실행 범위로 승인됐다. Phase 3 이후는 별도 범위 확인 전 시작하지 않는다.
`ARCHITECTURE_GAP_ANALYSIS`와 `ARCHITECTURE_MULTI_AGENT_REVIEW`에 남은 ADR-013
`Proposed`/`REQUEST CHANGES` 문구는 2026-08-15 승인 전 snapshot이며 현재 status가 아니다.

---

## 🗺️ Historical 문서 구조 및 읽는 순서

```
시작
  ↓
1. REFACTORING_SUMMARY.md  ← 먼저 읽기 (전체 그림 파악)
  ↓
2. AGENT_REFACTORING_PLAN.md  ← 상세 설계 이해
  ↓
3. PARLANT_SERVER_SEPARATION_PLAN.md  ← Parlant 서버 분리 방법
  ↓
4. DESIGN_IMPROVEMENTS.md  ← 에러 처리, 세션 관리 등 구현 디테일
  ↓
구현 시작
```

---

## 📄 문서별 상세 가이드

### 1. REFACTORING_SUMMARY.md (시작점 - 5분)

**📌 목적**: 전체 프로젝트의 개요와 핵심만 빠르게 파악

**읽는 방법**:
```
1단계: "핵심 설계 결정" 섹션 읽기
   → 로컬/원격 에이전트가 무엇인지 이해

2단계: "새로운 폴더 구조" 보기
   → 어떻게 재구성될지 시각화

3단계: "기대 효과" 확인
   → 왜 이 리팩토링이 필요한지 동기 파악

4단계: "구현 로드맵" 스캔
   → 전체 작업 규모 파악 (2-3주)
```

**핵심 포인트**:
- ✅ 로컬 에이전트 = 직접 실행 (Nutrition, Quiz 등)
- ✅ 원격 에이전트 = Parlant 서버 (Research Paper, Medical Welfare)
- ✅ 플러그인 아키텍처 = `@AgentRegistry.register()` 데코레이터로 자동 등록
- ✅ 통일된 인터페이스 = 모든 에이전트가 `AgentRequest/Response` 사용

**다음 단계**: AGENT_REFACTORING_PLAN.md로 이동

---

### 2. AGENT_REFACTORING_PLAN.md (메인 설계 - 30분)

**📌 목적**: 전체 시스템 아키텍처와 구현 계획 상세 이해

**읽는 방법**:
```
1단계: "1. 현재 상태 분석" 읽기
   → 지금 무엇이 문제인지 파악

2단계: "2. 개선된 아키텍처 설계" 읽기
   → 어떻게 개선할지 설계 이해

3단계: "3. 핵심 컴포넌트 설계" 읽기 ⭐ 중요!
   → 3.1 BaseAgent
   → 3.2 LocalAgent
   → 3.3 RemoteAgent (Parlant 어댑터)
   → 3.4 AgentRegistry
   → 3.5 사용 예시

4단계: "4. 마이그레이션 전략" 읽기
   → Phase 1-5 순서 확인

5단계: "9. Parlant 원격 에이전트 통합 상세" 읽기
   → RemoteAgent가 어떻게 HTTP 통신하는지 이해
```

**핵심 컴포넌트 이해하기**:

#### 3.1 BaseAgent (추상 클래스)
```python
class BaseAgent(ABC):
    @abstractmethod
    async def process(self, request: AgentRequest) -> AgentResponse:
        pass

    @property
    @abstractmethod
    def execution_type(self) -> AgentType:
        pass
```
→ **모든 에이전트가 따라야 할 계약**

#### 3.2 LocalAgent (로컬 실행)
```python
class LocalAgent(BaseAgent):
    def __init__(self, agent_type: str, openai_service=None):
        self.openai_service = openai_service or OpenAIService.get_instance()

    @property
    def execution_type(self):
        return AgentType.LOCAL
```
→ **OpenAI API 직접 호출하는 에이전트**

#### 3.3 RemoteAgent (Parlant 프록시)
```python
class RemoteAgent(BaseAgent):
    def __init__(self, agent_type: str, server_url: str, server_port: int):
        self.base_url = f"http://{server_url}:{server_port}"

    async def process(self, request: AgentRequest) -> AgentResponse:
        # 1. Parlant 세션 생성/조회
        # 2. 메시지 전송
        # 3. 이벤트 폴링 (trace ID 기반 완료 감지)
        # 4. 응답 변환
        pass
```
→ **Parlant 서버와 HTTP로 통신하는 어댑터**

#### 3.4 AgentRegistry (플러그인 시스템)
```python
@AgentRegistry.register("nutrition")  # 이 한 줄로 자동 등록!
class NutritionAgent(LocalAgent):
    pass

# AgentManager는 자동으로 발견
agents = AgentRegistry.list_agents()  # ['nutrition', 'research_paper', ...]
```
→ **에이전트를 자동으로 발견하고 등록하는 시스템**

**체크포인트**:
- [ ] BaseAgent의 역할 이해
- [ ] LocalAgent vs RemoteAgent 차이 이해
- [ ] AgentRegistry가 어떻게 자동 등록하는지 이해
- [ ] RemoteAgent가 Parlant 이벤트를 어떻게 폴링하는지 이해

**다음 단계**: PARLANT_SERVER_SEPARATION_PLAN.md로 이동

---

### 3. PARLANT_SERVER_SEPARATION_PLAN.md (Parlant 상세 - 20분)

**📌 목적**: Parlant 서버 분리 전략과 구현 방법 상세 이해

**읽는 방법**:
```
1단계: "현재 상황" 읽기
   → healthcare_v2_en.py에 모든 도구가 통합되어 있음을 확인

2단계: "분리 전략" 읽기
   → 옵션 A (완전 독립) vs 옵션 B (하이브리드) 비교
   → 권장: 옵션 A

3단계: "구현 계획" 읽기 ⭐ 중요!
   → Phase 1: 공통 모듈 추출
   → Phase 2: Research Paper 서버 분리
   → Phase 3: Medical Welfare 서버 생성

4단계: "코드 예시" 읽기
   → 실제 구현 코드 확인
```

**핵심 이해할 점**:

#### 현재 문제
```python
# healthcare_v2_en.py (하나의 서버에 모든 도구)
@p.tool
async def search_medical_qa(...):  # Research Paper용
    pass

@p.tool
async def search_welfare_programs(...):  # Medical Welfare용
    pass

@p.tool
async def search_hospitals(...):  # Medical Welfare용
    pass

@p.tool
async def check_emergency_keywords(...):  # 공통
    pass
```

#### 개선 후
```
Research Paper Server (port 8800)
├── search_medical_qa
└── check_emergency_keywords (모듈 import)

Medical Welfare Server (port 8801)
├── search_welfare_programs
├── search_hospitals
└── check_emergency_keywords (모듈 import)
```

**공통 모듈 재사용 방법**:
```python
# agents/remote/common/emergency_tools.py
@p.tool
async def check_emergency_keywords(context, text):
    # 공통 구현
    pass

# research_paper/server/research_server.py
from ...common.emergency_tools import check_emergency_keywords

# medical_welfare/server/welfare_server.py
from ...common.emergency_tools import check_emergency_keywords
```

**체크포인트**:
- [ ] 왜 서버를 분리해야 하는지 이해 (장애 격리)
- [ ] 공통 모듈을 어떻게 재사용하는지 이해
- [ ] Phase 1-5 순서 이해
- [ ] start_all_servers.sh 스크립트 역할 이해

**다음 단계**: DESIGN_IMPROVEMENTS.md로 이동

---

### 4. DESIGN_IMPROVEMENTS.md (구현 디테일 - 30분)

**📌 목적**: 피드백을 반영한 에러 처리, 세션 관리, 모니터링 등 구현 디테일 이해

**읽는 방법**:
```
1단계: "1. RemoteAgent 에러 처리 및 복원력 개선" 읽기
   → Circuit Breaker 패턴 이해
   → Retry + Exponential Backoff 이해
   → 폴링 종료 조건 명확화

2단계: "2. 세션 관리 전략" 읽기
   → LAZY, EXPLICIT, HYBRID 전략 이해
   → 자동 세션 생성 흐름 이해

3단계: "3. AgentRequest/Response 호환성 정책" 읽기
   → 버전 관리 방법
   → Legacy Adapter 역할

4단계: "4. 모니터링 및 헬스 체크" 읽기
   → Prometheus 메트릭
   → Health Check 엔드포인트

5단계: "5. Import 및 패키징 전략" 읽기
   → 절대 경로 import 설정
   → start_all_servers.sh 개선
```

**핵심 패턴 이해하기**:

#### Circuit Breaker 패턴
```
정상 (CLOSED)
  ↓ 5회 연속 실패
장애 (OPEN) - 요청 차단!
  ↓ 60초 대기
복구 시도 (HALF_OPEN)
  ↓ 성공 시
정상 (CLOSED)
```
→ **서버 장애 시 자동으로 요청 차단해서 시스템 보호**

#### Exponential Backoff
```
1차 실패 → 1초 대기
2차 실패 → 2초 대기
3차 실패 → 4초 대기
```
→ **재시도 시 점점 간격을 늘려서 서버 부하 줄임**

#### Session 전략
```python
HYBRID (권장):
  - 세션 ID 있으면 → 재사용
  - 세션 ID 없으면 → 자동 생성
  - API 레벨에서 생성, Agent는 재사용
```

#### 버전 관리
```python
AgentResponse(
    answer="...",
    version="1.0",  # 버전 필드
    # ...
)

# 기존 API는 Legacy Adapter로 변환
legacy = LegacyResponseAdapter.to_legacy_format(response)
```

**체크포인트**:
- [ ] Circuit Breaker가 왜 필요한지 이해
- [ ] Exponential Backoff 동작 원리 이해
- [ ] HYBRID 세션 전략 이해
- [ ] Legacy Adapter 역할 이해
- [ ] Prometheus 메트릭 종류 이해

---

## 🎯 문서별 활용 시점

### 기획/설계 단계
1. **REFACTORING_SUMMARY.md** - 팀원들에게 공유, 전체 그림 설명
2. **AGENT_REFACTORING_PLAN.md** - 아키텍처 리뷰, 설계 검증

### 구현 단계
1. **AGENT_REFACTORING_PLAN.md** - 컴포넌트 구현 시 참조
2. **DESIGN_IMPROVEMENTS.md** - 에러 처리, 세션 관리 구현 시 참조
3. **PARLANT_SERVER_SEPARATION_PLAN.md** - Parlant 서버 분리 시 참조

### 테스트/검증 단계
1. **DESIGN_IMPROVEMENTS.md** - Health Check, Monitoring 구현
2. **PARLANT_SERVER_SEPARATION_PLAN.md** - 서버 실행 스크립트 작성

---

## 📋 구현 체크리스트 (문서 기반)

### Week 1: 핵심 인프라
- [ ] AGENT_REFACTORING_PLAN.md → 3.4 AgentRegistry 구현
- [ ] AGENT_REFACTORING_PLAN.md → 3.1 BaseAgent 구현
- [ ] AGENT_REFACTORING_PLAN.md → 3.2 LocalAgent 구현
- [ ] DESIGN_IMPROVEMENTS.md → 1. RemoteAgent 구현 (Circuit Breaker)

### Week 2: 세션 + 호환성
- [ ] DESIGN_IMPROVEMENTS.md → 2. SessionManager (HYBRID)
- [ ] DESIGN_IMPROVEMENTS.md → 3. AgentRequest/Response + Legacy Adapter
- [ ] DESIGN_IMPROVEMENTS.md → API v1/v2 분리

### Week 3: Parlant 서버 분리
- [ ] PARLANT_SERVER_SEPARATION_PLAN.md → Phase 1 (공통 모듈)
- [ ] PARLANT_SERVER_SEPARATION_PLAN.md → Phase 2 (Research Paper)
- [ ] PARLANT_SERVER_SEPARATION_PLAN.md → Phase 3 (Medical Welfare)

### Week 4: 모니터링 + 프로덕션
- [ ] DESIGN_IMPROVEMENTS.md → 4. Monitoring + Health Check
- [ ] DESIGN_IMPROVEMENTS.md → 5. Import 설정
- [ ] PARLANT_SERVER_SEPARATION_PLAN.md → start_all_servers.sh

---

## 🤔 자주 묻는 질문

### Q1: 어떤 문서부터 읽어야 하나요?
**A**: REFACTORING_SUMMARY.md → AGENT_REFACTORING_PLAN.md 순서로 읽으세요.

### Q2: 구현 시작 전에 모든 문서를 읽어야 하나요?
**A**: 아니요. REFACTORING_SUMMARY.md로 전체 그림만 파악하고, 구현하면서 필요한 부분을 찾아 읽으세요.

### Q3: 가장 중요한 문서는 무엇인가요?
**A**: AGENT_REFACTORING_PLAN.md입니다. 전체 아키텍처와 컴포넌트 설계가 모두 들어있습니다.

### Q4: Parlant를 잘 모르는데 어떻게 하나요?
**A**: PARLANT_INTEGRATION.md (기존 문서)를 먼저 읽고, PARLANT_SERVER_SEPARATION_PLAN.md를 읽으세요.

### Q5: 에러 처리 구현이 어려워 보이는데요?
**A**: DESIGN_IMPROVEMENTS.md의 "1. RemoteAgent 에러 처리" 섹션에 전체 코드가 있습니다. 복사해서 사용하세요.

---

## 💡 효율적인 읽기 팁

### 1. 목적별 읽기
- **전체 이해**: REFACTORING_SUMMARY.md만 읽기 (5분)
- **설계 이해**: AGENT_REFACTORING_PLAN.md까지 읽기 (30분)
- **구현 준비**: 4개 문서 모두 읽기 (1.5시간)

### 2. 섹션별 건너뛰기
- 급하면 "코드 예시" 섹션은 나중에 읽기
- "비교 표" 섹션은 빠르게 스캔만 하기

### 3. 북마크 추천
- AGENT_REFACTORING_PLAN.md → "3. 핵심 컴포넌트 설계"
- DESIGN_IMPROVEMENTS.md → "1. RemoteAgent 에러 처리"
- PARLANT_SERVER_SEPARATION_PLAN.md → "구현 계획"

---

## 📖 문서 맵 (한눈에 보기)

```
REFACTORING_SUMMARY.md (5분)
├── 왜 리팩토링이 필요한가?
├── 무엇이 바뀌는가?
└── 얼마나 걸리는가?

AGENT_REFACTORING_PLAN.md (30분)
├── 현재 문제점
├── 새로운 아키텍처
├── BaseAgent / LocalAgent / RemoteAgent 설계
├── AgentRegistry 플러그인 시스템
└── Phase 1-5 마이그레이션

PARLANT_SERVER_SEPARATION_PLAN.md (20분)
├── 왜 서버를 분리하는가?
├── 어떻게 분리하는가?
├── 공통 모듈 재사용
└── start_all_servers.sh

DESIGN_IMPROVEMENTS.md (30분)
├── RemoteAgent 에러 처리 (Circuit Breaker)
├── 세션 관리 (LAZY/EXPLICIT/HYBRID)
├── 버전 관리 (Legacy Adapter)
├── 모니터링 (Prometheus)
└── Import 설정 (패키징)
```

---

## 🚀 시작하기

1. **지금 바로**: REFACTORING_SUMMARY.md 읽기 (5분)
2. **오늘 중**: AGENT_REFACTORING_PLAN.md 읽기 (30분)
3. **내일**: Phase 1 구현 시작 (AgentRegistry)

---

**작성일**: 2025-11-23
**버전**: 1.0
