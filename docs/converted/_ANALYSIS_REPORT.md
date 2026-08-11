# CareGuide Ground Truth Specification Analysis Report

**Generated**: 2026-05-23  
**Source authority**: PRD v0.95 (2025-11-24) + Requirements v0.96 (2025-11-12)  
**Purpose**: 이후 모든 구현이 최신 문서(spec)에 부합하도록 하기 위한 종합 분석

---

## 1. Document Conversion Status

| 파일 | 대상 경로 | 변환 결과 | 비고 |
|------|-----------|-----------|------|
| `CareGuide_PRD_Update_v0.95_251124.docx` | `docs/converted/PRD_v0.95_251124.md` | ✅ 변환 성공 (139줄) | **최신 PRD** |
| `CareGuide_요구사항_기능정의서_v0.96_251112.xlsx` | `docs/converted/Requirements_v0.96.md` | ✅ 변환 성공 (2441줄) | **최신 요구사항**; 다중 시트 포함 |
| `Copy of Copy of CareGuide_PRD_Update_v0.94_251112.docx` | `docs/converted/PRD_v0.94.md` | ✅ 변환 성공 (128줄) | 이전 버전 참고용 |
| `CareGuide_요구사항_기능정의서_v0.95_251112.xlsx` | `docs/converted/Requirements_v0.95.md` | ✅ 변환 성공 (2405줄) | v0.96과 시트 구조 동일; REQ 항목 내용 동일 |
| `CareGuide_지식검색_흐름도.docx` | `docs/converted/Knowledge_Search_Flow.md` | ✅ 변환 성공 (53줄) | 이미지 base64 포함(일부 노이즈); 텍스트 흐름은 추출됨 |
| `CareGuide_UserScenarios_261029.pptx` | `docs/converted/UserScenarios.md` | ✅ 변환 성공 (311줄) | 이미지 placeholder 다수 포함; 텍스트 슬라이드는 정상 |
| `KidneyWise_기술명세서.docx` | `docs/converted/KidneyWise_TechSpec.md` | ✅ 변환 성공 (1537줄) | 상세 기술 명세 |
| `환자_Journey Map_251026.pptx` | `docs/converted/Patient_JourneyMap.md` | ✅ 변환 성공 (205줄) | 일부 이미지 placeholder; 여정 5단계 텍스트 추출됨 |
| `Parlant 프레임워크 완전 가이드.pptx` | `docs/converted/Parlant_Guide.md` | ✅ 변환 성공 (1177줄) | |
| `[커널아카데미] AI 심화 캠프 1기_바이오팀_Careguide(1).pptx` | `docs/converted/Final_Presentation.md` | ✅ 변환 성공 (457줄) | 이미지 placeholder 포함 |

**결과 요약**: 10/10 변환 성공. 노이즈: PPTX 파일들은 이미지 placeholder(`Image0.jpg`, `Image1.jpg` 등)와 rasterized 임시파일 참조가 남아 있음. 내용 파악에는 영향 없음.

---

## 2. Authoritative Spec Summary (v0.95 PRD + v0.96 Requirements)

### 2.1 제품 비전 / 핵심 가치 제안

**제품 정의**: 만성콩팥병(CKD) 환자 및 관련 이해관계자를 위한 종합 지식 케어 플랫폼.

**핵심 가치 제안** (PRD v0.95 §1.1):
- **3가지 페르소나 지원**: 일반인(노비스), 질환자(경험자), 연구자/의료진
- **PubMed RAG 연동**: 최신 PubMed 논문 검색 · 요약 · 관련 정보 제공
- **의도분류 기반 대화**: AI 정책 적용, 카테고리별 정교한 맞춤 응대
- **False Negative 방지**: 의료 안전성 최우선 설계

### 2.2 대상 사용자 (페르소나)

| 페르소나 | 특징 | 주요 니즈 | 주요 기능 |
|----------|------|-----------|-----------|
| 일반인 / 노비스 | 진단 전 일반인, 간병인 | 예방 정보, 기초 의학 지식, 식단 관리법 | AI 챗봇 기본 대화, NutriCoach 레시피 검색, 커뮤니티 질문 |
| 질환자 / 경험자 | CKD 진단 환자, 이식 후 관리 | Stage별 식단·영양 관리, 증상 대처, 복지 정보 | 프로필 등록, NutriCoach, 학습 퀴즈 |
| 연구자 / 의료진 | CKD 연구·임상 종사자 | 최신 논문 검색, 메타분석, 환자 데이터 트렌드 | PubMed RAG, 논문 북마크, 연구자 대시보드, 커뮤니티 설문 생성 |

