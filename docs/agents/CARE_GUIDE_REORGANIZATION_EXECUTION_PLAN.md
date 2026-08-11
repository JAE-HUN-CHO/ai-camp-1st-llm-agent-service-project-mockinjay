# CareGuide 재구성 실행 계획

> 실행 계획의 migration 입력과 당시 경로는 historical reference다. 현재 product root,
> provider, cache source of truth는 `DOCUMENT_CONSISTENCY_MATRIX.md`와 ADR-011을
> 따른다. 이 계획의 Phase gate를 다시 실행할 때도 `frontend/`와 local Ollama/MongoDB를
> 대상으로 한다.

## 목표

CareGuide를 AI가 좁은 맥락에서 빠르게 이해하고 안전하게 수정할 수 있는 구조로 정리한다.

최종 top-level은 다음 8개로 제한한다.

```text
data/ docs/ scripts/ tests/ frontend/ backend/ logs/ eval/
```

핵심 원칙은 파일 수 증가가 아니라 `one module = one responsibility`다. 작은 파일을 만들되, 실제 input/output/state/seam이 있을 때만 나눈다.

## 고정할 결정

- 최종 frontend는 `frontend/` 하나다.
- 현재 기능 원본은 `new_frontend/`로 삼고 parity 검증 후 이전한다.
- `stitch_frontend/`는 디자인 자산만 선별 이관한다.
- LLM/embedding은 local-first adapter를 기본값으로 한다. 현재 후보는 Ollama다.
- DB와 vector 검색은 로컬 MongoDB를 기본값으로 한다.
- 외부 LLM은 opt-in adapter다.
- PubMed/ClinicalTrials.gov는 외부 data source이며 local cache를 통해 재현한다.
- package는 최신 안정 호환 버전을 조사한 뒤 lockfile/compiled requirements로 고정한다.
- 결제 SDK·결제 UI·결제 endpoint는 추가하지 않는다.

## 참고 artifact

- [`BOUNDARY_MAP.md`](./BOUNDARY_MAP.md)
- [`BASELINE_INVENTORY.md`](./BASELINE_INVENTORY.md)
- [`CACHE_POLICY.md`](./CACHE_POLICY.md)
- [`ADR-005-vector-db.md`](../adr/ADR-005-vector-db.md)
- [`ADR-008-single-frontend-root.md`](../adr/ADR-008-single-frontend-root.md)
- [`ADR-009-local-first-runtime.md`](../adr/ADR-009-local-first-runtime.md)
- 참고 worktree: `.worktrees/MiniMax-M2.7-1779124465965/`

## Worktree와 Docker 참고 결과

- 네 개 worktree는 같은 base commit에서 파생됐다.
- MiniMax worktree에는 `docker-compose.yml`, backend Dockerfile, new frontend Dockerfile이 있다.
- 해당 compose는 `mongo:7`과 `new_frontend`를 사용한다. Vector Search 기준이 ADR-005와 다르므로 최종 compose로 복사하지 않는다.
- Docker Desktop daemon은 승인된 실행 경로에서 접근 가능하며, 임시 `mongo:7` 컨테이너의 `mongosh` ping smoke가 통과했다. 이는 일반 Mongo 연결만 증명하고 vector search는 증명하지 않는다.
- `mongodb/mongodb-atlas-local:latest` pull은 레이어 진행이 멈춰 중단했고 이미지/컨테이너는 확보하지 못했다. 따라서 MiniMax compose와 `mongo:7`은 orchestration/연결 참고로만 둔다.
- ADR-005에 맞는 vector image가 확보되기 전에는 vector 검증 완료로 보고하지 않는다.

## Phase 0 — 기준 통일 및 inventory

### 작업

1. `BASELINE_INVENTORY.md`와 현재 git status/diff를 확인한다.
2. 세 frontend의 route/API/asset/test parity 표를 완성한다.
3. `frontend/`, `new_frontend/`, `stitch_frontend/`의 기능을 `reuse / replace / obsolete`로 분류한다.
4. `data/`, `processed/`, `embedding_cache/`, `preprocess/`, `backend/scripts/`의 이동 후보를 기록한다.
5. cache를 domain-persistent / provider-computation / frontend UX / test fixture로 분류한다.

### 산출물

- frontend parity matrix
- data/script migration matrix
- cache owner/TTL/invalidation matrix

### 통과 기준

- 모든 핵심 feature에 source file, endpoint, page, collection, test 위치가 있다.
- 삭제 대상은 기능·자산·테스트 근거 없이 지정하지 않는다.

## Phase 1 — Local-first runtime과 최신 호환 package

### 작업

1. Docker daemon과 local MongoDB image/compose를 확인한다.
2. ADR-005에 맞는 `mongodb/mongodb-atlas-local` image를 사용한다.
3. MongoDB healthcheck, volume, credentials, DB name, vector index setup을 문서화한다.
4. Ollama healthcheck와 model/embedding model 설정을 정한다.
5. root/backend requirements를 하나의 backend dependency 정책으로 합칠 후보를 만든다.
6. 최종 frontend가 정해진 뒤에만 package upgrade를 수행한다.
7. 최신 안정 호환 버전을 확인하고 major upgrade별로 build/lint/test를 실행한다.
8. Node lockfile과 Python compiled requirements를 생성한다.

### 통과 기준

