# CareGuide Project Context

> **Last updated**: 2026-05-23
> **Authority**: PRD v0.95 (2025-11-24) + Requirements v0.96 (2025-11-12)
> **Companion docs**: `docs/converted/_ANALYSIS_REPORT.md` (gap analysis), `docs/adr/` (architecture decisions)

이 문서는 코드베이스에 살아있는 **도메인 언어와 결정 사항의 단일 출처(single source of truth)** 입니다. 새로운 세션·새 기여자는 이 문서를 먼저 읽고 시작하세요.

---

## 1. Product One-Liner

**CareGuide**는 만성콩팥병(CKD) 환자·일반인·연구자를 대상으로 PubMed RAG 기반 의학 정보, 식단 영양 분석, 복지 정보, 학습 퀴즈를 통합 제공하는 AI 에이전트 케어 플랫폼이다.

핵심 차별점:
- **3-페르소나 라우팅** (일반인 / 질환자 / 연구자)
- **False Negative 방지** 의료 안전 정책
- **Parlant SDK 기반** 멀티 에이전트 오케스트레이션

---

## 2. Domain Language (Glossary — Top 25)

전체 용어집은 `docs/converted/_ANALYSIS_REPORT.md` Section 3 참조. 아래는 코드 식별자에서도 자주 쓰이는 핵심 용어.

| 한국어 | English / Code identifier | 의미 |
|---|---|---|
| 만성콩팥병 | CKD (Chronic Kidney Disease) | 대상 질환. eGFR 기준 1~5단계 |
| 환자군 분류 | `disease_stage` | CKD1~5, DKD-C, CKD_T, AKI, PD, HD |
| 일반인 / 노비스 | `user_type=general` | 진단 전 사용자, 간병인 |
| 질환자 / 경험자 | `user_type=patient` | CKD 진단 환자, 이식 후 환자 |
| 연구자 | `user_type=researcher` | 의료진·연구자 |
| 의도분류 | Intent Classification | 발화를 10개 카테고리로 분류. 정확도 ≥90% 목표 |
| Agent Manager | `agent_manager.py` | 4개 에이전트(Medical_Welfare/Nutrition/Research_Paper/Quiz) 오케스트레이션 |
| 지식검색 | Knowledge Search | PubMed API + RAG 요약 |
| NutriCoach | Nutrition agent 기능 | 질환단계 목표치 대비 위험도 분석(안전/주의/위험) |
| 식단 로그 | Diet Log (`/diet-log`) | 끼니별 식사 기록 |
| 복지 에이전트 | Medical_Welfare agent | 산정특례·지원금·보험 정보 |
| Confidence Score | `confidence_score` | LLM 응답 신뢰도. <0.7 → "전문의 상담 권장" |
| False Negative 방지 | Safety policy CHK-001~009 | 응급 키워드 → 즉시 119 안내. 안심 답변 금지 |
| 면책조항 | Disclaimer | 챗봇 상단 고정 배너 |
| RAG | Retrieval-Augmented Generation | Vector DB 검색 + LLM 컨텍스트 주입 |
| 산정특례 | Special Cost Exemption | 말기신부전 등록 시 의료비 본인부담 경감 |
| eGFR / 크레아티닌 | eGFR / Creatinine | CKD 단계 판정 핵심 수치 |
| 투석 | Dialysis (HD / PD) | 혈액투석 / 복막투석 |
| 멀티턴 | Multi-turn | 최근 5턴 컨텍스트 유지 |
| 세션키 | `session_key` (UUID) | FE 생성, Parlant 세션과 매핑 |
| 의도분류 카테고리 | 10 categories | MEDICAL_INFO, DIET_INFO, RESEARCH, WELFARE_INFO, HEALTH_RECORD, LEARNING, POLICY, CHIT_CHAT, NON_MEDICAL, NON_ETHICAL |
| 게미피케이션 | Gamification | 포인트(+10P/+5P/+20P/+3P), 100P=100토큰, 프리미엄 결제 |
| 환자 여정 5단계 | Patient Journey | 진단 → 정보탐색 → 검사이해 → 일상관리 → 복지탐색 |
| Parlant Journey | Parlant SDK 흐름 정의 | 에이전트별 다이얼로그 트리. JSON import 또는 코드 정의 |
| 트렌드 시각화 | Trend Viz (KNO-007) | 최근 5년 PubMed 연도별 막대 그래프 |

**Naming convention** (코드 식별자에서 지켜야 할 일관성):
- API 라우트: 하이픈 케이스 (`/diet-care`, `/clinical-trials`, `/test-results`)
- Python: snake_case
- TS / React: camelCase / PascalCase
- 페르소나: `user_type` (값: `general` / `patient` / `researcher`)
- 질환 단계: `disease_stage` (값: `CKD1`~`CKD5`, `DKD-C`, `CKD_T`, `AKI`, `PD`, `HD`)