### 2.3 인-스코프(In-scope) 기능 목록 (v0.96 기준)

#### P0 (MVP 필수)
- **공통/유틸리티**: Header, Sidebar, Footer, 알림, 에러 메시지 (UTI-001~005)
- **회원관리**: 사용자 유형 선택(일반인/질환자/연구자), 로그인 안내, 세션 만료 처리 (MEM-004, 009, 010)
- **AI 챗봇 공통**: 자연어+PDF 입력 (이미지 불가), 의도분류, 대화 정책 필터, 멀티턴 대화, 질환 대화 관리, 신뢰도 정책, 안전성 정책(Confidence Score), 면책조항 UI, 새 대화 시작 (CHA-001~011, REQ-016~026)
- **지식검색(Knowledge Search)**: PubMed 검색·파싱·RAG 요약·북마크·다중 논문 비교·검색 횟수 제한(10회/일)·연구 트렌드 시각화·시계열 대시보드 (KNO-001~008)

#### P1 (MVP 부가)
- **회원관리**: 회원가입, 로그인, 비밀번호 재설정, 프로필 관리, 환자군 프로필, 약관 (MEM-001~007)
- **NutriCoach**: 식단/영양 검색(질환단계별 위험도), 대체 식재료 추천, 대체 레시피 추천, 질환 식단 요약(PDF RAG), 관련 QnA 생성 (NUT-001~005)
- **퀴즈**: 초기 1분 퀴즈 레벨 설정, 레벨별 RAG 퀴즈 생성, 게미피케이션(포인트 적립/전환) (QUI-006~009)
- **마이페이지**: 레벨·포인트 조회, 프리미엄 구매, 결제 관리, 푸시 알림, 논문 북마크 관리 (MYP-001~006)

#### P2 (선택 / 비필수)
- **커뮤니티**: 게시판 CRUD, 설문조사(연구자 전용), CSV 다운로드, 챌린지, 댓글·좋아요, 이미지 업로드 (COM-001~016)
- **회원관리 추가**: 회원탈퇴, 세션 만료 (MEM-008~009)
- **마이페이지 추가**: 알림 히스토리, 상세 결제 관리 (MYP-001~006)

#### P1/검증
- **테스트/품질**: API 단위 테스트(커버리지 리포트), 의도분류 정확도 90%+, 시나리오 테스트 (TES-001~003)

### 2.4 비기능 요구사항 (NFR)

| 항목 | 요구사항 |
|------|----------|
| 의료 안전 | False Negative 방지 — 응급 키워드(흉통, 호흡곤란, 의식저하, 경련) → 즉시 119 안내. 증상 보고 시 "괜찮습니다/정상입니다" 응답 절대 금지 |
| AI 신뢰도 | Confidence Score < 0.7 → "전문의 상담 권장" 메시지 표시 |
| 개인정보 | 대한민국 개인정보보호법·정보통신망법·의료법·2024~2025 개정안 준수. 주민번호·전화번호·주소·얼굴사진·금융정보 자동 마스킹·차단 |
| 민감정보 처리 | 텍스트: 부분 마스킹. 이미지: 얼굴 감지 시 전체 거부. 파일: OCR → 민감정보 포함 시 업로드 전체 거부 |
| 멀티턴 | 최근 5턴 컨텍스트 유지 |
| 세션 | JWT Access Token 1시간, Refresh Token 7일. 비로그인 시 GUID 기반 캐시 세션(20분 이후 재접속 시 복원) |
| 의도분류 정확도 | 90% 이상 목표 (REQ-056) |
| 파일 업로드 | 챗봇 공통: PDF만 허용 5MB 이하 / Nutrition 에이전트: 추가로 png/jpg/svg 허용 (정책서 기준) |

### 2.5 성공 지표 / KPIs

PRD v0.95에는 명시적 KPI 섹션("6. 성공 지표")이 **없음**(섹션 번호가 5→7로 건너뜀). Requirements 정책서 시트에서 추출 가능한 품질 지표:
- 의도분류 정확도 ≥ 90% (REQ-056)
- API 테스트 커버리지 리포트 (REQ-055)
- 시나리오 테스트 성공/실패 리포트 (REQ-057)

### 2.6 기술 스택 지정 (tech-spec.md + 정책서)

