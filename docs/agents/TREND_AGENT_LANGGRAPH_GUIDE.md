# TrendVisualizationAgent LangGraph 리팩토링 완료!

## 🎉 변경 사항

### ✅ 완전히 재작성

- **기존**: MongoDB 기반 트렌드 분석
- **신규**: PubMed API 기반 + LangGraph 워크플로우

---

## 🔧 주요 개선사항

### 1. LangGraph 워크플로우 도입

```
analyze_request → fetch_pubmed_data → generate_visualization → generate_explanation
```

**4개의 노드로 구성**:

1. **analyze_request**: 요청 분석 및 키워드 추출
2. **fetch_pubmed_data**: PubMed에서 데이터 가져오기
3. **generate_visualization**: 차트 설정 생성
4. **generate_explanation**: 분석 결과 설명 생성

### 2. MongoDB 제거, PubMed만 사용

- ✅ **PubMed API 직접 활용**
  - 시간별 트렌드 (`get_publication_trends_parallel`)
  - 지역별 분포 (`get_geographic_distribution_parallel`)
  - 키워드 비교
- ❌ **MongoDB 완전 제거**
  - 더 이상 MongoDB 의존성 없음
  - 실시간 PubMed 데이터만 사용

### 3. State 기반 관리

```python
class AgentState(TypedDict):
    query: str
    session_id: str
    context: Dict[str, Any]
    analysis_type: str
    keywords: List[str]
    pubmed_data: Optional[Dict[str, Any]]
    papers: List[Dict[str, Any]]
    chart_config: Optional[Dict[str, Any]]
    explanation: str
    status: str
    error: Optional[str]
    metadata: Dict[str, Any]
```

---

## 📊 지원하는 분석 타입

### 1. Temporal Trends (시간별 트렌드)

```python
context = {
    "analysisType": "temporal_trends",
    "start_year": 2015,
    "end_year": 2024
}
```

**응답**:

- 연도별 논문 수 그래프
- 정규화된 트렌드 (per 100K)
- 최고 발행 연도 및 통계

### 2. Geographic Distribution (지역별 분포)

```python
context = {
    "analysisType": "geographic_distribution",
    "countries": ["United States", "China", "Korea"]  # Optional
}
```

**응답**:

- 국가별 논문 수 바 차트
- 최다 연구 국가 통계

### 3. Keyword Comparison (키워드 비교)

```python
context = {
    "analysisType": "keyword_comparison",
    "keywords": ["diabetes", "CKD", "hypertension"],
    "start_year": 2015,
    "end_year": 2024
}
```

**응답**:

- 여러 키워드 트렌드 비교 라인 차트
- 키워드별 통계

### 4. General (기본 검색)

```python
# analysisType이 없거나 다른 값이면 기본 검색
```

**응답**:

- 최근 논문 목록
- 간단한 통계

---

## 🧪 테스트 방법

### 1. 의존성 설치

```bash
pip install langgraph langchain
```

또는

```bash
pip install -r backend/requirements.txt
```

### 2. 테스트 실행

```bash
python backend/Agent/interactive_test.py
```

**테스트 시나리오**:

1. 에이전트 선택: `2` (trend_visualization)
2. 쿼리 입력: `1` (당뇨병 연구 트렌드)

### 3. 예제 코드

```python
import asyncio
from Agent.trend_visualization.agent import TrendVisualizationAgent
from Agent.core.contracts import AgentRequest

async def test():
    agent = TrendVisualizationAgent()

    # 시간별 트렌드 분석
    request = AgentRequest(
        query="diabetes CKD",
        session_id="test-001",
        context={
            "analysisType": "temporal_trends",
            "start_year": 2018,
            "end_year": 2024
        }
    )

    response = await agent.process(request)
    print(response.answer)
    print(f"Papers: {len(response.papers)}")
    print(f"Chart: {response.sources[0]['type'] if response.sources else 'N/A'}")

asyncio.run(test())
```

---

## 📈 LangGraph 플로우 시각화

```
┌─────────────────────┐
│  analyze_request    │  요청 분석, 키워드 추출
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ fetch_pubmed_data   │  PubMed API 호출
│                     │  - Temporal trends
│                     │  - Geographic data
│                     │  - Keyword comparison
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│generate_visualization│ Chart.js 설정 생성
│                     │  - Line chart
│                     │  - Bar chart
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│generate_explanation │  분석 결과 설명 생성
│                     │  - 통계 요약
│                     │  - 트렌드 해석
└─────────────────────┘
```

---

## 🔍 로깅 예시

```
🚀 Starting LangGraph workflow for query: diabetes CKD
📊 Node 1: Analyzing request...
   Analysis type: temporal_trends
   Keywords: ['diabetes CKD']
🔍 Node 2: Fetching PubMed data...
   Fetching temporal trends (2018-2024)...
   ✅ Fetched 10 papers
📈 Node 3: Generating visualization...
   ✅ Generated line chart
💬 Node 4: Generating explanation...
   ✅ Generated explanation (428 chars)
```

---

## ⚙️ 설정 가능한 옵션

### Context 옵션

```python
context = {
    # 분석 타입
    "analysisType": "temporal_trends" | "geographic_distribution" | "keyword_comparison",

    # 시간별 트렌드
    "start_year": 2015,
    "end_year": 2024,

    # 지역별 분포
    "countries": ["United States", "China"],  # Optional

    # 키워드 비교
    "keywords": ["diabetes", "CKD", "hypertension"]  # 최대 4개
}
```

---

## 🎯 장점

1. **워크플로우 명확성**: LangGraph로 각 단계가 명확히 분리됨
2. **실시간 데이터**: MongoDB 대신 PubMed에서 실시간 데이터 가져옴
3. **확장성**: 새로운 노드 추가가 쉬움
4. **디버깅**: 각 노드별 로깅으로 문제 추적 용이
5. **유연성**: State 기반으로 데이터 흐름 관리

---

## 📝 변경된 파일

1. ✅ `backend/Agent/trend_visualization/agent.py` - 완전히 재작성 (LangGraph)
2. ✅ `backend/requirements.txt` - langgraph, langchain 추가

---

## 🚀 다음 단계

테스트 해보시고, 피드백 주세요!

```bash
python backend/Agent/interactive_test.py
```
