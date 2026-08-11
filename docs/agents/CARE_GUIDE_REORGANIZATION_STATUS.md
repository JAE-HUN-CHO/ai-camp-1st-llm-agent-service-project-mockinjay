# CareGuide 재구성 실행 상태

> 이 문서는 Phase 0–6 작업의 실행 스냅샷이다. 당시의 `new_frontend`/provider/cache
> 표는 historical evidence이며, 현재 계약과 검증 결과는
> [`DOCUMENT_CONSISTENCY_MATRIX.md`](DOCUMENT_CONSISTENCY_MATRIX.md),
> [ADR-011](../adr/ADR-011-current-runtime-contract.md), 그리고 현재 테스트를 따른다.

- **Started:** 2026-08-11 (Asia/Seoul)
- **Scope:** `CARE_GUIDE_REORGANIZATION_EXECUTION_PLAN.md`의 Phase 0–6
- **Decision rule:** 기존 사용자 변경과 untracked 데이터는 보존하며, parity·복구 가능성·회귀 테스트 없이 삭제/덮어쓰기를 수행하지 않는다.
- **Current phase:** Phases 0–6 complete for the safe KEEP/REPAIR gate; follow-up seams, local-provider measurements, and documentation/log relocation are recorded below.

## Initial working-tree record

이 기록은 코드나 파일을 이동하기 전에 수집했다.

### Existing tracked modifications (preserved)

```text
 M backend/app/api/careguide.py
 M backend/app/api/user_health_records.py
 M backend/app/config.py
 M backend/app/main.py
 M frontend/.DS_Store
 M new_frontend/src/pages/ChatPageEnhanced.tsx
 M new_frontend/src/pages/HealthRecordsPage.tsx
```

`git diff --stat` at start:

```text
 backend/app/api/careguide.py                 |   7 +-
 backend/app/api/user_health_records.py       |   2 +-
 backend/app/config.py                        |   2 +-
 backend/app/main.py                          | 100 +-----
 frontend/.DS_Store                           | Bin 6148 -> 6148 bytes
 new_frontend/src/pages/ChatPageEnhanced.tsx  |   3 +-
 new_frontend/src/pages/HealthRecordsPage.tsx | 455 +++++++++++++++------------
 7 files changed, 273 insertions(+), 296 deletions(-)
```

Untracked content at start included `.omx/`, `AGENTS.md`, `data/` datasets and images, `stitch_frontend/`, and `.omx/plans/careguide-optimization-and-rebuild-plan.md`. The complete path list was obtained with `git ls-files --others --exclude-standard`; no untracked content has been removed or moved.

`git diff --check` passed before this report was added.

## Phase 0 — parity and ownership inventory

### Frontend route/API/asset/test parity

`new_frontend/` was the feature source during parity work; canonical `frontend/` is now active. Rollback copies are preserved under `logs/rollback/` until cleanup is explicitly approved.

