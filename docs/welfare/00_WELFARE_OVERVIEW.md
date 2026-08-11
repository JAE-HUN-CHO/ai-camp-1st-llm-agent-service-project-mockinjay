# 복지 기능 구현 개요
## CareGuide Welfare Module Overview

**작성일**: 2025-11-19
**버전**: v2.0
**상태**: 구현 대기
**총 예상 시간**: 10시간 (2일)

---

## 📋 목차

이 문서는 CareGuide 복지 기능 구현의 전체 개요를 제공합니다.
상세 내용은 아래 개별 문서를 참조하세요.

### 문서 구조

1. **00_WELFARE_OVERVIEW.md** (이 문서) - 전체 개요
2. **01_WELFARE_DATABASE_DESIGN.md** - 데이터베이스 스키마 및 설계
3. **02_WELFARE_BACKEND_IMPLEMENTATION.md** - WelfareManager 구현
4. **03_WELFARE_PARLANT_INTEGRATION.md** - Parlant Tools & Journey 7
5. **04_WELFARE_API_REFERENCE.md** - REST API 명세
6. **05_WELFARE_TESTING_GUIDE.md** - 테스트 계획 및 실행
7. **06_WELFARE_DEPLOYMENT.md** - 배포 및 운영 가이드

---

## 🎯 프로젝트 목표

### 복지 기능 목적

만성콩팥병(CKD) 환자를 위한 **복지 정보 검색 및 안내 시스템** 구축:

1. **산정특례 제도** (Copay Reduction)
   - 본인부담금 90-95% 감면
   - V001 (CKD 3기 이상), V003 (혈액투석)

2. **장애인 복지** (Disability Benefits)
   - 장애 등급 등록 (2급: 투석, 5급: 이식)
   - 장애인연금, 의료비 지원

3. **의료비 지원** (Medical Aid)
   - 차상위 의료급여
   - 재난적 의료비 지원
   - 긴급 의료비 지원

4. **신장이식 지원** (Transplant Support)
   - 수술비 최대 3,000만원
   - 면역억제제 월 최대 20만원

5. **교통비 지원** (Transport Support)
   - 투석 환자 월 15만원

---

## 📊 현재 상태 분석

### ✅ 구축 완료된 인프라

#### 백엔드 인프라 (70%)
- **FastAPI**: app/main.py (CORS, lifespan, 6개 라우터)
- **MongoDB**: OptimizedMongoDBManager (Connection pooling, 비동기)
- **HospitalManager**: 104,836개 병원/약국/투석센터 로딩 완료
- **Parlant Agent**: healthcare_v2_en.py (1,860줄, 2 Journeys)
- **Profile System**: researcher/patient/general (자동 감지)

#### 데이터베이스 (60%)
- **hospitals 컬렉션**: ✅ 104,836 records
- **qa_kidney 컬렉션**: ✅ 3,993 documents
- **papers_kidney 컬렉션**: ✅ 1,597 documents
- **medical_kidney 컬렉션**: ✅ 7,512 documents
- **users 컬렉션**: ✅ 사용자 관리
- **welfare_programs 컬렉션**: ❌ 0 documents (15개 필요)

#### Parlant 통합 (50%)
- **Journey 1**: ✅ Medical Information Journey (7 states)
- **Journey 2**: ✅ Research Paper Deep Dive (researchers)
- **Journey 7**: ❌ Welfare Support Journey (미구현)
- **Tools**: ✅ search_medical_qa, get_kidney_stage_info, get_symptom_info, check_emergency_keywords
- **Welfare Tools**: ❌ search_welfare_programs, search_hospitals (미구현)

### ❌ 미구현 복지 기능

#### 데이터 레이어
- [ ] `welfare_programs` MongoDB 컬렉션 (0/15 documents)
- [ ] 복지 데이터 로딩 스크립트 (`data/welfare/load_welfare_data.py`)

#### 백엔드 레이어
- [ ] `backend/app/db/welfare_manager.py` (WelfareManager 클래스)
- [ ] `backend/app/models/welfare.py` (Pydantic 모델)
- [ ] `backend/app/api/welfare.py` (REST API)

#### Parlant 레이어
- [ ] `search_welfare_programs` Tool (healthcare_v2_en.py)
- [ ] `search_hospitals` Tool (HospitalManager 활용)
- [ ] Journey 7: Welfare Support Journey
- [ ] Welfare 관련 Guidelines

