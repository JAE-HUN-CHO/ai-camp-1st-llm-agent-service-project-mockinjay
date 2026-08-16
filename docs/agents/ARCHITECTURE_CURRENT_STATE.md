# CareGuide 현재 아키텍처 및 시스템 상태

**작성일:** 2026-08-16
**최종 갱신일:** 2026-08-17
**상태:** 사실 기준 문서
**목적:** Phase 0 이전 기준선과 Phase 0~3B gate 이후 상태를 구분해 기록한다.
**Baseline commit:** `fda93b9dbb81` (`codex/ollama-integration-smoke-fix`)

> 이 문서는 완료 보고서가 아니다. 문서에 존재하는 계획과 실제 실행 증거를 구분한다.
> 도메인은 [`domain.md`](./domain.md)의 규칙대로 하나의 CKD bounded context로 유지한다.

## 상태 시점과 증거 식별자

| 시점 | 식별자 | 의미 |
|---|---|---|
| Phase 0 이전 baseline | Git `fda93b9dbb81` | 아래 구조 분석을 시작한 코드 기준점 |
| Phase 0~1 최종 runtime gate | run `20260815T143102Z`, worktree fingerprint `d5f1f73380f1f107e6ed2861032fc89b929f32553e5fe5ee3145a85fa45dfb04` | Research/Welfare 실제 HTTP와 31개 명령의 로컬 evidence |
| ADR-013 owner 승인 기록 | run `20260816T004558Z`, worktree fingerprint `db41dc55c9387f22f27153e64f904982974ffba8948179fd78911a84aca1f56f` | Accepted 전환과 Phase 2 Chat 범위 승인 evidence |
| Phase 2 Chat 고정 gate | Git `0d435fc48d35d1650fddd4375746f0e74e63c320`, run `20260816T044829Z` | frozen v1, 저장 멱등성, hex 5회 REST/SSE canary, legacy rollback evidence; fingerprint는 manifest가 authoritative |
| Phase 3A Health Records 고정 gate | Git `12199ec324efa1f47ccfa3f78e45fbe18b6e9085`, run `20260816T132213Z` | active REST v1/schema 보존, owner isolation, hex 실제 HTTP와 selector-unset legacy rollback; fingerprint는 manifest가 authoritative |
| Phase 3B Health Profile 고정 gate | Git `20d714a6b2bafd0d9b3ca97a66940b5f22a57404`, run `20260816T173056Z` | active MyPage REST v1/`health_profiles` schema 보존, legacy/hex 실제 HTTP, owner isolation, invalid selector fail-closed evidence; fingerprint는 manifest가 authoritative |

다섯 run의 manifest는 각각
`logs/verification/fda93b9dbb8107ecbffa593041c9417f822a6688/20260815T143102Z/manifest.json`과
`logs/verification/fda93b9dbb8107ecbffa593041c9417f822a6688/20260816T004558Z/manifest.json`,
`logs/verification/0d435fc48d35d1650fddd4375746f0e74e63c320/20260816T044829Z/manifest.json`,
`logs/verification/12199ec324efa1f47ccfa3f78e45fbe18b6e9085/20260816T132213Z/manifest.json`,
`logs/verification/20d714a6b2bafd0d9b3ca97a66940b5f22a57404/20260816T173056Z/manifest.json`에 있다.
`logs/`는 git-ignored 로컬 evidence이므로 Git SHA만으로 dirty-worktree 실행을 재현했다고 간주하지
않고, 반드시 worktree fingerprint까지 함께 대조한다. 이후 PR head의 정적/단위 회귀는 별도 gate이며
이 장시간 HTTP run을 같은 SHA에서 다시 실행했다는 뜻이 아니다.

## 1. 현재 런타임 계약

- canonical frontend는 `frontend/`이다.
- FastAPI 진입점은 `backend/app/main.py`이다.
- Agent 구현은 `backend/Agent/`에 있지만 HTTP 런타임 조립·lifecycle은
  `backend/app/services/agent_runtime.py`와 `backend/app/main.py`가 소유한다.
- 기본 `OLLAMA_ENABLED=true` chat 경로는 Router/5개 capability를 거치지 않고
  `OllamaChatService`를 직접 호출한다. Router/AgentManager 경로는 compatibility fallback이다.
- `CHAT_IMPLEMENTATION`은 API composition root에서 한 번만 평가하며 미설정 기본값은
  `legacy`다. 명시적 `hex`는 `SendChatMessage`/`StreamChatMessage`와 MongoDB/Ollama adapter를
  호출하고 실패 시 다른 provider로 fallback하지 않는다.
- `HEALTH_RECORDS_IMPLEMENTATION`도 같은 composition root에서 한 번만 평가하며 미설정 기본값은
  `legacy`다. 명시적 `hex`는 Health Records application use case와 owner-scoped MongoDB adapter를
  호출하고, legacy facade는 process restart rollback을 위해 유지한다.