| Feature | `new_frontend` source and routes | Legacy `frontend` | `stitch_frontend` | API surface | Assets | Test evidence | Decision |
|---|---|---|---|---|---|---|---|
| Auth | `LoginPageFull`, `SignupPage`, `AuthContext`; `/login`, `/signup` | `LoginPage`, `SignupPage`, `SignUp` | no auth page | `auth/login`, `auth/register`, `auth/me`, terms | logos, auth illustrations | `AuthContext.test`, `SignupPage.test` (currently failing) | reuse new; verify contract |
| Chat | `ChatPageEnhanced`; `/chat`, `/chat/medical-welfare`, `/chat/nutrition`, `/chat/research` | multiple chat pages and `routes.tsx` | `ChatPage` and three chat routes | rooms, session, `/api/chat/message`, `/api/chat/stream` | chat icons/food image flow | `ChatInterface.test`, hooks tests | reuse new; split stream seam later |
| Diet | `DietCarePageEnhanced`; diet care, nutri coach, diet log routes | `DietCarePage`, `DietLogPage`, `NutriCoachPage` | `DietCarePage` | `/api/diet-care/*`, nutrition analysis | `data/Food_StockImage`, upload assets | diet component/API tests (some failing) | reuse new; preserve upload parity |
| Health | `HealthRecordsPage`; profile/test-results routes | health record add/edit/list and profile pages | MyPage health tab only | `/api/health-records/*`, health tracking | health form assets | no explicit PATCH/null contract test | reuse new; add regression first |
| Research / clinical trials | `TrendsPageEnhanced`, `NewsDetailPage`; trends/detail/news routes | trends/news pages | `TrendsPage` | `/api/trends/*`, `/api/clinical-trials/*`, `/api/news/*` | charts and trial cards | clinical trial/trends component tests | reuse new; ADR-004 information-only guard |
| Community | `CommunityPageEnhanced`; community list/detail routes | community list/create/detail/edit | absent | `/api/community/posts/*`, comments, likes, upload | post/upload images | no backend ownership regression | reuse new; add ownership tests |
| Quiz | `QuizListPage`, `QuizPage`, `QuizCompletionPage`; quiz/list/play/level/daily | quiz list/play pages | `QuizPage` | `/api/quiz/session/*`, stats/history, points | quiz illustrations | quiz component tests; backend quiz tests | reuse new; point idempotency gate |
| Account | `MyPageEnhanced`, profile, bookmark, notification, change-password; protected account routes | MyPage/profile/bookmark/notification | MyPage subset | `/api/mypage/*`, bookmarks, notifications, points | avatar/menu assets | MyPage/hooks tests | reuse new; preserve legacy-only routes |
| Legal/support | `LegalPages`, `SupportPage`; terms/privacy/cookie/support | terms/privacy/support pages | absent | `/api/terms`, footer/header | legal icons | no route smoke | reuse new; verify copy |

**Route parity note:** the trees are not name-equivalent. Legacy declares additional routes such as `/dashboard`, `/mypage/test-results/*`, and `/subscribe`; `new_frontend` redirects or renders placeholders for some of them. These require an explicit reuse/replace decision and cannot be solved by renaming a directory.

### Backend feature → endpoint → data → test matrix

| Feature | Entrypoints | Primary data/source of truth | Existing test evidence | Required regression lock |
|---|---|---|---|---|
| Auth/account | `auth.py`, `auth_enhanced.py`, `user.py`, `mypage.py`, `bookmarks.py`, `notification.py` | `users`, bookmarks, notifications, points | partial auth/context coverage | auth, expiry, ownership |
| Chat/session | `chat.py`, `rooms.py`, `session.py`, `careguide.py` | `chat_rooms`, `messages`, session state | `test_chat_endpoints.py`, router tests | stream, emergency bypass, persistence |
| Health | `user_health_records.py`, `health_tracking.py` | `user_health_records`, lab/medication/vital records | partial | PATCH omitted vs explicit `null` |
| Diet/nutrition | `diet.py`, `diet_care.py`, `nutri.py`, `nutrition.py` | diet sessions/meals/goals and data artifacts | `test_diet_care_api.py`, nutrition tests | upload validation and deterministic analysis |
| Research | `trends.py`, research Agent, `news.py` | PubMed/vector artifacts, news cache, daily counter | trends/Agent tests; integration gaps | quota, vector mapping, provider fallback |
| Clinical trials | `clinical_trials.py` | `clinical_trials_cache` (Mongo source of truth) | frontend card/tab tests only | cache fallback, TTL, information-only copy |
| Community | `community.py` | posts/comments/likes/uploads | endpoint coverage incomplete | owner-only edit/delete and upload safety |
| Quiz/points | `quiz.py`, quiz Agent | quiz pool/sessions/history/stats, point ledger | `test_quiz_agent.py` | grading and idempotent points |
| Runtime/health | `main.py`, dependencies, error handlers | process lifecycle; no product cache | import/smoke only | `/health`, provider startup isolation |

### Cache ownership matrix