| 영역 | 기술 |
|------|------|
| Backend | Python 3.10+, FastAPI |
| DB | MongoDB (일반 데이터), MongoDB Atlas Vector Search (논문 임베딩, 1536차원, cosine) |
| AI/ML | OpenAI API (GPT-3.5-turbo / text-embedding-3-small), **Parlant SDK** (에이전트 오케스트레이션) |
| Frontend | React 18, TypeScript, Tailwind CSS, Vite |
| 상태관리 | React Context API |
| HTTP 클라이언트 | Axios |
| 벡터 DB | Pinecone (PubMed 초록 임베딩) / MongoDB Atlas Vector Search |

---

## 3. Domain Glossary (Korean ↔ English)

| 한국어 | English | 정의 |
|--------|---------|------|
| 만성콩팥병 (CKD) | Chronic Kidney Disease | eGFR 기준 1~5단계로 분류되는 만성 신장 질환 |
| 질환자 / 경험자 | Patient / Experienced | CKD 진단 후 환자, 이식 후 관리 환자 포함 |
| 일반인 / 노비스 | General / Novice | 진단 전 일반인 또는 간병인 |
| 연구자 | Researcher | CKD 의학·영양학 연구자, 의료진 |
| 환우 | Patient peer | 같은 질환을 가진 동료 환자. 커뮤니티에서 경험 공유 주체 |
| 산정특례 | Special Medical Cost Exemption | 중증질환(말기신부전 등) 환자 의료비 본인부담률 경감 제도 (건강보험 급여 적용) |
| 식단케어 (Diet Care) | Diet Care | 식이영양 관리 기능 영역. NutriCoach + 식단 로그 포함 |
| 뉴트리코치 (NutriCoach) | NutriCoach | 질환 단계별 식재료·레시피 위험도 분석 및 대체재 추천 기능 |
| 식단 로그 (Diet Log) | Diet Log | 아침/점심/저녁/간식 식사 정보 등록 및 조회 |
| 복지 에이전트 (Welfare Agent) | Welfare Agent | 복지 혜택·지원금·보험 정보를 제공하는 AI 에이전트 (Medical_Welfare agent) |
| 지식검색 (Knowledge Search) | Knowledge Search | PubMed API 기반 논문 검색 + RAG 분석 기능 |
| 의도분류 | Intent Classification | 사용자 발화를 MEDICAL_INFO·DIET_INFO·RESEARCH 등 10개 카테고리로 분류 |
| False Negative 방지 | False Negative Prevention | 위험 증상을 "괜찮다"고 잘못 답변하는 오류를 원천 차단하는 안전 정책 |
| 멀티턴 대화 | Multi-turn Conversation | 최근 5턴의 대화 히스토리를 컨텍스트로 유지하는 연속 대화 |
| RAG | Retrieval-Augmented Generation | 검색 기반 생성 — 벡터 DB 검색 후 LLM에 컨텍스트 주입 |
| eGFR | Estimated Glomerular Filtration Rate | 추정 사구체 여과율; CKD 단계 분류의 핵심 수치 |
| 크레아티닌 (Cr) | Creatinine | 신장 기능 지표 혈액 수치 |
| 투석 | Dialysis | 신장 기능 대체 치료. 혈액투석(HD)과 복막투석(PD) 구분 |
| 혈액투석 (HD) | Hemodialysis | 혈액을 기계에 통과시켜 노폐물 제거. 칼륨·인·나트륨 제한 엄격 |
| 복막투석 (PD) | Peritoneal Dialysis | 복강 내 투석액을 이용한 투석. 감염 위험 있음 |
| 이식환자 (CKD_T) | Transplant Patient | 신장 이식 후 면역억제제 복용하며 관리 필요 환자 |
| 당뇨성 신장병 (DKD-C) | Diabetic Kidney Disease | 당뇨병 합병증으로 발생한 신장병 |
| 급성신손상 (AKI) | Acute Kidney Injury | 일시적 신장 기능 저하; 회복 모니터링 필요 |
| 게미피케이션 | Gamification | 포인트 적립·레벨업·뱃지 등 게임 요소를 통한 사용자 동기 부여 |
| 대화 정책 필터 | Conversation Policy Filter | 비의료 도메인(NON_MEDICAL) 및 비윤리(NON_ETHICAL) 요청 차단 |
| Confidence Score | Confidence Score | LLM 응답의 신뢰도 점수. 0.7 미만 시 전문의 상담 권장 메시지 추가 |
| 면책조항 (Disclaimer) | Disclaimer | "본 답변은 진단이 아니며 참고용" 고정 배너 |
| 에이전트 매니저 | Agent Manager | Medical_Welfare·Nutrition·Research_Paper·Quiz 에이전트를 오케스트레이션하는 중앙 관리자 |
| 세션키 | Session Key | FE에서 생성하는 UUID; 컨텍스트(disease_stage, profile_type, 관심 키워드) 저장 단위 |
| 환자군 분류체계 | Patient Classification System | CKD1~5, DKD-C, CKD_T, AKI, PD, HD 코드로 분류하는 질환 분류 스키마 |
| 산정특례 | Special Cost Exemption | 말기신부전 등록 시 의료비 본인부담 경감 |
| 포인트 | Points | 퀴즈(+10P)·커뮤니티 활동(+5P)·설문 참여(+20P)·출석(+3P)으로 적립 |
| 토큰 | Token | 100P = 100토큰으로 전환; 프리미엄 기능(추가 논문 검색 등)에 사용 |

