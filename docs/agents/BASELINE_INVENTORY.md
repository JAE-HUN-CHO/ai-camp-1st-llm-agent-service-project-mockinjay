# CareGuide Baseline Inventory

- **Snapshot:** 2026-08-11
- **Purpose:** 구조 통합·cache 분리·local-first 전환 전의 사실 기준
- **Source:** 현재 체크아웃의 파일 목록과 manifest를 읽어 작성

> 이 문서는 2026-08-11 통합 전의 historical baseline입니다. 현재 제품
> 경로·provider·Agent 계약은 [ADR-011](../adr/ADR-011-current-runtime-contract.md)과
> `AGENTS.md`를 우선하며, 이 표의 `new_frontend` 및 legacy 역할 표기는
> 당시 migration 입력을 설명하는 기록입니다.

## Target top-level vs current top-level

| Target | Current | Action |
|---|---|---|
| `data/` | `data/`, `processed/`, `embedding_cache/` | generated artifacts와 cache를 `data/` 아래로 정리 |
| `docs/` | `docs/` | ADR/domain/계약/보고서 유지 |
| `scripts/` | `scripts/`, `preprocess/`, `backend/scripts/` | 반복 실행 작업을 `scripts/`로 통합 |
| `tests/` | `backend/tests/`, `backend/Agent/test/`, frontend colocated tests | 기능별 test tree로 재배치 |
| `frontend/` | `frontend/`, `new_frontend/`, `stitch_frontend/` | `new_frontend` 기능을 최종 `frontend`로 통합 |
| `backend/` | `backend/` | 내부에 feature/module/adapter 구조 도입 |
| `logs/` | `logs/` | runtime log와 검증 artifact만 보관 |
| `eval/` | `eval/` | model/router/RAG 품질 평가 유지 |

`.venv/`, `node_modules/`, `.git/`, `.omx/`, `.worktrees/`는 제품 top-level 경계에서 제외한다.

## Frontend inventory

| Directory | Package | Source files | Pages | Services | Tests | Role |
|---|---:|---:|---:|---:|---:|---|
| `frontend/` | `careguide-frontend@1.0.0` | 156 | 41 | 9 | 1 | legacy application |
| `new_frontend/` | `new_frontend@0.0.0` | 274 | 29 | 10 | 28 | current feature source |
| `stitch_frontend/` | `stitch-frontend@1.0.0` | 46 | 7 | 7 | 0 | design prototype |

### Frontend 결합

- 동일한 `App`, route, `ChatPage`, `DietCarePage`, `TrendsPage`, `api.ts`, `intentRouter.ts` 계열이 여러 tree에 존재한다.
- route graph도 서로 다르다. legacy `frontend`는 `/dashboard`, `/mypage/test-results/*`, `/subscribe` 등을 직접 선언하고, `new_frontend`는 별도 lazy route graph와 redirect를 사용하며, `stitch_frontend`는 더 작은 prototype route graph를 가진다.
- 따라서 디렉터리 이름만 바꾸는 migration은 불가능하고, route/API/asset parity 표가 선행되어야 한다.
- `new_frontend/src/pages/ChatPageEnhanced.tsx`가 room state, streaming, persistence, image flow를 넓게 소유한다.
- `new_frontend/src/hooks/useChatStream.ts`는 존재하지만 실제 사용 여부와 page 내부 streaming 구현이 중복된다.
- `new_frontend/src/services/api.ts`는 auth interceptor, chat, user, terms 등 여러 domain을 한 module에 담는다.
- `new_frontend/src/components/mypage/MyPageModals.tsx`는 여러 modal 책임을 한 module에 담는다.
- frontend 통합은 삭제가 아니라 `route/API/asset/test parity`를 통과한 뒤 수행한다.

## Backend inventory

- Python files: 약 192개
- API modules: `auth`, `chat`, `clinical_trials`, `community`, `diet_care`, `health_tracking`, `mypage`, `news`, `quiz`, `rooms`, `session`, `trends`, `user_health_records` 등
- Agent modules: Medical Welfare, Nutrition, Quiz, Research Paper, Router, Trend Visualization

## Feature contract inventory

