# CareGuide 기술 경계 지도

## 목적

CareGuide의 도메인은 하나의 bounded context로 유지한다. 다만 변경 영향, 소유권, 테스트 범위를 명확히 하기 위해 저장소를 기술 경계로 나눈다.

도메인 기준은 [`domain.md`](./domain.md)이며, 이 문서는 도메인을 여러 bounded context로 쪼개는 문서가 아니다.

## 최상위 경계

```text
                         ┌──────────────────────────┐
                         │  Docs / Contracts         │
                         │  ADR, domain, API spec   │
                         └────────────┬─────────────┘
                                      │ defines
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
   ┌──────────▼──────────┐  ┌─────────▼─────────┐  ┌──────────▼──────────┐
   │ Frontend             │  │ Backend            │  │ Data                 │
   │ frontend/            │  │ backend/app        │  │ raw/processed/vector │
   │ UI, state, API client│  │ backend/Agent      │  │ Mongo collections    │
   └──────────┬──────────┘  └─────────┬─────────┘  └──────────┬──────────┘
              │ HTTP/API              │ repository/adapters  │
              └───────────────────────┴──────────────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │ External Integrations     │
                         │ Ollama, Parlant, PubMed,  │
                         │ ClinicalTrials.gov        │
                         └──────────────────────────┘

             Tests / Eval observe every boundary; Scripts execute workflows.
```

## Target top-level tree

```text
.
├── data/       # raw, processed, embeddings, fixtures
├── docs/       # ADR, domain, API/DB contracts, reports
├── scripts/    # preprocess, migration, indexing, smoke, maintenance
├── tests/      # backend, frontend, integration, fixtures
├── frontend/   # the only web application
├── backend/    # FastAPI, Agents, services, repositories
├── logs/       # runtime/debug artifacts; ignored by default
└── eval/       # router/agent/RAG evaluation
```

`.venv/`, `node_modules/`, `.git/`, `.omx/` 같은 개발 도구·런타임 디렉터리는 최상위 제품 경계에서 제외한다.

## 1. Data boundary

### 포함 범위

- `data/`: 원천·정제·가공 데이터
- `processed/`, `embedding_cache/`: 생성 산출물과 캐시
- `backend/app/db/`: MongoDB 연결, index, repository 기반
- `backend/rag/`: RAG 전용 로컬 산출물
- MongoDB collections: users, chat rooms, messages, health records, points, trials cache, embeddings

### 책임

- schema, ownership, retention, TTL, index 정의
- raw → processed → indexed 변환 재현성
- PII/건강정보 보존과 마스킹 정책
- point ledger와 daily counter의 무결성

### 허용 의존성

- Backend repository/service가 data adapter를 통해 접근
- 전처리 스크립트가 raw/processed 파일을 생성
- Tests가 fixture와 test database를 사용

### 금지 사항

- Frontend가 MongoDB나 파일 경로에 직접 접근
- Agent가 collection 이름과 query를 여러 곳에 중복 하드코딩
- generated data를 source-of-truth로 취급
- 비밀키와 PII를 데이터 파일에 커밋

### 정리 대상

- Pinecone/MongoDB vector 구현 중복
- 임베딩 캐시의 소유자와 invalidation 규칙
- 데이터 생성 스크립트와 결과 파일의 분리
- MongoDB index/TTL 정의의 단일화
- cache 값의 수명·소유자·source of truth 분리 ([`CACHE_POLICY.md`](./CACHE_POLICY.md))

## 2. Docs / Contracts boundary

### 포함 범위

- `AGENTS.md`: 저장소 운영 규칙
- `docs/adr/`: 아키텍처 결정
- `docs/agents/domain.md`: 도메인 언어와 불변식
- `docs/converted/`: 제품 요구사항·기술 명세
- `docs/agents/`: 운영·구현·검증 보고서
- OpenAPI, DB schema, event/stream 계약 문서

### 문서 종류

| 종류 | 예시 | 권위 |
|---|---|---|
| 정책/결정 | `AGENTS.md`, `docs/adr/` | 가장 높음 |
| 도메인/계약 | `domain.md`, API/DB schema | 구현 기준 |
| 제품 요구사항 | `docs/converted/` | 기능 범위 기준 |
| 작업 보고서 | `docs/agents/*_REPORT.md` | 참고·증거 |
| 계획/초안 | `.omx/plans/` | 실행 제안 |

### 책임

- API request/response, 오류, 인증, pagination 계약 정의
- DB schema와 invariants 기록
- ADR과 구현의 충돌 추적
- 실행 명령과 검증 결과 재현

### 금지 사항

