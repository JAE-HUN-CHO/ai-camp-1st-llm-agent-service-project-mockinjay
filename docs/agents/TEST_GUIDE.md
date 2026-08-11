# 로컬 에이전트 테스트 가이드

직접 리팩토링한 로컬 에이전트를 테스트해볼 수 있습니다!

---

## 🚀 빠른 시작

### 방법 1: 대화형 테스트 (추천)

```bash
# 가상환경 활성화
source .venv/bin/activate

# 대화형 테스트 실행
cd backend
python Agent/interactive_test.py
```

**사용법:**

1. 테스트 모드 선택 (1: 대화형, 2: 빠른 테스트)
2. 에이전트 선택 (nutrition, quiz, trend_visualization)
3. 쿼리 입력 (또는 예제 번호 선택)
4. 결과 확인!

---

### 방법 2: Python REPL에서 직접 테스트

```bash
# 가상환경 활성화
source .venv/bin/activate

# Python REPL 실행
cd backend
python
```

**예제 코드:**

```python
import asyncio
from Agent.core.agent_registry import AgentRegistry
from Agent.core.contracts import AgentRequest

# 에이전트 import (자동 등록)
from Agent.nutrition.agent import NutritionAgent
from Agent.quiz.agent import QuizAgent
from Agent.trend_visualization.agent import TrendVisualizationAgent

# 등록된 에이전트 확인
print(AgentRegistry.list_agents())
# ['nutrition', 'quiz', 'trend_visualization']

# 에이전트 생성
agent = AgentRegistry.create_agent("nutrition")

# 메타데이터 확인
print(agent.metadata)

# 요청 생성
request = AgentRequest(
    query="김치찌개 영양 분석해줘",
    session_id="my-session",
    context={"user_profile": "patient"}
)

# 비동기 함수로 실행
async def test():
    response = await agent.process(request)
    print(f"Status: {response.status}")
    print(f"Answer: {response.answer}")
    print(f"Tokens: {response.tokens_used}")
    return response

# 실행
response = asyncio.run(test())
```

---

## 📋 에이전트별 테스트 예제

### 1. NutritionAgent

```python
from Agent.nutrition.agent import NutritionAgent
from Agent.core.contracts import AgentRequest
import asyncio

async def test_nutrition():
    agent = NutritionAgent()

    # 텍스트 쿼리
    request = AgentRequest(
        query="저염 식단 추천해줘",
        session_id="test-001",
        context={"user_profile": "patient"}
    )

    response = await agent.process(request)
    print(response.answer)

    # 메타데이터에서 영양 정보 확인
    if response.metadata.get("nutritionData"):
        print(response.metadata["nutritionData"])

asyncio.run(test_nutrition())
```

### 2. QuizAgent

```python
from Agent.quiz.agent import QuizAgent
from Agent.core.contracts import AgentRequest
import asyncio

async def test_quiz():
    agent = QuizAgent()

    # 사용자 통계 조회
    request = AgentRequest(
        query="내 퀴즈 통계",
        session_id="test-002",
        context={
            "action": "get_stats",
            "userId": "user-123"
        }
    )

    response = await agent.process(request)
    print(response.answer)
    print(response.metadata)  # totalSessions, totalQuestions 등

asyncio.run(test_quiz())
```

**QuizAgent Action 종류:**

- `get_stats`: 사용자 통계 조회
- `generate_quiz`: 퀴즈 세션 생성
- `submit_answer`: 답안 제출
- `complete_session`: 세션 완료
- `get_history`: 퀴즈 이력 조회

### 3. TrendVisualizationAgent

```python
from Agent.trend_visualization.agent import TrendVisualizationAgent
from Agent.core.contracts import AgentRequest
import asyncio

async def test_trend():
    agent = TrendVisualizationAgent()

    # 트렌드 분석
    request = AgentRequest(
        query="당뇨병 연구 트렌드",
        session_id="test-003",
        context={
            "analysisType": "temporal_trends",
            "start_year": 2015,
            "end_year": 2024
        }
    )

    response = await agent.process(request)
    print(response.answer)

    # 차트 데이터 확인
    if response.metadata.get("chart_data"):
        print(response.metadata["chart_data"])

asyncio.run(test_trend())
```

---

## 🔍 자동 등록 시스템 테스트