- `HEALTH_PROFILE_IMPLEMENTATION`은 같은 composition root에서 한 번만 평가하며 미설정 기본값은
  `legacy`다. 명시적 `hex`는 Health Profile application use case와 owner-scoped MongoDB adapter를
  호출하고, 잘못된 값은 HTTP ready 전에 fail-closed한다.
- 생성·임베딩 기본 provider는 로컬 Ollama이다.
- 데이터베이스와 vector search는 로컬 Docker MongoDB 계약을 따른다.
- Parlant Research/Welfare는 별도 서버 진입점과 포트(`8800`/`8801`)를 가진다. 위 Phase 1
  runtime gate에서 각 customer/session/message 왕복과 agent identity를 검증했다.
- ClinicalTrials.gov detail은 원문, 선택적 충실 번역, 출처, 정보 제공 면책만 반환한다.
  이전 `aiSummary` 생성 경로는 제거됐고 cache key는 source-faithful contract version으로 격리한다.
- 결제 기능과 결제 SDK는 범위에서 제외한다.
- ADR-006이 구현됐다고 기록한 `daily_search_counter` 10회 제한은 현재 활성 코드·index가 없다.

근거: [`ADR-011`](../adr/ADR-011-current-runtime-contract.md),
[`BOUNDARY_MAP.md`](./BOUNDARY_MAP.md), [`domain.md`](./domain.md).

## 2. 현재 구조

```text
frontend/
  pages, features, components, hooks, services, types
        │ REST / SSE
        ▼
backend/app/
  api/ → features/{chat,health}/application → domain/ports ← MongoDB/Ollama adapters
       → legacy services/Agent compatibility facade
        │
        ├── app/features/       # account/chat/community/diet/health/quiz/research
        ├── app/ports/          # llm/embedding/vector/external_search Protocol
        ├── app/adapters/ollama/
        ├── app/repositories/
        └── app/db/

backend/Agent/
  AgentManager / Router / LocalAgent / RemoteAgent(미사용 공통 구현)
        ├── Nutrition / Quiz / Trend Visualization
        └── Research Paper / Medical Welfare → Parlant HTTP

MongoDB local Docker + Ollama local runtime
```

현재 runtime ownership은 분산되어 있다. `backend/app`이 HTTP-scoped runtime과 Parlant proxy를
조립하고 `backend/Agent`가 Agent 구현과 Parlant server 코드를 가진다. Chat, active Health
Records, active MyPage Health Profile은 각각 Phase 2, Phase 3A, Phase 3B에서 production-selectable
hexagonal seam이 됐지만, 나머지 `app/features`의 대부분은 metadata/naming anchor이고 기존
`app/ports` 네 개는 production consumer가 확인되지 않았다. 따라서 이 세 slice 이외를 완성된
hexagonal seam으로 간주하면 안 된다. 특히 Nutrition은
`backend/agents/`와 `backend/Agent/`에 구현이 중복되어 있다.

## 3. 구현상 강점

| 영역 | 현재 상태 |
|---|---|
| 외부 provider | Ollama, MongoDB, PubMed, Parlant를 adapter/client 형태로 분리하려는 구조가 존재한다. |
| Agent 공통 계약 | `Agent/core/contracts.py`, `local_agent.py`, `remote_agent.py`가 공통 실행 계약을 제공한다. |
| 기존 port | `app/ports/llm.py`, `embedding.py`, `vector.py`, `external_search.py`가 정의돼 있으나 production wiring/consumer는 확인되지 않았다. |
| 기존 feature seam | Chat, active Health Records, active MyPage Health Profile은 domain/application/port와 real adapter가 wiring됐다. `research`에는 runtime이 있고 다른 feature는 주로 metadata/naming anchor다. |
| API 계층 | 도메인별 FastAPI router와 service/repository 계층이 존재한다. |
| 데이터 경계 | MongoDB repository·vector adapter·local data 처리 경계가 문서화되어 있다. |
| 런타임 안전 | 포트 검증, embedding 차원 검증, Ollama-only 정책, emergency pre-filter가 존재한다. |
| 검증 기반 | Phase 1 Research/Welfare 및 Chat HTTP 증거는 존재하지만, 전체 API와 실제 browser 사용자 여정 gate는 아직 미완료다. |

### 이미 구현된 비동기 경계

알림 outbox는 신규 설계가 아니라 현재 구현이다. `notification_service.py`에 event id,
atomic lease, backoff, terminal failure가 있고 FastAPI lifespan이 in-process periodic task를
시작한다. 별도 worker 프로세스와 live 실패→재시도 증거, backlog 진단은 없다. ADR-012는
여전히 Proposed이므로 구현 사실과 결정 승인을 구분한다.