- 구현 상태를 확인하지 않은 채 보고서를 source-of-truth로 사용
- Accepted ADR을 직접 수정해 결정 변경
- 코드와 문서의 용어를 다르게 사용
- 완료되지 않은 작업을 완료 보고서로 기록

## 3. Backend boundary

### 포함 범위

- `backend/app/`: FastAPI transport, models, services, repositories, DB adapters
- `backend/Agent/`: Agent registry, routing, prompt/tool orchestration
- `backend/agents/`: 레거시/호환 Agent 코드
- `backend/rag/`, `backend/tools/`: 검색·도구 adapter
- `backend/tests/`, `backend/Agent/test/`: backend regression tests

### 내부 계층

```text
HTTP Router
  → Application Service
    → Domain/Agent Orchestrator
      → Repository / External Adapter
        → MongoDB, LLM, PubMed, ClinicalTrials.gov
```

### 책임

- 인증·권한·소유권 검증
- emergency pre-filter와 confidence policy
- API 계약 준수와 오류 표준화
- DB transaction/idempotency
- 외부 API timeout/retry/cache

### 금지 사항

- Router에 장문의 business logic과 raw DB query 혼합
- Frontend 전용 response shape를 여러 endpoint에 복제
- Agent가 인증·결제·DB transaction을 직접 책임짐
- 외부 provider를 import-time에 무조건 초기화

### 우선 분리 대상

- `backend/app/api/community.py`
- `backend/app/api/chat.py`
- `backend/app/api/diet_care.py`
- `backend/app/db/hospital_manager.py`
- `backend/Agent/nutrition/agent.py`
- `backend/Agent/research_paper/agent.py`

## 4. Frontend boundary

### 포함 범위

- `frontend/`: 유일한 최종 canonical frontend
- `frontend/src/pages/`: route-level composition
- `frontend/src/components/`: UI/presentation
- `frontend/src/hooks/`: client state와 async workflow
- `frontend/src/services/`: typed HTTP API client
- `frontend/src/types/`: API/domain view types
- `frontend/src/config/`: 환경·feature flag·route constants
- `frontend/src/**/__tests__/`: frontend tests

### 책임

- 사용자 흐름과 접근성
- 인증 상태와 보호 라우트
- API 호출, loading/error/empty state
- 파일 업로드의 1차 validation
- 의료 면책과 정보 제공 카피의 표시

### 금지 사항

- MongoDB/LLM/외부 API 직접 호출
- API 오류를 임의로 성공 상태로 변환
- 결제 SDK, 결제 버튼, 결제 진입점 추가
- `new_frontend/`, `stitch_frontend/`에 신규 기능 추가

### 정리 대상

- `frontend/` 내부의 legacy component/service 정리
- `frontend/src/services/api.ts` 도메인별 분리
- `frontend/src/components/mypage/MyPageModals.tsx` 분리
- `ChatPageEnhanced.tsx`, `TrendsPageEnhanced.tsx`의 fetching을 hooks로 이동
- 기존 `frontend`와 `stitch_frontend`의 read-only inventory 후 중복 제거

### Frontend consolidation rule

통합은 완료됐다. ADR-011에 따라 `frontend/`만 제품 코드이며 `new_frontend/`와
`stitch_frontend/`는 `logs/rollback/` 아래 historical material이다. 신규 기능·버그 수정·디자인
이관의 기준은 항상 현재 `frontend/`이고 rollback 원본을 migration source로 사용하지 않는다.

## 5. Scripts boundary

### 포함 범위

- `scripts/`: preprocess, migration, indexing, seed, smoke, maintenance
- `backend/scripts/`: backend 전용 스크립트는 단계적으로 `scripts/`로 이동
- `preprocess/`: 기존 전처리 코드는 검토 후 `scripts/`로 통합
- 실행 명령과 환경 준비 문서

### 책임

- 반복 가능한 데이터·DB·평가 작업
- dry-run, idempotency, 입력/출력 경로 명시
- 파괴적 명령의 대상 확인과 백업 검증
- 새 개발자의 재현 가능한 실행 절차 제공

### 현재 위험

- 문서상 Docker MongoDB 전제에 비해 compose 파일이 없음
- preprocess, backend/scripts, root scripts가 분산됨
- 결과 파일을 생성하는 스크립트와 원천 데이터 경계가 불명확함

## 6. Tests boundary

### 포함 범위

- `tests/backend/`: backend API/service/repository/Agent tests
- `tests/frontend/`: frontend component/hook/service tests
- `tests/integration/`: MongoDB·provider adapter·API contract tests
- `tests/e2e/`: 핵심 사용자 흐름
- `tests/fixtures/`: 테스트 전용 데이터

