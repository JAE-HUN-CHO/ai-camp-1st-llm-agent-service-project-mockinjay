# Parlant 서버 분리 계획

## 현재 상황

### 문제점
`healthcare_v2_en.py`에 모든 도구가 하나의 서버에 등록되어 있음:
- `search_medical_qa` (Research Paper Agent용)
- `search_welfare_programs` (Medical Welfare Agent용)
- `search_hospitals` (Medical Welfare Agent용)
- 기타 보조 도구들 (CKD stage, symptoms, emergency)

### 결과
- 에이전트별 독립 실행 불가능
- 서버 하나가 죽으면 모든 기능 중단
- 확장성 제약 (새 에이전트 추가 시 기존 서버 수정 필요)

---

## 분리 전략

### 옵션 A: 에이전트별 완전 독립 서버 (권장)
```
backend/Agent/agents/remote/
├── research_paper/
│   └── server/
│       ├── research_paper_server.py  # Parlant 서버
│       │   └── @p.tool search_medical_qa
│       │   └── @p.tool get_kidney_stage_info
│       │   └── @p.tool check_emergency_keywords
│       └── run_server.py (port 8800)
│
├── medical_welfare/
│   └── server/
│       ├── medical_welfare_server.py  # Parlant 서버
│       │   └── @p.tool search_welfare_programs
│       │   └── @p.tool search_hospitals
│       │   └── @p.tool check_emergency_keywords
│       └── run_server.py (port 8801)
│
└── common/
    ├── emergency_tools.py  # 공통 도구
    │   └── check_emergency_keywords
    └── parlant_utils.py    # 공통 유틸
```

**장점**:
- 완전한 독립성 (한 서버 장애가 다른 서버에 영향 없음)
- 스케일링 용이 (각 서버를 독립적으로 확장)
- 명확한 책임 분리

**단점**:
- 코드 중복 가능성 (emergency_tools 등)
- 서버 관리 복잡도 증가

### 옵션 B: 공통 도구 서버 + 전문 서버 (하이브리드)
```
backend/Agent/agents/remote/
├── common_tools/
│   └── server/
│       ├── common_server.py  # 공통 도구 서버
│       │   └── @p.tool check_emergency_keywords
│       │   └── @p.tool get_kidney_stage_info
│       │   └── @p.tool get_symptom_info
│       └── run_server.py (port 8799)
│
├── research_paper/
│   └── server/
│       ├── research_server.py  # 논문 검색 전문
│       │   └── @p.tool search_medical_qa
│       └── run_server.py (port 8800)
│
└── medical_welfare/
    └── server/
        ├── welfare_server.py  # 복지 검색 전문
        │   └── @p.tool search_welfare_programs
        │   └── @p.tool search_hospitals
        └── run_server.py (port 8801)
```

**장점**:
- 코드 중복 최소화
- 공통 도구 재사용
- 유지보수 효율성

**단점**:
- 공통 서버가 SPOF가 될 수 있음
- 서버 간 의존성 발생

---

## 권장: 옵션 A (완전 독립)

### 이유
1. **장애 격리**: 한 에이전트 문제가 다른 에이전트에 영향 없음
2. **확장성**: 각 에이전트를 독립적으로 확장 가능
3. **배포 유연성**: 각 서버를 다른 머신에 배포 가능
4. **명확한 경계**: 에이전트별 책임이 명확

### 중복 해결 방안
공통 도구는 **Python 모듈로 공유**:
```python
# agents/remote/common/emergency_tools.py
@p.tool
async def check_emergency_keywords(context, text):
    # 공통 구현
    ...

# research_paper/server/research_server.py
from ...common.emergency_tools import check_emergency_keywords

# medical_welfare/server/welfare_server.py
from ...common.emergency_tools import check_emergency_keywords
```

---

## 구현 계획

### Phase 1: 공통 모듈 추출
1. `agents/remote/common/` 생성
2. 공통 도구 분리:
   - `emergency_tools.py`: check_emergency_keywords
   - `kidney_tools.py`: get_kidney_stage_info, get_symptom_info
   - `parlant_utils.py`: get_profile, convert_objectid_to_str 등

### Phase 2: Research Paper 서버 분리
1. `agents/remote/research_paper/server/research_server.py` 생성
2. `search_medical_qa` 도구 이전
3. 필요한 공통 도구 import
4. Guidelines, Journey 설정
5. 테스트 및 검증

### Phase 3: Medical Welfare 서버 생성
1. `agents/remote/medical_welfare/server/welfare_server.py` 생성
2. `search_welfare_programs`, `search_hospitals` 도구 이전
3. 필요한 공통 도구 import
4. Guidelines, Journey 설정
5. 테스트 및 검증