## 4. 구조적 결합

### 4.1 API와 업무 로직의 결합

일부 대형 router가 HTTP validation, DB query, 외부 provider 호출, cache, 응답 변환을 동시에 수행한다.
Chat, active Health Records, active MyPage Health Profile의 명시적 hex 경로는 use case로 분리됐지만 frozen v1과 rollback을
위한 legacy facade가 남아 있으므로 이 결합을 전체 제거한 것으로 해석하지 않는다.

- `backend/app/api/community.py`
- `backend/app/api/chat.py`
- `backend/app/api/diet_care.py`
- `backend/app/api/clinical_trials.py`

이 구조에서는 API를 바꾸지 않고 business rule만 테스트하거나, provider를 fake로 교체하기 어렵다.

### 4.2 Agent와 infrastructure의 결합

일부 Agent가 MongoDB collection, Ollama client, 포인트 service를 직접 생성·호출한다.

- `backend/Agent/quiz/agent.py`
- `backend/Agent/api/mongodb_client.py`
- `backend/Agent/router/agent.py`
- `backend/Agent/nutrition/agent.py`

Agent는 입력 해석과 응답 조합을 담당하고, DB transaction·권한·도메인 정책은 application/domain 계층이 소유해야 한다.

### 4.3 Research 서버의 책임 집중

`backend/Agent/research_paper/server/healthcare_v2_en.py`는 서버 lifecycle, Parlant 등록, NLP, 검색, cache, tool, 안전 지침을 넓게 포함한다. 이 파일은 adapter/bootstrap과 도메인 규칙을 분리할 우선순위가 높다.

### 4.4 전역 mutable state와 cache 결합

상태의 scope가 서로 다르다.

- Chat `StreamRegistry`: `request.app.state`가 소유하는 application-scoped, process-local state
- Nutrition `conversation_states`: Agent instance-scoped state
- `AgentRegistry`: decorator/import-order 기반 global registry
- Chat `_background_tasks`: module-global task set
- provider cache: 일부 process-local mutable cache

이 값들은 일반 cache와 runtime state를 구분하고, 소유권·수명·다중 프로세스 동작을 명시한 뒤 composition root에서 조립해야 한다.

## 5. 현재 검증 상태

Phase 0 이전 baseline 확인과 Phase 0~3B 이후 검증을 섞어 읽지 않는다. 아래는 gate 이후 로컬 evidence다.

정적 검사 첫 네 행은 당시 console 결과이며 영구 artifact가 없다. Phase 0~1 runtime evidence는
`20260815T143102Z` manifest와 그 하위 HTTP/runtime artifact에 보관한다. Phase 2, Phase 3A,
Phase 3B evidence는 이 문서 상단 표에 분리해 적은 각 manifest를 따른다.

백엔드 테스트 루트는 마이그레이션과 legacy 회귀 보존을 위해 의도적으로 병존하며,
Phase 0~1에서는 통합하거나 이동하지 않는다.

| 테스트 루트 | 역할 | 실행 명령 |
|---|---|---|
| `tests/backend/unit/` | Phase 0~1 안전·계약·검증 도구의 격리 단위 회귀 | `PYTHONPATH=backend .venv/bin/python -m pytest -q tests/backend/unit` |
| `tests/backend/integration/` | 로컬 Docker MongoDB를 사용하는 명시적 통합 경계 | `docker compose up -d mongodb` 후 `PYTHONPATH=backend .venv/bin/python -m dotenv run -- .venv/bin/python -m pytest -q -m integration tests/backend/integration` |
| `backend/tests/` | 기존 API·서비스 회귀를 보존하는 legacy suite | `PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests` |

| 검증 | 결과 | 의미 |
|---|---|---|
| `cd frontend && npm run build` | 통과 | TypeScript compile 및 Vite production bundle 생성; 보관 artifact 없음 |
| `cd frontend && npm run lint` | 오류 0, 경고 70 | 정적 오류는 없지만 hook/`any`/번들 관련 정리 필요 |
| `cd frontend && npm run test -- --run` | 30 files, 410 tests passed | unit/component 범위이며 실제 browser E2E는 아님 |
| `PYTHONPATH=backend .venv/bin/python -m pytest -q tests/backend/unit/test_api_contract.py tests/backend/unit/test_logging_redaction.py tests/backend/unit/test_ollama_chat_service.py` | 8 passed | 핵심 단위 계약 일부 통과 |
| Research Parlant HTTP | 통과 | agent/customer/session/response event 식별자는 `<redacted>`; run ID·manifest·fingerprint로 추적 |
| Welfare Parlant HTTP | 통과 | agent/customer/session/response event 식별자는 `<redacted>`; run ID·manifest·fingerprint로 추적 |
| hosted LLM provider | 호출 0 | 최종 승인 run의 manifest/runtime log 기준 |
| Phase 3A Health Records 실제 HTTP | legacy/hex 각각 CRUD·날짜 내림차순·정확한 error detail·cross-user 2/2·delete retry 통과 | selector-unset legacy rollback, unauthorized write·PII·synthetic 잔존 0 |
| Phase 3B Health Profile 실제 HTTP | legacy/hex 각각 GET·PUT·null/unset·422·cross-user 3/3 통과 | 기본값 legacy, invalid selector bounded non-zero, unauthorized write·PII·synthetic 잔존 0; hosted call 0은 구조·runtime 설정·import gate 기반 local-only 파생 판정 |
| 전체 핵심 API·브라우저 흐름 | 미완료 | Phase 2 Chat·Phase 3A Health Records·Phase 3B Health Profile 이외의 실제 사용자 여정은 아직 범위 밖 |

