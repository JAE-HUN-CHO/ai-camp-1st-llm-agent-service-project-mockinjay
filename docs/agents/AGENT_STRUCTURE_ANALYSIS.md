# Backend/Agent 디렉토리 구조 분석

**분석 날짜**: 2025-11-23  
**총 에이전트**: 5개 (3 Local + 2 Remote)  
**총 파일**: 100개 이상

---

## 📊 전체 구조 개요

```
backend/Agent/
├── 📁 core/                    # 핵심 인프라 레이어 (9 files)
├── 📁 parlant_common/          # Parlant 공통 도구 (6 files)
├── 📁 nutrition/               # 영양 에이전트 (Local)
├── 📁 quiz/                    # 퀴즈 에이전트 (Local)
├── 📁 trend_visualization/     # 트렌드 시각화 에이전트 (Local + LangGraph)
├── 📁 research_paper/          # 연구 논문 에이전트 (Remote, 25 files)
├── 📁 medical_welfare/         # 의료 복지 에이전트 (Remote, 5 files)
├── 📁 adapters/                # 어댑터 패턴
├── 📁 api/                     # API 관련 (5 files)
├── 📁 common/                  # 공통 유틸리티
├── 📁 config/                  # 설정
├── 📄 agent_manager.py         # 에이전트 관리자 (8.1KB)
├── 📄 base_agent.py            # 베이스 에이전트 (2.2KB)
├── 📄 context_tracker.py       # 컨텍스트 추적 (4.0KB)
├── 📄 session_manager.py       # 세션 관리 (4.7KB)
├── 📄 interactive_test.py      # 대화형 테스트 (8.9KB)
├── 📄 test_local_agents.py     # 로컬 에이전트 테스트 (9.3KB)
└── 📄 __init__.py
```

---

## 🏗️ 1. Core 인프라 레이어 (`core/`)

### 📁 파일 목록 (9개)

| 파일명              | 크기   | 설명                        |
| ------------------- | ------ | --------------------------- |
| `agent_registry.py` | 3.1KB  | 에이전트 자동 등록 시스템   |
| `contracts.py`      | 2.2KB  | AgentRequest/Response 계약  |
| `execution_type.py` | 292B   | LOCAL/REMOTE Enum           |
| `local_agent.py`    | 887B   | 로컬 에이전트 베이스 클래스 |
| `remote_agent.py`   | 14.6KB | 원격 에이전트 베이스 클래스 |
| `exceptions.py`     | 5.0KB  | 커스텀 예외 클래스          |
| `policies.py`       | 4.1KB  | 정책 관리                   |
| `types.py`          | 468B   | 타입 정의                   |
| `__init__.py`       | 183B   | 패키지 초기화               |

### 🔑 핵심 기능

#### 1.1 AgentRegistry (agent_registry.py)

```python
class AgentRegistry:
    """에이전트 자동 등록 및 관리"""

    @classmethod
    def register(cls, agent_type: str):
        """데코레이터로 에이전트 등록"""

    @classmethod
    def create_agent(cls, agent_type: str):
        """등록된 에이전트 인스턴스 생성"""

    @classmethod
    def list_agents(cls):
        """등록된 모든 에이전트 목록"""
```

**사용 예시**:

```python
@AgentRegistry.register("nutrition")
class NutritionAgent(LocalAgent):
    pass
```

#### 1.2 Contracts (contracts.py)

```python
class AgentRequest(BaseModel):
    """통합 요청 계약"""
    query: str
    session_id: str
    context: Dict[str, Any]
    profile: str = "general"
    language: str = "ko"

class AgentResponse(BaseModel):
    """통합 응답 계약"""
    answer: str
    sources: List[Dict]
    papers: List[Dict]
    tokens_used: int
    status: str
    agent_type: str
    metadata: Dict[str, Any]
```

#### 1.3 ExecutionType (execution_type.py)

```python
class ExecutionType(Enum):
    LOCAL = "local"   # Python 프로세스 내 실행
    REMOTE = "remote" # Parlant 서버 HTTP 통신
```

#### 1.4 LocalAgent (local_agent.py)

