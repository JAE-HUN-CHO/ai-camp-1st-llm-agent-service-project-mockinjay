# ADR-013: Feature-First Hexagonal Modular Monolith

- **Status:** Accepted
- **Date:** 2026-08-15
- **Accepted:** 2026-08-16
- **Deciders:** Project owner
- **Related:** ADR-004, ADR-005, ADR-006, ADR-011, [`DOCUMENT_CONSISTENCY_MATRIX.md`](../agents/DOCUMENT_CONSISTENCY_MATRIX.md), [`ARCHITECTURE_REFERENCE_ALIGNMENT.md`](../agents/ARCHITECTURE_REFERENCE_ALIGNMENT.md)

## Context

CareGuide는 하나의 CKD bounded context 안에서 FastAPI, Agent orchestration, 로컬 Ollama, MongoDB Atlas Local, PubMed/ClinicalTrials.gov, Parlant Research/Welfare를 사용한다.

현재 `backend/app`에는 API, service, repository, feature, port, adapter seam이 있고 `backend/Agent`에는 Agent registry와 로컬/원격 Agent 계약이 있다. 그러나 일부 router·service·Agent가 MongoDB, Ollama, HTTP client를 직접 호출하며 Nutrition 구현, Mongo connection, cache/runtime state 소유권도 중복되어 있다.

전면 재작성이나 즉시 microservice 분리는 현재 팀·로컬 runtime·MVP 범위에 비해 운영 복잡도가 높다. 반대로 현재 layered 구조만 유지하면 provider 교체, fake 기반 단위 테스트, 의료 안전 정책의 독립 검증이 어렵다.

## Decision

CareGuide는 **Local-first Modular-Monolith Core + Feature-first Hexagonal Application Core +
Process-isolated Parlant Adapters/Workers** 구조로 점진적으로 전환한다.

Project owner는 Option B를 승인했다. 이 승인은 Phase 2 Chat vertical slice만 다음 실행
범위로 허용하며, Phase 3 이후 구현은 각 phase의 별도 범위 확인 전까지 승인하지 않는다.

1. `domain.md`의 단일 CKD bounded context를 유지한다.
2. `app/features`를 기능별 vertical slice의 migration anchor로 사용하되 현재 placeholder와 실제 wiring을 구분한다.
3. 기존 `app/ports`와 `app/adapters`는 consumer/implementation/contract test가 확인된 경우에만 재사용한다. 호환 seam을 확인하지 않고 같은 계약을 새로 만들지 않는다.
4. application use case는 FastAPI, Motor/PyMongo, Ollama, Parlant SDK를 직접 import하지 않는다.
5. FastAPI/SSE와 Parlant server handler는 inbound adapter다.
6. MongoDB, Ollama, PubMed, ClinicalTrials.gov, FastAPI에서 호출하는 Parlant HTTP client는 outbound adapter다.
7. `backend/Agent`는 application use case를 호출하는 compatibility facade와 Agent-specific adapter로 축소한다.
8. embedding, ingestion, enrichment, notification retry 같은 장시간 작업만 async worker로 분리한다.
9. 기존 REST/SSE wire contract를 migration 동안 유지한다. 새로운 계약은 versioned API와 별도 결정으로 도입한다.
10. 프로덕션 데이터베이스·HA·배포 방식은 이 ADR에서 결정하지 않는다. ADR-005에 따라 별도 ADR이 필요하다.
11. modular-monolith core와 Research/Welfare Parlant adapter, worker의 process boundary를 구분하고 각 process에 composition root를 하나만 둔다.
12. slice 전환은 `legacy|hex` implementation selector로 수행하며 provider toggle과 섞지 않는다.
13. architecture risk는 ATAM-lite quality scenario와 sensitivity/tradeoff로 평가하고 test/artifact에 추적한다.

## Module dependency rules