---

## 4. User Journey & Knowledge Search Flow

### 4.1 환자 여정도 (Patient Journey Map — 5단계)

출처: `docs/converted/Patient_JourneyMap.md` + `UserScenarios.md`

| 단계 | 터치포인트 | Pain Point | 플랫폼 대응 기능 |
|------|-----------|-----------|-----------------|
| **1. 진단받기** | 병원 | 혈액검사 수치만 나옴. eGFR 생략 → 직접 계산해야 함 | AI 챗봇 수치 해석, 용어 사전 |
| **2. 정보 탐색** | 유튜브·ChatGPT | 신뢰성 불확실. 새 용어 → 검색 무한 루프 | 공신력 의료 정보(질병청/식약처/복지부/신장학회) RAG |
| **3. 검사 이해** | 병원 앱 | 병원마다 다른 수치 기준, 환자가 다 기억해야 함 | 프로필 검진 수치 등록·자동 계산 |
| **4. 일상 관리** | 식당·약국 | 메뉴 선택 시 검색, 약 상호작용 확인, 증상 판단 어려움 | NutriCoach 위험도 분석, False Negative 방지 챗봇 |
| **5. 복지 탐색** | 온라인 | 병원에서 안 알려줌. 정보 부족으로 못 받음. 지역별로 다름 | 복지 에이전트(Medical_Welfare) — 지역별 혜택·신청법 |

### 4.2 지식 검색 흐름도

출처: `docs/converted/Knowledge_Search_Flow.md`

```
사용자 접속 → 로그인 여부 확인(쿠키/캐시)
    ↓ (비로그인 또는 로그인)
사용자 유형 선택: 일반인 / 질환자 / 연구자
    ↓
발화 내용 분석
  → '연구/논문' 유사 질의 포함 여부 판단 OR 질의 전문성 난이도 ≥ 0.7
    ↓
[분기 1: 일반인]
  - '연구/논문' 질의: NO → PubMed 미조회, 논문 답변 금지 → 주 답변만
  - '연구/논문' 질의: YES → PubMed 조회 → 논문 답변 포함

[분기 2: 질환자]
  - '연구/논문' 질의: NO → PubMed 미조회 → 주 답변 + 하단 최신 논문 추천 버블
  - '연구/논문' 질의: YES → PubMed 조회 → 논문 답변 포함

[분기 3: 연구자]
  - 항상 PubMed 논문 답변 포함

프론트엔드: 유형별 답변/추천 UI → END
```

### 4.3 에이전트 오케스트레이션 흐름 (정책서 기준)

```
/chat 진입 → Agent Manager 활성화
  ├── Medical_Welfare agent: 의료/질환/복지/병원 관련 (텍스트 입력만)
  ├── Nutrition agent: 식단/레시피 (텍스트 + 이미지 png/jpg/svg)
  └── Research_Paper agent: 논문/연구 (텍스트 입력만)

/quiz 진입 → Quiz agent 단독 운영 (RAG 기반 문제 생성)

복합 Intent → 병렬 호출 후 응답 병합 → 단일 응답으로 FE 전달
컨텍스트 공유: session_key(UUID), user_type, profile_type, disease_stage, 관심 키워드
```

---

## 5. Code-vs-Spec Gap Analysis

아래는 v0.95 PRD / v0.96 Requirements 기준으로 현재 코드 구현 상태를 분석한 것입니다.

