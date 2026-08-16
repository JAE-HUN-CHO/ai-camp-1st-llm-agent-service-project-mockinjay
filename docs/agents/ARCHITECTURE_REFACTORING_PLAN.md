# CareGuide 아키텍처 리팩토링 실행 계획

**작성일:** 2026-08-15
**상태:** Phase 0~1 verified; Phase 2 Chat authorized
**전제:** 현재 API·MongoDB·Ollama·Parlant 계약을 보존하는 점진적 strangler refactor

**착수 판정:** Phase 0~1은 완료·검증됐다. Project owner는 Phase 2 Chat만 다음 실행 범위로
승인했다. Phase 3 이후는 각 phase의 별도 범위 확인 전 startable하지 않다.

실제 실행 작업에 전달할 복사 가능한 지시문과 계량 성공조건은
[`ARCHITECTURE_REFACTORING_EXECUTION_PROMPT.md`](./ARCHITECTURE_REFACTORING_EXECUTION_PROMPT.md)를 사용한다.

## 실행 원칙

1. 한 번에 전체 구조를 재작성하지 않는다.
2. 한 vertical slice마다 구현·정적검사·단위테스트·실서비스 smoke를 모두 통과시킨다.
3. 기존 endpoint는 compatibility facade로 유지한다.
4. untracked `data/`와 생성 artifact는 변경 범위에 포함하지 않는다.
5. 실패한 runtime gate를 문서에 남기고, 통과 전 다음 gate로 넘어가지 않는다.
6. [`ADR-013`](../adr/ADR-013-feature-first-hexagonal-modular-monolith.md)의 범위에 따라 현재는 Phase 2 Chat만 실행한다.

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
app/adapters/ollama/client.py              # 현재 LLMProvider 구현체 아님
app/ports/llm.py                           # keep/adapt/replace 결정 후 한 계약만 사용
```

- [ ] `ChatMessage`, `ChatRoom`, `ChatSafetyPolicy` 정의
- [ ] `ChatRepository`, `ChatGenerator`, `AgentRouter` 중복 여부를 판정하고 한 계약만 정의
- [ ] `ActorContext`로 room/session owner를 모델 호출·저장 전에 검증
- [ ] `SendChatMessage`와 `StreamChatMessage` use case 구현
- [ ] 기존 `/api/chat/message`, `/api/chat/stream`, rooms/history/proxy를 stable facade로 유지
- [ ] `/message`의 현재 JSON/SSE 이중 media type을 유지할지 별도 API 결정으로 고정
- [ ] Agent의 raw DB·Ollama 접근 제거
- [ ] optional `client_message_id`와 additive `idempotency_key/_schema_version` migration 설계
- [ ] duplicate audit 후 `(user_id, idempotency_key)` sparse unique index와 resumable backfill
- [ ] legacy default → contract pass → hex 전환 및 legacy/new call counter·rollback drill
- [ ] fake adapter 단위 테스트 작성
- [ ] Ollama 실제 HTTP smoke와 MongoDB authenticated ping/실제 query 실행
- [ ] 두 frontend parser에 동일 fixture를 사용해 전체 v1 status/payload/error/cancel 의미 테스트
- [ ] headers 전 503/504와 stream 시작 후 error frame을 분리 테스트
- [ ] `[DONE]`을 transport 종료로만 처리하고 error+DONE을 성공으로 승격하지 않는지 검증
- [ ] 새 named-event 계약이 필요하면 별도 API ADR과 `/api/v2`로 분리

**완료 조건:** unit·contract·integration·real smoke, owner isolation, 저장 idempotency, selector rollback이
통과한다. 비스트리밍/headers 전 장애는 503/504, stream 시작 후 장애는 HTTP 200+terminal error
frame이며 provider 원문을 노출하지 않는다.

## Phase 3 — Health vertical slices

- [ ] 3A: active `/api/health-records` → `health_records`를 behavior-preserving migration
- [ ] 3B: active `/api/mypage/health` → `health_profiles`를 별도 migration
- [ ] 3C: dormant `/api/health`와 `HealthRepository`를 retain/delete/versioned-activate 결정
- [ ] collection/field/API matrix와 schema ADR 없이 collection 병합 금지
- [ ] 건강기록 entity와 validation policy 이동
- [ ] 사용자 소유권·인증 정책을 application 계층으로 이동
- [ ] `HealthRecordRepository`의 get/update/delete에 `owner_id`를 필수 인자로 고정
- [ ] create/read/update/delete 계약 테스트 추가
- [ ] null과 unset semantics 보존
- [ ] 민감정보 로그 redaction end-to-end 검증

**완료 조건:** router raw query 제거, 타 사용자 접근 거부, 삭제·재시도·부분 실패 재현 가능.

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
  eval/{router-summary,safety-summary}.json
```

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