| Current location | Classification | Key/TTL or bound | Owner/source of truth | Invalidation/authorization gap |
|---|---|---|---|---|
| `clinical_trials.py` dict | domain-persistent | query/condition; currently process-scoped | must become Mongo `clinical_trials_cache` | TTL and authorized clear not explicit |
| `news.py` dict | provider-computation | query; process-scoped | news query adapter; Mongo/disk optional | unrestricted clear and no bounded eviction |
| `pubmed_search.py` translation/count | provider-computation | query/text; process-scoped | PubMed/translation adapter | provider/cache coupled; TTL unclear |
| `vector_manager.py` LRU + pickle | provider-computation | embedding/query; memory+disk | vector/embedding adapter; `data/cache/` artifacts | path, version, invalidation mixed with Pinecone logic |
| research `cache_manager.py` | provider-computation | Redis namespace | injected cache adapter | global lifecycle |
| `translateApi.ts` localStorage | frontend UX | translation key/version | frontend shared cache | schema/version/privacy/eviction tests missing |
| `daily_search_counter` and session TTL | domain-persistent | `{user_id}:{date}` / expiry | local MongoDB | TTL/index verification required |
| `active_streams`, `conversation_states` | runtime state (not cache) | request/session scope | app-scoped stream/session registry | conversation state remains in `context_system`; stream registry seam is isolated |

### Data/script migration candidates

| Current path | Candidate final path | Action | Safety condition |
|---|---|---|---|
| `processed/`, `embedding_cache/` | `data/processed/`, `data/cache/` | inventory then move generated artifacts | manifest and gitignore before move |
| `preprocess/` | `scripts/preprocess/` | move only after import/CLI audit | dry-run and output path tests |
| `backend/scripts/` | `scripts/backend/` or feature-specific `scripts/` | consolidate repeatable DB/index jobs | preserve executable entrypoints |
| `data/*` raw/filtered | remain under `data/` | no rewrite | source-of-truth vs generated manifest |
| `backend/Agent/test`, `backend/tests` | `tests/backend/{unit,integration}` | copy/migrate after fake adapter setup | test imports and live-test classification |
| colocated frontend tests | `tests/frontend` (eventual) | keep local during frontend migration | parity test and Vitest config first |

## Baseline verification before structural changes

| Check | Result | Evidence / implication |
|---|---|---|
| `git diff --check` | PASS | initial tracked changes are whitespace-clean |
| `cd new_frontend && npm run build` | PASS | Vite build completed; warning: `TrendsPageEnhanced` chunk ~610 kB |
| `cd new_frontend && npm run lint` | FAIL | 123 problems (109 errors, 14 warnings), including `_backup_legacy` and source files |
| `cd new_frontend && npm test -- --run` | FAIL | initial baseline was 28 files: 22 failed, 104 failed tests, 17 errors; stale contracts were repaired in the current test-lock pass |
| `.venv/bin/python -m ruff check backend/app/` | BLOCKED | installed environment has no `ruff` module |
| `.venv/bin/python -m pytest -q backend/tests backend/Agent/test` | FAIL/BLOCKED | collection hits live Ollama at `localhost:11434`; process interrupted after connection-refused retries |

These failures are the baseline, not regressions caused by this report. Unit tests must be made provider-independent before large module moves.

## Phase 1 runtime/package evidence

- `docker info` succeeds against Docker Desktop 28.5.2 (ARM64, 8 GiB reported).
- Existing images include `mongo:7` and Pinecone local, but **not** `mongodb/mongodb-atlas-local`; the former is not accepted as vector verification under ADR-005.
- Reference worktree compose uses `mongo:7` only. It is retained as orchestration reference and is not copied.
- Root `docker-compose.yml` now pins `mongodb/mongodb-atlas-local:8.0.6`, includes the required `db`, `configdb`, and `mongot` volumes, and has a healthcheck. `docker compose config` passes.
- The pinned Atlas Local image was pulled successfully (`sha256:e1615c46d1d9c050e89bc7ba296407400ab1583cd29a3c86e7efc31409e0b3c5`); the container reached `healthy`, authenticated `ping` returned `{ok: 1}`, and `scripts/build_vector_index.py` created/recognized `careguide.pubmed_embeddings.vector_index` as `READY`, `vectorSearch`, 1536 dimensions, cosine.
- Ollama 0.32.8 is running at `127.0.0.1:11434` (health endpoint HTTP 200). `qwen2.5:0.5b` generation returned `LOCAL_OK`; `nomic-embed-text` embedding returned a 768-dimensional vector. The latter is a smoke-only local model and **does not match** ADR-005's 1536-dimensional production index, so no schema substitution was made.
- Root `requirements.txt` and `backend/requirements.txt` overlap but differ materially. No upgrade or deletion has been performed; dependency graph and supported-version review are prerequisites.
- Node lockfiles exist for all three frontend trees. No package upgrade has been performed before canonical frontend consolidation.
- After verification, the Atlas Local compose service was stopped without removing its ignored `data/.mongo/` volumes, and the temporary Ollama process was stopped; downloaded model artifacts remain managed by Ollama outside the repository.

