# CareGuide 아키텍처 10개 관점 재검증

**검토일:** 2026-08-15
**대상 snapshot:** `fda93b9dbb81` (`codex/ollama-integration-smoke-fix`)
**대상:** 현재 상태, 갭 분석, 목표 설계, 실행 계획, ADR-013
**종합 판정:** **REQUEST CHANGES — ADR-013은 Proposed 유지, Phase 0만 즉시 착수 가능**

후속 외부 방법론 대조와 quality scenario는
[`ARCHITECTURE_REFERENCE_ALIGNMENT.md`](./ARCHITECTURE_REFERENCE_ALIGNMENT.md)에 기록한다.

이 문서는 서로 다른 model·추론강도·persona를 가진 10개 read-only reviewer의 결과를 주 검토자가
실제 코드·ADR·테스트에 다시 대조해 합의점과 문서 반영 상태를 기록한 것이다. reviewer는 문서를
수정하지 않았으며 최종 편집과 판정은 주 검토자가 수행했다.

## 1. Reviewer 구성

| # | 관점/persona | Model | 추론강도 | 판정 초점 |
|---|---|---|---|---|
| 1 | 엄격한 principal architecture purist | `gpt-5.6-sol` | xhigh | 의존 방향, module boundary, ADR 승인 순환 |
| 2 | 의료 DDD/domain guardian | `gpt-5.6-sol` | ultra | aggregate, ubiquitous language, capability ownership |
| 3 | runtime forensic engineer | `gpt-5.6-sol` | high | 실제 entrypoint/import/listener/test evidence |
| 4 | ADR governance auditor | `gpt-5.6-terra` | xhigh | status, supersession, binding/deferred decision |
| 5 | API/SSE compatibility staff engineer | `gpt-5.6-sol` | high | REST media type, SSE state/error/cancel contract |
| 6 | release/test gate auditor | `gpt-5.6-terra` | high | pytest 수집, smoke/eval/browser/CI artifact |
| 7 | medical safety/privacy architect | `gpt-5.6-sol` | xhigh | emergency, ownership, PII/token, trial safety |
| 8 | local-first SRE/reliability operator | `gpt-5.6-terra` | high | readiness, retry, worker, recovery, topology |
| 9 | strangler migration pragmatist | `gpt-5.6-sol` | high | selector, schema cutover, rollback, phase startability |
| 10 | Korean technical documentation editor | `gpt-5.6-terra` | medium | source of truth, reading order, terminology, drift |

## 2. 합의된 핵심 판정

모든 reviewer는 **단일 CKD bounded context + feature-first hexagonal modular-monolith core +
local Ollama/MongoDB + process-isolated Parlant**라는 방향 자체에는 동의했다. microservices나
전면 재작성은 현재 규모와 local-first 계약에 맞지 않는다.

그러나 기존 문서는 다음 이유로 바로 구현할 수준이 아니었다.

1. ADR-004를 위반하는 ClinicalTrials LLM 해석 API가 공개돼 있다.
2. emergency 정책, chat room/session owner 검증, token/PII 저장·로그가 P0 안전 gate를 통과하지 못한다.
3. 기본 Chat은 Router/5개 capability가 아니라 direct `OllamaChatService` 경로다.
4. 기존 `app/ports`에는 production consumer가 없고 현재 Ollama 구현과 signature도 맞지 않는다.
5. health, rewards, daily quota의 route/collection/schema/owner가 중복되거나 빠져 있다.
6. SSE 상태·payload·오류·취소 의미가 backend와 frontend consumer마다 다르다.
7. 실제 Research/Welfare/API HTTP smoke 실행기, browser E2E, CI workflow, reviewable artifact가 없다.
8. outbox/worker는 이미 구현됐는데 계획이 신규 구현으로 잘못 기록했다.
9. migration selector와 additive schema/backfill/rollback drill이 없어 Phase 2~6이 startable하지 않다.
10. ADR status와 문서 reading order가 실제 binding 계약과 어긋났다.

