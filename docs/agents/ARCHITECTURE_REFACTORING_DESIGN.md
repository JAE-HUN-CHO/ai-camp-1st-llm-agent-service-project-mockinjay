# CareGuide 리팩토링 목표 아키텍처 설계안

**작성일:** 2026-08-15
**상태:** Approved target design (ADR-013 Accepted)
**결정 성격:** 전면 재작성 없이 현재 계약을 보존하는 점진적 구조 개선
**승인 게이트:** 충족됨. 다음 실행 범위는 Phase 2 Chat vertical slice로 제한한다.
**방법 근거:** [`ARCHITECTURE_REFERENCE_ALIGNMENT.md`](./ARCHITECTURE_REFERENCE_ALIGNMENT.md)

## 1. 결정

CareGuide는 다음 조합으로 발전시킨다.

> **Local-first Modular-Monolith Core + Hexagonal Application Core + Process-isolated Parlant Adapters/Workers**

도메인은 하나의 CKD bounded context로 유지한다. `chat`, `health`, `welfare`, `research`, `nutrition`, `community`는 별도 bounded context가 아니라 동일한 도메인 안의 기술·기능 모듈이다.

## 2. 설계 목표

- business rule이 FastAPI, MongoDB, Ollama, Parlant에 종속되지 않게 한다.
- Agent가 DB transaction·권한·의료 안전 정책을 직접 소유하지 않게 한다.
- 로컬 Ollama/MongoDB 계약과 canonical `frontend/`를 보존한다.
- API 계약과 기존 route를 유지하면서 내부 구현을 교체할 수 있게 한다.
- 장시간 작업을 HTTP 요청에서 분리한다.
- 외부 provider 장애를 기능별로 격리한다.
- 각 vertical slice를 fake adapter와 실제 local runtime으로 모두 검증한다.

## 3. 목표 의존성 방향

```text
Inbound adapters
  FastAPI routes / SSE endpoints / Parlant server handlers
                  │
                  ▼
Application use cases
                  │
                  ▼
Domain entities / policies / ports
                  ▲
                  │
Outbound adapters
  MongoDB / Ollama / PubMed / ClinicalTrials.gov / Parlant HTTP clients
```

Parlant의 방향은 실행 위치에 따라 구분한다.

- FastAPI가 Research/Welfare Parlant 서버를 호출하는 HTTP client는 outbound adapter다.
- 별도 Parlant 서버에서 요청을 받아 application use case를 호출하는 handler는 inbound adapter다.
- Parlant SDK type은 adapter/bootstrap 밖으로 노출하지 않는다.

금지 방향:

- domain/application → FastAPI, Motor, Ollama SDK, Parlant SDK 직접 import
- router → raw MongoDB query 또는 외부 provider 직접 호출
- Agent → frontend response shape 또는 collection 이름 의존
- frontend → MongoDB·파일 경로·health record 직접 접근

## 4. 목표 디렉터리

기존 `backend/app/features`와 `backend/app/ports`는 완성된 seam이 아니라 naming anchor와
일부 미연결 Protocol이다. Phase 0에서 각각을 `사용 중 / 정의만 존재 / 확장 / 대체 / 폐기`로
분류한 뒤 재사용 여부를 결정한다.

```text
backend/app/
  features/
    account/             # 현재 anchor
    chat/
    health/
    welfare/             # 목표 책임; 현재 package 없음
    research/            # trend_visualization capability 포함
    diet/                # nutrition capability의 현재 migration anchor
    quiz/
    community/
    notification/        # 목표 책임; 현재 service/outbox에서 이동 여부 검토

    <feature>/           # 각 feature의 내부 형태
      domain.py          # 필요할 때만 entity/value/policy 분리
      application.py     # use cases
      ports.py           # feature-owned repository/service ports
      runtime.py         # application-scoped state가 필요한 경우

  ports/                 # 두 feature 이상이 실제 공유하는 provider port만
    llm.py
    embedding.py
    vector.py
    external_search.py

  adapters/
    mongodb/
    ollama/
    pubmed/
    clinical_trials/
    parlant/
    cache/

  bootstrap/             # API process composition root와 lifespan
  workers/
  api/                   # 기존 HTTP/SSE compatibility inbound adapter

backend/Agent/
  core/                  # Agent 계약과 compatibility facade
  router/                # 입력 해석 inbound adapter
  research_paper/        # compatibility facade + 별도 server bootstrap
  medical_welfare/       # compatibility facade + 별도 server bootstrap
  nutrition/             # application use case facade
  quiz/                  # application use case facade
  trend_visualization/   # research application use case facade
```