```python
class LocalAgent(BaseAgent):
    """로컬 실행 에이전트 베이스"""

    @abstractmethod
    async def process(self, request: AgentRequest) -> AgentResponse:
        """에이전트 로직 구현"""

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """에이전트 메타데이터"""
```

---

## 🛠️ 2. Parlant Common (`parlant_common/`)

### 📁 파일 목록 (6개)

| 파일명                  | 크기   | 설명                             |
| ----------------------- | ------ | -------------------------------- |
| `emergency_tools.py`    | 2.5KB  | 응급 상황 감지 도구              |
| `kidney_tools.py`       | 13.1KB | CKD 정보 도구 (단계, 증상)       |
| `utils.py`              | 2.7KB  | 공통 유틸리티 (프로필, ObjectId) |
| `server.py`             | 2.5KB  | Parlant 서버 헬퍼                |
| `run_unified_server.py` | 2.2KB  | 통합 서버 실행 스크립트          |
| `__init__.py`           | 543B   | 패키지 export                    |

### 🔑 핵심 도구

#### 2.1 Emergency Tools (emergency_tools.py)

```python
async def check_emergency_keywords(context: ToolContext, text: str):
    """응급 키워드 감지"""
    # 감지 키워드: 가슴 통증, 호흡곤란, 의식 저하 등
    # 911/119 안내 제공
```

#### 2.2 Kidney Tools (kidney_tools.py)

```python
async def get_kidney_stage_info(context: ToolContext, gfr: float = None, stage: int = None):
    """CKD 단계 정보 (1-5단계)"""
    # GFR 기반 또는 단계 번호 기반

async def get_symptom_info(context: ToolContext, symptoms: str):
    """증상 정보 및 관리 방법"""
    # 응급 감지 통합
```

#### 2.3 Utils (utils.py)

```python
async def get_profile(context: ToolContext) -> str:
    """사용자 프로필 결정 (researcher/patient/general)"""

def convert_objectid_to_str(data):
    """MongoDB ObjectId를 문자열로 변환"""

def get_default_profile() -> str:
    """환경변수에서 기본 프로필 가져오기"""
```

#### 2.4 Unified Server (run_unified_server.py)

```python
async def main():
    """Port 8800에 두 Agent 등록"""
    async with p.Server(host="127.0.0.1", port=8800) as server:
        await register_research_agent(server)
        await register_welfare_agent(server)
```

**실행 방법**:

```bash
source .venv/bin/activate && python backend/Agent/parlant_common/run_unified_server.py
```

---

## 🥗 3. Nutrition Agent (`nutrition/`)

### 구조

```
nutrition/
├── agent.py          # NutritionAgent 구현
├── prompts.py        # 프롬프트 템플릿
└── __init__.py
```

### 특징

- **타입**: Local Agent
- **기능**: 식단 분석 및 CKD 환자 맞춤 영양 추천
- **등록**: `@AgentRegistry.register("nutrition")`
- **실행**: Python 프로세스 내 직접 실행

---

## 📝 4. Quiz Agent (`quiz/`)

### 구조

```
quiz/
├── agent.py          # QuizAgent 구현
├── prompts.py        # 퀴즈 생성 프롬프트
└── __init__.py
```

### 특징

- **타입**: Local Agent
- **기능**: RAG 기반 CKD 관련 퀴즈 생성
- **등록**: `@AgentRegistry.register("quiz")`
- **데이터**: MongoDB QA 컬렉션 활용

---

## 📊 5. Trend Visualization Agent (`trend_visualization/`)

### 구조

```
trend_visualization/
├── agent.py          # TrendVisualizationAgent (LangGraph)
├── prompts.py        # 분석 프롬프트
└── __init__.py
```

### 특징

- **타입**: Local Agent + **LangGraph**
- **기능**: PubMed 기반 CKD 연구 트렌드 분석 및 시각화
- **등록**: `@AgentRegistry.register("trend_visualization")`
- **워크플로우**:
  ```
  analyze_request → fetch_pubmed_data → generate_visualization → generate_explanation
  ```

### LangGraph StateGraph