| Feature | Backend entrypoints | Frontend source | Primary data | Existing test evidence |
|---|---|---|---|---|
| Auth | `/api/auth/register`, `/api/auth/login`, `/api/auth/me` | `LoginPage*`, `SignupPage*`, `AuthContext` | `users` | auth context/tests, auth endpoint coverage to verify |
| Chat | `/api/chat/message`, `/api/chat/stream`, `/api/rooms/*`, `/api/session/*` | `ChatPageEnhanced`, `ChatInterface`, chat hooks | `chat_rooms`, `messages`, session state | `backend/tests/test_chat_endpoints.py`, Agent router tests |
| Diet | `/api/diet-care/*`, `/api/nutrition/analyze` | `DietCarePageEnhanced`, diet-care modules | `diet_sessions`, `diet_meals`, `diet_goals`, nutrition artifacts | `backend/tests/test_diet_care_api.py`, nutrition tests |
| Health | `/api/health-records/*`, health tracking routes | `HealthRecordsPage`, health profile modal | `user_health_records`, lab/medication collections | partial; null/PATCH semantics need explicit tests |
| Community | `/api/community/posts/*`, comments, likes, uploads | `CommunityPageEnhanced` and community modules | posts, comments, likes, uploads | endpoint coverage to verify |
| Research | `/api/trends/*`, `/api/clinical-trials/*`, `/api/news/*` | `TrendsPageEnhanced`, trends modules | PubMed/vector results, `clinical_trials_cache`, news cache | trend/clinical trial frontend tests; backend integration gap |
| Quiz | `/api/quiz/session/*`, stats/history | `QuizPage`, `QuizListPage` | quiz sessions, points, quiz pool | `backend/tests/test_quiz_agent.py` |
| Account | `/api/mypage/*`, bookmarks, notifications | `MyPageEnhanced`, account pages | users, bookmarks, notifications, points | colocated frontend tests; backend contract gap |

### 주요 대형 module

| Module | Approx. size | Mixed responsibilities |
|---|---:|---|
| `backend/app/api/community.py` | 1,223 lines | HTTP, validation, DB, upload, comments, likes |
| `backend/app/api/chat.py` | 724 lines | request context, stream, Agent, SSE, persistence, proxy |
| `backend/Agent/nutrition/agent.py` | 1,215 lines | Agent workflow, LLM/RAG, conversation state |
| `backend/Agent/research_paper/server/healthcare_v2_en.py` | 1,203 lines | server lifecycle, search, cache, NLP components |
| `backend/app/db/hospital_manager.py` | 1,235 lines | connection/query/schema/domain mapping |
| `backend/app/db/vector_manager.py` | 742 lines | Pinecone, embedding, disk cache, LRU, chunking |

### Backend 결합

- `chat.py`와 `session.py`가 process-global active stream 상태를 공유한다.
- `AgentManager`, `RouterAgent`, `AgentRegistry`가 Agent 생성·routing·context·token accounting을 나눠 소유한다.
- `connection.py`와 `mongodb_manager.py`가 서로 다른 Mongo connection seam을 제공한다.
- `backend/agents/nutrition_agent.py`와 `backend/Agent/nutrition/agent.py`가 Nutrition 구현을 중복 제공한다.
- router가 raw DB query나 외부 provider 호출을 직접 소유하는 지점을 추가 조사해야 한다.

## Data and cache inventory

### Persistent data

- raw files: `data/rawdata/`
- processed files: `data/processed/`, `data/processed_nutrition_data*`
- filtered knowledge: `data/kidney_filtered/`
- local embedding artifacts: `embedding_cache/`
- Mongo collections: users, chat rooms, messages, health records, points, trials cache, embeddings

### Cache implementations

| Location | Cache | Scope | Risk |
|---|---|---|---|
| `backend/app/api/clinical_trials.py` | trial/translation dict | process | multi-instance inconsistency |
| `backend/app/api/news.py` | news dict | process | router/cache coupling, unrestricted clear |
| `backend/app/services/pubmed_search.py` | translation/count cache | process | provider/cache coupling |
| `backend/app/db/vector_manager.py` | memory LRU + disk pickle | process/disk | provider/cache coupling, cache path ambiguity |
| `backend/Agent/research_paper/server/cache_manager.py` | Redis cache manager | shared | global lifecycle and multiple cache strategy |
| `new_frontend/src/services/translateApi.ts` | localStorage translation | browser | schema/version/privacy not centralized |
| `backend/app/api/chat.py`, `session.py` | active stream registry | process | hidden mutable state, not ordinary cache |