2026-08-16 CodeRabbit 후속 수정은 기존 Phase 0 runtime manifest를 대체하지 않는
PR console 검증이다. 해당 worktree에서 `tests/backend/unit`은 165 passed(55 warnings),
명시적 Mongo integration은 4 passed(26 warnings), frontend는 31 files/416 tests passed,
build 통과, lint 0 errors/64 warnings였다. 변경 Python Ruff, architecture dependency gate,
15개 normative 문서 링크, `git diff --check`가 통과했고 보존된 runtime artifact 37개에서
PII pattern은 0건이었다.

`tasks/plan.md`와 `tasks/todo.md`의 체크리스트는 계획 문서이며, 체크되지 않은 항목을 실행 증거로 간주하지 않는다.

Phase 2 최종 run은 frozen REST/SSE v1 fixture, emergency/ownership/PII/import gate, MongoDB
순차·동시 idempotency 통합 테스트, 명시적 `hex` REST 5회·SSE 5회와 process-restart legacy
rollback을 한 worktree fingerprint로 묶는다. 원문 prompt/response는 저장하지 않고 hash·length·status만
artifact에 남긴다. exact 수치와 argv는 `20260816T044829Z/manifest.json`을 기준으로 한다.

Phase 3A 최종 run은 frozen Health Records REST v1 fixture, legacy/hex fake adapter 단위 테스트,
로컬 MongoDB 명시적 integration, import gate, selector invalid/default/rollback, 실제 CRUD·cross-user·
날짜 내림차순·정확한 error detail·null/unset·delete retry HTTP를 한 manifest로 묶는다. 최종 수치는
backend unit/delivery 245, Mongo integration 7, frontend 31 files/428 tests이며 건강값과 JWT는
artifact에 저장하지 않고 body/record ID hash·length·status만 남긴다. exact argv와 단계별
worktree fingerprint는 `20260816T132213Z/manifest.json`을 기준으로 한다.

Phase 3B 최종 run은 frozen `GET/PUT /api/mypage/health-profile` REST v1 fixture, legacy/hex
fake adapter 단위 테스트, 로컬 MongoDB 명시적 integration, import gate, selector default/invalid,
실제 GET·PUT·null/unset·422·cross-user HTTP와 schema/index audit를 한 manifest로 묶는다. 최종 수치는
backend unit 285, Mongo integration 8, frontend 32 files/432 tests이며 건강값과 JWT는 artifact에
저장하지 않고 body/owner ID hash·length·status만 남긴다. exact argv와 worktree fingerprint는
`20260816T173056Z/manifest.json`을 기준으로 한다. Health Profile에는 provider port가 없고 검증
환경의 Ollama·hosted credential을 제거했으며 import gate가 이를 보강한다. 따라서 hosted provider
호출 0은 packet capture 실측값이 아니라 해당 구조·runtime 설정에서 파생한 값으로 표시한다.

## 6. 운영 판정

현재 시스템은 **내부 개발·QA 데모 전용**이다. 공개 운영과 외부 파일럿은 NO-GO다.
Phase 0은 access token의 `localStorage` 저장·복원과 민감 console/raw log 경로를 제거했고,
Phase 2, Phase 3A, Phase 3B는 각 slice의 로컬 canary와 rollback까지 통과했지만 공개 운영 승인에 필요한
다음 gate는 남아 있다.

1. CI와 릴리스 gate
2. 실제 browser E2E와 전체 사용자 여정
3. 외부 pilot/production profile, TLS/HA/managed DB에 대한 별도 운영 ADR
4. Phase 3C dormant Health 결정과 Phase 6 research-owned `DailySearchQuota`의 별도 범위 승인

이 문서에서 “현재 adapter가 존재한다”는 표현은 “provider 교체가 완전히 검증됐다”는 의미가 아니다.