| 기능 | Spec 요구사항 | 구현 상태 | 비고 |
|------|--------------|-----------|------|
| **식단케어 (Diet Care)** | `/diet-care` → NutriCoach + 식단 로그 (`/diet-log`, `/add-food`, `/diet-log-detail`) | ⚠️ | `diet_care.py` 라우터 있음. 프론트 `DietCarePageEnhanced.tsx` 있음. 식단 로그(`/diet-log`) 분리 구현 여부 확인 필요. `diet.py`는 deprecated 처리됨 |
| **NutriCoach 위험도 계산** | 질환단계 목표치(Na/K/P/단백질) 대비 위험도: 안전/주의/위험 | ⚠️ | `nutrition.py` 라우터, nutrition agent 존재. 영양 분석 API(`analyzeNutrition`) 프론트엔드 연동됨. 질환단계 목표치 연산 완성도 불명확 |
| **NutriCoach 이미지 분석** | Nutrition agent에서만 png/jpg/svg 허용 (정책서). CHA-001(REQ-016)에선 이미지 불가라고 명시 — **내부 모순** | ⚠️ | `ChatPageEnhanced.tsx`에서 `analyzeNutrition` 호출 시 이미지 지원. 정책서 기준으로는 Nutrition agent만 허용이 맞음. REQ-016과 충돌 상태 |
| **AI 챗봇 / 지식검색** | 3개 에이전트(Medical_Welfare, Nutrition, Research_Paper) + Agent Manager, Parlant 기반 | ✅ | `agent_manager.py`, 각 에이전트 디렉터리 존재. Parlant SDK 연동. `careguide.py`에서 통합 라우팅 |
| **PubMed 검색 및 RAG** | KNO-001~003: 키워드 검색, 메타데이터 파싱, RAG 요약 | ✅ | Research Paper agent + PubMed API 연동 구현됨 |
| **논문 북마크** | KNO-004: 마이페이지에서 PMID 저장 목록 조회 | ✅ | `bookmarks.py` 라우터, `bookmarkApi.ts` 서비스 모두 존재 |
| **다중 논문 비교** | KNO-005: 여러 논문 체크박스 선택 → 비교 테이블 | ❌ | 프론트엔드에 별도 구현 흔적 미확인 |
| **논문 검색 10회 제한** | KNO-006: 1일 10회 초과 시 포인트 100P 또는 프리미엄 안내 | ❌ | 검색 횟수 제한 로직 미구현 확인 필요 |
| **연구 트렌드 시각화** | KNO-007: 최근 5년 연도별 막대 그래프 | ⚠️ | `trends.py` 라우터, `TrendsPageEnhanced.tsx` 존재. 구체적 PubMed 연도별 집계 구현 여부 불명확 |
| **시계열 대시보드** | KNO-008: 월별/연도별 라인 차트, 기간 선택 | ⚠️ | Trends 페이지에 포함 가능성 있음; 상세 확인 필요 |
| **복지 에이전트** | Medical_Welfare agent: 복지 혜택/지원금/보험 정보 제공 | ✅ | `backend/Agent/medical_welfare/` 디렉터리 + agent.py, prompts.py 존재. Parlant WelfareGuide 에이전트 계획 문서화됨 |
| **트렌드 / 뉴스** | `/trends` → 뉴스 스크래핑('신장병' 키워드) + 대시보드 | ⚠️ | `news.py` 라우터 존재. `TrendsPageEnhanced.tsx` 있음. 뉴스 스크래핑 실제 구현 여부 확인 필요 |
| **퀴즈** | 초기 1분 퀴즈 레벨 설정 + 챗봇 4회 후 OX 퀴즈 카드 + RAG 생성 + 포인트 | ⚠️ | `quiz.py` 라우터, `QuizPage.tsx`·`QuizListPage.tsx` 존재. Quiz agent 있음. `/quiz` 라우트 정의됨. RAG 퀴즈 생성 완성도 불명확 |
| **마이페이지** | 레벨/포인트 조회·히스토리, 북마크, 프리미엄 구매, 결제 관리, 알림 설정 | ⚠️ | `mypage.py`, `MyPageEnhanced.tsx` 존재. 프리미엄 결제(Stripe/토스페이먼츠) 미구현 가능성 |
| **커뮤니티** | 게시판 CRUD, 댓글, 좋아요, 설문(연구자), 챌린지, 이미지 업로드 | ✅ | `community.py` 라우터, `CommunityPageEnhanced.tsx`, `communityApi.ts` 모두 존재. COM-001~016 상세 명세 충족 수준으로 구현 |
| **영양 분석 (nutrition analysis)** | Nutrition agent 이미지 업로드 → 음식 분석 + 대체 식재료 추천 | ⚠️ | `dietCareApi.ts`의 `analyzeNutrition` 함수 + `ChatPageEnhanced.tsx` 연동됨. 내부적으로 multipart/form-data 처리. 완성도 확인 필요 |
| **임상시험 (Clinical Trials)** | v0.96 REQ 목록에 **임상시험 전용 REQ 항목 없음**. 연구자 페르소나 설명에만 "임상시험 진행" 언급 | 🔄 | `clinical_trials.py` 라우터(`/api/clinical-trials`)와 Router agent(`agent.py`) 실제 구현됨. Spec에 명시적 요구사항 없음 → **스펙 미반영 구현** |
| **회원가입 / 로그인** | JWT 기반, Access 1h/Refresh 7d, 이메일 인증, 사용자 유형 선택 | ✅ | `auth.py`, `SignupPage.tsx`, `LoginPageFull.tsx` 존재 |
| **의도분류** | 10개 카테고리(MEDICAL_INFO, DIET_INFO, RESEARCH, WELFARE_INFO, HEALTH_RECORD, LEARNING, POLICY, CHIT_CHAT, NON_MEDICAL, NON_ETHICAL) | ✅ | `intentRouter.ts`, Agent router 구현됨. 평가 스크립트(`eval/`)도 존재 |
| **False Negative 방지** | 응급 키워드 → 119 안내. 안심 답변 금지. Confidence < 0.7 → 전문의 권장 | ⚠️ | Parlant Journey에 CHK-001~009 안전 체크 정의됨. 실제 런타임 enforcement 확인 필요 |
| **식단 로그 (Diet Log)** | `/diet-log` — 식단 목표 등록, 아침/점심/저녁/간식 기록, 상세 보기/수정/삭제 | ⚠️ | `diet_care.py`에 포함 추정. `DietCarePageEnhanced.tsx` 내 구현 여부 별도 확인 필요 |
| **프로필 검진 기록** | `/test-results`, `/test-results/add`, `/test-results/edit` | ⚠️ | `HealthRecordsPage.tsx`, `user_health_records.py` 존재. Spec의 `/test-results` URI와 일치 여부 확인 필요 |
| **알림 시스템** | 퀴즈·커뮤니티 댓글·레벨업·챌린지 등 8종 알림, FCM/브라우저 알림 | ❌ | `notification.py` 라우터 존재하나 FCM 실제 연동 여부 불명확; MYP-005 상세 명세 대비 미완성 가능성 높음 |