기존 `api`, `services`, `repositories`, `db`, `features`, `ports`를 즉시 삭제하거나 중복 생성하지
않는다. 각 vertical slice에서 현재 파일을 목표 책임에 mapping하고 compatibility facade를 거친 뒤
legacy 경로를 제거한다. 각 프로세스는 별도 composition root를 가진다:
`bootstrap/api`, `bootstrap/research_server`, `bootstrap/welfare_server`, `bootstrap/worker`.

### Runtime capability mapping

결정의 단일 source of truth는 [ADR-013의 capability mapping](../adr/ADR-013-feature-first-hexagonal-modular-monolith.md#runtime-capability-mapping)이다.
현재 runtime에서 `medical_welfare`는 복지·병원 탐색, `research_paper`는 일반 의료정보·건강기록
해석도 담당한다. `health` CRUD 책임을 Agent capability와 합치지 않는다. 책임 이동은 Phase 0
mapping과 회귀 검증 뒤에만 허용한다.

### 모듈 의존 규칙

| From | 허용 | 금지 |
|---|---|---|
| `feature/domain.py` | 표준 라이브러리, 승인된 shared value | FastAPI, DB/SDK, 다른 feature |
| `feature/application.py` | 자기 domain, 소비자 소유 port | concrete adapter, 다른 feature private module |
| inbound/outbound adapter | application public API 또는 port | 다른 feature repository 직접 호출 |
| feature 간 협력 | public application facade 또는 명시적 event | runtime/private module import |

Phase 0에서 import-linter 또는 동등한 AST 검사를 필수 gate로 정한다.

## 5. 핵심 Port 계약

현재 shared provider port는 `llm.py`, `embedding.py`, `vector.py`, `external_search.py`뿐이며
production wiring이 확인되지 않았다. `ChatRepository`, `ResearchAgentPort`,
`WelfareAgentPort`, `NotificationPort`는 아직 존재하지 않는다. 신규 계약은 소비 feature의
`features/<feature>/ports.py`가 소유하고, 두 feature 이상이 실제 공유할 때만 `app/ports/`로
승격한다.

다음은 복사 가능한 구현이 아닌 **개념적 인터페이스**다. 정확한 signature는 Phase 0의
consumer/implementation inventory와 contract test로 확정한다.

```python
class LLMProvider(Protocol):
    async def generate(self, prompt: str) -> str: ...
    async def stream(self, prompt: str) -> AsyncIterator[str]: ...

class EmbeddingProvider(Protocol):
    dimensions: int
    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...

class ChatRepository(Protocol):
    async def save_message(self, message: ChatMessage) -> None: ...
    async def list_messages(self, room_id: str) -> list[ChatMessage]: ...

class ResearchAgentPort(Protocol):
    async def answer(self, request: AgentRequest) -> AgentAnswer: ...
```

`LLMProvider`와 현재 `OllamaClient`/`OllamaChatService`의 method·return type은 일치하지 않는다.
따라서 Ollama를 현재 구현체라고 부르지 않는다. port signature를 고치거나 별도 adapter를 만든 뒤
contract test가 통과해야 구현체로 인정한다. 1536차원 검증, timeout, retry, provider-specific
response 변환은 outbound adapter가 담당한다.

## 6. Application use case

첫 번째 기준 흐름은 `SendChatMessage`다.

```text
HTTP/SSE request
  → input validation
  → emergency pre-check
  → intent routing
  → retrieval/agent port
  → safety post-check
  → ChatRepository 저장
  → response/SSE 변환
```

Use case는 provider 이름이나 HTTP status를 직접 다루지 않는다. 오류는 `ProviderUnavailable`, `SafetyBlocked`, `InvalidInput`, `PersistenceFailure` 같은 내부 예외로 변환한 뒤 inbound adapter가 API 오류로 매핑한다.

현재 기본 흐름은 `FastAPI → OllamaChatService → Mongo vector search → Ollama`이며 Router를
우회한다. 목표 흐름의 intent routing 도입은 단순 코드 이동이 아니라 behavior migration이다.
따라서 `ollama_rag`의 소유 module과 유지/대체 정책을 Phase 0에서 먼저 결정한다.

### SSE compatibility

기존 unversioned `/api/chat/*`를 frozen v1으로 취급한다. 현재 관측된 상태는
`streaming`, `processing`, `partial`, `synthesizing`, `complete`, `new_message`, `success`,
`error`, `cancelled`이며 payload text는 `content`, `answer`, `response` 중 하나다. 두 frontend
parser가 delta/snapshot 의미를 다르게 해석하므로 아래 의미표를 확정하기 전에는 호환성 완료로
판정하지 않는다.

| 상태/종료 | v1 의미 | 성공 여부 |
|---|---|---|
| `processing`, `synthesizing` | progress; 본문 교체 금지 | 미정 |
| `streaming`, `partial`, `new_message` | 현 구현별 delta/snapshot을 fixture로 동결 | 미정 |
| `complete`, `success` | 업무 성공 terminal frame | 성공 |
| `error` | stream 시작 후 업무 실패 terminal frame | 실패 |
| `cancelled` | 사용자/서버 취소 terminal frame | 실패 |
| `[DONE]` | 전송 종료 sentinel | 성공을 의미하지 않음 |

headers 전 오류는 JSON HTTP `4xx/503/504`, stream 시작 후 오류는 HTTP 200 안의 failure frame과
종료 sentinel로 표현한다. `open → completed|failed|cancelled|disconnected` 전이를 contract test로
고정하고 EOF-without-DONE, AbortSignal, session stop, partial-response 저장 정책도 검증한다.
새 named-event 계약은 별도 API ADR과 정확한 `/api/v2/chat/stream` 경로, dual-run/telemetry/rollback
정책으로만 도입한다.

## 7. Agent 설계

Agent는 **도메인 정책의 최종 소유자**가 아니라 입력 해석·오케스트레이션·표현 adapter다.

```text
사용자 입력
  → emergency rule pre-filter
  → intent classifier
  → application use case
  → Research/Welfare Parlant adapter 또는 local use case
  → safety/citation post-process
  → API response
```

Parlant Research/Welfare는 독립 프로세스로 유지하고, application 계층에는
`ResearchAgentPort`, `WelfareAgentPort`만 노출한다. Parlant가 중단되어도 Health·Community
같은 다른 기능은 계속 응답해야 한다.

## 8. 데이터와 Worker

MongoDB는 persistent state의 system of record다. 다만 소유 module과 canonical schema는 Phase 0에서
정한다. `UserAccount`, `HealthProfile`, `HealthRecord`, `ChatRoom`, `PointLedger`,
`DailySearchQuota`는 `user_id`로 연결되는 독립 aggregate root다. `rewards`가 PointLedger를
단독 소유하고 Quiz/Community는 application command만 호출한다. `research`는
ClinicalTrialsInformation과 DailySearchQuota를 소유한다. `health`는 HealthProfile과
HealthRecord를 분리해 소유하며 dormant health 경로는 Phase 3까지 신규 쓰기를 허용하지 않는다.
`diet`가 nutrition capability의 구현 owner다.

알림 outbox는 이미 FastAPI lifespan의 in-process task로 구현되어 있다. 현재 schema
`attempts/next_attempt_at/event_id/status=delivered`를 보존하고 ADR-012 승인 전에는 별도 worker
추출을 결정된 구조로 취급하지 않는다. generic job schema와 notification outbox schema를 섞지 않는다.

다음은 별도 worker 후보이며 실제 추출은 slice별 결정과 검증 뒤 수행한다.

- embedding과 vector index 갱신
- PDF/data ingestion
- PubMed enrichment와 논문 요약
- notification retry(현재 in-process 구현의 추출 후보)
- cache refresh

작업 상태는 `pending → processing → completed|failed`로 관리하고, `job_id`, `attempt_count`, `next_retry_at`, `idempotency_key`, `last_error`를 저장한다. Kafka는 현재 도입하지 않는다.

## 9. 배포 토폴로지

다음은 **로컬 개발·통합 검증용 reference topology**다.

```text
Reverse Proxy
  ├── frontend static assets
  └── backend-api
        ├── MongoDB local Docker
        ├── Ollama
        ├── Research Parlant :8800
        └── Welfare Parlant :8801

worker ── MongoDB jobs/outbox
```

ADR-005에 따라 프로덕션 배포는 MVP 범위 밖이며 이 토폴로지는 프로덕션 승인안이 아니다. 운영 배포가 필요해지면 managed/self-hosted MongoDB, HA, backup/restore, TLS, secret management를 별도 ADR로 결정한다. 그 전에도 production profile은 `debug=False`와 fail-closed 설정을 보장해야 한다.

## 10. 선택하지 않는 대안

| 대안 | 결정 | 이유 |
|---|---|---|
| Full microservices | 보류 | 현재 도메인·팀·로컬 runtime 대비 운영 복잡도가 높다. |
| Full DDD bounded-context 분리 | 보류 | 현재 domain.md가 하나의 bounded context를 정의한다. |
| 모든 기능 event-driven | 보류 | 알림·ingestion·embedding에만 비동기를 적용하는 편이 단순하다. |
| Agent가 business rule을 소유 | 금지 | 의료 안전·권한·무결성 검증을 prompt에 맡길 수 없다. |
| 유료 provider 자동 fallback | 금지 | local-first와 검증 가능성 계약을 위반한다. |

## 11. 수용 기준

- 새 application use case는 외부 SDK를 직접 import하지 않는다.
- 기존 `app/features`와 `app/ports`가 사용 중/정의만/확장/대체/폐기로 분류된다.
- Chat·Health·Welfare·Research·Nutrition·Quiz의 핵심 use case는 fake adapter 단위 테스트가 가능하다.
- 실제 Ollama/MongoDB adapter smoke가 별도로 통과한다.
- Research/Welfare customer/session/message HTTP 증거가 저장된다.
- provider 장애가 해당 기능의 명시적 오류로 끝나며 다른 기능으로 전파되지 않는다.
- frozen v1 REST/SSE response, 오류, 취소 계약과 canonical frontend 흐름이 fixture로 유지된다.
- ADR-004 ClinicalTrials 생성형 해석 위반은 제거하고 DailySearchQuota는 승인된 research
  phase에서만 구현한다.
- capability별 공통 완료 기준은 실행 계획의 acceptance matrix 한 곳에서 관리한다.

## 12. Architecture evaluation

ADR-013 승인 기준으로 ATAM-lite review를 수행했으며, 각 migration PR에서 영향받는 scenario만
다시 평가한다. scenario의 단일 source of truth는
[`ARCHITECTURE_REFERENCE_ALIGNMENT.md`](./ARCHITECTURE_REFERENCE_ALIGNMENT.md#3-초기-quality-attribute-scenario)다.

평가 기록은 다음 연결을 가져야 한다.

```text
quality scenario → architecture decision/sensitivity point
  → characterization/unit/integration/real-smoke test
  → redacted artifact → owner decision
```

RTO, latency, availability 같은 측정값은 실제 local/pilot baseline 없이 확정하지 않는다.