---

## 3. Persona × Feature Matrix

| 기능 | 일반인 | 질환자 | 연구자 |
|---|---|---|---|
| AI 챗봇 (Medical_Welfare / Nutrition) | ✅ | ✅ | ✅ |
| Nutrition 이미지 분석 | ✅ | ✅ | ✅ |
| PubMed 검색 (자동) | ❌ (논문 키워드 시 only) | ❌ (보조 추천 only) | ✅ (항상) |
| NutriCoach 위험도 분석 (질환단계) | 제한적 | ✅ | ✅ |
| 학습 퀴즈 (RAG 생성) | ✅ | ✅ | ✅ |
| 커뮤니티 게시판 | ✅ | ✅ | ✅ |
| 커뮤니티 설문 생성 | ❌ | ❌ | ✅ |
| 시계열 대시보드 (KNO-008) | 제한적 | ✅ | ✅ |
| 산정특례 / 복지 정보 | 제한적 | ✅ | 참조 |
| 프리미엄 결제 / 포인트 전환 | ✅ | ✅ | ✅ |

→ 출처: PRD v0.95 §1.2, Requirements v0.96 정책서 시트, `docs/converted/Knowledge_Search_Flow.md`

---

## 4. Architecture Snapshot

```
┌──────────────────────┐       ┌────────────────────┐
│ Frontend             │       │ FastAPI Backend    │
│ new_frontend/ (canonical, ADR-001)             │
│  React 18 + Vite + TS + Tailwind               │
│  Context API state                             │
└──────────┬───────────┘       └─────────┬──────────┘
           │ HTTPS / SSE                  │
           ▼                              ▼
┌──────────────────────┐       ┌────────────────────┐
│ /api/chat/stream     │──────▶│ Agent Manager      │
│ /api/quiz/...        │       │  (agent_manager.py)│
│ /api/community/...   │       └─────────┬──────────┘
│ /api/diet-care/...   │                 │
│ /api/clinical-trials │                 ▼
│ /api/health-records  │       ┌────────────────────┐
│ /api/auth, /api/user │       │ Parlant SDK (port 8800)
└──────────────────────┘       │  - Medical_Welfare │
                               │  - Nutrition       │
                               │  - Research_Paper  │
                               │  - Quiz            │
                               └─────────┬──────────┘
                                         ▼
              ┌──────────────────────────────────────┐
              │  MongoDB (general data)              │
              │  MongoDB Atlas Vector Search /       │
              │  Pinecone (PubMed embeddings)        │
              │  → ADR-005 단일화 결정 보류          │
              └──────────────────────────────────────┘
```

**Tech stack**: Python 3.10+ / FastAPI / MongoDB / Parlant SDK / OpenAI API (GPT-3.5-turbo, text-embedding-3-small) / React 18 + Vite + TS + Tailwind / Axios.

자세한 구성요소는 `docs/converted/KidneyWise_TechSpec.md` 참조.

---

## 5. Non-Functional Requirements (Hard Constraints)

| 분류 | 요구사항 | 근거 |
|---|---|---|
| **의료 안전** | 응급 키워드(흉통/호흡곤란/의식저하/경련) → 즉시 119 안내. 증상 보고 시 "괜찮습니다" 류 응답 절대 금지 | PRD v0.95, Requirements 정책서 |
| **AI 신뢰도** | Confidence Score < 0.7 → "전문의 상담 권장" 메시지 첨부 | REQ-022 |
| **개인정보** | 개인정보보호법·정보통신망법·의료법(2024~2025 개정안) 준수. 주민번호·전화·주소·얼굴사진·금융정보 자동 마스킹 | 정책서 시트 |
| **민감정보 처리** | 텍스트: 부분 마스킹 / 이미지: 얼굴 감지 시 전체 거부 / 파일: OCR → 민감정보 발견 시 업로드 거부 | 정책서 시트 |
| **세션** | JWT Access 1h / Refresh 7d. 비로그인 GUID 캐시 세션 20분(이후 재접속 복원) | 정책서, ADR-007 |
| **멀티턴** | 최근 5턴 컨텍스트 유지 | REQ-019 |
| **의도분류 정확도** | ≥ 90% (eval/router 평가 스크립트로 측정) | REQ-056 |
| **파일 업로드** | 챗봇 공통: PDF만, 5MB 이하 / Nutrition: 추가로 png/jpg/svg → ADR-003 충돌 해소 | REQ-016 vs 정책서 |

---