**상태 범례**: ✅ 구현됨(스펙 부합) | ⚠️ 구현됨(완성도 불확실하거나 스펙 일부 미반영) | ❌ 미구현 | 🔄 스펙 변경/스펙 미포함 구현

---

## 6. Critical Findings (RED FLAGS)

### 🔴 RED FLAG #1 — 이미지 업로드 정책 내부 모순

**현상**: Requirements v0.96에서 **두 가지 상충되는 규칙**이 공존함:
- `REQ-016` (CHA-001) P0 필수: "이미지나 기타 파일 입력 불가" — 텍스트·PDF만 허용
- 정책서 시트: "Nutrition agent에서만 png/jpg/svg 허용"

**현재 코드**: `ChatPageEnhanced.tsx`에서 `analyzeNutrition` 호출 시 이미지를 Nutrition agent로 전송하고 있음 → 정책서 기준으로는 맞지만 REQ-016과 불일치.

**위험**: QA 테스트 시 REQ-016을 기준으로 삼으면 Nutrition 이미지 기능이 "버그"로 판정될 수 있음. **명확한 합의 필요**.

---

### 🔴 RED FLAG #2 — 임상시험(Clinical Trials) 기능이 스펙에 없음

**현상**: `backend/app/api/clinical_trials.py` (prefix `/api/clinical-trials`)와 `backend/Agent/router/agent.py` (임상시험 라우팅 포함)가 실제 구현되어 있음. 그러나 v0.96 Requirements의 57개 REQ 항목 어디에도 임상시험 전용 요구사항이 존재하지 않음. PRD v0.95 연구자 페르소나 설명에 "임상시험 진행"이라는 언급만 있을 뿐 기능 명세 없음.

**위험**: 
1. 유지보수 비용 증가 — 스펙 없는 기능은 테스트 기준이 없음
2. 임상시험 정보를 제공하는 것이 의료법상 허용 범위인지 검토되지 않음
3. 후속 스프린트에서 Clinical Trials API를 확장할 경우 스펙과의 갭이 커짐