## Decision gates and remaining risks

### Phase 3 risk register (current residual risks)

| Severity | Area | Evidence | Safe disposition |
|---|---|---|---|
| MEDIUM | Chat room ownership | room endpoints require a JWT subject and reject mismatched caller-supplied IDs; authenticated CRUD/history coverage passes against the live local Mongo runtime | keep the token subject authoritative when adding new room routes |
| MEDIUM | Process-global agent/service state | Chat stream, router, nutrition, quiz/agent-manager, context/session, and trends provider state now resolve through app-scoped runtime seams; remaining import-time objects are registry metadata, bounded caches, or stateless compatibility services | migrate remaining services opportunistically; do not put user/session state back in module globals |
| MEDIUM | Local embedding retrieval quality | Ollama smoke is successful; `nomic-embed-text` 768d vectors are expanded losslessly to the required 1536d index width, but representative retrieval-quality evaluation is still required | keep the width policy in Proposed ADR-010 and compare recall/precision before changing the accepted vector decision |
| MEDIUM | Frontend lint debt | canonical lint exits successfully with 0 errors and 71 warnings; warnings are explicit compiler/dynamic-boundary/Fast Refresh advisories | reduce warnings by rule family without reintroducing a second frontend root |
| MEDIUM | Dependency convergence | root/backend application requirements are represented by one reviewed compiled lock; `dnspython` is pinned at 2.7.0 to satisfy the installed email-validator contract | rerun the lock and clean-environment checks whenever the dependency graph is upgraded |

| Gate | Status | Next action |
|---|---|---|
| Existing implementation vs rebuild | KEEP/REPAIR provisionally | Contracts are discoverable; add golden tests and fake adapters before deciding |
| Frontend rollback cleanup | DEFERRED safely | parity passed and canonical `frontend/` is active; rollback trees are retained under `logs/rollback/` because they contain user/reference material |
| Local vector runtime | PASS | Atlas Local 8.0.6 health + 1536d cosine index verified; keep image tag pinned |
| Local model smoke | PASS with quality follow-up | local generation and Ollama embedding work; adapter exposes 1536d vectors through a documented lossless width policy |
| CRITICAL/HIGH risk count | ZERO in reviewed scope | Remaining findings are MEDIUM and are recorded above; no accepted ADR was changed |
| Top-level cleanup | PASS for visible product roots | canonical `frontend/` is active; rollback/generated/data candidates are under `logs/rollback/`, `scripts/`, or `data/`; hidden tool/runtime dirs (`.venv`, `.git`, `.omx`) are intentionally retained |

### Next phase prerequisites

1. Select and verify an Ollama-compatible 1536-dimensional embedding model, or retain the external 1536d adapter as an explicit opt-in.
2. Run provider-backed Mongo query and LLM stream p50/p95 benchmarks with representative fixtures; the checked-in fake-adapter baseline must not be used as provider latency.
3. Profile frontend rerenders in a browser when a browser-driver tool is available; the HTTP E2E is delivery-only.
4. Define recovery/expiry for points reservations and reduce the documented legacy Ruff/query-plan debt in bounded follow-up changes.

## Changes made after the initial record