- API key 없이 핵심 unit/integration test가 실행된다.
- local MongoDB healthcheck가 통과한다.
- local model 또는 deterministic fake adapter로 chat smoke가 실행된다.
- package versions가 재현 가능하게 고정된다.

## Phase 2 — 테스트 고정

### Backend

- auth/권한/세션 만료
- chat message/stream/emergency filter
- health record PATCH/null semantics
- diet/image validation
- research rate limit/vector result mapping
- quiz grading/point ledger
- community ownership/CRUD
- clinical trial cache fallback

### Frontend

- protected route/auth context
- chat stream state
- diet/health forms
- research/clinical trial display
- point/bookmark/account flows

### 배치

```text
tests/backend/{unit,integration}
tests/frontend/{unit,integration}
tests/e2e
tests/fixtures
eval/                 # model-quality only
```

live localhost test는 integration 또는 e2e로 명시하고, unit test에서는 deterministic fake를 사용한다.

## Phase 3 — 위험 제거

- PII/health data 로그 노출
- JWT/auth ownership 누락
- upload MIME/path traversal
- NoSQL injection
- point transaction/idempotency
- TTL/index 누락
- unauthorized cache clear
- 무제한 process-global dict
- 외부 API timeout/retry/rate limit
- import-time provider initialization
- 결제 UI/API/SDK 잔존

CRITICAL/HIGH 이슈는 구조 분리 전에 0건이어야 한다.

## Phase 4 — Frontend 통합

### 순서

1. `new_frontend` route/API/asset/test를 기준으로 한다.
2. 기존 `frontend`의 고유 기능을 선별한다.
3. 최종 `frontend/`에 기능을 이전한다.
4. `frontend/src/features/{chat,diet,health,research,community,quiz,account}`로 기능 locality를 높인다.
5. `frontend/src/shared/{ui,http,auth,cache}`에는 실제 여러 feature가 공유하는 것만 둔다.
6. `stitch_frontend`의 디자인 자산·토큰만 이관한다.
7. route/API/asset/test parity를 검증한다.
8. parity 통과 후 `new_frontend`, `stitch_frontend` 삭제를 별도 커밋으로 수행한다.

### frontend 내부 규칙

- feature module은 다른 feature의 내부 파일을 직접 import하지 않는다.
- 공통 module은 shared seam을 통해서만 사용한다.
- `services/api.ts` 같은 cross-domain giant module을 domain별로 나눈다.
- `MyPageModals.tsx` 같은 giant module을 modal 책임별로 나눈다.
- `ChatPageEnhanced`는 화면 조합만 담당하고 stream 상태·HTTP·persistence는 feature 내부 module로 이동한다.

## Phase 5 — Backend/Data/Cache 구조 분리

### Backend target

```text
backend/app/features/{chat,diet,health,research,community,quiz,account}
backend/app/ports/{llm,embedding,vector,external_search}
backend/app/adapters/{ollama,mongodb,clinical_trials,pubmed,parlant,cache}
```

기존 `backend/Agent`는 한 번에 이동하지 않고 compatibility adapter 뒤에 둔다.

### 우선 seam

1. chat intake: request/context/stream encoding/recording
2. vector search: provider와 embedding/cache 분리
3. Mongo connection: 하나의 lifecycle와 repository ownership
4. Agent registry: import order 대신 composition root 주입
5. Nutrition: 두 구현 parity test 후 하나를 선택

### Cache 배치

- domain-persistent: feature repository → local MongoDB
- computation/provider: `backend/app/cache` 또는 `backend/app/adapters/cache`
- disk artifact: `data/cache/` 및 gitignore
- frontend UX: `frontend/src/shared/cache` 또는 feature 내부
- test fixture: `tests/fixtures`
- logs에는 value가 아니라 hit/miss/expiry만 기록

## Phase 6 — 성능 개선

측정 후 변경한다.

- Mongo query profile/index/N+1
- embedding/external API cache hit rate
- LLM latency/token usage
- frontend bundle/chunk/re-render
- stream p50/p95 latency

## Rebuild decision gate

기존 구현을 유지한다.

- 핵심 계약을 복구할 수 있다.
- 테스트가 재현 가능하게 고정된다.
- local runtime이 실행된다.
- CRITICAL/HIGH가 0건이다.

문서 기반 재구축으로 전환한다.

- API/DB/Agent 계약이 복구되지 않는다.
- frontend parity가 반복해서 실패한다.
- vector/provider/session 모델을 통일할 수 없다.
- 두 번의 제한된 수선 사이클 후에도 build/test가 불안정하다.

재구축 시에도 API contract, DB schema, golden test를 먼저 작성하고 vertical slice 단위로 교체한다.

## Verification commands

```bash
git diff --check
.venv/bin/python -m pytest -q backend/tests backend/Agent/test
.venv/bin/python -m ruff check backend/app/
cd frontend && npm run build && npm run lint && npm test -- --run
docker compose config
docker compose up -d mongodb
docker compose exec mongodb mongosh --quiet --eval 'db.adminCommand({ping:1})'
curl -f "http://localhost:${BACKEND_PORT:-8000}/health"
```

`frontend/` 통합 전의 baseline build/lint는 `new_frontend/`에서 실행하고, 최종 디렉터리 통합 후 위 명령의 `frontend/` 경로를 사용한다. Docker와 local model이 없는 환경에서는 해당 단계의 실패를 `logs/`와 보고서에 기록하고, fake adapter로 unit test를 계속한다.