---

### 🔴 RED FLAG #3 — PRD v0.95에 Section 6(성공 지표/KPIs)이 누락됨

**현상**: PRD v0.95의 목차가 1→2→3→4→5→**7**→8로 진행됨(Section 6 없음). 즉 **성공 지표·비즈니스 KPI가 공식 스펙에 정의되지 않음**. Requirements v0.96에도 KPI 전용 시트 없음.

**위험**: 개발 완료 후 "무엇이 성공인지" 판단 기준이 없어 데모·배포 시 평가 기준 혼선 발생 가능. 의도분류 정확도(90%)만 유일한 측정 가능 지표.

---

### 🔴 RED FLAG #4 — 프론트엔드 3중화 문제

**현상**: `frontend/`, `new_frontend/`, `stitch_frontend/` 세 개의 별도 프론트엔드 디렉터리가 존재함. 스펙(PRD, Requirements)에는 어느 것이 canonical frontend인지 명시 없음.

**위험**: 
- 동일 기능이 여러 곳에서 구현되어 유지보수 혼선
- `new_frontend/`가 현재 활성 개발 기준인 것으로 보이나(ChatPageEnhanced, CommunityPageEnhanced 등 Enhanced 시리즈) 공식 결정 부재
- `stitch_frontend/`는 별도 빌드 시스템(package.json)이 있어 실험적 UI로 보임

---

### 🔴 RED FLAG #5 — 논문 검색 10회 제한·포인트 전환 로직 미구현 가능성

**현상**: KNO-006(P0 필수)에서 "1일 10회 초과 시 포인트 100P 차감 또는 프리미엄 구매 안내"를 P0으로 요구. 그러나 백엔드 API 파일들에서 일일 검색 횟수를 Redis/DB로 추적하는 로직이 발견되지 않음.

**위험**: P0 필수 기능 미구현 시 MVP 기준 미달.

---

### 🔴 RED FLAG #6 — 다중 논문 비교(KNO-005) 미구현

**현상**: KNO-005(P0 필수) — 복수 논문 체크박스 선택 후 비교 테이블 생성. 프론트엔드(`new_frontend/src/pages/`, `services/`) 어디에서도 다중 선택·비교 UI 흔적이 발견되지 않음.

---

## 7. Recommended ADR Topics

다음 7개 주제는 명시적 아키텍처 결정 기록(ADR)이 필요합니다.

### ADR-001: Canonical Frontend — `new_frontend` vs `frontend` vs `stitch_frontend`

- **결정 필요 이유**: 세 개 FE가 공존. 어느 것이 배포 대상인지 확정되지 않음
- **선택지**: `new_frontend` 단일화(Enhanced 컴포넌트 시리즈 기준), 또는 `frontend`를 유지하며 `new_frontend`로 점진 마이그레이션

### ADR-002: Parlant SDK — Agent Orchestration 방식 확정

- **결정 필요 이유**: Parlant 서버(포트 8800)를 별도 프로세스로 운영 vs FastAPI 내부 통합. Journey JSON import 방식 vs 코드 직접 정의
- **관련 문서**: `docs/converted/Parlant_Guide.md`, `docs/IMPLEMENTATION_PLAN.md`

### ADR-003: 이미지 업로드 허용 범위 (REQ-016 vs 정책서 충돌 해소)

- **결정 필요 이유**: REQ-016(P0)은 이미지 불가, 정책서는 Nutrition agent만 png/jpg/svg 허용. 어느 것이 최종 기준인가
- **선택지**: (A) REQ-016 우선 → 모든 이미지 차단, (B) 정책서 우선 → Nutrition agent만 이미지 허용

### ADR-004: 임상시험(Clinical Trials) 기능 포함 여부

- **결정 필요 이유**: 구현은 됐으나 스펙에 없음. 유지·확장·제거 중 방향 결정 필요
- **법적 검토**: 임상시험 정보 제공의 의료법 준수 여부 확인 필요

### ADR-005: 벡터 DB 단일화 — Pinecone vs MongoDB Atlas Vector Search

- **결정 필요 이유**: tech-spec.md에서는 MongoDB Atlas Vector Search를 주로 언급. Requirements 정책서에서는 Pinecone을 명시. 두 시스템 혼용 또는 단일화 결정 필요
- **비용 영향**: Pinecone 사용 시 추가 과금 발생