- Added `docker-compose.yml` for pinned Atlas Local runtime and `scripts/build_vector_index.py` for idempotent vector index setup.
- Added `backend/app/utils/upload.py` and hardened community image uploads against path traversal, non-image MIME types, and files over 10 MiB.
- Added admin authorization to the news cache-clear endpoint.
- Added deterministic unit coverage under `tests/backend/unit/` for health PATCH/null semantics, emergency pre-filter, chat SSE stream framing/persistence, upload validation, cache-clear authorization, clinical-trial cache isolation/fallback, points idempotency seam, room ownership, chat query indexes, app-scoped stream/context/agent/research runtime seams, local embedding dimension guard, and vector index schema (`42 passed`, 18 existing deprecation/future warnings).
- Added app-scoped `ResearchRuntime` for trends, PubMed, summarization, and news provider clients; import-time provider construction is no longer required by the trends routes.
- Added a unique sparse points-history idempotency index and stable quiz-completion event key; quiz completion now writes the canonical points ledger without awarding the same session twice on retry.
- Clinical-trial cache keys now include status filters, expired responses remain available for bounded stale fallback, translation cache entries use the same TTL, and OpenAI summarization is lazy/opt-in rather than an import-time global client.
- Fixed the all-terms checkbox accessibility contract in `new_frontend`; the focused suite passes. Repaired stale selectors, UTF-8-corrupt fixtures, Jest globals, async room creation tests, Router/Auth fake seams, and current diet-care API signatures without adding a test dependency.
- Full frontend Vitest now passes: `168` suites and `405` tests, `0` failures. The canonical production build passes (`tsc -b && vite build`); the largest warning chunk is `TrendsPageEnhanced` at ~610 kB.
- After parity approval, canonical source was synchronized from `new_frontend/` into `frontend/` with user `.DS_Store`/`.claude` settings preserved; `frontend` build passes and canonical Vitest reports `29` files/`406` tests with `0` failures. The source is preserved under `logs/rollback/` for recovery.
- Canonical frontend package metadata now uses `careguide-frontend` in both `frontend/package.json` and `frontend/package-lock.json`; build and 406-test Vitest reruns remain green.
- Rollback trees were moved (not deleted) to `logs/rollback/new_frontend-rollback/` and `logs/rollback/stitch_frontend-rollback/`; `scripts/check_frontend_parity.py` now validates canonical `frontend/` against that preserved source. This keeps the allowed product top-level namespace while retaining recovery material.
- Generated data/runtime candidates were moved into allowed roots: preprocessing tools to `scripts/preprocess/`, duplicate processed exports to `data/processed_legacy/`, embedding cache to `data/cache/embedding/` with the vector manager default updated, and root `node_modules/` to `logs/rollback/root-node_modules/`. No generated artifact was deleted.
- Vitest-only environment defaults are mode-gated in `vitest.config.ts`; production builds continue to read `.env.production` and do not receive the test localhost substitution.
- Added Proposed ADR-010 documenting the local embedding width guard without changing Accepted ADR-005.
- Payment residue scan is now clean across `backend/`, all frontend trees, `scripts/`, and `tests/`; the deprecated Stitch env's unused Stripe key was removed. No payment SDK, UI, or endpoint was added.
- `npm run lint` now exits successfully with `0 errors` and `71 warnings`; the warnings are explicit dynamic-boundary types, effect/compiler advisories, and Fast Refresh export advisories. Preserved `_backup_legacy` is excluded from lint but remains recoverable.
- Added a dependency-free HTTP-level frontend E2E smoke at `tests/e2e/test_frontend_delivery.py`; the production Vite artifact serves six canonical SPA routes (`6 passed`). Browser-driver E2E remains unclaimed because Playwright is not a canonical dependency.
- Added live authenticated Mongo room CRUD/history coverage (`1 passed`) and retained the vector-index smoke (`1 passed`) against pinned Atlas Local. Added `pytest.ini` integration markers so default tests remain provider-independent (`42 passed`); Mongo/Ollama/preview checks are opt-in integration tests.
- Added `backend/requirements.lock`, an exact transitive snapshot of the union of root/backend application requirements so route adapters are included; `toon-python` was removed as unused and replaced by the actually imported `toon-format` pin. No unbounded `latest` specifier was introduced.
- Lock reproducibility check: `pip install --dry-run --no-index --no-deps -r backend/requirements.lock` reports every pinned package already satisfied.
- Ruff is installed only in the development environment for verification; the full legacy `backend/app` scan reports 2,021 findings, while all newly added/edited test and parity scripts pass Ruff with zero findings.
- Added `docs/agents/CARE_GUIDE_PERFORMANCE_BASELINE.md` with measured artifact/cache/index evidence and explicit deferrals for provider-dependent stream/query p50/p95 profiling.
- Added idempotent `chat_rooms`/`conversation_history` compound indexes for owner filtering, room sorting, and timestamp-descending history reads; live Atlas Local listing confirmed all four names.
- Added `backend/app/features/{chat,diet,health,research,community,quiz,account}` boundaries and `ports`/`adapters` seams; chat and research API imports now resolve through feature-owned runtime modules while compatibility imports remain documented for older callers.
- Moved project documentation into `docs/` (`docs/project-plans`, `docs/backend`, `docs/frontend`, `docs/scripts`, and `docs/data`) and moved runtime/legacy logs into `logs/` (`logs/backend`, `logs/runtime`, `logs/legacy`, and `logs/rollback`). The root `AGENTS.md` remains at the repository root as the execution contract; generated `.pytest_cache` metadata and dependency-vendored READMEs are tooling exceptions.
- Added Ollama's local embedding adapter with a fail-closed dimension policy and cosine-preserving 768d-to-1536d expansion; local smoke passed with `nomic-embed-text` and 1536 output dimensions.
- Added stale points-reservation expiry (`300s`) with audit-preserving `expired` status and a `(status, createdAt)` recovery index; stale reservations never auto-award points.
- Added provider-backed performance artifacts: Ollama generation/embedding, indexed Atlas Local room/history queries, Vite delivery, and Chrome CDP navigation/paint profiles under `eval/`.
- Added `dnspython==2.7.0` to the reviewed requirement sources and lock; the installed environment now satisfies the email-validator dependency contract.
- Added `scripts/benchmark_runtime.py` and `eval/performance_baseline.json`; 25 provider-independent chat stream requests measured route/SSE/fake-persistence overhead at p50 `0.451 ms` and p95 `0.760 ms`. The scope explicitly excludes LLM, network, and MongoDB latency.
- Added local runtime directories to `.gitignore`; runtime data remains outside the product source-of-truth.
- Narrowed `.gitignore` to ignore only `/data/.mongo/` rather than the whole `data/` root, keeping moved source/generated manifests discoverable without tracking Mongo runtime volumes.
- Hardened the secondary JWT dependency seam: it now uses the application secret configuration, fails closed when the secret is missing or malformed, and converts malformed admin ObjectIds into 401 responses. Focused regression coverage passes (`12 passed` across auth, cache authorization, and upload validation tests).