`active_streams`와 `conversation_states`는 cache가 아니라 runtime state로 분류한다. `daily_search_counter`, session TTL, `clinical_trials_cache`처럼 domain behavior에 영향을 주는 값은 local MongoDB가 source of truth여야 한다.

## Tests and eval inventory

- Backend tests: `backend/tests/`와 `backend/Agent/test/`에 분산
- Frontend tests: 주로 `new_frontend/src/**/__tests__`
- 일부 backend tests는 localhost HTTP와 timestamped log에 의존한다.
- `eval/`에는 router evaluation script와 CSV 결과가 있다.
- 최종 target은 `tests/{backend,frontend,integration,e2e,fixtures}`이며, `eval/`은 model-quality 측정으로 분리한다.

## Runtime and package inventory

- Root `requirements.txt`와 `backend/requirements.txt`가 별도 존재한다.
- 세 frontend 각각 `package.json`과 lockfile을 가진다.
- backend requirements에는 현재 import와 일치 여부를 별도로 확인해야 하는 provider가 있다.
- 현재 환경에는 `USE_OLLAMA`, `OLLAMA_*`, `MONGODB_URI` 계열 설정이 존재한다.
- 최종 정책은 최신 안정 호환 버전 조사 → lockfile/compiled requirements 생성 → build/lint/test/smoke 검증이다.

### Current package generations

| Area | Current baseline | Observation |
|---|---|---|
| legacy `frontend/` | React 18, TypeScript 5.2, Tailwind 3.3, ESLint 8 | final destination으로 직접 업그레이드하지 않고 기능 선별 대상 |
| `new_frontend/` | React 19, TypeScript 5.9, Vite 7, Tailwind 3.4, ESLint 9, Vitest 2 | 최종 `frontend/`의 기능 원본 후보 |
| `stitch_frontend/` | React 19, TypeScript 5.7, Vite 7, Tailwind 3.4, ESLint 9 | prototype; package upgrade 대상 아님 |
| backend requirements | FastAPI 0.120 range, Pydantic Settings 2.x, Motor 3.3, PyMongo 4.6 | root requirements와 중복·불일치 조사 필요 |
| installed `.venv` | FastAPI 0.120.4, Pydantic 2.12.4, LangGraph 1.0.4, LangChain 1.1.0, Parlant 3.1.0a1 | requirements lock과 실제 runtime 차이 확인 필요 |

### Local runtime check

- Ollama binary는 설치되어 있으나 현재 `127.0.0.1:11434` endpoint가 실행 중이지 않다.
- Docker Desktop daemon은 승인된 실행 경로에서 접근 가능하며, 임시 `mongo:7` 컨테이너의 `mongosh` ping smoke가 통과했다. 이는 일반 Mongo 연결만 증명하고 vector search는 증명하지 않는다.
- `mongodb/mongodb-atlas-local:latest` pull은 레이어 진행이 멈춰 중단되었고, 해당 이미지/컨테이너는 확보되지 않았다.
- `USE_OLLAMA`, `OLLAMA_*`, `MONGODB_URI` 환경변수 계약은 이미 존재한다.
- 따라서 package upgrade보다 먼저 local runtime smoke를 재현 가능한 명령으로 문서화하고, Mongo vector image 제약은 ADR/로그에 명시해야 한다.

## Coupling priority

### P0 — 먼저 seam을 고정해야 하는 결합

1. 세 frontend의 source-of-truth 중복
2. Pinecone/MongoDB vector 선택과 embedding cache의 혼합
3. `chat.py`/`session.py`의 global stream state
4. 두 Mongo connection seam과 legacy globals
5. Agent registry·routing·Agent creation 중복

### P1 — 테스트 고정 후 분리할 결합

1. clinical trials/news router와 cache
2. PubMed provider와 translation/count cache
3. Nutrition 이중 구현
4. frontend API client와 localStorage cache
5. colocated/live tests와 실제 interface 불일치

## Next verification actions

1. 세 frontend route/API/asset parity 표 작성
2. package dependency graph와 최신 안정 호환 후보 조사
3. local MongoDB + local model smoke 실행
4. cache별 key/TTL/owner/invalidation 표 작성
5. P0 module interface에 대한 regression test 추가
6. 최종 `frontend/` 통합 후 그 directory만 최신 안정 package로 upgrade
7. local MongoDB/Ollama 실행 권한과 health check를 smoke script로 고정