- domain은 framework, SDK, DB, 다른 feature에 의존하지 않는다.
- application은 자기 domain과 소비자 소유 port에만 의존한다.
- adapter는 application public API/port를 구현하거나 호출한다.
- feature 간 호출은 public application facade 또는 명시적 event만 사용한다.
- 다른 feature의 repository, runtime, private module import는 금지한다.
- Phase 0에서 import-linter 또는 동등한 AST 검사를 필수 gate로 정한다.

## Runtime capability mapping

| ADR-011 capability | Application module | Adapter/facade |
|---|---|---|
| `medical_welfare` | `welfare` + hospital search | `Agent/medical_welfare` |
| `research_paper` | `research` + migration 중 medical-information 해석 | `Agent/research_paper` |
| `nutrition` | `diet`를 migration anchor로 사용; rename 별도 결정 | `Agent/nutrition` |
| `quiz` | `quiz` | `Agent/quiz` |
| `trend_visualization` | `research` | `Agent/trend_visualization` |

`health`는 HealthProfile/HealthRecord의 소유권·검증을 담당하며 일반 의료정보 Agent와 합치지
않는다. `research`는 ClinicalTrialsInformation과 DailySearchQuota를 소유한다.

## Aggregate ownership

`UserAccount`, `HealthProfile`, `HealthRecord`, `ChatRoom`, `PointLedger`, `DailySearchQuota`는
`user_id`로 참조하는 독립 aggregate root다. Phase 0에서 canonical collection/schema를 결정한다.
`rewards`가 PointLedger를 단독 소유하며 Quiz/Community는 public command만 호출한다.
`research`가 ClinicalTrialsInformation과 DailySearchQuota를 소유한다. HealthProfile과
HealthRecord는 분리하고 dormant health 경로는 Phase 3까지 신규 쓰기 없이 유지한다. `diet`는
구현 owner이고 `nutrition`은 공개 capability다. schema 병합은 별도 migration 결정 없이
허용하지 않는다.

## Safety and privacy invariants

- 모든 chat entrypoint는 routing/provider 전에 단일 fail-closed emergency policy를 실행한다.
- 모든 room/session/health repository operation은 trusted `ActorContext`의 owner id를 필수로 받는다.
- token, raw prompt/response, 건강정보는 localStorage·console·일반 application log에 저장하지 않는다.
- ClinicalTrials는 ADR-004에 따라 원문·충실한 번역·metadata·면책만 제공하고 적합성·eligibility
  판단·임상적 의의·추천을 생성하지 않는다.

## Options Considered

### Option A: 기존 Layered Architecture 유지

| Dimension | Assessment |
|---|---|
| Complexity | Low |
| Migration cost | Low |
| Testability | Medium-Low |
| Provider isolation | Low |

**Pros:** 변경량과 단기 delivery risk가 작다.
**Cons:** router/service/Agent의 infrastructure 결합과 중복 lifecycle을 해소하기 어렵다.

### Option B: Feature-First Hexagonal Modular Monolith

| Dimension | Assessment |
|---|---|
| Complexity | Medium |
| Migration cost | Medium, incremental |
| Testability | High |
| Provider isolation | High |

**Pros:** 기존 feature/port seam을 활용하고 vertical slice 단위로 전환·롤백할 수 있다.
**Cons:** composition root, port ownership, compatibility facade를 일관되게 관리해야 한다.

### Option C: Full Microservices + Event-Driven Architecture

| Dimension | Assessment |
|---|---|
| Complexity | High |
| Migration cost | High |
| Operational burden | High |
| Independent scaling | High |

**Pros:** 서비스별 배포·격리·확장이 가능하다.
**Cons:** 인증, session, 관측성, 데이터 일관성, 로컬 개발과 배포 복잡도가 현재 규모에 비해 크다.

## Trade-off Analysis

Option B를 선택한다. Option A보다 초기 설계 비용은 높지만, 현재 존재하는 naming anchor와 일부
Protocol을 inventory한 뒤 선택적으로 활용하면 전면 재작성 없이 의존성을 역전할 수 있다.
재사용을 전제하지는 않는다. Option C의 독립 확장성은 현재 필수 요구사항이 아니며
Research/Welfare의 기존 별도 서버 진입점·포트 경계만 장애 격리 후보로 유지한다. 실제 별도
프로세스 readiness는 runtime gate에서 검증한다.