#### 프론트엔드 레이어
- [ ] `frontend/src/api/welfareApi.ts` (API 클라이언트)
- [ ] `WelfareProgramList` 컴포넌트 (ChatPage 통합)
- [ ] WelfarePage (선택 사항)

#### 테스트 레이어
- [ ] `tests/` 디렉토리 전체 (현재 존재하지 않음)
- [ ] Unit tests (WelfareManager, MongoDB search)
- [ ] Integration tests (Journey, API)
- [ ] E2E tests (완전한 플로우)

---

## 🏗️ 아키텍처 개요

### 시스템 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                         사용자                               │
└────────────────────┬────────────────────────────────────────┘
                     │ "산정특례 신청 방법 알려주세요"
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (React)                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ChatPage.tsx                                         │  │
│  │  - SSE 스트리밍 (parlantClient.ts)                    │  │
│  │  - 메시지 렌더링                                      │  │
│  │  - WelfareProgramList 컴포넌트                        │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP Request (port 5173)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend - FastAPI (port 8000)                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  /api/chat/* Proxy                                    │  │
│  │  - Forward to Parlant server                          │  │
│  └─────────────────┬─────────────────────────────────────┘  │
│                    │                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  /api/welfare/* (Optional REST API)                  │   │
│  │  - GET /search                                        │   │
│  │  - GET /categories                                    │   │
│  │  - GET /stats                                         │   │
│  └─────────────────┬─────────────────────────────────────┘  │
└────────────────────┼────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│          Parlant Server - healthcare_v2_en.py (port 8800)    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Agent: CareGuide_v2                                  │  │
│  │  - 11 Guidelines (Safety, Profile, Blocking)          │  │
│  │  - 6 Tools (medical, welfare, hospital)               │  │
│  │  - 3 Journeys                                         │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Intent Classification                                │  │
│  │  - WELFARE_INFO 감지                                  │  │
│  │  - Journey 7 라우팅                                   │  │
│  └─────────────────┬─────────────────────────────────────┘  │
│                    │                                         │
│  ┌─────────────────▼─────────────────────────────────────┐  │
│  │  Journey 7: Welfare Support Journey                   │  │
│  │  Step 0: Welcome                                      │  │
│  │  Step 1: search_welfare_programs Tool ───────────┐    │  │
│  │  Step 2: Present results                         │    │  │
│  │  Step 3: search_hospitals Tool (optional) ───┐   │    │  │
│  │  Step 4: End or loop                         │   │    │  │
│  └──────────────────────────────────────────────┼───┼────┘  │
└─────────────────────────────────────────────────┼───┼───────┘
                                                  │   │
                     ┌────────────────────────────┘   │
                     │                                │
                     ▼                                ▼
┌──────────────────────────────────┐  ┌──────────────────────┐
│    WelfareManager                │  │   HospitalManager    │
│  - search_by_text()              │  │  - get_dialysis_     │
│  - search_by_category()          │  │    centers()         │
│  - search_by_disease()           │  │  - search_by_region()│
│  - get_by_id()                   │  │  - search_nearby()   │
└────────────┬─────────────────────┘  └──────────┬───────────┘
             │                                    │
             ▼                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                MongoDB (careguide database)                  │
│  ┌───────────────────────────┐  ┌─────────────────────────┐ │
│  │  welfare_programs         │  │  hospitals              │ │
│  │  - 15 documents           │  │  - 104,836 documents    │ │
│  │  - Text search index      │  │  - Geospatial index     │ │
│  └───────────────────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 구현 범위

### Phase 1: 데이터 레이어 (4시간)
📄 **문서**: `01_WELFARE_DATABASE_DESIGN.md`, `02_WELFARE_BACKEND_IMPLEMENTATION.md`

**작업**:
1. MongoDB `welfare_programs` 컬렉션 생성
2. 15개 복지 프로그램 데이터 작성 및 로딩
3. 텍스트 검색 인덱스 생성
4. WelfareManager 클래스 구현 (5개 검색 메서드)

**파일**:
- `data/welfare/load_welfare_data.py` (신규)
- `backend/app/db/welfare_manager.py` (신규)
- `backend/app/models/welfare.py` (신규)

**패턴**: HospitalManager, OptimizedMongoDBManager

### Phase 2: Parlant 통합 (4시간)
📄 **문서**: `03_WELFARE_PARLANT_INTEGRATION.md`

**작업**:
1. `search_welfare_programs` Tool 구현
2. `search_hospitals` Tool 구현 (HospitalManager 활용)
3. Journey 7 (Welfare Support Journey) 구현
4. Welfare Guidelines 추가
5. main() 함수에 등록

**파일**:
- `backend/Agent/research_paper/server/healthcare_v2_en.py` (업데이트)

**패턴**: Journey 1 (Medical Information Journey)

### Phase 3: API & 테스트 (2시간)
📄 **문서**: `04_WELFARE_API_REFERENCE.md`, `05_WELFARE_TESTING_GUIDE.md`

**작업**:
1. REST API 엔드포인트 4개 구현
2. 프론트엔드 API 클라이언트 (welfareApi.ts)
3. ChatPage 복지 결과 렌더링
4. Unit/Integration/E2E 테스트

**파일**:
- `backend/app/api/welfare.py` (신규)
- `frontend/src/api/welfareApi.ts` (신규)
- `tests/` 전체 (신규)

**패턴**: community.py, trends.py, parlantClient.ts

---

## 📊 현재 상태 요약

### 기존 인프라 활용도

| 컴포넌트 | 상태 | 활용 방법 |
|----------|------|-----------|
| **HospitalManager** | ✅ 완료 (104,836 records) | `search_hospitals` Tool로 재사용 |
| **OptimizedMongoDBManager** | ✅ 완료 | WelfareManager 패턴 참고 |
| **Profile System** | ✅ 작동 중 | 복지 검색 결과도 프로필별 제한 |
| **Journey 패턴** | ✅ 2개 작동 | Journey 7에 동일 패턴 적용 |
| **Tool 패턴** | ✅ 4개 작동 | search_welfare_programs 동일 구조 |
| **REST API 패턴** | ✅ 5개 작동 | welfare.py에 적용 |

### 신규 구현 필요

| 컴포넌트 | 파일 | 예상 시간 | 우선순위 |
|----------|------|----------|---------|
| **복지 데이터** | data/welfare/load_welfare_data.py | 2시간 | P0 |
| **WelfareManager** | backend/app/db/welfare_manager.py | 2시간 | P0 |
| **복지 검색 Tool** | healthcare_v2_en.py | 1.5시간 | P0 |
| **병원 검색 Tool** | healthcare_v2_en.py | 30분 | P0 |
| **Journey 7** | healthcare_v2_en.py | 2시간 | P0 |
| **REST API** | backend/app/api/welfare.py | 1시간 | P1 |
| **프론트엔드** | frontend/src/api/welfareApi.ts | 30분 | P1 |
| **테스트** | tests/* | 2시간 | P1 |

**총 예상 시간**: **10시간**

---

## 🔄 데이터 흐름

### 시나리오: "산정특례 신청 방법 알려주세요"

```
1. 사용자 입력
   └─> "산정특례 신청 방법 알려주세요"

2. Frontend (ChatPage.tsx)
   └─> SSE 연결 (parlantClient.ts)
       └─> POST /api/chat/message

3. Backend (FastAPI)
   └─> Proxy to Parlant server (port 8800)

4. Parlant Server (healthcare_v2_en.py)
   └─> Intent Classification
       └─> WELFARE_INFO 감지 (keywords: 산정특례, 신청, 방법)
           └─> Journey 7: Welfare Support Journey 시작

5. Journey Step 0: Welcome
   └─> "복지 지원 상담에 오신 것을 환영합니다..."

6. Journey Step 1: Tool Execution
   └─> search_welfare_programs(query="산정특례")
       └─> WelfareManager.search_by_text("산정특례", limit=5)
           └─> MongoDB welfare_programs collection
               └─> Text search with scoring
                   └─> Results: [V001, V003]

7. Tool Result
   └─> ToolResult(data={
         "results": [
           {"title": "만성콩팥병 산정특례 (V001)", ...},
           {"title": "혈액투석 산정특례 (V003)", ...}
         ],
         "synthesis_prompt": "Based on user query..."
       })

8. Journey Step 2: Present Results
   └─> LLM (Claude 3.5 Sonnet) synthesizes response
       └─> "산정특례는 다음과 같습니다. 1. V001: 본인부담금 10%..."

9. SSE Streaming
   └─> Events: message, tool, status
       └─> Frontend receives

10. ChatPage Rendering
    └─> Message bubble (assistant)
    └─> WelfareProgramList component (2 programs)

11. Journey Step 3: Follow-up
    └─> "다른 복지 프로그램 알아보기? 근처 병원 찾기?"
```

---

## 🎯 성공 기준

### 기술적 지표

| 지표 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|
| **복지 데이터** | 0개 | 15개 | `db.welfare_programs.count_documents({})` |
| **API 응답 시간** | N/A | <500ms | 로그 `response_time` |
| **Tool 실행 시간** | N/A | <2s | ToolResult metadata |
| **검색 정확도** | N/A | >80% | 사용자 피드백 |
| **의도 분류** | N/A | >90% | WELFARE_INFO 테스트 |
| **Journey 완료율** | N/A | >80% | END_JOURNEY 도달 비율 |

### 기능 체크리스트

**필수 (P0)**:
- [ ] 15개 복지 프로그램 MongoDB 로딩
- [ ] WelfareManager 5개 메서드 작동
- [ ] search_welfare_programs Tool 작동
- [ ] search_hospitals Tool 작동
- [ ] Journey 7 등록 및 작동
- [ ] WELFARE_INFO → Journey 7 라우팅

**선택 (P1)**:
- [ ] REST API 4개 엔드포인트
- [ ] 프론트엔드 welfareApi.ts
- [ ] WelfareProgramList 렌더링
- [ ] Unit tests >90% 통과

---

## 📅 구현 일정

### Week 1: 데이터 + Parlant 통합 (8시간)

**Day 1** (4시간):
- ✅ 복지 데이터 작성 (15개 프로그램) - 2시간
  - 📄 참고: `01_WELFARE_DATABASE_DESIGN.md`
- ✅ data/welfare/load_welfare_data.py 작성 및 실행 - 30분
- ✅ WelfareManager 구현 (5개 메서드) - 1.5시간
  - 📄 참고: `02_WELFARE_BACKEND_IMPLEMENTATION.md`

**Day 2** (4시간):
- ✅ search_welfare_programs Tool 구현 - 1.5시간
  - 📄 참고: `03_WELFARE_PARLANT_INTEGRATION.md`
- ✅ search_hospitals Tool 구현 - 30분
- ✅ Journey 7 구현 및 등록 - 2시간

### Week 2: API + 테스트 (2시간)

**Day 3** (2시간):
- ✅ REST API 구현 (welfare.py) - 1시간
  - 📄 참고: `04_WELFARE_API_REFERENCE.md`
- ✅ 프론트엔드 통합 (welfareApi.ts) - 30분
- ✅ 통합 테스트 - 30분
  - 📄 참고: `05_WELFARE_TESTING_GUIDE.md`

**총 시간**: **10시간** (2-3일)

---

## 🔗 연관 문서

### 프로젝트 전체 문서
- `EXECUTION_STATUS.md` - 전체 프로젝트 실행 현황
- `AI_CHAT_KNOWLEDGE_TRENDS_TODO.md` - jh 담당 영역 To-Do
- `IMPLEMENTATION_AND_TEST_PLAN.md` - 구현 및 테스트 계획

### 코드베이스 참고
- `backend/app/db/hospital_manager.py` - WelfareManager 패턴
- `backend/app/db/mongodb_manager.py` - MongoDB 연결 패턴
- `backend/Agent/research_paper/server/healthcare_v2_en.py` - Tool/Journey 패턴
- `backend/app/api/community.py` - REST API 패턴
- `frontend/src/pages/chat/ChatPage.tsx` - 프론트엔드 통합

### 설계 문서
- `docs/journey.md` - Journey 설계 가이드 (50KB)
- `docs/chat.md` - Intent classification
- `docs/community.md` - Gamification

---

## 🚀 시작하기

### 1단계: 문서 읽기 순서
1. **00_WELFARE_OVERVIEW.md** (이 문서) - 전체 개요
2. **01_WELFARE_DATABASE_DESIGN.md** - 데이터 스키마 이해
3. **02_WELFARE_BACKEND_IMPLEMENTATION.md** - WelfareManager 구현
4. **03_WELFARE_PARLANT_INTEGRATION.md** - Parlant Tools & Journey
5. **04_WELFARE_API_REFERENCE.md** - REST API (선택)
6. **05_WELFARE_TESTING_GUIDE.md** - 테스트 실행
7. **06_WELFARE_DEPLOYMENT.md** - 배포 가이드

### 2단계: 구현 시작
```bash
# 1. 복지 데이터 로딩
cd data/welfare
python load_welfare_data.py

# 2. WelfareManager 테스트
cd backend
python -m app.db.welfare_manager

# 3. Parlant 서버 재시작
cd backend
python Agent/research_paper/server/healthcare_v2_en.py

# 4. 테스트 실행
cd tests
pytest -v
```

### 3단계: 검증
```bash
# MongoDB 확인
mongosh careguide --eval "db.welfare_programs.count()"
# Expected: 15

# API 테스트
curl http://localhost:8000/api/welfare/stats
# Expected: {"total": 15, "by_category": {...}}

# Parlant 테스트
# 프론트엔드에서 "산정특례 신청 방법 알려주세요" 입력
```

---

## 📝 작성 가이드

### 각 문서의 역할

| 문서 | 크기 | 목적 | 대상 독자 |
|------|------|------|----------|
| **00_OVERVIEW** | ~300줄 | 전체 개요, 로드맵 | 모든 개발자 |
| **01_DATABASE** | ~500줄 | 스키마, 인덱스, 데이터 | Backend 개발자 |
| **02_BACKEND** | ~600줄 | WelfareManager 구현 | Backend 개발자 |
| **03_PARLANT** | ~800줄 | Tools, Journey 7 구현 | AI/Parlant 개발자 |
| **04_API** | ~400줄 | REST API 명세 | Backend/Frontend 개발자 |
| **05_TESTING** | ~500줄 | 테스트 작성 및 실행 | QA/개발자 |
| **06_DEPLOYMENT** | ~300줄 | 배포, 모니터링 | DevOps/운영 |

### 코드 작성 원칙

1. **기존 패턴 준수**: 새로운 패턴 만들지 말고 기존 코드 참고
2. **비동기 우선**: async/await 사용
3. **타입 힌트**: 모든 함수에 타입 명시
4. **에러 핸들링**: try-except + logging
5. **문서화**: Docstring 필수

---

## ⚠️ 주의사항

### 1. MongoDB Connection
- URI는 환경변수에서 가져오기 (`MONGODB_URI`)
- Connection pooling 반드시 설정 (maxPoolSize=100)
- 비동기 Motor 사용 (PyMongo는 동기)

### 2. Parlant 통합
- Tool은 반드시 `@p.tool` 데코레이터
- ToolResult 반환 필수
- Journey는 main()에서 등록
- Guidelines는 Journey별로 추가 가능

### 3. 프로필 시스템
- researcher: 10 results, academic tone
- patient: 5 results, practical advice
- general: 3 results, simple language

### 4. 캐싱 전략
- 통계는 캐싱 (TTL 1시간)
- 검색 결과는 캐싱하지 않음 (실시간성 중요)

---

## 🎉 예상 결과

### 구현 완료 후 사용 예시

**사용자**: "산정특례 신청하려면 어떻게 해야 하나요?"

**CareGuide 응답**:
```
산정특례는 희귀난치성질환 환자의 본인부담금을 대폭 감면해주는 제도입니다.

💳 **만성콩팥병 산정특례 (V001)**
- 본인부담금: 10% (90% 감면)
- 대상: CKD 3기 이상, eGFR 60 미만
- 유효기간: 5년

💳 **혈액투석 산정특례 (V003)**
- 본인부담금: 5% (95% 감면)
- 대상: 정기 혈액투석 환자
- 유효기간: 투석 중단 시까지

📋 **신청 방법**:
1. 병원에서 진단서 발급 받기
2. 국민건강보험공단 지사 또는 병원 원무과 방문
3. 신청서 및 서류 제출
4. 7-14일 후 승인 통보

📄 **필요 서류**:
- 산정특례 등록 신청서
- 의사 진단서 (희귀난치성질환 등록 신청용)
- 검사결과지 (eGFR, 크레아티닌)
- 신분증

📞 **문의**: 1577-1000 (국민건강보험공단)
🌐 **웹사이트**: https://www.nhis.or.kr

---

추가로 궁금하신 사항이 있으신가요?
- 다른 복지 프로그램 알아보기
- 근처 신청 가능한 병원 찾기
- 상담 종료
```

**사용자**: "근처 병원 찾아줘"

**CareGuide 응답**:
```
근처 투석 및 산정특례 신청 가능한 병원을 찾았습니다:

🏥 **서울대학교병원**
- 주소: 서울특별시 종로구 대학로 101
- 전화: 02-2072-2114
- 투석기: 20대
- 야간투석: 가능
- [네이버 지도](url) | [카카오맵](url)

🏥 **삼성서울병원**
- 주소: 서울특별시 강남구 일원로 81
- 전화: 02-3410-2114
- 투석기: 25대
- 야간투석: 가능
- [네이버 지도](url) | [카카오맵](url)

산정특례 신청은 위 병원 원무과에서 가능합니다.
진단서는 신장내과에서 발급받으시면 됩니다.
```

---

## 🛠️ 개발 환경 설정

### 필수 패키지

**Backend**:
```bash
pip install motor pymongo python-dotenv
```

**Frontend**:
```bash
npm install axios
```

**Testing**:
```bash
pip install pytest pytest-asyncio httpx
```

### VS Code 설정 (권장)

```json
{
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "editor.formatOnSave": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

---

## 🔍 FAQ

### Q1: 왜 별도의 WelfareManager가 필요한가요?
**A**: 복지 데이터는 의료 데이터와 구조가 다릅니다:
- 의료 데이터: 논문, QA, 가이드라인 (학술적)
- 복지 데이터: 제도, 신청 방법, 연락처 (행정적)

분리하면 각각의 검색 로직을 최적화할 수 있습니다.

### Q2: HospitalManager는 어떻게 활용하나요?
**A**: `search_hospitals` Tool로 래핑하여 사용:
- 복지 프로그램 검색 후 → 신청 가능한 근처 병원 찾기
- 투석 가능 병원 → 교통비 지원 안내 연계

### Q3: Journey 7이 꼭 필요한가요? Tool만으로는 안되나요?
**A**: Journey의 장점:
- **대화 흐름 관리**: 다단계 질문 처리
- **Context 유지**: 이전 대화 기억
- **Fork 기반 선택**: 사용자 의도에 따라 분기
- **Guideline 적용**: Journey별 안전 규칙

Tool만 있으면 단발성 검색만 가능합니다.

### Q4: 테스트는 꼭 해야 하나요?
**A**: 의료/복지 정보는 정확성이 생명입니다:
- False Negative: 응급 상황 놓치면 안됨
- False Positive: 잘못된 복지 정보 제공 시 신뢰 손실
- Regression: 기존 기능 깨지면 안됨

최소한 Unit tests는 필수입니다.

---

## 📞 도움이 필요하면

### 개발 관련
- **Backend**: `backend/app/db/welfare_manager.py:1` - WelfareManager 클래스
- **Parlant**: `backend/Agent/research_paper/server/healthcare_v2_en.py:1060` - Tools
- **API**: `backend/app/api/welfare.py:1` - REST endpoints

### 문서 관련
- **데이터 스키마**: `docs/welfare/01_WELFARE_DATABASE_DESIGN.md`
- **구현 가이드**: `docs/welfare/02_WELFARE_BACKEND_IMPLEMENTATION.md`
- **Parlant 통합**: `docs/welfare/03_WELFARE_PARLANT_INTEGRATION.md`

### 이슈 트래킹
- GitHub Issues (해당 시)
- TODO 주석 검색: `grep -r "TODO.*welfare" backend/`

---

## ✅ Next Steps

1. **데이터베이스 설계 읽기**: `01_WELFARE_DATABASE_DESIGN.md`
2. **복지 데이터 작성**: 15개 프로그램 정의
3. **WelfareManager 구현**: `02_WELFARE_BACKEND_IMPLEMENTATION.md`
4. **Parlant 통합**: `03_WELFARE_PARLANT_INTEGRATION.md`

---

**END OF OVERVIEW**

각 개별 문서로 이동하여 상세 구현을 진행하세요.
질문이 있으면 각 문서 하단의 FAQ를 참조하거나 팀에 문의하세요.

**Happy Coding! 🚀**
