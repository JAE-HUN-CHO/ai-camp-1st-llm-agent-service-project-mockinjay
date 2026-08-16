# CareGuide 아키텍처 리팩토링 실행 계획

**작성일:** 2026-08-15
**최종 갱신일:** 2026-08-17
**상태:** Phase 0~2와 Phase 3A~3B verified; Phase 3C 이후 별도 승인 필요
**전제:** 현재 API·MongoDB·Ollama·Parlant 계약을 보존하는 점진적 strangler refactor

**착수 판정:** Phase 0~2는 완료·검증됐고 owner가 Phase 3A `/api/health-records`와 Phase 3B
`/api/mypage/health-profile`을 순서대로 별도 승인했다. Phase 3C 또는 이후 phase는 승인하지 않았다.
**Tracking:** [GH-#30](https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-mockinjay/issues/30), [GH-#31](https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-mockinjay/issues/31)

실제 실행 작업에 전달할 복사 가능한 지시문과 계량 성공조건은
[`ARCHITECTURE_REFACTORING_EXECUTION_PROMPT.md`](./ARCHITECTURE_REFACTORING_EXECUTION_PROMPT.md)를 사용한다.

## 실행 원칙

1. 한 번에 전체 구조를 재작성하지 않는다.
2. 한 vertical slice마다 구현·정적검사·단위테스트·실서비스 smoke를 모두 통과시킨다.
3. 기존 endpoint는 compatibility facade로 유지한다.
4. untracked `data/`와 생성 artifact는 변경 범위에 포함하지 않는다.
5. 실패한 runtime gate를 문서에 남기고, 통과 전 다음 gate로 넘어가지 않는다.
6. [`ADR-013`](../adr/ADR-013-feature-first-hexagonal-modular-monolith.md)의 범위에 따라 승인된 Phase 3B에서 멈추고 Phase 3C 이후는 별도 승인 전 실행하지 않는다.

## Phase 0 — 기준선과 안전장치

- [x] 현재 API/DB/Agent 계약을 `ARCHITECTURE_CURRENT_STATE.md`와 대조
- [x] [`ARCHITECTURE_REFERENCE_ALIGNMENT.md`](./ARCHITECTURE_REFERENCE_ALIGNMENT.md)의 ATAM-lite workshop 수행
- [x] quality scenario → decision → test → artifact traceability matrix 작성
- [x] P0 API misuse/abuse case와 threat model 작성
- [x] ADR-004 위반인 ClinicalTrials `aiSummary` 생성 경로 제거/비활성화
- [x] token/user/SSE console log와 credential/chat localStorage 위반 제거
- [x] 모든 chat 경로의 emergency short-circuit와 room/session owner 검증을 characterization test로 고정
- [x] ADR-013 review 및 Accepted 여부 확인
- [x] `git status`, worktree, generated data를 기록
- [x] `ruff`, frontend lint/build, targeted pytest 기준 결과 저장
- [x] import 방향 규칙과 금지 목록을 문서화
- [x] `route → service/runtime → collection/schema → test` inventory 작성
- [x] `app/features/*`, `app/ports/*`, `app/adapters/*`를 `사용 중/정의만/확장/대체/폐기`로 분류
- [x] capability별 application owner와 inbound/outbound/facade/fake/real-smoke mapping 작성
- [x] health/rewards/quota canonical vocabulary·aggregate owner·schema 결정
- [x] `diet → nutrition`, `ollama_rag`, `RemoteAgent`, Parlant client 4종의 keep/delegate/delete 결정
- [x] `CHAT_IMPLEMENTATION=legacy|hex` 등 slice별 selector와 rollback drill 합의
- [x] import-linter 또는 동등한 AST dependency 검사를 필수 gate로 선택
- [x] unversioned `/api/chat/*` endpoint inventory(method/path/auth/aliases/content-type/schema/owner) 작성
- [x] endpoint inventory에 actor/resource owner, quota, sensitive fields, logs, lifecycle 추가
- [x] risk/non-risk, sensitivity point, tradeoff, owner를 architecture risk register에 기록

**완료 조건:** P0 safety 위반이 차단되고, 기준선 artifact·파일/endpoint/schema/owner mapping·selector
registry·dependency rule이 review되었다. ADR-013 승인은 이 설계 증거로 판단하며 구현 완료 증거를
선행 요구하지 않는다.

## Phase 1 — 실제 runtime gate

- [x] Parlant lock과 `.venv` 버전 일치 확인
- [x] `RESEARCH_PORT`/`WELFARE_PORT` 검증
- [x] Research/Welfare 인덱싱 완료와 listening port 확인
- [x] 각 서버 customer/session/message 실제 HTTP smoke
- [x] status/body/session event/provider를 JSON artifact로 저장
- [x] canonical standalone entrypoint와 custom local Ollama NLP 주입 확인
- [x] readiness를 HTTP 200 + schema + 목표 agent identity로 검증
- [x] `scripts/smoke_parlant_http.py`, `scripts/smoke_api_chat.py` 구현

두 smoke script는 timeout·non-zero failure·redacted body·endpoint/provider/session/event ID를 남기고,
chat stream은 terminal frame과 `[DONE]`을 분리 판정해야 한다. 이 파일들이 생기기 전에는 Phase 1
완료를 주장하지 않는다.

**중단 조건:** 서버 미기동, final HTTP response 부재, 유료 provider fallback, 포트·session 저장소 충돌.

## Phase 2 — Chat vertical slice

### 기존 seam을 확장할 경계

```text
app/features/chat/domain.py
app/features/chat/application.py
app/features/chat/ports.py
app/adapters/mongodb/chat_repository.py
app/bootstrap/container.py                 # selector를 한 번만 평가
app/adapters/ollama/chat_generator.py      # Chat consumer-owned adapter
app/ports/llm.py                           # signature 불일치로 재사용하지 않음
```

- [x] `ChatMessage`, `ChatRoom`, `ChatSafetyPolicy` 정의; safety policy는 Phase 0 singleton을 alias로 재사용
- [x] `ChatRepository`, `ChatGenerator`, `AgentRouter` 중복 여부를 판정; Router 추가 없이 두 consumer-owned port만 정의
- [x] `ActorContext`로 room/session owner를 모델 호출·저장 전에 검증
- [x] `SendChatMessage`와 `StreamChatMessage` use case 구현
- [x] 기존 `/api/chat/message`, `/api/chat/stream`, rooms/history/proxy를 stable facade로 유지
- [x] `/message`의 현재 JSON/SSE 이중 media type을 frozen v1 fixture로 유지
- [x] hex 경로의 raw DB·Ollama 접근을 outbound adapter 뒤로 이동; legacy Agent facade는 rollback을 위해 유지
- [x] optional `client_message_id`와 신규 문서 `_schema_version=2`를 additive하게 적용
- [x] duplicate audit 후 user-scoped deterministic MongoDB `_id` + `$setOnInsert`를 채택; custom index·backfill·cleanup 불필요
- [x] legacy default → contract pass → 명시적 hex canary와 legacy/new call counter·restart rollback drill
- [x] fake adapter 단위 테스트 작성
- [x] Ollama 실제 HTTP smoke와 MongoDB authenticated ping/실제 query 실행
- [x] 두 frontend parser에 동일 fixture를 사용해 전체 v1 status/payload/error/cancel 의미 테스트
- [x] headers 전 503/504와 stream 시작 후 error frame을 분리 테스트
- [x] `[DONE]`을 transport 종료로만 처리하고 error+DONE을 성공으로 승격하지 않는지 검증
- [x] 새 named-event 계약이 필요하지 않음을 확인; `/api/v2` 추가 없음

**완료 조건:** unit·contract·integration·real smoke, owner isolation, 저장 idempotency, selector rollback이
통과한다. 비스트리밍/headers 전 장애는 503/504, stream 시작 후 장애는 HTTP 200+terminal error
frame이며 provider 원문을 노출하지 않는다.

### Phase 2 고정 결정과 증거

- selector 기본값은 계속 `legacy`다. `hex`는 로컬 canary에서만 명시적으로 선택했고 종료 후
  process restart로 `legacy` REST/SSE rollback을 확인한다.
- 동일 `client_message_id`의 순차·동시 재시도는 hardening 전 통합 테스트에서 중복 문서를
  재현했다. 신규 write는 `(user_id, client_message_id)`의 SHA-256 기반 deterministic `_id`와
  `$setOnInsert`를 사용하므로 기본 `_id` unique invariant만으로 논리 write가 1개다.
- 기존 문서 backfill, custom unique index, collection 병합, cleanup은 수행하지 않는다. 이 결정은
  additive하며 selector rollback과 독립적이다.
- 최종 근거는
  `logs/verification/0d435fc48d35d1650fddd4375746f0e74e63c320/20260816T044829Z/manifest.json`과
  동일 run의 `selector/hex-canary.json`, `storage/idempotency-audit.json`에 보관한다.

## Phase 3 — Health vertical slices

- [x] 3A: active `/api/health-records` → `health_records`를 behavior-preserving migration
- [x] 3B: active `/api/mypage/health-profile` → `health_profiles`를 behavior-preserving migration
- [ ] 3C: dormant `/api/health`와 `HealthRepository`를 retain/delete/versioned-activate 결정
- [x] 3A에서 collection/field/API를 재대조하고 schema ADR 없이 collection 병합 금지
- [x] frozen v1 validation을 바꾸지 않고 3A 건강기록 entity를 framework-independent domain으로 이동
- [x] 3A 사용자 소유권·인증 정책을 application 계층으로 이동
- [x] `HealthRecordRepository`의 get/update/delete에 `owner_id`를 필수 인자로 고정
- [x] legacy/hex 공통 create/read/update/delete 계약 테스트 추가
- [x] null과 unset semantics 보존
- [x] 실제 HTTP synthetic canary로 민감정보 artifact/application log 유출 0 검증
- [x] 3B `HealthProfile`과 owner-scoped `HealthProfileRepository`/application use case 정의
- [x] 3B legacy/hex GET·PUT 공통 frozen v1 fixture와 frontend client 회귀 추가
- [x] 3B 기존 unique `userId` index·upsert와 null/unset 보존 의미 유지
- [x] 3B 실제 legacy/hex HTTP cross-user 3/3, unauthorized write·PII 0 검증. hosted call 0은
  Health Profile provider port 부재, runtime provider 비활성화, hosted credential 제거와 import gate를
  근거로 한 local-only 파생 판정이며 network 실측값이 아니다.

**완료 조건:** 3A는 삭제·재시도·부분 실패를 재현하고, 3B는 owner-scoped read/upsert와
null/unset 보존을 재현한다. 두 slice 모두 타 사용자 접근과 비인가 쓰기를 fail-closed한다.

### Phase 3A 고정 결정과 증거

- `HEALTH_RECORDS_IMPLEMENTATION=legacy|hex`는 API composition root에서 한 번만 평가한다.
  미설정 기본값은 `legacy`이며 잘못된 값은 startup을 fail-closed한다.
- 기존 REST v1 method/path/status/media type/payload key와 `health_records` 문서 필드를 유지한다.
  legacy facade는 restart rollback을 위해 남기고 hex 경로만 application port와 MongoDB adapter를
  사용한다.
- create idempotency key, 신규 index, backfill, collection 병합, cleanup은 frozen schema를 바꿀
  필요가 없어 추가하지 않았다. delete retry는 기존 404 계약으로 fail-closed한다.
- Phase 3A 검증 당시에는 Phase 3B `/api/mypage/health-profile`, Phase 3C dormant `/api/health`와
  기존 `HealthRepository`를 수정하지 않았다.
- 근거는
  `logs/verification/12199ec324efa1f47ccfa3f78e45fbe18b6e9085/20260816T132213Z/manifest.json`과
  동일 run의 `http/health-records.json`, `http/health-records-hex.json`,
  `selector/health-records-hex.json`, `selector/health-records-rollback.json`에 보관한다.

### Phase 3B 고정 결정

- `HEALTH_PROFILE_IMPLEMENTATION=legacy|hex`는 API composition root에서 한 번만 평가한다.
  미설정 기본값은 `legacy`이고 잘못된 값은 HTTP ready 전에 fail-closed한다.
- 실제 frozen 경로는 `GET/PUT /api/mypage/health-profile`이다. status, JSON media type,
  `userId/conditions/healthConditions/allergies/dietaryRestrictions/age/gender/updatedAt`, validation,
  기본 empty profile과 null/unset 보존 의미를 바꾸지 않는다.
- legacy `HealthService`는 compatibility facade 뒤에 유지하고 hex 경로만 framework-independent
  application port와 MongoDB adapter를 사용한다. 두 구현 모두 JWT에서 검증한 actor의 `userId`만
  DB query/upsert에 전달한다.
- 기존 unique `idx_health_profiles_userId`와 upsert가 단일 profile의 idempotency를 제공하므로 신규
  key/index/backfill/collection merge/cleanup은 추가하지 않는다.
- Phase 3C dormant `/api/health`와 기존 `HealthRepository`는 수정하지 않는다.
- 근거는
  `logs/verification/e47098b09164b47724da38542580a4c546530d2a/20260816T165944Z/manifest.json`과
  동일 run의 `http/health-profile-{legacy,hex,rollback}.json`,
  `selector/health-profile-{legacy,hex,invalid,rollback}.json`,
  `storage/health-profiles-schema-after.json`에 보관한다.

## Phase 4 — Welfare/Research adapter 정리

- [ ] `WelfareSearchPort`, `ResearchSearchPort`, `ResearchAgentPort` 정의
- [ ] raw proxy, customer service, generic RemoteAgent, Research/Welfare clients inventory
- [ ] `ParlantMessagePort`, `ParlantCustomerPort`, legacy transparent-proxy facade를 구분
- [ ] FastAPI의 canonical Parlant HTTP client를 outbound adapter로 이동
- [ ] Parlant server handler를 inbound adapter로 분리
- [ ] Parlant guideline/tool과 application policy 분리
- [ ] PubMed/ClinicalTrials adapter response를 내부 schema로 변환
- [ ] source/citation/warning 계약 통일
- [ ] ClinicalTrials는 원문·충실한 번역·정보 제공 면책만 반환하고 생성형 해석 금지
- [ ] refactor 전후 Research/Welfare smoke 비교

**완료 조건:** Parlant SDK import가 adapter/bootstrap 밖으로 새지 않음, Research 장애 격리, 임상시험 정보 제공·면책 유지.

## Phase 5 — Cache, state, worker

- [ ] persistent cache와 computation cache 분류
- [ ] Chat app-scoped `StreamRegistry`, Nutrition instance-scoped `conversation_states`, module-global task set의 scope 명시
- [ ] global registry를 explicit composition root로 이동
- [ ] 기존 notification outbox schema/lease/backoff/idempotency와 12개 관련 test 보존
- [ ] ADR-012 Accepted 후 in-process worker의 별도 프로세스 추출 여부 결정
- [ ] live failure→retry, backlog/terminal-failed, shutdown grace 진단 추가
- [ ] embedding/ingestion job 상태·idempotency 추가
- [ ] process-local cache의 TTL·scope·invalidation 테스트

**완료 조건:** 무한 재시도 없음, worker 재실행 중복 side effect 없음, notification outbox와 generic
job schema가 구분되고 MongoDB source of truth가 일관된다.

## Phase 6 — Nutrition/Quiz/Community 정리

- [ ] Nutrition 이중 구현의 canonical 경로 결정
- [ ] Quiz Agent의 points/session DB 접근을 use case로 이동
- [ ] Community router의 post/comment/like/upload 책임 분리
- [ ] notification·points ledger invariants 테스트
- [ ] `research` 소유 `DailySearchQuota`와 10/day TTL/concurrency/우회 방지 구현·검증
- [ ] legacy facade 호출 경로 확인 후 삭제 검토

## Phase 7 — 로컬 운영·릴리스 hardening

- [ ] production profile에서 `debug=False` 강제
- [ ] secret, CORS, host, upload policy fail-fast
- [ ] `/live` process probe와 Mongo/Ollama/capability별 `/ready`를 분리
- [ ] request id, provider latency, worker backlog, error rate metrics
- [ ] PII/raw prompt/log redaction 확인
- [ ] backend pytest, frontend test/build/lint 실행
- [ ] `tests/e2e/test_frontend_delivery.py`를 browser E2E가 아닌 delivery smoke로 명시
- [ ] 실제 browser E2E runner/dependency/script를 구현한 뒤 주요 사용자 흐름 확인
- [ ] `.github/workflows`가 생긴 뒤 unit/build/lint/integration/artifact/review gate 확인
- [ ] real HTTP/pilot baseline 수집 후 user-journey SLI/SLO/error-budget 채택 여부 결정
- [ ] Parlant failure, Mongo isolated restore, provider timeout, PII canary recovery drill
- [ ] incident/postmortem action에 owner·due condition·verification·close evidence 기록

reverse proxy/TLS/HA/managed DB는 프로덕션 ADR 승인 전 이 phase의 구현 항목이 아니다.

## 검증 명령

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q tests/backend/unit
PYTHONPATH=backend .venv/bin/python -m pytest -q -m integration \
  tests/backend/integration tests/e2e backend/tests backend/Agent/test

# 변경 파일은 항상 0 error를 요구하고, 전체 tree legacy baseline은 별도 기록
.venv/bin/ruff check <changed-python-files>

cd frontend
npm run test -- --run
npm run build
npm run lint
```

실제 Parlant HTTP와 핵심 API smoke는 단위 테스트 결과로 대체하지 않는다.
`pytest.ini`는 기본적으로 integration marker를 제외하므로 live service 검증은 `-m integration`을 명시한다.

## 증거 artifact 계약

```text
logs/verification/<git-sha>/<UTC-run-id>/
  manifest.json                 # command, SHA, environment fingerprint, exit/timestamps
  unit.junit.xml
  integration.junit.xml
  frontend-vitest.junit.xml
  frontend-build.txt
  frontend-lint.txt
  provider/{ollama-chat,ollama-embedding}.json
  http/{research,welfare,chat-message}.json
  http/chat-stream.ndjson
  http/{health-records,health-records-hex}.json
  selector/{health-records-hex,health-records-rollback}.json
  http/health-profile-{legacy,hex,rollback}.json
  selector/health-profile-{legacy,hex,invalid,rollback}.json
  storage/health-profiles-schema-after.json
  eval/{router-summary,safety-summary}.json
```

Phase 3B rollback은 `scripts/summarize_health_profiles_phase3b.py`에 동일 run의 필수 입력
`--unit-junit`, `--integration-junit`, `--frontend-junit`, `--hex-selector`, `--invalid-selector`,
`--hex-http`, `--schema-audit`, `--import-rules`, `--pii`, `--output`을 모두 전달한 상태에서
`--legacy-selector selector/health-profile-rollback.json`과
`--legacy-http http/health-profile-rollback.json`을 함께 전달해 판정한다. 두 rollback artifact는
`result=pass`, 구현 `legacy`, selector 미설정·기본값 `legacy`, owner 격리 3/3, 무인증 쓰기 0,
null/unset·나이 경계 보존을 충족해야 종합 결과가 PASS다.

artifact는 raw prompt/response, token, email, 건강정보를 저장하지 않는다. local `logs/`는 ignored이므로
향후 CI가 동일 directory를 build artifact로 업로드해야 review evidence가 된다.

## 공통 acceptance matrix

| Slice/capability | Public use case/owner | 최소 fake test | 실제 smoke |
|---|---|---|---|
| Chat/`ollama_rag` | Send/StreamChatMessage, `chat` | success/error/cancel/owner/idempotency | API JSON+SSE |
| Health | HealthRecord/Profile commands, `health` | CRUD/owner/null-unset | Mongo API |
| Welfare | WelfareSearch, `welfare` | provider unavailable/citation | Parlant HTTP |
| Research/Trend | Research/Trial information, `research` | source/safety/quota | Parlant+PubMed/Trials |
| Nutrition | nutrition capability, migration anchor `diet` | state/validation | local Agent/API |
| Quiz/Rewards | Quiz + rewards public commands | ledger/idempotency | Mongo API |

Router quality eval은 test/smoke와 분리한다. future blocking 기준은 gold dataset과 실행기가 생긴 뒤
router macro accuracy ≥ 0.90, emergency false negative = 0, failed/unevaluated = 0,
schema validation = 100%로 고정하며 exit code로 실패를 강제한다.

## 롤백 전략

- 각 phase는 작은 commit 또는 논리적 PR 하나로 만든다.
- 기존 API route는 새 use case facade 뒤에 남긴다.
- adapter 전환은 composition root 선택으로 되돌릴 수 있게 한다.
- schema migration은 additive change → backfill → read switch → cleanup 순서로 한다.
- 실패 시 generated `data/`를 삭제하거나 reset하지 않고 code path만 되돌린다.

## PR review 계약

각 PR은 한 selector 또는 한 vertical slice를 기본 단위로 하고, 본문에 quality scenario/risk,
contract 변화, pass/fail evidence, rollback, irreversible cleanup 시점을 기록한다. review는 단순 defect
탐지뿐 아니라 change understanding과 design rationale 전달을 완료 조건으로 삼는다.

## 최종 릴리스 gate

- [ ] P0 runtime smoke evidence가 Research/Welfare/API/Frontend에 존재
- [ ] Chat·Health·Welfare vertical slice가 port 기반으로 동작
- [ ] ADR-011의 5개 Agent capability가 목표 module/facade에 모두 mapping됨
- [ ] Agent의 직접 DB/provider 접근이 제거됨
- [ ] 의료 안전·장애·재시도 시나리오가 재현 가능
- [ ] frontend build/lint/test와 backend 회귀 결과가 기록됨
- [ ] 문서·코드·환경변수·ADR이 일치함
- [ ] CI/review/merge gate가 완료됨
- [ ] emergency, actor ownership, PII canary, ClinicalTrials information-only P0가 모두 통과