## 3. 심각도별 검증 결과와 처리

| Severity | Finding | 재검증 근거 | 문서 처리 |
|---|---|---|---|
| P0 | ClinicalTrials가 `Clinical Significance` LLM 해석을 반환 | `clinical_trials.py`, ADR-004 | current/gap/plan/ADR에 차단 gate 추가 |
| P0 | emergency 정책이 direct/router/Parlant에서 불일치 | `ollama_chat.py`, `router`, emergency tools | 단일 fail-closed policy와 전 경로 test 요구 |
| P0 | `room_id`/`session_id` owner 검증 누락 | `chat.py`, `context_manager.py` | `ActorContext`, owner-bound port/test 요구 |
| P0 | token/chat/응답이 localStorage·console/log에 남음 | `security.ts`, `AuthContext`, chat UI/API | 외부 파일럿 NO-GO와 PII canary gate 추가 |
| P0 | pytest 기본 명령이 backend legacy integration tree 누락 | `pytest.ini`, 두 conftest | explicit test path/marker 명령으로 교정 |
| P0 | real HTTP/browser/CI gate가 실행 불가 | smoke scripts 부재, workflow 부재 | prerequisite와 artifact contract 명시 |
| P1 | port/feature seam 성숙도 과장 | port consumer 0, marker-only feature | five-state inventory를 Phase 0 blocker로 변경 |
| P1 | SSE v1 contract 불완전 | backend status와 두 frontend parser | frozen v1 state/error/cancel matrix 추가 |
| P1 | Health/points/quota owner와 schema 불명확 | active/dormant routes와 collections | split phase와 canonical schema gate 추가 |
| P1 | Parlant unified runner/readiness 부정확 | hard-coded port, NLP 미주입, 404 accepted | standalone entrypoint와 200+schema identity gate |
| P1 | outbox 신규 구현 오기 | service/lifespan/index/test 존재 | existing implementation verify/추출 decision으로 교정 |
| P1 | ADR status/온보딩 drift | ADR-011 supersession, old reading guide | status/index/matrix/reading order 동기화 |

## 4. 문서에 반영했지만 코드에는 남은 차단 항목

이번 작업은 설계 문서 개선이며 다음 코드는 수정하지 않았다.

- ClinicalTrials 생성형 해석 제거
- 전 경로 emergency pre-filter와 chat owner authorization
- token/chat localStorage와 console/raw log 제거
- Parlant unified runner/readiness/process recovery
- daily search quota, health/rewards schema 통합
- migration selector와 idempotency migration
- real HTTP smoke scripts, browser E2E, CI workflow, eval threshold runner

따라서 문서가 개선됐다는 사실은 런타임 또는 릴리스 완료를 의미하지 않는다.

## 5. 최종 startability

| Phase | 판정 | 선행조건 |
|---|---|---|
| Phase 0 | STARTABLE | P0 safety fix, inventories, ADR review |
| Phase 1 | PARTIAL/BLOCKED | 두 HTTP smoke script와 artifact schema 구현 |
| Phase 2 Chat | BLOCKED | endpoint/schema/selector/owner matrix 승인 |
| Phase 3 Health | BLOCKED | 3A/3B/3C route·collection decision |
| Phase 4 Parlant | BLOCKED | client 계약 분리와 canonical entrypoint |
| Phase 5 Worker/state | BLOCKED | ADR-012와 existing outbox extraction decision |
| Phase 6 Feature cleanup | BLOCKED | feature별 owner/schema/facade/rollback |
| Phase 7 | 일부 STARTABLE | 정적 보안 hardening 가능; production topology는 별도 ADR |

ADR-013은 approval criteria와 migration completion criteria를 분리했으므로 승인 순환은 해소됐다.
다만 Project owner의 명시적 승인 전 Status는 계속 Proposed다.