```python
class AgentState(TypedDict):
    query: str
    session_id: str
    context: Dict[str, Any]
    analysis: Optional[Dict]
    pubmed_data: Optional[List]
    visualization: Optional[Dict]
    explanation: Optional[str]
    error: Optional[str]
```

---

## 📚 6. Research Paper Agent (`research_paper/`)

### 구조 (25 files)

```
research_paper/
├── agent.py                    # ResearchPaperAgent (Remote)
├── server/
│   ├── healthcare_v2_en.py     # Parlant 서버 (Port 8800)
│   ├── research_paper_server.py
│   ├── research_paper_guidelines.py
│   ├── advanced_components.py
│   ├── cache_manager.py
│   └── ... (20+ files)
└── __init__.py
```

### 특징

- **타입**: Remote Agent
- **서버**: Port 8800 (healthcare_v2_en.py)
- **등록**: `@AgentRegistry.register("research_paper")`
- **통신**: AsyncParlantClient
- **기능**:
  - 하이브리드 검색 (MongoDB + Pinecone + PubMed)
  - 논문 검색 및 QA
  - 프로필 기반 결과 제한

### Agent 구조

```python
class ResearchPaperAgent(LocalAgent):
    _server_url = "http://localhost:8800"

    async def process(self, request: AgentRequest) -> AgentResponse:
        # 1. Parlant 서버 자동 시작
        await self._ensure_server_running()

        # 2. Client 연결
        client = await self._get_client()

        # 3. 세션 생성 (프로필 태그 포함)
        session = await client.sessions.create(...)

        # 4. 메시지 전송
        await client.sessions.create_event(...)

        # 5. 응답 폴링
        events = await client.sessions.list_events(...)

        # 6. 응답 조합
        return AgentResponse(...)
```

---

## 🏥 7. Medical Welfare Agent (`medical_welfare/`)

### 구조 (5 files)

```
medical_welfare/
├── agent.py                        # MedicalWelfareAgent (Remote)
├── server/
│   ├── medical_welfare_server.py   # Parlant 서버
│   ├── medical_welfare_guidelines.py
│   └── __init__.py
└── __init__.py
```

### 특징

- **타입**: Remote Agent
- **서버**: Port 8800 (healthcare_v2_en.py 공유)
- **등록**: `@AgentRegistry.register("medical_welfare")`
- **통신**: AsyncParlantClient
- **기능**:
  - 복지 프로그램 검색 (13개 프로그램)
  - 병원/약국/투석센터 검색 (104,836개 시설)
  - 위치 기반 검색

### Parlant Tools

```python
@p.tool
async def search_welfare_programs(
    context: ToolContext,
    query: str,
    category: Optional[str] = None,
    disease: Optional[str] = None,
    ckd_stage: Optional[int] = None
) -> ToolResult:
    """복지 프로그램 검색"""

@p.tool
async def search_hospitals(
    context: ToolContext,
    query: str,
    hospital_type: Optional[str] = None,
    region: Optional[str] = None,
    has_dialysis: Optional[bool] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> ToolResult:
    """병원/시설 검색"""
```

---

## 🔧 8. Agent Manager (`agent_manager.py`)

### 기능

```python
class AgentManager:
    """에이전트 통합 관리자"""

    def __init__(self):
        # AgentRegistry에서 자동 발견
        self.agents = {}
        for agent_type in AgentRegistry.list_agents():
            self.agents[agent_type] = AgentRegistry.create_agent(agent_type)

    async def process_query(
        self,
        query: str,
        agent_type: str,
        session_id: str,
        context: Dict = None
    ) -> Dict:
        """쿼리 처리 (AgentRequest/Response 변환)"""
```

### 특징

- ✅ 하드코딩 제거
- ✅ AgentRegistry 자동 발견
- ✅ 통합된 계약 (Request/Response)
- ✅ 동적 에이전트 초기화

---

## 🧪 9. 테스트 파일

### 9.1 interactive_test.py (8.9KB)

```python
"""대화형 에이전트 테스트"""
# 사용자가 에이전트 선택 → 쿼리 입력 → 응답 확인
```