### Latest verification after the auth hardening

- Root deterministic suite: `./.venv/bin/python -m pytest -q` → `42 passed, 10 deselected`; the room ownership, chat stream, query-index, app-scoped stream/context/agent/research runtime, and local embedding imports add existing Pydantic/LangChain/Transformers warnings but no failures.
- `git diff --check` → PASS.
- Python compile check for the changed dependency module → PASS.
- FastAPI route registration smoke → PASS (`103` paths; required chat/session/rooms/nutrition/trends/quiz paths present).
- No artifact deletion or commit was performed; preserved rollback trees remain available under `logs/rollback/`.
- Explicit integration selection now has an authenticated room HTTP contract smoke (`2 passed`) using an injected local fake store, a live Atlas Local vector-index smoke (`1 passed`), authenticated live room CRUD/history (`1 passed`), and canonical frontend HTTP E2E (`6 passed`) using the pinned `mongodb/mongodb-atlas-local:8.0.6`; the repository's `pytest.ini` intentionally scopes default collection to `tests/`, while live Mongo/Ollama/preview checks remain opt-in.
- Chat room create/list/read/update/delete/history now require a JWT subject and reject caller-supplied user IDs that do not match it; a focused ownership seam test passes (`2 passed`).
- The room change is deliberately contract-preserving for authenticated clients: existing `user_id` query/body fields remain accepted, but are checked against the token rather than trusted as authority.

## Phase output summary