### Phase 4: RemoteAgent 어댑터 업데이트
1. 각 에이전트별 RemoteAgent 설정
   ```python
   # agents/remote/research_paper/agent.py
   class ResearchPaperAgent(RemoteAgent):
       def __init__(self):
           super().__init__(
               agent_type="research_paper",
               server_url="127.0.0.1",
               server_port=8800,
           )

   # agents/remote/medical_welfare/agent.py
   class MedicalWelfareAgent(RemoteAgent):
       def __init__(self):
           super().__init__(
               agent_type="medical_welfare",
               server_url="127.0.0.1",
               server_port=8801,
           )
   ```

### Phase 5: 기존 healthcare_v2_en.py 단계적 폐기
1. 새 서버들이 안정화되면
2. 기존 서버 deprecated 마크
3. 프론트엔드 전환 완료 후
4. 기존 파일 삭제

---

## 서버 실행 관리

### 개발 환경
```bash
# 모든 서버 동시 실행 스크립트
# backend/Agent/agents/remote/start_all_servers.sh

#!/bin/bash
echo "Starting all Parlant servers..."

# Research Paper Server
python -m Agent.agents.remote.research_paper.server.run_server &
RESEARCH_PID=$!

# Medical Welfare Server
python -m Agent.agents.remote.medical_welfare.server.run_server &
WELFARE_PID=$!

echo "✅ All servers started"
echo "   Research Paper: PID $RESEARCH_PID (port 8800)"
echo "   Medical Welfare: PID $WELFARE_PID (port 8801)"
echo ""
echo "To stop all servers: kill $RESEARCH_PID $WELFARE_PID"
```

### 프로덕션 환경
```yaml
# docker-compose.yml
services:
  research-paper-server:
    build: ./backend/Agent/agents/remote/research_paper
    ports:
      - "8800:8800"
    environment:
      - PARLANT_PORT=8800
    restart: unless-stopped

  medical-welfare-server:
    build: ./backend/Agent/agents/remote/medical_welfare
    ports:
      - "8801:8801"
    environment:
      - PARLANT_PORT=8801
    restart: unless-stopped
```

---

## 코드 예시

### 공통 도구 모듈
```python
# agents/remote/common/emergency_tools.py
import parlant.sdk as p
from parlant.sdk import ToolContext, ToolResult

@p.tool
async def check_emergency_keywords(context: ToolContext, text: str) -> ToolResult:
    """Emergency keyword detection (공통 도구)"""
    EMERGENCY_KEYWORDS_EN = [...]
    EMERGENCY_KEYWORDS_KO = [...]

    found = [kw for kw in EMERGENCY_KEYWORDS if kw in text.lower()]

    return ToolResult(data={
        "is_emergency": len(found) > 0,
        "found_keywords": found,
        "message": "..." if found else "No emergency"
    })
```

### Research Paper 서버
```python
# agents/remote/research_paper/server/research_server.py
import parlant.sdk as p
from ...common.emergency_tools import check_emergency_keywords
from ...common.kidney_tools import get_kidney_stage_info, get_symptom_info
from ...common.parlant_utils import get_profile, convert_objectid_to_str

# 기존 search_medical_qa 로직 (변경 없음)
@p.tool
async def search_medical_qa(context, query, profile="general", ...):
    # 기존 구현 그대로
    ...

async def main():
    """Research Paper Parlant Server"""
    async with p.Server(
        name="Research Paper Agent",
        description="Medical research and PubMed search agent",
        nlp_service=create_healthcare_nlp_service,
        host="0.0.0.0",
        port=8800,
    ) as server:
        # Agent 생성
        agent = await server.create_agent(
            name="CareGuide Research",
            description="Healthcare research assistant"
        )

        # Guidelines 추가
        await add_safety_guidelines(agent)
        await add_profile_guidelines(agent, disclaimer_guideline)

        # Journey 추가
        await create_medical_info_journey(agent)
        await create_research_paper_journey(agent)

        print("✅ Research Paper Server running on port 8800")
        await server.run()
```