**실행**:

```bash
python backend/Agent/interactive_test.py
```

### 9.2 test_local_agents.py (9.3KB)

```python
"""로컬 에이전트 자동 테스트"""
# AgentRegistry 검증
# 메타데이터 검증
# process() 메서드 검증
```

**실행**:

```bash
python backend/Agent/test_local_agents.py
```

---

## 📊 통계 요약

### 에이전트 분포

| 타입     | 개수  | 에이전트                            |
| -------- | ----- | ----------------------------------- |
| Local    | 3     | Nutrition, Quiz, TrendVisualization |
| Remote   | 2     | ResearchPaper, MedicalWelfare       |
| **총계** | **5** |                                     |

### 파일 크기 분포

| 카테고리       | 파일 수 | 총 크기     |
| -------------- | ------- | ----------- |
| Core           | 9       | ~35KB       |
| Parlant Common | 6       | ~23KB       |
| Agents         | 40+     | ~150KB+     |
| Tests          | 3       | ~23KB       |
| **총계**       | **60+** | **~230KB+** |

### 코드 라인 수 (추정)

| 카테고리            | 라인 수    |
| ------------------- | ---------- |
| Core Infrastructure | ~800       |
| Parlant Common      | ~600       |
| Local Agents        | ~1,500     |
| Remote Agents       | ~1,200     |
| Tests               | ~500       |
| **총계**            | **~4,600** |

---

## 🎯 핵심 디자인 패턴

### 1. **Registry Pattern**

```python
@AgentRegistry.register("agent_name")
class MyAgent(LocalAgent):
    pass
```

### 2. **Strategy Pattern**

```python
# LocalAgent vs RemoteAgent
if execution_type == ExecutionType.LOCAL:
    result = await agent.process(request)
else:
    result = await remote_agent.call_parlant_server(request)
```

### 3. **Singleton Pattern**

```python
class ResearchPaperAgent:
    _parlant_client: Optional[AsyncParlantClient] = None

    @classmethod
    async def _get_client(cls):
        if cls._parlant_client is None:
            cls._parlant_client = AsyncParlantClient(...)
        return cls._parlant_client
```

### 4. **Factory Pattern**

```python
AgentRegistry.create_agent("nutrition")  # NutritionAgent 인스턴스 생성
```

---

## 🚀 실행 흐름

### Local Agent 실행

```
User Query
    ↓
AgentManager.process_query()
    ↓
AgentRegistry.create_agent("nutrition")
    ↓
NutritionAgent.process(AgentRequest)
    ↓
AgentResponse
```

### Remote Agent 실행

```
User Query
    ↓
AgentManager.process_query()
    ↓
ResearchPaperAgent.process(AgentRequest)
    ↓
AsyncParlantClient.sessions.create_event()
    ↓
Parlant Server (Port 8800)
    ↓
Tool Execution (search_medical_qa)
    ↓
AsyncParlantClient.sessions.list_events()
    ↓
AgentResponse
```

---

## 📝 주요 의존성

### Python 패키지

- `parlant.sdk` - Parlant 서버/클라이언트
- `langgraph` - TrendVisualizationAgent 워크플로우
- `langchain-community` - LangChain 통합
- `pydantic` - 데이터 검증
- `motor` - MongoDB 비동기 드라이버
- `httpx` - HTTP 클라이언트

### 내부 의존성

```
Agent
  ├── core (인프라)
  ├── parlant_common (공통 도구)
  ├── app.services (검색 엔진)
  ├── app.db (데이터베이스 매니저)
  └── app.utils (유틸리티)
```

---

## 🎉 결론

`backend/Agent` 디렉토리는:

- ✅ **모듈화**: 명확한 책임 분리
- ✅ **확장성**: 새 에이전트 추가 용이
- ✅ **유지보수성**: 통합된 계약 및 패턴
- ✅ **테스트 가능**: 자동화된 테스트
- ✅ **현대적**: LangGraph, AsyncParlantClient 사용

**총 5개 에이전트**가 **통합된 아키텍처**로 **CKD 환자 지원 시스템**을 구성합니다! 🎊