| Phase | Changed areas | Verification | Remaining risk / next precondition |
|---|---|---|---|
| 0 inventory | status snapshot, parity/matrices, migration candidates | initial `git status`/diff/untracked record; parity PASS | rollback material remains until an explicit retention decision |
| 1 local runtime/package | Atlas Local compose/index script, Ollama checks, compiled backend lock | `docker compose config`; Atlas Local health/vector READY; Ollama 1536d smoke; lock dry-run | retrieval quality for lossless local expansion needs representative evaluation |
| 2 tests | backend unit/integration contracts, frontend Vitest and HTTP E2E | backend `42 passed`; frontend `406 passed`; E2E `6 passed` | browser-driver E2E remains unavailable by design |
| 3 risk | upload/auth/cache/ownership/idempotency/global-state seams | focused tests, payment scan clean, CRITICAL/HIGH zero | points reservation recovery and legacy Ruff debt remain MEDIUM |
| 4 frontend | canonical `frontend/`, preserved rollback trees, parity checker | parity PASS; build PASS; lint `0 errors/71 warnings` | remove rollback copies only after a separate retention decision |
| 5 backend/data/cache | app-scoped runtimes, feature/port/adapter boundaries, chat/history indexes, data/scripts consolidation | live index listing; room CRUD/history and vector integration PASS | remaining nutrition parity and aggregation query-plan comparison need follow-up |
| 6 performance | deterministic, provider, database, delivery, and browser profiles | Ollama, Atlas Local, Vite, and Chrome artifacts recorded under `eval/` | browser artifact covers navigation/paint, not full interaction rerender tracing |

## Current gate summary

- **Parity:** `scripts/check_frontend_parity.py` → PASS; canonical `frontend` preserves required feature routes plus explicit legacy aliases, API contract references, matching public assets, and feature test coverage. Rollback trees are preserved under `logs/rollback/`.
- **Tests:** backend deterministic `42 passed`; canonical `frontend` Vitest `406 passed` (170 suites); canonical `frontend` build PASS; frontend lint PASS (`0 errors`, 71 warnings); HTTP-level frontend E2E `6 passed`; browser-driver E2E remains out of scope because Playwright is not installed.
- **Runtime:** Atlas Local 8.0.6 and vector index smoke PASS; Ollama generation and the documented 1536d embedding adapter smoke PASS.
- **Performance:** fake-adapter stream p50 `0.451 ms` / p95 `0.760 ms`; Ollama generation p50/p95 `184.492/1309.939 ms`, embedding `26.041/154.907 ms`; indexed Mongo room/history p95 `0.764/0.596 ms`; Chrome navigation/paint metrics are in `eval/frontend_browser_profile.json`.
- **Risk:** CRITICAL/HIGH = 0 in the reviewed scope; remaining MEDIUM items are retrieval-quality evaluation for local expansion, legacy Ruff/query-plan debt, and retention of rollback copies.
- **Post-gate follow-ups:** run representative retrieval-quality and aggregation `explain()` comparisons, reduce legacy Ruff debt in bounded slices, and decide whether preserved rollback copies under `logs/rollback/` may be removed. Canonical `frontend/` sync, lint, HTTP E2E, and visible-root consolidation are complete; no user settings were removed.

## Latest follow-up verification (2026-08-12)

- `./.venv/bin/python -m pytest -q`: **45 passed, 10 deselected** (the
  deselected cases are opt-in integration tests).
- `frontend`: Vitest **29 files / 406 tests passed**, production build passed,
  and ESLint passed with **0 errors / 71 warnings**.
- `scripts/check_frontend_parity.py`: **PASS**; no missing routes, APIs, or
  feature tests.
- Atlas Local opt-in integration: vector index and authenticated room
  CRUD/history **2 passed** when run with approved local-network access.
- `pip check`: **No broken requirements**; lock dry-run reports every pinned
  package already satisfied, including `dnspython==2.7.0`.
- Project markdown is under `docs/` and runtime/legacy logs are under
  `logs/`; only the root `AGENTS.md`, hidden tool metadata, vendored
  dependency READMEs, and reference worktrees remain outside that policy.
- Temporary Atlas Local containers were stopped after verification; ignored
  local volumes were preserved.