### 테스트 피라미드

```text
Unit        : validation, pure service, mapper, reducer
Integration : Mongo repository, API router, Agent adapter
E2E/Smoke   : login → chat → health/diet/research user flow
Observability: logs, error payload, latency, cache hit/miss
```

### 책임

- 각 경계의 계약을 깨지지 않게 보호
- regression test를 리팩터링보다 먼저 추가
- 외부 API는 mock/fixture와 실제 smoke를 분리
- 테스트 결과와 알려진 gap을 기록

## 7. Logs boundary

### 포함 범위

- `logs/`: 로컬 실행 로그, smoke 결과, 성능 측정 결과
- 구조화된 application log와 테스트 artifact

### 규칙

- runtime log는 기본적으로 git에 커밋하지 않는다.
- PII, access token, 건강기록 원문, API key를 기록하지 않는다.
- 재현에 필요한 로그는 익명화 후 `docs/agents/` 보고서가 참조한다.
- 로그 보존 기간과 크기 제한을 정의한다.

## 8. Eval boundary

### 포함 범위

- `eval/`: intent router, Agent response, RAG retrieval, safety 평가
- gold cases, scoring script, benchmark 결과

### 책임

- 정확도와 안전성 평가를 unit test와 분리
- prompt/model/provider 변경 전후 비교
- threshold, false positive/negative, citation 품질 기록
- benchmark 입력에 PII를 포함하지 않음

## Backend-owned external adapters

### 포함 범위

- Ollama local generation/embedding adapter
- Parlant local runtime
- PubMed/ClinicalTrials.gov
- MongoDB/Vector Search

### 규칙

- local runtime과 공개 정보 source별 adapter를 둔다.
- timeout, retry, rate limit, fallback을 adapter 경계에서 처리한다.
- provider response를 내부 domain/API schema로 변환한다.
- API key와 provider-specific type이 frontend로 새지 않게 한다.
- hosted/paid LLM provider는 비활성 historical 경로이며 local-first runtime에서 호출·fallback하지 않는다.

## Runtime / configuration rule

별도 최상위 `infra/` 디렉터리는 만들지 않는다. 실행 설정은 다음 경계에 둔다.

- backend runtime: `backend/`와 `backend/.env.example`
- frontend runtime: `frontend/`와 `frontend/.env.example`
- 공통 실행·migration: `scripts/`
- 정책·실행 설명: `docs/`
- 실제 비밀값: 로컬 `.env` 또는 secret manager만 사용

### Local-first rule

- LLM과 embedding은 local adapter를 기본값으로 둔다.
- MongoDB와 vector 검색은 로컬 runtime을 기본값으로 둔다.
- PubMed/ClinicalTrials.gov 같은 외부 데이터는 backend adapter와 local cache를 통해서만 사용한다.
- PubMed/ClinicalTrials.gov 같은 공개 정보 source는 명시적으로 opt-in하며, hosted LLM provider 없이
  핵심 테스트와 로컬 채팅이 실행되어야 한다.
- 패키지는 최신 안정 버전을 검토하되 lockfile/compiled requirements로 고정한다.

Cache는 별도 최상위 경계가 아니다. domain-persistent cache는 backend feature repository와 local MongoDB가 소유하고, 재생성 가능한 cache는 backend cache adapter 또는 frontend의 비민감 UX cache가 소유한다.

## Dependency Rules

```text
Docs/Contracts  → defines → Backend / Frontend / Data / Scripts
Frontend        → HTTP    → Backend
Backend         → adapter → Data / External Integrations
Scripts         → writes  → Data artifacts / Logs
Tests           → observes→ Backend / Frontend / Data contracts
Eval            → measures→ Agent / RAG / Safety behavior
Logs            → records → runtime evidence only
```

다음 방향은 금지한다.

- Frontend → Data 직접 접근
- Router → raw external SDK 직접 호출
- Agent → frontend response shape 의존
- Docs report → 구현 사실을 검증 없이 덮어씀
- Generated data → source data를 덮어씀

## Boundary-based work order

1. Docs/Contracts와 현재 구현의 충돌 목록 작성
2. Data schema/index/vector 선택 고정
3. Backend API와 Frontend API client 계약 고정
4. 핵심 흐름 테스트 추가
5. 위험 제거
6. 각 경계 내부 리팩터링
7. 경계 간 의존성·성능 검증

이 순서를 지키면 기존 시스템을 유지할 수 있는지, 문서 기반 재구축이 필요한지 Phase 6 decision gate에서 판단할 수 있다.
