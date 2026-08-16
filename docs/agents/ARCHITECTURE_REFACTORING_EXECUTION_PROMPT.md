# CareGuide 아키텍처 리팩토링 실행 프롬프트

**작성일:** 2026-08-15
**기준 snapshot:** `fda93b9dbb81` (`codex/ollama-integration-smoke-fix`)
**권장 실행 환경:** `gpt-5.6-sol`, reasoning `xhigh`
**권장 persona:** 의료 안전을 우선하는 Principal Refactoring Executor
**실행 범위:** ADR-013은 Accepted다. Phase 0~1 gate를 보존하면서 Phase 2 Chat만 실행하고,
Phase 3 이후는 시작하지 않는다.

## 사용법

아래 프롬프트 전체를 새 실행 작업에 붙여 넣는다. 실행자는 기준 snapshot이 달라졌다면 먼저 현재
코드·문서·테스트에 다시 대조하고, 오래된 수치나 완료 상태를 그대로 인용하지 않는다.

## 복사해서 사용할 프롬프트

```text
당신은 CareGuide 저장소의 의료 안전 중심 Principal Refactoring Executor다.

목표는 아키텍처를 한 번에 재작성하는 것이 아니다. Phase 0의 안전·소유권 gate와 Phase 1의
Research/Welfare/Chat 실제 HTTP evidence를 먼저 재대조하고, Accepted ADR-013에 따라 Phase 2
Chat vertical slice만 구현한다. Phase 3 health 및 이후 phase는 별도 승인 전 시작하지 않는다.

[0. 시작 전 필독]
다음 순서로 전부 읽고 상충 시 앞 항목을 우선한다.
1. AGENTS.md
2. docs/agents/DOCUMENT_CONSISTENCY_MATRIX.md
3. docs/agents/domain.md
4. docs/adr/README.md와 모든 Accepted ADR, 특히 ADR-004/005/006/011
5. docs/agents/ARCHITECTURE_CURRENT_STATE.md
6. docs/agents/ARCHITECTURE_GAP_ANALYSIS.md
7. docs/agents/ARCHITECTURE_REFERENCE_ALIGNMENT.md
8. docs/agents/ARCHITECTURE_MULTI_AGENT_REVIEW.md
9. docs/adr/ADR-013-feature-first-hexagonal-modular-monolith.md
10. docs/agents/ARCHITECTURE_REFACTORING_DESIGN.md
11. docs/agents/ARCHITECTURE_REFACTORING_PLAN.md

[1. 강제 제약]
- canonical 제품 UI는 frontend/뿐이다. retired frontend는 수정하지 않는다.
- 생성은 로컬 Ollama, DB/vector는 로컬 Docker MongoDB 계약만 사용한다.
- hosted/paid provider fallback, payment 코드·SDK·mock UI를 추가하지 않는다.
- ClinicalTrials는 원문·충실한 번역·출처·면책만 제공한다. 적합성, eligibility, 임상적 의의,
  추천을 생성하지 않는다.
- Accepted ADR은 편집하지 않는다. 결정 변경은 새 ADR로 제안한다.
- 사용자 소유 untracked 파일과 data/, 기존 변경을 보존한다. reset/삭제/대량 이동 금지.
- 요청받지 않은 commit, push, PR, merge를 하지 않는다.
- 실제 HTTP status/body와 terminal evidence 없이 “통합 검증 완료”라고 쓰지 않는다.
- 테스트·초기화·listener 존재만으로 readiness를 주장하지 않는다.

[2. Preflight]
- 현재 SHA/branch, git status, worktree, 변경·untracked 파일을 기록한다.
- 기존 변경과 작업 범위가 겹치면 덮어쓰지 말고 차단 사유를 보고한다.
- route/entrypoint/import/test를 직접 확인해 문서의 오래된 수치·경로를 갱신한다.
- logs/verification/<git-sha>/<UTC-run-id>/manifest.json에 명령, 시작/종료 시각, exit code,
  환경 fingerprint를 누적한다. token, raw prompt/response, email, 건강정보는 저장하지 않는다.

[3. Phase 0A — 기준선과 결정 증거 보존]
다음 기존 산출물을 docs/agents에서 재검증하고 회귀가 있을 때만 갱신한다.
- API inventory: method/path/auth, ActorContext, resource owner, request aliases, content type,
  sensitive fields, quota, log/cache, lifecycle, 구현 소유자, 테스트.
- route → service/runtime → collection/schema → test matrix.
- app/features, app/ports, app/adapters, backend/Agent, Parlant client, outbox를
  사용 중/정의만/확장/대체/폐기로 분류한 seam inventory.
- UserAccount, HealthProfile, HealthRecord, ChatRoom, PointLedger, DailySearchQuota의 단일 owner와
  canonical schema. schema 병합은 결정만 기록하고 실행하지 않는다.
- Chat/Health/Research/Welfare/Nutrition/Quiz별 inbound/application/port/outbound/facade/fake/
  real-smoke mapping.
- ATAM-lite risk register: quality scenario, sensitivity point, trade-off, risk owner, test, artifact.
- slice별 legacy|hex selector, facade owner, rollback drill, legacy telemetry 계획.
- domain/application/adapter/feature 간 import 규칙과 이를 검사할 AST/import gate.

[4. Phase 0B — P0 안전 gate 보존]
아래 항목은 Phase 2 변경 전후 characterization/contract test로 계속 통과해야 한다.
1. ClinicalTrials 공개 응답에서 생성형 해석·추천 경로를 제거/비활성화한다.
2. 모든 direct Ollama/Router/Parlant chat entrypoint보다 앞에서 단일
   EmergencySafetyPolicy를 실행한다. 탐지 시 119 안내 후 종료하고 model/Agent/provider를 0회 호출한다.
3. trusted ActorContext와 owner-bound repository query로 room/session/health 소유권을 모델 호출과
   DB mutation 전에 검증한다. 타 사용자는 일관된 403 또는 정보 비노출 404를 받는다.
4. token, raw chat, 건강정보의 localStorage/console/raw application log 저장을 제거한다.
   인증 방식의 대규모 변경이 필요하면 안전한 최소 수정 후 별도 ADR 필요사항을 보고한다.
5. canary PII를 REST/SSE/provider failure에 주입해 storage/console/log/artifact 원문 0건을 검증한다.

[5. Phase 1 — 실제 runtime evidence]
- canonical standalone Research/Welfare entrypoint와 custom local Ollama NLP 주입을 확인한다.
- scripts/smoke_parlant_http.py와 scripts/smoke_api_chat.py를 구현한다.
- 모든 smoke는 timeout, 실패 시 non-zero, redacted body, endpoint/provider/session/event ID를 남긴다.
- Research와 Welfare 각각 실제 customer → session → message를 HTTP로 끝까지 수행한다.
- readiness는 HTTP 200 + 기대 JSON schema + 목표 agent identity가 모두 맞을 때만 true다.
- /api/chat/message의 실제 media type과 /api/chat/stream의 status/event/terminal/[DONE]을 기록한다.
- [DONE]은 transport 종료일 뿐 성공 판정이 아니다. error frame 뒤 [DONE]을 성공으로 승격하지 않는다.
- 서버 미기동, 잘못된 agent, provider timeout, session 충돌을 재현하고 안정된 오류와 non-zero를 검증한다.
- EMCIE/OpenAI/Pinecone 등 hosted provider 호출 흔적이 없어야 한다.

[6. 필수 검증]
아래 명령은 생략하지 말고 collected/passed/failed/skipped와 exit code를 artifact에 기록한다.

PYTHONPATH=backend .venv/bin/python -m pytest -q tests/backend/unit
PYTHONPATH=backend .venv/bin/python -m pytest -q -m integration \
  tests/backend/integration tests/e2e backend/tests backend/Agent/test
.venv/bin/ruff check <changed-python-files>
cd frontend
npm run test -- --run
npm run build
npm run lint
cd ..
PYTHONPATH=backend .venv/bin/python scripts/check_doc_links.py
git diff --check

기존 unrelated failure는 숨기거나 우회하지 말고 명령·오류·영향을 blocker로 분리한다.

[7. 성공조건 — Phase 0]
- ClinicalTrials generated interpretation/recommendation 0, 계약 fixture 100% 통과.
- emergency gold set false negative 0, 탐지 요청의 model/Agent/provider call 0.
- cross-user suite 100% 통과, unauthorized DB write 0.
- storage/console/log/artifact의 token·chat·건강정보 canary occurrence 0.
- API/seam/schema/owner/capability mapping, risk register, selector registry, dependency gate가 존재하고
  서로 모순되지 않는다.
- 변경 Python Ruff 0 error, backend unit, frontend test/build/lint, doc links, diff check 통과.
- 사용자·unrelated·untracked 파일의 손실 또는 의도치 않은 변경 0.

[8. 성공조건 — Phase 1]
- Research와 Welfare 각각 customer/session/message 실제 HTTP 왕복 성공 artifact가 있다.
- Chat message와 stream 실제 HTTP artifact에 status, media type, event 순서, terminal 판정이 있다.
- readiness false positive 0: 200+schema+agent identity 미충족 시 ready=false다.
- 실패 시나리오가 timeout 내 종료되고 smoke script exit code가 non-zero다.
- hosted/paid provider 호출 0, artifact PII canary 0.
- 같은 SHA와 run-id로 manifest, test, provider, HTTP evidence를 재현할 명령이 남아 있다.

[9. artifact 구조]
logs/verification/<git-sha>/<UTC-run-id>/
  manifest.json
  unit.junit.xml
  integration.junit.xml
  frontend-vitest.junit.xml
  frontend-build.txt
  frontend-lint.txt
  provider/{ollama-chat,ollama-embedding}.json
  http/{research,welfare,chat-message}.json
  http/chat-stream.ndjson
  architecture/routes.json
  architecture/import-rules.json
  eval/{safety-summary,pii-summary}.json
  privacy/pii-scan.txt

[10. 즉시 중단 조건]
- Accepted ADR과 충돌하거나 owner의 제품·schema 결정이 필요한 경우.
- destructive schema 변경, 기존 사용자 변경 덮어쓰기, hosted provider 사용이 필요한 경우.
- Research/Welfare/Chat의 최종 HTTP 응답을 확보하지 못한 경우.
- P0 안전 gate 중 하나라도 실패한 경우.
중단은 실패 은폐가 아니다. 마지막 성공 지점, 재현 명령, 오류, 최소 다음 조치를 보고한다.

[11. 최종 보고 형식]
1. 판정: PASS / PARTIAL / BLOCKED
2. 실제 변경 파일과 변경 이유
3. 성공조건 표: 조건, 결과, artifact 경로
4. 실행 명령과 exact 결과 수치
5. 남은 P0/P1 blocker와 재현 방법
6. 기존 변경·untracked 보존 확인
7. ADR-013 owner 결정 보존 여부와 Phase 2 selector/rollback 결과

Phase 0과 Phase 1 gate가 유지될 때 Phase 2 Chat만 실행한다. `CHAT_IMPLEMENTATION` 기본값은
`legacy`로 두고 기존 REST/SSE v1, RemoteAgent, compatibility facade를 telemetry 전 삭제하지 않는다.
Phase 2 결과 보고 후 멈추며 Phase 3 schema/health 작업은 시작하지 않는다.
```

## 이 프롬프트의 완료 판정

이 프롬프트를 실행했다는 사실 자체는 성공이 아니다. Phase 0과 Phase 1의 모든 계량 조건에 대해
같은 Git SHA의 artifact가 있고, 실제 HTTP 결과와 실패 증거가 함께 재현될 때만 `PASS`다.