## Consequences

### Positive

- 외부 provider 없이 use case 단위 테스트가 가능해진다.
- 의료 안전·권한·무결성 규칙을 prompt와 infrastructure에서 분리할 수 있다.
- Ollama, MongoDB, Parlant 변경 영향을 adapter에 제한할 수 있다.
- vertical slice별 migration과 rollback이 가능하다.

### Negative

- migration 동안 legacy service와 compatibility facade가 공존한다.
- port를 과도하게 만들면 shallow abstraction이 증가할 수 있다.
- import 방향과 composition root를 자동 검사하지 않으면 구조가 다시 무너질 수 있다.

### Neutral / deferred

- MongoDB Atlas Local과 Ollama-only 계약은 변경하지 않는다.
- 프로덕션 배포·HA·managed database 선택은 후속 ADR로 미룬다.
- Kafka, Redis queue, Kubernetes는 현재 결정 범위가 아니다.

## Migration and rollback

1. 현재 runtime/API evidence를 먼저 확보한다.
2. Chat → Health → Welfare/Research 순으로 vertical slice를 전환한다.
3. 기존 endpoint는 compatibility facade로 유지한다.
4. selector 기본값은 `legacy`이며 contract/smoke 통과 후 `hex`로 전환한다.
5. schema는 additive change → backfill → read switch → cleanup 순서로 변경한다.
6. 새 경로 실패 시 composition root selector를 기존 구현으로 되돌린다.
7. legacy call telemetry가 두 번 연속 release gate에서 0이고 회귀·실서비스 smoke가 통과한 뒤에만 제거한다.

현재 승인된 다음 실행 범위는 Phase 2 Chat vertical slice 하나뿐이다. selector 기본값은
`legacy`이고 기존 REST/SSE v1 계약은 frozen contract로 유지한다. RemoteAgent와 compatibility
facade는 telemetry 조건을 충족하기 전 삭제하지 않는다. Parlant는 별도 프로세스로 유지하고,
worker 분리는 embedding/ingestion/enrichment/notification retry 같은 장시간 작업으로 제한한다.

## ADR approval criteria

- [x] Accepted ADR-004/005/006/011과 충돌하지 않는다.
- [x] 기존 feature/port/adapter의 사용/placeholder/확장/대체/폐기 mapping이 작성된다.
- [x] ADR-011의 5개 Agent capability가 모두 mapping된다.
- [x] module dependency, aggregate ownership, process composition root가 합의된다.
- [x] selector/rollback과 frozen v1 REST/SSE migration policy가 합의된다.
- [x] 위 safety/privacy invariant가 설계와 Phase 0 gate에 반영된다.
- [x] 우선 quality scenario, sensitivity point, tradeoff, risk owner가 ATAM-lite review로 합의된다.

이 기준은 ADR을 승인하기 위한 설계 증거다. 구현 후에만 가능한 조건을 선행 요구하지 않는다.

## Migration completion criteria

- [ ] frozen v1 REST/SSE success/error/cancel wire contract가 fixture로 보존된다.
- [ ] Research/Welfare 실제 customer/session/message HTTP evidence가 있다.
- [ ] 공통 acceptance matrix의 모든 slice가 fake test와 해당 real smoke를 통과한다.
- [ ] 실제 Ollama/MongoDB adapter smoke와 장애 시나리오가 통과한다.
- [ ] emergency/owner isolation/PII canary/ClinicalTrials information-only 계약이 통과한다.

## Action Items

1. [x] Project owner가 ADR-013을 Accepted로 승인했다.
2. [x] Phase 0 inventory와 owner/capability/selector mapping을 기록했다.
3. [x] `ARCHITECTURE_REFACTORING_PLAN.md` Phase 0~1을 실행·검증했다.
4. [ ] 승인된 다음 범위인 Phase 2 Chat vertical slice를 별도 실행한다.
