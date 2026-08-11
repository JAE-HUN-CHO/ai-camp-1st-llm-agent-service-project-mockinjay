# 🏥 CareGuide Backend 완전 분석 문서

**프로젝트**: 만성 신장 질환(CKD) 환자를 위한 AI 기반 헬스케어 플랫폼
**코드 규모**: 75개 Python 파일, 19,410줄
**핵심 기술**: FastAPI, OpenAI GPT-4o, Parlant, CLIP, Pinecone, MongoDB

---

## 📋 목차

1. [아키텍처 개요](#1-아키텍처-개요)
2. [메인 애플리케이션](#2-메인-애플리케이션)
3. [Agent 시스템 심층 분석](#3-agent-시스템-심층-분석)
4. [RAG 시스템](#4-rag-시스템)
5. [API 라우터 상세](#5-api-라우터-상세)
6. [데이터베이스 계층](#6-데이터베이스-계층)
7. [인증 & 보안](#7-인증--보안)
8. [서비스 계층](#8-서비스-계층)
9. [도구 및 유틸리티](#9-도구-및-유틸리티)
10. [데이터 플로우](#10-데이터-플로우)

---

## 1. 아키텍처 개요

### 1.1 전체 구조

```
backend/
├── app/               # FastAPI 애플리케이션
│   ├── main.py       # 메인 엔트리포인트
│   ├── api/          # API 라우터들
│   ├── db/           # 데이터베이스 관리
│   ├── models/       # Pydantic 모델
│   └── services/     # 비즈니스 로직
├── Agent/            # AI Agent 시스템
│   ├── base_agent.py
│   ├── nutrition/    # 영양 Agent
│   ├── research_paper/ # 논문 Agent (Parlant)
│   ├── quiz/         # 퀴즈 Agent
│   ├── medical_welfare/
│   └── trend_visualization/
├── rag/              # RAG 시스템
│   └── nutrition_rag.py
└── tools/            # 도구들
    ├── nutrient_lookup.py
    └── rag_recipe_tool.py
```

### 1.2 기술 스택 맵

| 레이어 | 기술 | 용도 |
|--------|------|------|
| **웹 프레임워크** | FastAPI | REST API 서버 |
| **LLM** | OpenAI GPT-4o | 영양 분석, 퀴즈 생성 |
| **AI 프레임워크** | Parlant | 의료 논문 검색 Agent |
| **벡터 DB** | Pinecone | 음식 이미지/텍스트 검색 |
| **문서 DB** | MongoDB | 사용자, 퀴즈, 커뮤니티 데이터 |
| **키워드 검색** | BM25 (rank_bm25) | 하이브리드 검색 |
| **이미지 임베딩** | CLIP (Hugging Face) | 음식 이미지 벡터화 |
| **인증** | JWT (jose) | 토큰 기반 인증 |
| **비밀번호** | bcrypt | 해싱 |

---

## 2. 메인 애플리케이션

### 2.1 `app/main.py` - 전체 구조

**파일 위치**: `backend/app/main.py`
**라인 수**: 184줄
**역할**: FastAPI 앱 초기화, 라우터 등록, 에러 핸들링, 전역 인스턴스 관리

#### 2.1.1 Lifespan 관리

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Application starting up...")
    yield
    # Cleanup on shutdown
    await close_parlant_server()  # Parlant 서버 정리
    logger.info("Application shutting down...")
```

**특징**:
- **시작 시**: 로그 출력
- **종료 시**: Parlant 프록시 클라이언트 정리 (`close_parlant_server()`)

#### 2.1.2 CORS 설정

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite 개발 서버
        "http://localhost:5174",  # 대체 포트
        "http://192.168.129.32:5173",  # 네트워크 IP
        "http://192.168.129.32:5174",  # 네트워크 IP (대체)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**목적**: 프론트엔드 Vite 개발 서버와 통신 허용 (로컬 + 네트워크)

#### 2.1.3 글로벌 인스턴스

```python
# Global instances for nutrition agent
nutrition_agent = NutritionAgent()  # 영양 Agent (싱글톤)
session_manager = SessionManager()  # 세션 관리자
```

**이유**:
- **NutritionAgent**: OpenAI 클라이언트, RAG 초기화 비용 절감
- **SessionManager**: 메모리 내 세션 저장소 (30분 타임아웃)

#### 2.1.4 라우터 등록 (8개)

```python
app.include_router(chat_router)           # /api/chat/* (Parlant 프록시)
app.include_router(trends_router)         # /api/trends/*
app.include_router(community_router, prefix="/api/community")
app.include_router(quiz_router, prefix="/api/quiz")
app.include_router(auth.router)           # /auth/*
app.include_router(user.router)           # /user/*
app.include_router(header_router)         # 헤더 데이터
app.include_router(footer_router)         # 푸터 데이터
app.include_router(notification_router)   # 알림
```

#### 2.1.5 에러 핸들러

```python
# Error handlers (UTI-005)
app.add_exception_handler(StarletteHTTPException, not_found_handler)  # 404
app.add_exception_handler(Exception, internal_server_error_handler)  # 500
app.add_exception_handler(RequestValidationError, validation_error_handler)  # 422
```

#### 2.1.6 주요 엔드포인트

**1. 영양 분석 API** (`/api/nutrition/analyze`)

```python
@app.post("/api/nutrition/analyze")
async def analyze_nutrition(
    session_id: str = Form(...),
    text: Optional[str] = Form(None),
    user_profile: str = Form("general"),  # general, patient, researcher
    image: Optional[UploadFile] = File(None)
):
```

**처리 플로우**:
1. **세션 검증**: `session_manager.get_session(session_id)`
2. **이미지 인코딩**: Base64 변환 (filename 체크로 실제 파일 확인)
3. **Context 구성**: `{image_data, has_image, user_profile}`
4. **Agent 호출**: `nutrition_agent.process(user_input, session_id, context)`
5. **응답 반환**: `{success, agent_type, result}`

**2. 세션 생성 API** (`/api/session/create`)

```python
@app.post("/api/session/create")
async def create_session(user_id: str = "default_user"):
    session_id = session_manager.create_session(user_id)
    session = session_manager.get_session(session_id)
    return {
        "session_id": session_id,
        "user_id": user_id,
        "status": "created",
        "created_at": session["created_at"].isoformat()
    }
```

**세션 구조**:
```python
{
    "user_id": str,
    "created_at": datetime,
    "last_activity": datetime,
    "active_agent": str | None,
    "conversation_history": List[Dict]
}
```

---

## 3. Agent 시스템 심층 분석

### 3.1 BaseAgent (추상 클래스)

**파일**: `backend/Agent/base_agent.py` (58줄)

#### 3.1.1 추상 메서드

```python
class BaseAgent(ABC):
    @abstractmethod
    async def process(
        self,
        user_input: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """사용자 입력 처리 (각 Agent가 구현)"""
        pass

    @abstractmethod
    def estimate_context_usage(self, user_input: str) -> int:
        """예상 컨텍스트 사용량 계산 (토큰 수)"""
        pass
```

#### 3.1.2 공통 메서드

```python
def get_agent_info(self) -> Dict[str, Any]:
    """Agent 정보 반환"""
    return {
        "agent_type": self.agent_type,
        "created_at": self.created_at.isoformat(),
        "context_usage": self.context_usage,
    }

def reset_context(self):
    """컨텍스트 사용량 초기화"""
    self.context_usage = 0
```

---

### 3.2 NutritionAgent (영양 분석 Agent) ⭐

**파일**: `backend/Agent/nutrition/agent.py` (1010줄)
**역할**: CKD 환자를 위한 식단 분석, 5가지 이미지 케이스 완벽 지원

#### 3.2.1 초기화 및 Lazy Loading

```python
class NutritionAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_type="nutrition")
        self.client = None  # OpenAI 클라이언트
        self._client_initialized = False

        self.rag = None  # RAG 시스템
        self._rag_initialized = False

        # 멀티턴 대화 상태 (session_id -> state)
        self.conversation_states = {}
```

**Lazy Initialization의 장점**:
- **메모리 절약**: API 키 없을 때 에러 방지
- **빠른 시작**: 초기 로딩 시간 단축

#### 3.2.2 대화 상태 관리

```python
def _get_conversation_state(self, session_id: str) -> Dict[str, Any]:
    if session_id not in self.conversation_states:
        self.conversation_states[session_id] = {
            "state": "initial",  # initial, awaiting_dish_selection, awaiting_ingredient_dish_selection
            "pending_candidates": None,
            "pending_dish_candidates": None,
            "last_image_data": None,
            "last_analysis_type": None
        }
    return self.conversation_states[session_id]
```

**멀티턴 대화 시나리오**:
1. **이미지 업로드** → 요리 후보 5개 제시
2. **사용자 선택** → 영양 분석 + 대체 재료 제시

#### 3.2.3 이미지 분류 (5가지 케이스)

**GPT-4o Vision API 사용**:

```python
async def _classify_image(self, image_data: str) -> Dict[str, Any]:
    response = await self.client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": IMAGE_CLASSIFICATION_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
        }],
        max_tokens=500,
        temperature=0.3  # 분류 정확도를 위해 낮은 temperature
    )

    classification = self._extract_json(content)
    return classification
```

**반환 형식**:
```json
{
  "analysisType": "dish | ingredient_single | ingredient_multiple | unclear | irrelevant",
  "primaryItem": "주요 항목명",
  "confidence": 0.95,
  "items": ["항목1", "항목2"],
  "message": "에러 메시지"
}
```

#### 3.2.4 케이스별 처리 플로우

**케이스 1: dish (단일 요리)**

```python
async def _handle_case_dish(self, image_data, classification, session_id):
    # 1. RAG로 유사 음식 검색 (Top-5)
    search_results = self.rag.search_by_image(image_data, top_k=5)

    # 2. 후보 목록 생성
    candidates = [{
        "dish_name": r["dish_name"],
        "confidence": round(r["score"] * 100, 1),
        "dish_data": r
    } for r in search_results]

    # 3. 대화 상태 업데이트
    self._update_conversation_state(session_id, {
        "state": "awaiting_dish_selection",
        "pending_candidates": candidates,
        "last_image_data": image_data
    })

    # 4. 확인 메시지 반환
    return {
        "response": f"업로드하신 것은 **{dish_name}**(으)로 보입니다.\n\n맞다면 '네'라고 해주세요.",
        "dishCandidates": candidates,
        "analysisType": "dish"
    }
```

**케이스 2: ingredient_single (단일 식재료)**

```python
async def _handle_case_ingredient_single(self, classification, session_id):
    ingredient_name = classification["primaryItem"]

    # 1. 식재료로 만들 수 있는 CKD 친화적 요리 추천
    recommended_dishes = await self._recommend_dishes_for_ingredient(ingredient_name)

    # 2. 대화 상태 업데이트
    self._update_conversation_state(session_id, {
        "state": "awaiting_ingredient_dish_selection",
        "pending_dish_candidates": recommended_dishes
    })

    return {
        "response": f"**{ingredient_name}**를 사용해 신장병 식이 관리를 위한 추천 요리를 알려드릴게요!",
        "recommendedDishes": recommended_dishes,
        "analysisType": "ingredient_single"
    }
```

**추천 요리 생성 (GPT-4o)**:

```python
async def _recommend_dishes_for_ingredient(self, ingredient_name: str):
    response = await self.client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": INGREDIENT_TO_DISH_PROMPT.format(ingredient_name=ingredient_name)}],
        max_tokens=1500,
        temperature=0.7
    )

    data = self._extract_json(response.choices[0].message.content)
    return data.get("recommendedDishes", [])[:5]
```

**반환 형식**:
```json
{
  "recommendedDishes": [
    {
      "dishName": "양배추 무침",
      "description": "데친 양배추에 레몬즙과 올리브오일로 버무린 저칼륨 반찬",
      "estimatedNutrients": {
        "sodium": 150,
        "potassium": 250,
        "phosphorus": 50,
        "protein": 3
      }
    }
  ]
}
```

**케이스 3: ingredient_multiple (복수 식재료)**

```python
async def _handle_case_ingredient_multiple(self, classification, session_id):
    ingredients = classification["items"][:5]  # 최대 5개

    # 1. 식재료별 영양소 분석
    ingredients_analysis = await self._analyze_multiple_ingredients(ingredients)

    # 2. 복수 식재료로 만들 수 있는 요리 추천
    recommended_dishes = await self._recommend_dishes_for_multiple_ingredients(ingredients)

    return {
        "response": f"인식된 식재료: **{', '.join(ingredients)}**",
        "ingredientCandidates": ingredients_analysis,
        "recommendedDishes": recommended_dishes,
        "analysisType": "ingredient_multiple"
    }
```

#### 3.2.5 영양 분석 및 대체 재료 추천

**RAG 데이터 기반 분석**:

```python
async def _analyze_dish_with_rag_data(self, dish_name, dish_data):
    nutrition = dish_data["nutrition"]
    ingredients = dish_data["ingredients"]

    # 1. CKD 제한 영양소 초과 재료 찾기
    high_risk_ingredients = self._find_high_risk_ingredients(nutrition, ingredients)

    # 2. 대체 재료 추천 (GPT-4o)
    alternatives = await self._recommend_alternative_ingredients(dish_name, high_risk_ingredients)

    # 3. Nutrition data 생성
    nutrition_data = {
        "dishName": dish_name,
        "nutrients": [
            {"name": "나트륨", "value": nutrition.get("sodium", 1500), "max": 2000, "unit": "mg", "status": "warning"},
            {"name": "칼륨", "value": nutrition.get("potassium", 1200), "max": 2000, "unit": "mg", "status": "safe"},
            # ... 인, 단백질, 칼슘
        ],
        "alternatives": alternatives,
        "guideline": "신장병 환자 식사 원칙: 나트륨·칼륨·인 최소화..."
    }

    # 4. 동적 응답 생성
    danger_nutrients = [n for n in nutrition_data["nutrients"] if n["status"] == "danger"]
    if danger_nutrients:
        response = f"⚠️ {dish_name}는 {', '.join([n['name'] for n in danger_nutrients])} 함량이 높아 주의가 필요해요."

    return {"response": response, "nutritionData": nutrition_data}
```

**대체 재료 추천 (간장 필터링)**:

```python
async def _recommend_alternative_ingredients(self, dish_name, high_risk_ingredients):
    response = await self.client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": ALTERNATIVE_INGREDIENT_PROMPT.format(...)}],
        max_tokens=1500,
        temperature=0.7
    )

    data = self._extract_json(response.choices[0].message.content)
    alternatives = []
    for alt in data.get("alternatives", []):
        for replacement in alt["replacements"][:2]:
            alternatives.append({
                "name": replacement["name"],
                "description": replacement["reason"],
                "nutrients": replacement["nutrients"]
            })

    # 간장 필터링 (절대 포함 금지)
    alternatives = [
        alt for alt in alternatives
        if not any(kw in alt["name"].lower() for kw in ["간장", "된장", "고추장", "soy sauce"])
    ]

    return alternatives[:3]
```

#### 3.2.6 사용자 프로필별 맞춤 응답

```python
def get_profile_instructions(user_profile: str) -> str:
    return PROFILE_INSTRUCTIONS.get(user_profile, PROFILE_INSTRUCTIONS["general"])
```

**프로필 종류**:
1. **general** (일반 사용자):
   - 쉽고 이해하기 쉬운 용어
   - 신장병 예방 및 건강한 식습관 위주

2. **patient** (신장병 환자):
   - 실질적이고 실천 가능한 식단 가이드
   - 증상 관리 및 삶의 질 향상에 초점
   - 투석 환자를 위한 특별 권장 사항 포함

3. **researcher** (연구자/의료진):
   - 의학적으로 정확하고 상세한 영양 정보
   - 최신 가이드라인 및 임상 연구 기반 설명
   - 영양소별 메커니즘 및 신장 기능 영향 설명

---

### 3.3 ResearchPaperAgent (논문 검색 Agent)

**파일**: `backend/Agent/research_paper/agent.py` (486줄)
**역할**: Parlant 프레임워크 기반 의료 논문 검색

#### 3.3.1 Parlant 서버 자동 시작

```python
@classmethod
async def _ensure_server_running(cls):
    # 1. 서버 실행 여부 확인
    if await cls._check_server_running():
        logger.info("✅ Parlant server already running")
        return

    # 2. 서버 시작
    healthcare_server_path = Path(__file__).parent / "server" / "healthcare_v2_en.py"
    cls._parlant_server_process = subprocess.Popen(
        [sys.executable, str(healthcare_server_path)],
        cwd=str(healthcare_server_path.parent),
        env=os.environ.copy()
    )

    # 3. 서버 준비 대기 (최대 60초)
    max_wait = 60
    while elapsed < max_wait:
        await asyncio.sleep(2)
        if await cls._check_server_running():
            logger.info(f"✅ Parlant server started successfully")
            return
```

**서버 확인**:
```python
@classmethod
async def _check_server_running(cls) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{cls._server_url}/api/agents", timeout=2.0)
            return response.status_code in [200, 401, 403, 404]
    except Exception:
        return False
```

#### 3.3.2 Parlant 클라이언트 (싱글톤)

```python
@classmethod
async def _get_client(cls):
    if cls._parlant_client is None:
        await cls._ensure_server_running()
        cls._parlant_client = AsyncParlantClient(base_url=cls._server_url)
        await cls._setup_agent_and_customer()
    return cls._parlant_client
```

**Agent 및 Customer 설정**:
```python
@classmethod
async def _setup_agent_and_customer(cls):
    # 1. Agent 목록 조회
    agents_response = await cls._parlant_client.agents.list()
    cls._agent_id = agents_response[0].id  # CareGuide_v2

    # 2. Customer 생성
    customer = await cls._parlant_client.customers.create(
        name=f"research_agent_{int(time.time())}"
    )
    cls._customer_id = customer.id
```

#### 3.3.3 검색 요청 처리

```python
async def process(self, user_input, session_id, context=None):
    # 1. 세션 생성 (프로필 태그 포함)
    profile = context.get('profile', 'general')
    profile_tag = await self.client.tags.create(name=f"profile:{profile}")

    session_customer = await self.client.customers.create(
        name=f"session_{session_id}_{int(time.time())}",
        tags=[profile_tag.id]
    )

    parlant_session = await self.client.sessions.create(
        agent_id=self._agent_id,
        customer_id=session_customer.id
    )

    # 2. 쿼리 전송
    customer_event = await self.client.sessions.create_event(
        session_id=parlant_session.id,
        kind="message",
        source="customer",
        message=user_input,
        moderation="none"  # 즉시 처리
    )

    # 3. 응답 대기 (폴링, 최대 10분)
    disclaimer_text = "⚠️ 이 답변은 교육 목적이며..."
    while True:
        events = await self.client.sessions.list_events(
            session_id=parlant_session.id,
            min_offset=last_event_offset + 1,
            kinds="message",
            wait_for_data=5  # 5초 대기
        )

        # Disclaimer 포함 시 완료
        if disclaimer_text in message_text:
            logger.info("✅ Response complete with disclaimer")
            break

    # 4. 응답 조합
    answer_text = '\n'.join([msg.data['message'] for msg in agent_messages])

    return {
        "answer": answer_text,
        "sources": [...],
        "papers": [],
        "tokens_used": estimated_tokens
    }
```

---

### 3.4 QuizAgent (퀴즈 생성 Agent)

**파일**: `backend/Agent/quiz/agent.py` (864줄)
**역할**: RAG 기반 퀴즈 생성 및 관리

#### 3.4.1 퀴즈 세션 생성

```python
async def _generate_quiz_session(self, context, session_id):
    user_id = context["userId"]
    session_type = context["sessionType"]  # level_test, learning_mission, daily_quiz
    category = context.get("category")
    difficulty = context.get("difficulty")

    # 1. 문제 구성 결정
    question_configs = self._determine_question_config(session_type, category, difficulty)
    # 예: [{"category": "nutrition", "difficulty": "easy", "count": 2}, ...]

    # 2. 각 구성에 따라 문제 생성
    all_questions = []
    for config in question_configs:
        questions = await self._generate_questions_with_rag(
            category=config["category"],
            difficulty=config["difficulty"],
            num_questions=config["count"]
        )
        all_questions.extend(questions)

    # 3. MongoDB에 저장
    sessions_collection = db["quiz_sessions"]
    quiz_questions_collection = db["quiz_questions"]

    question_ids = []
    for q in all_questions:
        result = quiz_questions_collection.insert_one({
            "category": q["category"],
            "difficulty": q["difficulty"],
            "question": q["question"],
            "answer": q["answer"],
            "explanation": q["explanation"],
            "totalAttempts": 0,
            "correctAttempts": 0
        })
        question_ids.append(str(result.inserted_id))

    session_doc = {
        "userId": user_id,
        "sessionType": session_type,
        "questionIds": question_ids,
        "currentQuestionIndex": 0,
        "answers": [],
        "score": 0,
        "consecutiveCorrect": 0,  # 연속 정답 카운터
        "status": "in_progress"
    }
    session_result = sessions_collection.insert_one(session_doc)

    # 4. 첫 번째 문제 반환 (답안/해설 숨김)
    first_question = quiz_questions_collection.find_one({"_id": ObjectId(question_ids[0])})
    return {
        "sessionId": str(session_result.inserted_id),
        "totalQuestions": len(question_ids),
        "currentQuestion": {
            "id": question_ids[0],
            "category": first_question["category"],
            "difficulty": first_question["difficulty"],
            "question": first_question["question"],
            "answer": True,  # 더미값
            "explanation": ""  # 숨김
        }
    }
```

#### 3.4.2 RAG 기반 퀴즈 생성

```python
async def _generate_questions_with_rag(self, category, difficulty, num_questions=5):
    # 1. 카테고리 키워드로 RAG 검색
    keywords = CATEGORY_KEYWORDS.get(category, [])
    search_query = f"만성콩팥병 {CATEGORY_NAMES_KR[category]} {' '.join(keywords[:5])}"

    # 2. Vector DB 검색 (의학 논문, 가이드라인)
    rag_results = await self.vector_client.semantic_search(
        query=search_query,
        namespace="papers_kidney",
        top_k=5
    )

    # 3. MongoDB 검색 (Q&A, 의료 정보)
    mongodb_results = await self.mongodb_client.search_parallel(
        query=search_query,
        collections=["qa_kidney", "guidelines_kidney"],
        limit=5
    )

    # 4. RAG 컨텍스트 구성
    rag_context = self._build_rag_context(rag_results, mongodb_results)

    # 5. OpenAI로 퀴즈 생성
    user_prompt = QUIZ_GENERATION_USER_PROMPT_TEMPLATE.format(
        num_questions=num_questions,
        category=category,
        difficulty=difficulty,
        rag_context=rag_context
    )

    result = await self.openai_client.generate(
        prompt=user_prompt,
        system_prompt=QUIZ_GENERATION_SYSTEM_PROMPT,
        temperature=0.7,
        max_tokens=2000
    )

    # 6. JSON 파싱
    questions = json.loads(result["text"])
    return questions
```

#### 3.4.3 답안 제출 및 연속 정답 보너스

```python
async def _submit_answer(self, context, session_id):
    quiz_session_id = context["sessionId"]
    question_id = context["questionId"]
    user_answer = context["userAnswer"]

    # 1. 정답 확인
    question = questions_collection.find_one({"_id": ObjectId(question_id)})
    is_correct = (user_answer == question["answer"])

    # 2. 연속 정답 보너스
    current_consecutive = session["consecutiveCorrect"]
    points_earned = 0
    new_consecutive = 0

    if is_correct:
        points_earned = 10
        new_consecutive = current_consecutive + 1

        # 3개 이상 연속 정답 시 +5점
        if new_consecutive >= 3:
            points_earned += 5
    else:
        new_consecutive = 0

    # 3. 세션 업데이트
    sessions_collection.update_one(
        {"_id": ObjectId(quiz_session_id)},
        {
            "$push": {"answers": {"questionId": question_id, "isCorrect": is_correct, "pointsEarned": points_earned}},
            "$set": {"score": session["score"] + points_earned, "consecutiveCorrect": new_consecutive}
        }
    )

    # 4. 문제 통계 업데이트
    questions_collection.update_one(
        {"_id": ObjectId(question_id)},
        {"$inc": {"totalAttempts": 1, "correctAttempts": 1 if is_correct else 0}}
    )

    # 5. 다음 문제 반환
    next_question = None
    if current_index + 1 < len(question_ids):
        next_q = questions_collection.find_one({"_id": ObjectId(question_ids[current_index + 1])})
        next_question = {"id": ..., "question": next_q["question"], "answer": True, "explanation": ""}

    return {
        "isCorrect": is_correct,
        "correctAnswer": question["answer"],
        "explanation": question["explanation"],
        "pointsEarned": points_earned,
        "currentScore": current_score,
        "consecutiveCorrect": new_consecutive,
        "nextQuestion": next_question
    }
```

#### 3.4.4 세션 완료 및 스트릭 계산

```python
async def _complete_session(self, context, session_id):
    # 1. 정답률 계산
    total_questions = len(session["questionIds"])
    correct_answers = sum(1 for a in session["answers"] if a["isCorrect"])
    accuracy_rate = (correct_answers / total_questions) * 100

    # 2. 스트릭 계산 (daily_quiz만)
    if session_type == "daily_quiz":
        last_date = existing_stats.get("lastSessionDate")
        days_diff = (completed_at - last_date).days

        if days_diff == 1:
            # 연속 달성
            current_streak = existing_stats["currentStreak"] + 1
            best_streak = max(current_streak, existing_stats["bestStreak"])
        elif days_diff > 1:
            # 스트릭 끊김
            current_streak = 1
        else:
            # 같은 날 (유지)
            current_streak = existing_stats["currentStreak"]

    # 3. 레벨 판정 (level_test만)
    if session_type == "level_test":
        if accuracy_rate >= 80:
            level = "advanced"
        elif accuracy_rate >= 50:
            level = "intermediate"
        else:
            level = "beginner"

    # 4. 카테고리별 성과 계산
    category_performance = self._calculate_category_performance(session)

    return {
        "totalQuestions": total_questions,
        "correctAnswers": correct_answers,
        "finalScore": session["score"],
        "accuracyRate": round(accuracy_rate, 2),
        "streak": current_streak,
        "categoryPerformance": category_performance
    }
```

---

## 4. RAG 시스템

### 4.1 NutritionRAG (CLIP + Pinecone)

**파일**: `backend/rag/nutrition_rag.py` (392줄)
**역할**: 음식 이미지/텍스트 하이브리드 검색

#### 4.1.1 CLIP 모델 초기화

```python
class NutritionRAG:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # CLIP 모델 로드
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.model.to(self.device)
        self.model.eval()

        # Pinecone 초기화
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index("nutrition-ckd")  # 512-dim, cosine

        # BM25 (in-memory)
        self.bm25 = None
        self.food_corpus = []
```

#### 4.1.2 이미지 임베딩

```python
def encode_image(self, image_input: Union[str, Image.Image]) -> torch.Tensor:
    # Base64 → PIL Image
    if isinstance(image_input, str):
        image_bytes = base64.b64decode(image_input)
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    else:
        image = image_input

    # CLIP 전처리
    inputs = self.processor(images=image, return_tensors="pt")
    inputs = {k: v.to(self.device) for k, v in inputs.items()}

    with torch.no_grad():
        image_features = self.model.get_image_features(**inputs)
        # L2 정규화
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

    return image_features.cpu().squeeze()  # (512,)
```

#### 4.1.3 텍스트 임베딩

```python
def encode_text(self, text: str) -> torch.Tensor:
    inputs = self.processor(text=[text], return_tensors="pt", padding=True)
    inputs = {k: v.to(self.device) for k, v in inputs.items()}

    with torch.no_grad():
        text_features = self.model.get_text_features(**inputs)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

    return text_features.cpu().squeeze()  # (512,)
```

#### 4.1.4 이미지 검색

```python
def search_by_image(self, image_input, top_k=5):
    # 1. 이미지 임베딩
    image_emb = self.encode_image(image_input)

    # 2. Pinecone 검색
    results = self.index.query(
        vector=image_emb.tolist(),
        top_k=top_k,
        include_metadata=True
    )

    # 3. 결과 파싱
    foods = []
    for match in results.matches:
        foods.append({
            "dish_name": match.metadata["dish_name"],
            "ingredients": match.metadata["ingredients"],
            "recipe": match.metadata["recipe"],
            "nutrition": match.metadata["nutrition"],
            "score": match.score  # Cosine 유사도
        })

    return foods
```

#### 4.1.5 하이브리드 검색 (Semantic + BM25)

```python
def hybrid_search(self, query, top_k=5, semantic_weight=0.7):
    # 1. Semantic search
    semantic_results = self.search_by_text(query, top_k=top_k * 2)

    # 2. BM25 keyword search
    if self.bm25:
        tokenized_query = query.split()
        bm25_scores = self.bm25.get_scores(tokenized_query)

        # 3. Weighted combination
        combined = {}
        for idx, food in enumerate(self.food_corpus):
            dish_name = food["dish_name"]
            bm25_score = bm25_scores[idx] / (max(bm25_scores) + 1e-6)

            # Find semantic score
            semantic_score = next((r["score"] for r in semantic_results if r["dish_name"] == dish_name), 0)

            # Hybrid score
            combined[dish_name] = {
                **food,
                "score": semantic_weight * semantic_score + (1 - semantic_weight) * bm25_score
            }

        # 4. Sort by score
        ranked = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]

    # Fallback to semantic only
    return semantic_results[:top_k]
```

#### 4.1.6 데이터 Upsert

```python
def upsert_food(self, food_id, dish_name, ingredients, recipe, nutrition, image=None):
    # 1. 임베딩 생성
    if image:
        embedding = self.encode_image(image)
    else:
        text = f"{dish_name} {' '.join(ingredients)} {recipe}"
        embedding = self.encode_text(text)

    # 2. Pinecone에 Upsert
    self.index.upsert(vectors=[(
        food_id,
        embedding.tolist(),
        {
            "dish_name": dish_name,
            "ingredients": ingredients,
            "recipe": recipe,
            "nutrition": nutrition
        }
    )])
```

---

### 4.2 RAGRecipeTool (FAISS + LangChain)

**파일**: `backend/tools/rag_recipe_tool.py` (217줄)
**역할**: 저칼륨/저인/저나트륨 레시피 검색

#### 4.2.1 벡터스토어 로드

```python
class RAGRecipeTool:
    def __init__(self):
        from langchain_openai import OpenAIEmbeddings
        from langchain_community.vectorstores import FAISS

        embeddings = OpenAIEmbeddings(
            openai_api_key=OPENAI_API_KEY,
            model="text-embedding-3-small"
        )

        self.vectorstore = FAISS.load_local(
            str(VECTORSTORE_PATH),
            embeddings,
            allow_dangerous_deserialization=True
        )
```

#### 4.2.2 레시피 검색

```python
def search_recipes(self, query, k=3, filter_metadata=None):
    if filter_metadata:
        results = self.vectorstore.similarity_search(query, k=k, filter=filter_metadata)
    else:
        results = self.vectorstore.similarity_search(query, k=k)

    return [{
        'content': doc.page_content,
        'metadata': doc.metadata,
        'source': doc.metadata.get('source_file', 'unknown')
    } for doc in results]
```

#### 4.2.3 특화 검색 메서드

```python
def get_low_potassium_recipes(self, food_type=""):
    """저칼륨 레시피 검색"""
    query = f"저칼륨 {food_type} 레시피 조리법".strip()
    return self.search_recipes(query, k=5)

def get_low_phosphorus_recipes(self, food_type=""):
    """저인 레시피 검색"""
    query = f"인 제한 {food_type} 레시피 조리법".strip()
    return self.search_recipes(query, k=5)

def get_ckd_guidelines(self, stage=3):
    """CKD 단계별 식이 가이드라인 검색"""
    query = f"만성 신부전 {stage}단계 식이요법 가이드라인 권장"
    return self.search_recipes(query, k=5)

def get_alternative_foods(self, high_risk_food, nutrient="칼륨"):
    """대체 식품 검색"""
    query = f"{high_risk_food} 대신 {nutrient} 낮은 대체 식품 추천"
    return self.search_recipes(query, k=3)
```

---

## 5. API 라우터 상세

### 5.1 Community API (`app/api/community.py`)

**라인 수**: 831줄
**역할**: 커뮤니티 게시글, 댓글, 좋아요, 이미지 업로드

#### 5.1.1 Authorization Testing Mode

```python
TEST_AUTH_ENABLED = os.getenv("TEST_AUTH_ENABLED", "false").lower() == "true"

def check_author_permission(user_id, author_id, operation="modify"):
    if TEST_AUTH_ENABLED and user_id != author_id:
        raise HTTPException(status_code=403, detail=f"권한이 없습니다. {operation} 권한이 있는 사용자만 가능합니다.")
```

**목적**:
- **개발 모드** (`TEST_AUTH_ENABLED=false`): 권한 검사 비활성화
- **프로덕션 모드** (`TEST_AUTH_ENABLED=true`): 작성자만 수정/삭제 가능

#### 5.1.2 게시글 목록 (Infinite Scroll)

```python
@router.get("/posts")
def get_posts(
    limit: int = Query(20, ge=1, le=50),
    cursor: Optional[str] = Query(None),
    postType: Optional[PostType] = Query(None),
    sortBy: str = Query("lastActivityAt")
):
    # 1. Featured 게시글 제외 (중복 방지)
    featured_posts = list(collection.find({"isPinned": True, "isDeleted": False}).limit(3))
    featured_ids = [post["_id"] for post in featured_posts]

    # 2. 쿼리 필터
    query = {"isDeleted": False, "_id": {"$nin": featured_ids}}
    if postType:
        query["postType"] = postType

    # 3. Cursor-based pagination
    if cursor:
        query["_id"] = {"$lt": ObjectId(cursor)}

    # 4. 정렬 및 조회
    posts = list(collection.find(query).sort(sortBy, -1).limit(limit))

    # 5. 응답
    return {
        "posts": [serialize_post(p) for p in posts],
        "nextCursor": posts[-1]["id"] if posts else None,
        "hasMore": len(posts) == limit
    }
```

#### 5.1.3 Featured 게시글 (Top 3)

```python
@router.get("/posts/featured")
def get_featured_posts():
    # 1. Pinned posts 우선
    pinned_posts = list(collection.find({"isPinned": True, "isDeleted": False}).sort("createdAt", -1).limit(3))

    # 2. 부족하면 Popular posts로 채우기
    if len(pinned_posts) < 3:
        remaining = 3 - len(pinned_posts)
        pinned_ids = [post["_id"] for post in pinned_posts]

        popular_posts = list(collection.aggregate([
            {"$match": {"isDeleted": False, "_id": {"$nin": pinned_ids}}},
            {"$addFields": {"popularity": {"$add": ["$viewCount", "$likes", "$commentCount"]}}},
            {"$sort": {"popularity": -1}},
            {"$limit": remaining}
        ]))

        pinned_posts.extend(popular_posts)

    return {"featuredPosts": [serialize_post(p) for p in pinned_posts]}
```

#### 5.1.4 게시글 상세 (조회수 증가)

```python
@router.get("/posts/{postId}")
def get_post(postId: str):
    # 1. 게시글 조회
    post = posts_collection.find_one({"_id": ObjectId(postId), "isDeleted": False})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # 2. 조회수 증가 (atomic)
    posts_collection.update_one(
        {"_id": ObjectId(postId)},
        {"$inc": {"viewCount": 1}}
    )
    post["viewCount"] = post.get("viewCount", 0) + 1

    # 3. 댓글 조회
    comments = list(comments_collection.find({"postId": postId, "isDeleted": False}).sort("createdAt", -1))

    # 4. PostDetail 형식으로 변환
    post_detail = {
        **serialize_post(post),
        "author": {"id": post["userId"], "name": post["authorName"], "profileImage": None},
        "likedByMe": False
    }

    return {"post": post_detail, "comments": [serialize_comment(c) for c in comments]}
```

#### 5.1.5 댓글 작성 (Post 통계 업데이트)

```python
@router.post("/comments", status_code=201)
def create_comment(comment_data: CommentCreate):
    # 1. Post 존재 확인
    post = posts_collection.find_one({"_id": ObjectId(comment_data.postId), "isDeleted": False})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # 2. 댓글 생성
    comment_doc = {
        "postId": comment_data.postId,
        "userId": "temp_user_123",
        "authorName": "Temporary User",
        "content": comment_data.content,
        "createdAt": datetime.utcnow(),
        "isDeleted": False
    }
    result = comments_collection.insert_one(comment_doc)

    # 3. Post 통계 업데이트 (댓글 수 +1, 마지막 활동 시간 갱신)
    posts_collection.update_one(
        {"_id": ObjectId(comment_data.postId)},
        {"$inc": {"commentCount": 1}, "$set": {"lastActivityAt": datetime.utcnow()}}
    )

    return serialize_comment(comments_collection.find_one({"_id": result.inserted_id}))
```

#### 5.1.6 이미지 업로드

```python
@router.post("/uploads", status_code=201)
def upload_image(file: UploadFile = File(...)):
    # 1. 파일 타입 검증
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type")

    # 2. 고유 파일명 생성 (타임스탬프)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = Path("uploads") / unique_filename

    # 3. 파일 저장
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"url": f"/uploads/{unique_filename}", "filename": unique_filename}
```

---

### 5.2 Quiz API (`app/api/quiz.py`)

**라인 수**: 237줄
**역할**: Agent 기반 퀴즈 세션 관리

#### 5.2.1 퀴즈 세션 시작

```python
@router.post("/session/start", status_code=201)
async def start_quiz_session(request: QuizSessionStart):
    # 1. 세션 생성
    session_id = agent_manager.create_user_session(request.userId)

    # 2. Context 구성
    context = {
        "action": "generate_quiz",
        "userId": request.userId,
        "sessionType": request.sessionType.value,  # level_test, learning_mission, daily_quiz
        "category": request.category.value if request.category else None,
        "difficulty": request.difficulty.value if request.difficulty else None
    }

    # 3. Quiz Agent 호출
    result = await agent_manager.route_request(
        agent_type="quiz",
        user_input=f"Generate {request.sessionType} quiz",
        session_id=session_id,
        context=context
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=f"퀴즈 생성 실패: {result.get('error')}")

    return QuizSessionResponse(**result["result"])
```

**요청 예시**:
```json
{
  "userId": "user123",
  "sessionType": "daily_quiz",
  "category": "nutrition",
  "difficulty": "medium"
}
```

**응답 예시**:
```json
{
  "sessionId": "64f1a2b3c4d5e6f7g8h9i0j1",
  "userId": "user123",
  "sessionType": "daily_quiz",
  "totalQuestions": 5,
  "currentQuestionNumber": 1,
  "score": 0,
  "status": "in_progress",
  "currentQuestion": {
    "id": "q1",
    "category": "nutrition",
    "difficulty": "medium",
    "question": "만성 신장병 환자에게 권장되는 1일 나트륨 섭취량은?",
    "answer": true,
    "explanation": ""
  }
}
```

---

### 5.3 Auth API (`app/api/auth.py`)

**라인 수**: 155줄
**역할**: 회원가입, 로그인, JWT 토큰 발급

#### 5.3.1 회원가입

```python
@router.post("/register")
async def register(user_data: RegisterRequest):
    # 1. 중복 확인
    if users_collection.find_one({"username": user_data.username}):
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다")

    # 2. 사용자 생성
    user_doc = {
        "username": user_data.username,
        "email": user_data.email,
        "password": hash_password(user_data.password),  # bcrypt
        "fullName": user_data.fullName,
        "role": "user",
        "created_at": datetime.utcnow()
    }
    result = users_collection.insert_one(user_doc)

    # 3. 토큰 생성 (7일 만료)
    token = create_access_token({"user_id": str(result.inserted_id), "username": user_data.username})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": str(result.inserted_id), "username": user_data.username, "email": user_data.email}
    }
```

#### 5.3.2 로그인

```python
@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    # 1. 사용자 찾기 (username 또는 email)
    user = users_collection.find_one({"$or": [{"username": username}, {"email": username}]})

    # 2. 비밀번호 검증
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 잘못되었습니다")

    # 3. 토큰 생성
    token = create_access_token({"user_id": str(user["_id"]), "username": user["username"]})

    return {"access_token": token, "token_type": "bearer", "user": {...}}
```

#### 5.3.3 개발용 자동 로그인

```python
@router.post("/dev-login")
async def dev_login():
    """테스트 사용자 자동 생성 및 로그인"""
    test_username = "testuser"
    test_password = "password123"

    # 기존 사용자 확인 or 생성
    user = users_collection.find_one({"username": test_username})
    if not user:
        user_doc = {
            "username": test_username,
            "email": "test@example.com",
            "password": hash_password(test_password),
            "fullName": "Test User",
            "role": "user"
        }
        result = users_collection.insert_one(user_doc)
        user = users_collection.find_one({"_id": result.inserted_id})

    # 토큰 발급
    token = create_access_token({"user_id": str(user["_id"]), "username": user["username"]})

    return {"access_token": token, "token_type": "bearer", "user": {...}}
```

---

## 6. 데이터베이스 계층

### 6.1 MongoDB 연결 (`app/db/connection.py`)

```python
# MongoDB 클라이언트 초기화
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "careguide"

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# 컬렉션 정의
users_collection: Collection = db["users"]
notifications_collection: Collection = db["notifications"]
notification_settings_collection: Collection = db["notification_settings"]

def check_connection():
    """MongoDB 연결 상태 확인"""
    try:
        client.admin.command('ping')
        return {"status": "success", "message": "MongoDB 연결 성공"}
    except Exception as e:
        return {"status": "error", "message": f"MongoDB 연결 실패: {str(e)}"}
```

### 6.2 MongoDB 컬렉션 구조

#### 6.2.1 `users` 컬렉션

```json
{
  "_id": "ObjectId",
  "username": "string (unique)",
  "email": "string (unique)",
  "password": "string (bcrypt hash)",
  "fullName": "string",
  "role": "user | admin",
  "created_at": "datetime"
}
```

#### 6.2.2 `quiz_sessions` 컬렉션

```json
{
  "_id": "ObjectId",
  "userId": "string",
  "sessionType": "level_test | learning_mission | daily_quiz",
  "questionIds": ["string"],
  "questionsMetadata": [{"questionId": "string", "category": "string", "difficulty": "string"}],
  "currentQuestionIndex": "int",
  "answers": [{"questionId": "string", "userAnswer": "boolean", "isCorrect": "boolean", "pointsEarned": "int"}],
  "score": "int",
  "consecutiveCorrect": "int",
  "status": "in_progress | completed",
  "startedAt": "datetime",
  "completedAt": "datetime | null"
}
```

#### 6.2.3 `quiz_questions` 컬렉션

```json
{
  "_id": "ObjectId",
  "category": "nutrition | treatment | lifestyle",
  "difficulty": "easy | medium | hard",
  "question": "string",
  "answer": "boolean",
  "explanation": "string",
  "totalAttempts": "int",
  "correctAttempts": "int",
  "createdAt": "datetime"
}
```

#### 6.2.4 `user_quiz_stats` 컬렉션

```json
{
  "_id": "ObjectId",
  "userId": "string",
  "totalSessions": "int",
  "totalQuestions": "int",
  "correctAnswers": "int",
  "totalScore": "int",
  "currentStreak": "int",
  "bestStreak": "int",
  "level": "beginner | intermediate | advanced",
  "lastSessionDate": "datetime"
}
```

#### 6.2.5 `posts` 컬렉션

```json
{
  "_id": "ObjectId",
  "userId": "string",
  "authorName": "string",
  "title": "string",
  "content": "string",
  "postType": "BOARD | CHALLENGE | SURVEY",
  "imageUrls": ["string"],
  "thumbnailUrl": "string | null",
  "likes": "int",
  "commentCount": "int",
  "viewCount": "int",
  "createdAt": "datetime",
  "updatedAt": "datetime",
  "lastActivityAt": "datetime",
  "isPinned": "boolean",
  "isDeleted": "boolean"
}
```

---

## 7. 인증 & 보안

### 7.1 JWT 토큰 생성 (`app/services/auth.py`)

```python
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, os.getenv("SECRET_KEY", "your-secret-key-here"), algorithm="HS256")
```

### 7.2 비밀번호 해싱 (bcrypt)

```python
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
```

### 7.3 현재 사용자 인증

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """토큰에서 현재 사용자 정보 추출"""
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
        user_id = payload.get("user_id")
    except JWTError:
        raise HTTPException(status_code=401, detail="인증 정보를 확인할 수 없습니다")

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")

    return user
```

---

## 8. 서비스 계층

### 8.1 Tools - NutrientLookupTool

**파일**: `backend/tools/nutrient_lookup.py` (80줄)
**역할**: MongoDB에서 식품 영양 정보 검색

```python
class NutrientLookupTool:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client["careguide"]
        self.food_collection = self.db['food_nutrients']
        self.users_collection = self.db['users']

    def search_food(self, food_name: str, limit: int = 5):
        """식품명으로 영양 정보 검색"""
        # 1. 텍스트 검색
        results = list(self.food_collection.find(
            {"$text": {"$search": food_name}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit))

        # 2. Fallback: Regex 검색
        if not results:
            results = list(self.food_collection.find(
                {"food_name": {"$regex": food_name, "$options": "i"}}
            ).limit(limit))

        return results
```

---

## 9. 도구 및 유틸리티

### 9.1 SessionManager

**파일**: `backend/Agent/session_manager.py` (176줄)
**역할**: 메모리 내 세션 관리

```python
class SessionManager:
    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[str, Dict] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)

    def create_session(self, user_id: str) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "active_agent": None,
            "conversation_history": []
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # 타임아웃 확인
        if datetime.utcnow() - session["last_activity"] > self.session_timeout:
            self.delete_session(session_id)
            return None

        return session
```

---

## 10. 데이터 플로우

### 10.1 영양 분석 플로우

```
1. Frontend → POST /api/nutrition/analyze
   ↓
2. main.py → session_manager.get_session(session_id)
   ↓
3. main.py → nutrition_agent.process(user_input, session_id, context)
   ↓
4. NutritionAgent → GPT-4o Vision (이미지 분류)
   ↓
5. NutritionAgent → NutritionRAG.search_by_image() (CLIP + Pinecone)
   ↓
6. NutritionAgent → GPT-4o (대체 재료 추천)
   ↓
7. NutritionAgent → return {response, nutritionData, alternatives}
   ↓
8. main.py → return {success, agent_type, result}
   ↓
9. Frontend → 영양 분석 결과 표시
```

### 10.2 퀴즈 생성 플로우

```
1. Frontend → POST /api/quiz/session/start
   ↓
2. quiz.py → agent_manager.route_request(agent_type="quiz", context)
   ↓
3. QuizAgent → _generate_questions_with_rag()
   ├→ VectorClient.semantic_search() (논문/가이드라인 검색)
   ├→ MongoDBClient.search_parallel() (Q&A 검색)
   └→ OpenAIClient.generate() (RAG 컨텍스트 기반 퀴즈 생성)
   ↓
4. QuizAgent → MongoDB에 questions, session 저장
   ↓
5. quiz.py → return {sessionId, currentQuestion, ...}
   ↓
6. Frontend → 퀴즈 시작
```

---

## 요약

**CareGuide Backend**는 만성 신장 질환(CKD) 환자를 위한 **AI 기반 종합 헬스케어 플랫폼**입니다.

### 핵심 특징

1. **멀티 Agent 아키텍처**: 영양, 퀴즈, 논문 검색 등 도메인별 전문 Agent
2. **하이브리드 RAG**: CLIP + Pinecone + BM25로 이미지/텍스트 동시 검색
3. **GPT-4o Vision**: 음식 이미지 5가지 케이스 분류 및 분석
4. **Parlant 프레임워크**: 의료 논문 검색을 위한 엔터프라이즈급 AI Agent
5. **JWT 인증**: bcrypt + JWT로 안전한 사용자 인증
6. **MongoDB + Pinecone**: 하이브리드 데이터베이스 아키텍처
7. **FastAPI**: 비동기 처리로 높은 성능

**총 코드 규모**: 75개 Python 파일, 19,410줄

---

## 파일 참조

| 컴포넌트 | 파일 위치 | 라인 수 |
|---------|----------|---------|
| 메인 애플리케이션 | `backend/app/main.py` | 184줄 |
| BaseAgent | `backend/Agent/base_agent.py` | 58줄 |
| NutritionAgent | `backend/Agent/nutrition/agent.py` | 1010줄 |
| ResearchPaperAgent | `backend/Agent/research_paper/agent.py` | 486줄 |
| QuizAgent | `backend/Agent/quiz/agent.py` | 864줄 |
| NutritionRAG | `backend/rag/nutrition_rag.py` | 392줄 |
| RAGRecipeTool | `backend/tools/rag_recipe_tool.py` | 217줄 |
| Community API | `backend/app/api/community.py` | 831줄 |
| Quiz API | `backend/app/api/quiz.py` | 237줄 |
| Auth API | `backend/app/api/auth.py` | 155줄 |
| SessionManager | `backend/Agent/session_manager.py` | 176줄 |
| DB Connection | `backend/app/db/connection.py` | 39줄 |
| Auth Service | `backend/app/services/auth.py` | 47줄 |

---

**작성일**: 2025-01-22
**작성자**: Claude Code