## 6. Critical Decisions (See ADRs)

| ADR | 주제 | 상태 |
|---|---|---|
| [ADR-001](adr/ADR-001-canonical-frontend.md) | Canonical frontend 단일화 | Proposed |
| [ADR-002](adr/ADR-002-parlant-orchestration.md) | Parlant SDK 운영 방식 | Proposed |
| [ADR-003](adr/ADR-003-image-upload-policy.md) | 이미지 업로드 정책 (REQ-016 vs 정책서) | Proposed |
| [ADR-004](adr/ADR-004-clinical-trials-scope.md) | 임상시험 기능 스펙 포함 여부 | Proposed |
| [ADR-005](adr/ADR-005-vector-db.md) | 벡터 DB 단일화 (Pinecone vs MongoDB Atlas) | Proposed |
| [ADR-006](adr/ADR-006-payment-mvp-scope.md) | 결제·포인트 시스템 MVP 범위 | Proposed |
| [ADR-007](adr/ADR-007-session-management.md) | Parlant 세션 ↔ JWT 통합 방식 | Proposed |

---

## 7. Unimplemented P0 Gaps (MVP Blockers)

전체 gap 분석은 `docs/converted/_ANALYSIS_REPORT.md` Section 5/6 참조. 아래는 MVP 출시를 막는 **P0 미구현/부분구현** 항목.

| 코드 | 기능 | 현재 상태 | 영향 |
|---|---|---|---|
| **KNO-005** | 다중 논문 비교 테이블 (체크박스 + 비교) | ❌ 미구현 | P0 차단 |
| **KNO-006** | 1일 검색 10회 제한 + 포인트 전환 + 프리미엄 안내 | ❌ Redis/DB 추적 미구현 | P0 차단 |
| **KNO-007** | 연구 트렌드 5년 막대그래프 | ⚠️ 라우터만 존재, PubMed 연도별 집계 미확인 | P0 검증 필요 |
| **KNO-008** | 시계열 대시보드 (월별/연도별 라인, 기간 선택) | ⚠️ Trends 페이지 부분 구현 | P0 검증 필요 |
| **CHA-007** | False Negative 방지 안전 체크 (CHK-001~009 런타임 enforcement) | ⚠️ Parlant Journey 정의됨, 실제 차단 동작 미검증 | 의료 안전 직결 |
| **REQ-022** | Confidence Score 정책 — <0.7 시 전문의 권장 메시지 | ⚠️ 적용 위치 검증 필요 | P0 차단 |
| **MYP-005** | 알림 시스템 (FCM/브라우저 알림 8종) | ❌ 라우터만 존재, FCM 미연동 | P1 |

→ 위 항목은 모든 P0 sprint 우선순위로 등록되어야 함.

---

## 8. Testing & Quality Gates

| 게이트 | 기준 | 검증 방법 |
|---|---|---|
| 의도분류 정확도 | ≥ 90% | `eval/router_eval.py` 출력 CSV |
| 응급 키워드 감지율 | 100% (False Negative 0건) | 안전 시나리오 테스트 |
| API 단위 테스트 커버리지 | 리포트 생성 가능 | pytest --cov |
| 사용자 시나리오 테스트 | 3개 이상 통과 | UserScenarios.md 기준 |
| 빌드 게이트 | `npm run build` 0 errors | CI |

---

## 9. Open Questions (Pending User Decision)

`docs/converted/_ANALYSIS_REPORT.md` Section 8 참조:
1. 이미지 업로드 정책 충돌 해소 (ADR-003)
2. Clinical Trials 기능 공식 스펙 포함 여부 (ADR-004)
3. Canonical frontend 결정 (ADR-001)
4. KPI 정식 정의
5. 결제 시스템 실제 연동 여부 (ADR-006)

---

## 10. How to Read This Repo (Onboarding)

1. 이 파일 (CONTEXT.md) — 도메인 언어 + 결정 + 게이트
2. `docs/adr/` — 왜 이렇게 결정했는지
3. `docs/converted/_ANALYSIS_REPORT.md` — spec ↔ code gap
4. `docs/converted/PRD_v0.95_251124.md` + `Requirements_v0.96.md` — 원본 스펙
5. `docs/converted/Knowledge_Search_Flow.md` + `Patient_JourneyMap.md` — 사용자 흐름
6. `docs/converted/Parlant_Guide.md` + `KidneyWise_TechSpec.md` — 구현 상세
7. 코드 진입점:
   - Backend: `backend/app/main.py` → `backend/app/api/careguide.py`
   - Agent: `backend/Agent/agent_manager.py`
   - Frontend: `new_frontend/src/App.tsx` → `new_frontend/src/pages/`