### ADR-006: 포인트·결제 시스템 MVP 범위 결정

- **결정 필요 이유**: MYP-003(프리미엄 구매, 결제 API Stripe/토스페이먼츠)와 KNO-006(포인트로 추가 검색)이 P0~P1로 명시됨. 캠프/데모 환경에서 실제 결제 연동이 현실적인지 판단 필요
- **선택지**: Mock 결제 구현 vs 포인트 시뮬레이션 only

### ADR-007: 세션 관리 — Parlant 세션 vs FastAPI JWT 세션 통합 방식

- **결정 필요 이유**: 현재 `rooms.py`(Parlant 세션 사전 생성), `session.py`(세션 관리 API), JWT Auth가 별도로 존재. 비로그인 게스트의 GUID 기반 세션과 로그인 사용자 세션의 연속성 보장 방식이 명확하지 않음

---

## 8. Open Questions for User

### Q1. 이미지 업로드 정책: REQ-016과 정책서 중 어느 것이 최종 기준인가?

REQ-016(P0 필수, 기능정의서)은 "이미지 입력 불가"라고 명시하지만, 정책서 시트는 "Nutrition agent에서 png/jpg/svg 허용"이라고 명시합니다. 현재 코드는 정책서 방향으로 구현되어 있습니다.

→ **답변 필요**: Nutrition agent의 음식 이미지 분석 기능을 유지하는가? 유지한다면 REQ-016을 "Nutrition agent 제외"로 수정해야 합니다.

### Q2. 임상시험(Clinical Trials) 기능을 공식 스펙에 포함할 것인가?

현재 `/api/clinical-trials` 라우터와 관련 Agent가 구현되어 있지만 v0.96 요구사항서에 해당 REQ 항목이 존재하지 않습니다.

→ **답변 필요**: (A) 스펙에 REQ 항목 추가 및 유지, (B) 삭제, (C) P3 백로그로 이동.

### Q3. `new_frontend`가 유일한 배포 대상 프론트엔드인가?

`frontend/`, `new_frontend/`, `stitch_frontend/` 세 개가 존재합니다. 향후 배포는 어느 것을 기준으로 하나요?

→ **답변 필요**: canonical frontend 결정 + 나머지 디렉터리의 아카이브 또는 삭제 계획.

### Q4. KPI/성공 지표가 정의되지 않은 채 진행할 것인가?

PRD v0.95의 Section 6(성공 지표)이 없습니다. 데모·발표 시 어떤 기준으로 "완성"을 판단하나요?

→ **답변 필요**: 최소한 3~5개 측정 가능 KPI 정의(예: 의도분류 정확도 90%, 사용자 시나리오 테스트 3개 이상 통과, 응급 키워드 감지율 100% 등).

### Q5. 결제 시스템(포인트 구매 / 프리미엄)을 캠프 데모 환경에서 실제 구현할 것인가?

MYP-003(프리미엄 구매, Stripe/토스페이먼츠)과 KNO-006(포인트 소진 후 추가 검색)이 P0~P1로 명시되어 있습니다. 실제 결제 연동은 상당한 개발 비용이 필요합니다.

→ **답변 필요**: Mock 결제(시뮬레이션) 구현 수준으로 처리할 것인지, 또는 해당 기능을 데모 범위에서 제외할 것인지.

---

## 부록: 파일 위치 빠른 참조

| 문서 | 경로 |
|------|------|
| 최신 PRD (v0.95) | `docs/converted/PRD_v0.95_251124.md` |
| 최신 요구사항 (v0.96) | `docs/converted/Requirements_v0.96.md` |
| 지식검색 흐름도 | `docs/converted/Knowledge_Search_Flow.md` |
| 환자 여정도 | `docs/converted/Patient_JourneyMap.md` |
| 사용자 시나리오 | `docs/converted/UserScenarios.md` |
| 최종 발표자료 | `docs/converted/Final_Presentation.md` |
| Parlant 가이드 | `docs/converted/Parlant_Guide.md` |
| KidneyWise 기술명세 | `docs/converted/KidneyWise_TechSpec.md` |
| 백엔드 메인 라우터 | `backend/app/main.py` |
| 에이전트 통합 라우터 | `backend/app/api/careguide.py` |
| 에이전트 매니저 | `backend/Agent/agent_manager.py` |
| 프론트엔드 서비스 | `new_frontend/src/services/` |
| 프론트엔드 페이지 | `new_frontend/src/pages/` |