```python
from Agent.core.agent_registry import AgentRegistry

# 모든 에이전트 import (자동 등록)
from Agent.nutrition.agent import NutritionAgent
from Agent.quiz.agent import QuizAgent
from Agent.trend_visualization.agent import TrendVisualizationAgent

# 1. 등록된 에이전트 목록
agents = AgentRegistry.list_agents()
print(f"등록된 에이전트: {agents}")

# 2. 에이전트 정보
info = AgentRegistry.get_agents_info()
for agent_type, data in info.items():
    print(f"{agent_type}: {data}")

# 3. 팩토리 패턴으로 생성
nutrition_agent = AgentRegistry.create_agent("nutrition")
quiz_agent = AgentRegistry.create_agent("quiz")

# 4. 메타데이터 확인
print(nutrition_agent.metadata)
print(quiz_agent.metadata)
```

---

## 🧪 예제 시나리오

### 시나리오 1: 영양 분석 플로우

```python
import asyncio
from Agent.nutrition.agent import NutritionAgent
from Agent.core.contracts import AgentRequest

async def nutrition_flow():
    agent = NutritionAgent()

    # 1단계: 음식 분석
    request1 = AgentRequest(
        query="김치찌개",
        session_id="scenario-001",
        context={"user_profile": "patient"}
    )
    response1 = await agent.process(request1)
    print("=== 음식 분석 ===")
    print(response1.answer)

    # 2단계: 대체 재료 추천 (메타데이터에 포함)
    if response1.metadata.get("nutritionData"):
        nutrition_data = response1.metadata["nutritionData"]
        if nutrition_data.get("alternatives"):
            print("\n=== 대체 재료 ===")
            for alt in nutrition_data["alternatives"]:
                print(f"- {alt}")

asyncio.run(nutrition_flow())
```

### 시나리오 2: 퀴즈 완전 플로우

```python
import asyncio
from Agent.quiz.agent import QuizAgent
from Agent.core.contracts import AgentRequest

async def quiz_flow():
    agent = QuizAgent()
    user_id = "test-user-999"

    # 1. 퀴즈 생성
    print("=== 퀴즈 생성 ===")
    req_generate = AgentRequest(
        query="일일 퀴즈 시작",
        session_id="quiz-001",
        context={
            "action": "generate_quiz",
            "userId": user_id,
            "sessionType": "daily_quiz"
        }
    )
    res_generate = await agent.process(req_generate)
    print(res_generate.answer)

    session_id = res_generate.metadata.get("sessionId")
    print(f"세션 ID: {session_id}")

    # 2. 통계 조회
    print("\n=== 통계 조회 ===")
    req_stats = AgentRequest(
        query="통계",
        session_id="quiz-002",
        context={
            "action": "get_stats",
            "userId": user_id
        }
    )
    res_stats = await agent.process(req_stats)
    print(res_stats.answer)

asyncio.run(quiz_flow())
```

---

## 📊 응답 구조

모든 에이전트는 동일한 `AgentResponse` 구조를 반환합니다:

```python
AgentResponse(
    answer="응답 텍스트",            # str
    sources=[],                    # List[Dict] - 참고 자료
    papers=[],                     # List[Dict] - 논문 목록
    tokens_used=100,               # int - 사용된 토큰
    status="success",              # str - 상태
    agent_type="nutrition",        # str - 에이전트 타입
    metadata={                     # Dict - 추가 정보
        "nutritionData": {...},
        "session_id": "...",
        ...
    }
)
```

---

## 🐛 문제 해결

### 문제: ModuleNotFoundError

```bash
# 가상환경이 활성화되었는지 확인
which python
# /Users/.../ai-camp.../venv/bin/python 이어야 함

# 가상환경 활성화
source .venv/bin/activate
```

### 문제: OpenAI API Key 오류

```bash
# .env 파일에 API 키가 있는지 확인
cat .env | grep OPENAI
```

### 문제: MongoDB 연결 오류

```bash
# MongoDB가 실행 중인지 확인
# QuizAgent는 MongoDB 필요
```

---

## ✨ 팁

1. **대화형 테스트가 가장 쉽습니다**

   ```bash
   python Agent/interactive_test.py
   ```

2. **예제 쿼리 사용**

   - 대화형 테스트에서 예제 번호만 입력하면 됩니다

3. **메타데이터 활용**

   - `response.metadata`에 각 에이전트의 고유 정보가 들어있습니다

4. **에러 확인**
   - `response.status`가 "error"면 `response.metadata["error"]` 확인

---

**즐거운 테스트 되세요! 🎉**