### Medical Welfare 서버
```python
# agents/remote/medical_welfare/server/welfare_server.py
import parlant.sdk as p
from ...common.emergency_tools import check_emergency_keywords
from ...common.parlant_utils import get_profile

# Welfare 전용 도구들
@p.tool
async def search_welfare_programs(context, query, category=None, ...):
    # 기존 구현
    ...

@p.tool
async def search_hospitals(context, query=None, region=None, ...):
    # 기존 구현
    ...

async def main():
    """Medical Welfare Parlant Server"""
    async with p.Server(
        name="Medical Welfare Agent",
        description="Welfare programs and hospital search",
        nlp_service=create_healthcare_nlp_service,
        host="0.0.0.0",
        port=8801,
    ) as server:
        agent = await server.create_agent(
            name="CareGuide Welfare",
            description="Welfare and hospital assistant"
        )

        # Welfare 전용 Guidelines
        await add_welfare_guidelines(agent)

        # Welfare Journey
        await create_welfare_journey(agent)

        print("✅ Medical Welfare Server running on port 8801")
        await server.run()
```

---

## RemoteAgent 통합

```python
# core/remote_agent.py (AGENT_REFACTORING_PLAN.md에서 설계한 것)
class RemoteAgent(BaseAgent):
    """원격 Parlant 서버 어댑터"""

    async def process(self, request: AgentRequest) -> AgentResponse:
        # HTTP로 Parlant 서버 호출
        # 이벤트 폴링 및 응답 수집
        ...

# agents/remote/research_paper/agent.py
@AgentRegistry.register("research_paper")
class ResearchPaperAgent(RemoteAgent):
    def __init__(self):
        super().__init__(
            agent_type="research_paper",
            server_url="127.0.0.1",
            server_port=8800,  # Research 서버
        )

# agents/remote/medical_welfare/agent.py
@AgentRegistry.register("medical_welfare")
class MedicalWelfareAgent(RemoteAgent):
    def __init__(self):
        super().__init__(
            agent_type="medical_welfare",
            server_url="127.0.0.1",
            server_port=8801,  # Welfare 서버
        )
```

---

## 마이그레이션 체크리스트

- [ ] Phase 1: 공통 모듈 추출
  - [ ] `agents/remote/common/emergency_tools.py`
  - [ ] `agents/remote/common/kidney_tools.py`
  - [ ] `agents/remote/common/parlant_utils.py`
  - [ ] 단위 테스트 작성

- [ ] Phase 2: Research Paper 서버
  - [ ] `research_server.py` 생성
  - [ ] `search_medical_qa` 이전
  - [ ] Guidelines 설정
  - [ ] Journey 설정
  - [ ] 테스트 (기존 healthcare_v2_en.py와 동일 동작 확인)

- [ ] Phase 3: Medical Welfare 서버
  - [ ] `welfare_server.py` 생성
  - [ ] `search_welfare_programs`, `search_hospitals` 이전
  - [ ] Guidelines 설정
  - [ ] Journey 설정
  - [ ] 테스트

- [ ] Phase 4: RemoteAgent 구현
  - [ ] `core/remote_agent.py` 작성
  - [ ] Parlant 이벤트 폴링 로직
  - [ ] `ResearchPaperAgent(RemoteAgent)` 구현
  - [ ] `MedicalWelfareAgent(RemoteAgent)` 구현

- [ ] Phase 5: 통합 테스트
  - [ ] 두 서버 동시 실행
  - [ ] AgentManager 라우팅 테스트
  - [ ] 프론트엔드 연동 테스트

- [ ] Phase 6: 배포 준비
  - [ ] `start_all_servers.sh` 스크립트
  - [ ] Docker Compose 설정
  - [ ] 모니터링 설정

- [ ] Phase 7: 기존 서버 폐기
  - [ ] `healthcare_v2_en.py` deprecated
  - [ ] 프론트엔드 전환
  - [ ] 기존 파일 삭제

---

## 환경 변수

```bash
# .env

# Research Paper Server
RESEARCH_PARLANT_HOST=127.0.0.1
RESEARCH_PARLANT_PORT=8800

# Medical Welfare Server
WELFARE_PARLANT_HOST=127.0.0.1
WELFARE_PARLANT_PORT=8801

# Common
OLLAMA_BASE_URL=http://localhost:11434
MONGODB_URI=...
OLLAMA_EMBEDDING_MODEL=nomic-embed-text-v2-moe
```

---

## 기대 효과

### 장애 격리
- Research Paper 서버 장애 → Medical Welfare는 정상 동작
- 반대도 마찬가지

### 독립 확장
- Research Paper 트래픽 많음 → 해당 서버만 스케일 아웃
- Medical Welfare는 그대로 유지

### 배포 유연성
- Research Paper 업데이트 → 해당 서버만 재시작
- Zero-downtime 배포 가능 (rolling update)

### 개발 효율성
- 팀을 나눠서 각 서버 담당 가능
- 도메인별 전문성 확보

---

**작성일**: 2025-11-23
**버전**: 1.0
**관련 문서**: AGENT_REFACTORING_PLAN.md
