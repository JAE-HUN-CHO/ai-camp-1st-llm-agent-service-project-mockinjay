# 복합 질문 처리 Router 설계 문서

**프로젝트**: CareGuide AI Agent System
**작성일**: 2025-11-23
**버전**: 1.0
**관련 문서**: AGENT_REFACTORING_PLAN.md, DESIGN_IMPROVEMENTS.md

---

## 📋 목차

1. [개요](#1-개요)
2. [요구사항](#2-요구사항)
3. [아키텍처 설계](#3-아키텍처-설계)
4. [컴포넌트 상세 설계](#4-컴포넌트-상세-설계)
5. [데이터 모델](#5-데이터-모델)
6. [처리 플로우](#6-처리-플로우)
7. [구현 가이드](#7-구현-가이드)
8. [테스트 전략](#8-테스트-전략)

---

## 1. 개요

### 1.1 배경

현재 CareGuide 시스템은 단일 에이전트 라우팅만 지원합니다:
- 사용자가 `agent_type`을 명시해야 함
- 복합 질문 처리 불가 (예: "저염식 레시피 알려주고, 관련 논문도 찾아줘")
- 하나의 에이전트만 호출 가능

### 1.2 목표

**복합 질문 처리 시스템** 구축:
1. **의도 자동 분류**: GPT-4o를 사용하여 사용자 질문의 의도 파악
2. **질문 분해**: 복합 질문을 서브 쿼리로 분해
3. **병렬 처리**: 여러 에이전트를 동시에 호출하여 응답 시간 단축
4. **응답 통합**: 여러 에이전트의 답변을 하나의 일관된 응답으로 조합

### 1.3 주요 기능

- ✅ 단일 질문 자동 라우팅
- ✅ 복합 질문 분해 및 병렬 처리
- ✅ GPT-4o 기반 응답 통합
- ✅ 부분 성공 허용 (일부 에이전트 실패 시에도 답변 생성)
- ✅ 타임아웃 및 에러 처리

---

## 2. 요구사항

### 2.1 기능적 요구사항

| 요구사항 ID | 설명 | 우선순위 |
|------------|------|---------|
| FR-1 | 사용자 입력에서 의도 자동 분류 | 필수 |
| FR-2 | 단일/복합 질문 자동 판단 | 필수 |
| FR-3 | 복합 질문을 서브 쿼리로 분해 | 필수 |
| FR-4 | 여러 에이전트 병렬 호출 | 필수 |
| FR-5 | 여러 에이전트 응답을 하나로 통합 | 필수 |
| FR-6 | 부분 성공 시 경고와 함께 응답 반환 | 권장 |
| FR-7 | 에이전트별 타임아웃 설정 | 권장 |

### 2.2 비기능적 요구사항

| 요구사항 ID | 설명 | 목표 |
|------------|------|------|
| NFR-1 | 의도 분류 응답 시간 | < 2초 |
| NFR-2 | 병렬 처리 응답 시간 | 단일 대비 1.5배 이하 |
| NFR-3 | 에이전트별 타임아웃 | 30초 |
| NFR-4 | 응답 통합 시간 | < 3초 |
| NFR-5 | 부분 성공률 허용 | 최소 1개 성공 시 응답 |

---

## 3. 아키텍처 설계

### 3.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                         │
└───────────────────┬─────────────────────────────────┘
                    │ POST /api/agents/query
                    │ {user_input, session_id}
                    ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI Router                     │
│            /api/agents/query 엔드포인트             │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│                  QueryRouter                        │
│              (복합 질문 처리 로직)                   │
└───────────────────┬─────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐      ┌────────────────┐
│IntentClassifier│      │ResponseAggregator│
│  (의도 분류)   │      │  (응답 통합)    │
└───────┬───────┘      └────────┬───────┘
        │                       │
        │ intent_result         │ aggregated_response
        ▼                       ▲
┌─────────────────────────────────────────────────────┐
│                  AgentManager                       │
│              (기존 에이전트 관리)                    │
└───────────────────┬─────────────────────────────────┘
                    │
        ┌───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │Nutrition│ │Research│ │ Quiz   │ │Welfare │
    │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
    └────────┘ └────────┘ └────────┘ └────────┘
```

### 3.2 폴더 구조 (업데이트)

```
backend/Agent/
├── core/
│   ├── contracts.py          # AgentRequest, AgentResponse
│   ├── base_agent.py         # BaseAgent
│   └── exceptions.py         # 커스텀 예외
│
├── application/              # 🆕 애플리케이션 레이어
│   ├── __init__.py
│   ├── agent_manager.py      # AgentManager (기존)
│   ├── router.py             # 🆕 QueryRouter (복합 질문 처리)
│   ├── intent_classifier.py  # 🆕 IntentClassifier (의도 분류)
│   └── response_aggregator.py # 🆕 ResponseAggregator (응답 통합)
│
├── agents/
│   ├── nutrition/agent.py
│   ├── research_paper/agent.py
│   ├── quiz/agent.py
│   └── medical_welfare/agent.py
│
├── infrastructure/
│   └── services/
│       └── openai_service.py
│
└── utils/
    ├── prompts.py            # 🆕 프롬프트 템플릿
    └── validators.py
```

---

## 4. 컴포넌트 상세 설계

### 4.1 IntentClassifier (의도 분류기)

**파일**: `backend/Agent/application/intent_classifier.py`

**역할**:
- GPT-4o를 사용하여 사용자 입력의 의도 분류
- 단일 vs 복합 질문 판단
- 복합 질문을 서브 쿼리로 분해

**클래스 다이어그램**:
```python
class IntentClassifier:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def classify(self, user_input: str) -> IntentClassificationResult:
        """
        사용자 입력 분류

        Returns:
            IntentClassificationResult {
                intent_type: "single" | "multi",
                primary_intent: QueryIntent,
                sub_intents: List[QueryIntent],
                decomposed_queries: List[SubQuery]
            }
        """

    def _parse_intent_result(self, response) -> IntentClassificationResult:
        """GPT-4o 응답을 파싱하여 IntentClassificationResult 생성"""

    def _validate_intent(self, intent: str) -> bool:
        """의도가 유효한지 검증 (정의된 에이전트 타입에 해당하는지)"""
```

**의도 타입 정의**:
```python
from enum import Enum

class QueryIntent(Enum):
    """질문 의도 타입"""
    NUTRITION = "nutrition"
    RESEARCH = "research_paper"
    WELFARE = "medical_welfare"
    QUIZ = "quiz"
    TREND = "trend_visualization"
```

**프롬프트 템플릿**:
```python
INTENT_CLASSIFICATION_PROMPT = """
당신은 만성 신장 질환(CKD) 환자를 돕는 AI 어시스턴트의 의도 분류기입니다.

사용자 질문을 분석하여 다음 카테고리로 분류하세요:
- nutrition: 음식, 영양, 식단, 칼로리, 영양소 관련
- research_paper: 의학 논문, 연구 자료, 임상 연구 검색
- medical_welfare: 복지 제도, 병원 정보, 의료 지원
- quiz: 퀴즈, 학습, 테스트, 문제 풀이
- trend_visualization: 통계, 트렌드, 데이터 시각화

복합 질문의 경우, 각 의도별로 분해하여 반환하세요.

**중요 규칙**:
1. 단일 질문: intent_type을 "single"로 설정하고 decomposed_queries는 빈 배열
2. 복합 질문: intent_type을 "multi"로 설정하고 각 의도별로 쿼리 분해
3. primary_intent는 가장 중요한 의도 (사용자가 먼저 언급한 것)
4. 각 분해된 쿼리는 완전한 문장으로 작성

**예시 1 (단일)**:
입력: "당근의 칼륨 함량이 얼마나 되나요?"
출력:
{
  "intent_type": "single",
  "primary_intent": "nutrition",
  "sub_intents": [],
  "decomposed_queries": []
}

**예시 2 (복합 - 2개)**:
입력: "저염식 레시피 알려주고, 관련 논문도 찾아줘"
출력:
{
  "intent_type": "multi",
  "primary_intent": "nutrition",
  "sub_intents": ["nutrition", "research_paper"],
  "decomposed_queries": [
    {
      "intent": "nutrition",
      "query": "저염식 레시피를 추천해주세요"
    },
    {
      "intent": "research_paper",
      "query": "저염식 식이요법 관련 의학 논문을 검색해주세요"
    }
  ]
}

**예시 3 (복합 - 3개)**:
입력: "CKD 3기 환자 식단 추천하고, 근처 병원 알려주고, 관련 퀴즈 풀고 싶어"
출력:
{
  "intent_type": "multi",
  "primary_intent": "nutrition",
  "sub_intents": ["nutrition", "medical_welfare", "quiz"],
  "decomposed_queries": [
    {
      "intent": "nutrition",
      "query": "CKD 3기 환자를 위한 식단을 추천해주세요"
    },
    {
      "intent": "medical_welfare",
      "query": "근처 병원 정보를 알려주세요"
    },
    {
      "intent": "quiz",
      "query": "CKD 관련 퀴즈를 풀고 싶습니다"
    }
  ]
}

JSON 형식으로만 응답하세요. 추가 설명은 포함하지 마세요.
"""
```

---

### 4.2 QueryRouter (복합 질문 라우터)

**파일**: `backend/Agent/application/router.py`

**역할**:
- 의도 분류 결과를 받아 적절한 처리 방식 선택
- 단일 질문: 기존 AgentManager 사용
- 복합 질문: 병렬 처리 + 응답 통합

**클래스 다이어그램**:
```python
class QueryRouter:
    def __init__(
        self,
        agent_manager: AgentManager,
        intent_classifier: IntentClassifier,
        response_aggregator: ResponseAggregator
    ):
        self.agent_manager = agent_manager
        self.intent_classifier = intent_classifier
        self.response_aggregator = response_aggregator

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

    async def _process_single_intent(
        self,
        intent: QueryIntent,
        query: str,
        session_id: str,
        context: Optional[Dict]
    ) -> RouterResult:
        """단일 의도 처리 (기존 route_request 사용)"""

    async def _process_multi_intent(
        self,
        decomposed_queries: List[SubQuery],
        session_id: str,
        context: Optional[Dict]
    ) -> RouterResult:
        """복합 의도 처리 (병렬 + 통합)"""

    def _group_by_agent(
        self,
        decomposed_queries: List[SubQuery]
    ) -> Dict[str, List[SubQuery]]:
        """에이전트별 쿼리 그룹화"""
```

**병렬 처리 로직**:
```python
async def _process_multi_intent(
    self,
    decomposed_queries: List[SubQuery],
    session_id: str,
    context: Optional[Dict]
) -> RouterResult:
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
    timeout_seconds = 30
    results = await asyncio.gather(
        *[
            asyncio.wait_for(task, timeout=timeout_seconds)
            for _, _, task in tasks
        ],
        return_exceptions=True
    )

    # 3. 에러 처리
    successful_results = []
    failed_results = []

    for (agent_type, query, _), result in zip(tasks, results):
        if isinstance(result, asyncio.TimeoutError):
            logger.warning(f"Agent {agent_type} timeout after {timeout_seconds}s")
            failed_results.append({
                "agent": agent_type,
                "query": query,
                "error": "timeout"
            })
        elif isinstance(result, Exception):
            logger.error(f"Agent {agent_type} failed: {result}")
            failed_results.append({
                "agent": agent_type,
                "query": query,
                "error": str(result)
            })
        elif result.get("success"):
            successful_results.append({
                "agent": agent_type,
                "query": query,
                "result": result["result"]
            })
        else:
            failed_results.append({
                "agent": agent_type,
                "query": query,
                "error": result.get("error", "Unknown error")
            })

    # 4. 부분 성공 허용
    if not successful_results:
        return RouterResult(
            success=False,
            error="All agents failed",
            failed_intents=[r["agent"] for r in failed_results]
        )

    # 5. 응답 통합
    aggregated_response = await self.response_aggregator.aggregate(
        successful_results
    )

    return RouterResult(
        success=True,
        type="multi",
        intents=[r["agent"] for r in successful_results],
        individual_results=successful_results,
        aggregated_response=aggregated_response,
        partial=len(failed_results) > 0,
        failed_intents=[r["agent"] for r in failed_results] if failed_results else None
    )
```

---

### 4.3 ResponseAggregator (응답 통합기)

**파일**: `backend/Agent/application/response_aggregator.py`

**역할**:
- 여러 에이전트의 응답을 하나의 일관된 답변으로 통합
- GPT-4o를 사용하여 자연스러운 흐름 생성

**클래스 다이어그램**:
```python
class ResponseAggregator:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

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

    def _extract_answers(
        self,
        agent_results: List[Dict]
    ) -> List[Dict]:
        """각 에이전트 응답에서 answer 필드 추출"""

    def _validate_aggregated_response(
        self,
        response: str,
        agent_results: List[Dict]
    ) -> bool:
        """통합 응답이 모든 에이전트 정보를 포함하는지 검증"""
```

**프롬프트 템플릿**:
```python
RESPONSE_AGGREGATION_PROMPT = """
당신은 여러 AI 에이전트의 답변을 하나의 일관된 응답으로 통합하는 전문가입니다.

각 에이전트의 답변을 받아 다음 원칙으로 통합하세요:

**통합 원칙**:
1. **자연스러운 흐름**: 답변 간 자연스러운 연결 (접속사, 전환구 사용)
2. **정보 보존**: 각 에이전트의 핵심 정보 모두 포함
3. **중복 제거**: 겹치는 내용은 하나로 통합
4. **사용자 중심**: 질문에 대한 완전한 답변 제공
5. **순서 유지**: 사용자가 질문한 순서대로 답변 제시

**형식 규칙**:
- 각 에이전트 답변을 명확히 구분 (제목, 섹션 사용)
- Markdown 형식 사용 (헤더, 리스트, 강조 등)
- 전문 용어는 쉬운 설명 추가

**예시**:

입력:
[
  {
    "agent": "nutrition",
    "query": "저염식 레시피",
    "answer": "저염식 레시피로는 무염 버터를 사용한 감자 샐러드를 추천합니다. 재료는 감자 200g, 무염 버터 1스푼, 올리브유 1스푼입니다. 나트륨 함량은 약 150mg으로 낮습니다."
  },
  {
    "agent": "research_paper",
    "query": "저염식 식이요법 논문",
    "answer": "2023년 'Journal of Renal Nutrition' 연구에 따르면 저염식이 CKD 환자의 혈압 조절에 효과적입니다. 연구에서는 1일 나트륨 섭취량 2000mg 이하 유지 시 수축기 혈압이 평균 10mmHg 감소했습니다."
  }
]

출력:
"## 저염식 식단 추천

저염식 레시피로는 **무염 버터를 사용한 감자 샐러드**를 추천드립니다.

**재료**:
- 감자 200g
- 무염 버터 1스푼
- 올리브유 1스푼

이 레시피의 나트륨 함량은 약 **150mg**으로 매우 낮아 신장병 환자에게 적합합니다.

## 관련 연구 결과

최신 연구 결과를 보면 저염식이 CKD 환자의 혈압 조절에 효과적입니다.

2023년 **'Journal of Renal Nutrition'** 연구에서는 1일 나트륨 섭취량을 **2000mg 이하**로 유지한 환자들의 수축기 혈압이 평균 **10mmHg 감소**했다는 결과가 있습니다.

이러한 연구 결과는 저염식이 단순히 맛의 문제가 아니라 실제로 건강 개선에 도움이 된다는 것을 보여줍니다."

통합된 답변만 반환하세요. JSON이나 추가 메타데이터는 포함하지 마세요.
"""
```

---

## 5. 데이터 모델

### 5.1 IntentClassificationResult

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

@dataclass
class SubQuery:
    """분해된 서브 쿼리"""
    intent: str  # "nutrition", "research_paper", etc.
    query: str   # 분해된 질문

@dataclass
class IntentClassificationResult:
    """의도 분류 결과"""
    intent_type: str  # "single" | "multi"
    primary_intent: str  # 주요 의도
    sub_intents: List[str]  # 모든 의도 목록
    decomposed_queries: List[SubQuery]  # 분해된 쿼리들
```

### 5.2 RouterResult

```python
@dataclass
class RouterResult:
    """라우터 처리 결과"""
    success: bool
    type: str  # "single" | "multi"
    intents: List[str]  # 처리된 의도 목록
    individual_results: List[Dict]  # 각 에이전트 결과
    aggregated_response: Optional[str]  # 통합 응답 (multi의 경우)
    partial: bool = False  # 부분 성공 여부
    failed_intents: Optional[List[str]] = None  # 실패한 의도들
    error: Optional[str] = None  # 에러 메시지
```

---

## 6. 처리 플로우

### 6.1 단일 질문 플로우

```
User: "당근의 칼륨 함량은?"
    ↓
QueryRouter.route_and_process()
    ↓
IntentClassifier.classify()
    ↓ GPT-4o 호출
{
  "intent_type": "single",
  "primary_intent": "nutrition"
}
    ↓
QueryRouter._process_single_intent()
    ↓
AgentManager.route_request(agent_type="nutrition")
    ↓
NutritionAgent.process()
    ↓
RouterResult(type="single", result=...)
    ↓
API Response
```

### 6.2 복합 질문 플로우

```
User: "저염식 레시피 추천하고, 관련 논문도 찾아줘"
    ↓
QueryRouter.route_and_process()
    ↓
IntentClassifier.classify()
    ↓ GPT-4o 호출
{
  "intent_type": "multi",
  "decomposed_queries": [
    {"intent": "nutrition", "query": "저염식 레시피를 추천해주세요"},
    {"intent": "research_paper", "query": "저염식 식이요법 관련 논문 검색"}
  ]
}
    ↓
QueryRouter._process_multi_intent()
    ↓
병렬 처리 (asyncio.gather)
    ├─→ NutritionAgent.process("저염식 레시피...")
    └─→ ResearchPaperAgent.process("저염식 식이요법 논문...")
    ↓
결과 수집
[
  {"agent": "nutrition", "result": {...}},
  {"agent": "research_paper", "result": {...}}
]
    ↓
ResponseAggregator.aggregate()
    ↓ GPT-4o 호출
"저염식 레시피로는 무염 버터를 사용한 감자 샐러드를 추천드립니다...
또한, 최신 연구 결과를 보면 저염식이 CKD 환자의 혈압 조절에..."
    ↓
RouterResult(type="multi", aggregated_response=...)
    ↓
API Response
```

### 6.3 부분 성공 플로우

```
User: "식단 추천, 논문 검색, 퀴즈 풀기"
    ↓
병렬 처리 (3개 에이전트)
    ├─→ NutritionAgent ✅ 성공
    ├─→ ResearchPaperAgent ❌ 타임아웃
    └─→ QuizAgent ✅ 성공
    ↓
부분 성공 처리
successful_results = [nutrition, quiz]
failed_results = [research_paper]
    ↓
ResponseAggregator.aggregate(successful_results)
    ↓
RouterResult(
  success=True,
  partial=True,
  warning="1개 에이전트 실패 (research_paper)",
  aggregated_response="..."
)
```

---

## 7. 구현 가이드

### 7.1 Phase 1: IntentClassifier 구현

**파일 생성**: `backend/Agent/application/intent_classifier.py`

```python
from typing import Dict, Any, List
import json
from Agent.infrastructure.services.openai_service import OpenAIService
from Agent.utils.prompts import INTENT_CLASSIFICATION_PROMPT

class IntentClassifier:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def classify(self, user_input: str) -> Dict[str, Any]:
        response = await self.openai_service.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": INTENT_CLASSIFICATION_PROMPT},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3,
            max_tokens=500
        )

        content = response.choices[0].message.content
        return self._parse_intent_result(content)

    def _parse_intent_result(self, content: str) -> Dict[str, Any]:
        # JSON 파싱 (코드 블록 제거)
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        try:
            result = json.loads(content.strip())
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent result: {e}")
            # Fallback: 단일 질문으로 처리
            return {
                "intent_type": "single",
                "primary_intent": "nutrition",
                "sub_intents": [],
                "decomposed_queries": []
            }
```

### 7.2 Phase 2: ResponseAggregator 구현

**파일 생성**: `backend/Agent/application/response_aggregator.py`

```python
import json
from typing import List, Dict
from Agent.infrastructure.services.openai_service import OpenAIService
from Agent.utils.prompts import RESPONSE_AGGREGATION_PROMPT

class ResponseAggregator:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def aggregate(self, agent_results: List[Dict]) -> str:
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
        response = await self.openai_service.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": RESPONSE_AGGREGATION_PROMPT},
                {"role": "user", "content": json.dumps(formatted_results, ensure_ascii=False)}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        return response.choices[0].message.content
```

### 7.3 Phase 3: QueryRouter 구현

**파일 생성**: `backend/Agent/application/router.py`

```python
import asyncio
from typing import Dict, Any, List, Optional
import logging

from .intent_classifier import IntentClassifier
from .response_aggregator import ResponseAggregator
from ..agent_manager import AgentManager

logger = logging.getLogger(__name__)

class QueryRouter:
    def __init__(
        self,
        agent_manager: AgentManager,
        intent_classifier: IntentClassifier,
        response_aggregator: ResponseAggregator
    ):
        self.agent_manager = agent_manager
        self.intent_classifier = intent_classifier
        self.response_aggregator = response_aggregator

    async def route_and_process(
        self,
        user_input: str,
        session_id: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
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
        intent: str,
        query: str,
        session_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        result = await self.agent_manager.route_request(
            agent_type=intent,
            user_input=query,
            session_id=session_id,
            context=context
        )

        return {
            "success": result.get("success", False),
            "type": "single",
            "intent": intent,
            "result": result
        }

    async def _process_multi_intent(
        self,
        decomposed_queries: List[Dict],
        session_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        # 병렬 처리 로직 (위 코드 참조)
        # ...
```

### 7.4 Phase 4: API 통합

**파일 수정**: `backend/app/main.py`

```python
from Agent.application.router import QueryRouter
from Agent.application.intent_classifier import IntentClassifier
from Agent.application.response_aggregator import ResponseAggregator
from Agent.infrastructure.services.openai_service import OpenAIService

# 글로벌 인스턴스 초기화
openai_service = OpenAIService()
intent_classifier = IntentClassifier(openai_service)
response_aggregator = ResponseAggregator(openai_service)
query_router = QueryRouter(agent_manager, intent_classifier, response_aggregator)

@app.post("/api/agents/query")
async def query_agents(
    user_input: str = Form(...),
    session_id: str = Form(...),
    context: Optional[str] = Form(None)
):
    """복합 질문 지원 통합 API"""
    context_dict = json.loads(context) if context else {}

    result = await query_router.route_and_process(
        user_input=user_input,
        session_id=session_id,
        context=context_dict
    )

    return result
```

---

## 8. 테스트 전략

### 8.1 단위 테스트

**파일**: `backend/tests/test_intent_classifier.py`

```python
import pytest
from Agent.application.intent_classifier import IntentClassifier

@pytest.mark.asyncio
async def test_classify_single_intent():
    classifier = IntentClassifier(mock_openai_service)
    result = await classifier.classify("당근의 칼륨 함량은?")

    assert result["intent_type"] == "single"
    assert result["primary_intent"] == "nutrition"

@pytest.mark.asyncio
async def test_classify_multi_intent():
    classifier = IntentClassifier(mock_openai_service)
    result = await classifier.classify("저염식 레시피 추천하고, 관련 논문도 찾아줘")

    assert result["intent_type"] == "multi"
    assert "nutrition" in result["sub_intents"]
    assert "research_paper" in result["sub_intents"]
    assert len(result["decomposed_queries"]) == 2
```

### 8.2 통합 테스트

**파일**: `backend/tests/test_query_router.py`

```python
@pytest.mark.asyncio
async def test_multi_intent_parallel_processing():
    router = QueryRouter(agent_manager, intent_classifier, response_aggregator)
    result = await router.route_and_process(
        user_input="저염식 레시피 추천하고, 관련 논문도 찾아줘",
        session_id="test_session"
    )

    assert result["success"] == True
    assert result["type"] == "multi"
    assert len(result["individual_results"]) == 2
    assert result["aggregated_response"] is not None
```

### 8.3 E2E 테스트

**파일**: `backend/tests/e2e/test_api_integration.py`

```python
def test_query_agents_api():
    response = client.post(
        "/api/agents/query",
        data={
            "user_input": "저염식 레시피 추천하고, 관련 논문도 찾아줘",
            "session_id": "test_session"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["type"] == "multi"
```

---

**작성일**: 2025-11-23
**작성자**: Claude Code
**버전**: 1.0
