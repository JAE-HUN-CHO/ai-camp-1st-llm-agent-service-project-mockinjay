# CareGuide 현재 아키텍처 및 시스템 상태

**작성일:** 2026-08-15
**상태:** 사실 기준 문서
**목적:** 리팩토링 전 현재 구현·의존성·검증 상태를 기록한다.
**Snapshot:** `fda93b9dbb81` (`codex/ollama-integration-smoke-fix`)

> 이 문서는 완료 보고서가 아니다. 문서에 존재하는 계획과 실제 실행 증거를 구분한다.
> 도메인은 [`domain.md`](./domain.md)의 규칙대로 하나의 CKD bounded context로 유지한다.

## 1. 현재 런타임 계약

- canonical frontend는 `frontend/`이다.
- FastAPI 진입점은 `backend/app/main.py`이다.
- Agent 구현은 `backend/Agent/`에 있지만 HTTP 런타임 조립·lifecycle은
  `backend/app/services/agent_runtime.py`와 `backend/app/main.py`가 소유한다.
- 기본 `OLLAMA_ENABLED=true` chat 경로는 Router/5개 capability를 거치지 않고
  `OllamaChatService`를 직접 호출한다. Router/AgentManager 경로는 compatibility fallback이다.
- 생성·임베딩 기본 provider는 로컬 Ollama이다.
- 데이터베이스와 vector search는 로컬 Docker MongoDB 계약을 따른다.
- Parlant Research/Welfare는 별도 서버 진입점과 포트(`8800`/`8801`)를 가진다. 실제 listening 및 customer/session/message 왕복은 아직 release evidence가 없다.
- ClinicalTrials.gov는 정보 제공 범위로 포함해야 한다. 그러나 현재 detail endpoint의
  `aiSummary`는 `Clinical Significance`를 LLM으로 생성하므로 ADR-004 위반 상태다.
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
  api/ → services/ → repositories/db/adapters
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
조립하고 `backend/Agent`가 Agent 구현과 Parlant server 코드를 가진다. `app/features`의 대부분은
metadata/naming anchor이고, `app/ports` 네 개는 정의되어 있지만 production consumer가 없다.
따라서 이들을 완성된 hexagonal seam으로 간주하면 안 된다. 특히 Nutrition은
`backend/agents/`와 `backend/Agent/`에 구현이 중복되어 있다.

## 3. 구현상 강점

| 영역 | 현재 상태 |
|---|---|
| 외부 provider | Ollama, MongoDB, PubMed, Parlant를 adapter/client 형태로 분리하려는 구조가 존재한다. |
| Agent 공통 계약 | `Agent/core/contracts.py`, `local_agent.py`, `remote_agent.py`가 공통 실행 계약을 제공한다. |
| 기존 port | `app/ports/llm.py`, `embedding.py`, `vector.py`, `external_search.py`가 정의돼 있으나 production wiring/consumer는 확인되지 않았다. |
| 기존 feature seam | `app/features/chat`, `research`에는 runtime이 있고 다른 feature는 주로 metadata/naming anchor다. |
| API 계층 | 도메인별 FastAPI router와 service/repository 계층이 존재한다. |
| 데이터 경계 | MongoDB repository·vector adapter·local data 처리 경계가 문서화되어 있다. |
| 런타임 안전 | 포트 검증, embedding 차원 검증, Ollama-only 정책, emergency pre-filter가 존재한다. |
| 검증 기반 | backend unit/integration, frontend build/lint/test, eval 및 component smoke가 있으나 real HTTP/browser gate는 없다. |

### 이미 구현된 비동기 경계

알림 outbox는 신규 설계가 아니라 현재 구현이다. `notification_service.py`에 event id,
atomic lease, backoff, terminal failure가 있고 FastAPI lifespan이 in-process periodic task를
시작한다. 별도 worker 프로세스와 live 실패→재시도 증거, backlog 진단은 없다. ADR-012는
여전히 Proposed이므로 구현 사실과 결정 승인을 구분한다.

## 4. 구조적 결합

### 4.1 API와 업무 로직의 결합

일부 대형 router가 HTTP validation, DB query, 외부 provider 호출, cache, 응답 변환을 동시에 수행한다.

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

2026-08-15에 위 snapshot에서 다시 실행한 검증:

아래 결과는 동일 snapshot에서 재실행했지만 영구 artifact로 보관하지 않았다.

| 검증 | 결과 | 의미 |
|---|---|---|
| `cd frontend && npm run build` | 통과 | TypeScript compile 및 Vite production bundle 생성; 보관 artifact 없음 |
| `cd frontend && npm run lint` | 오류 0, 경고 70 | 정적 오류는 없지만 hook/`any`/번들 관련 정리 필요 |
| `cd frontend && npm run test -- --run` | 30 files, 410 tests passed | unit/component 범위이며 실제 browser E2E는 아님 |
| `PYTHONPATH=backend .venv/bin/python -m pytest -q tests/backend/unit/test_api_contract.py tests/backend/unit/test_logging_redaction.py tests/backend/unit/test_ollama_chat_service.py` | 8 passed | 핵심 단위 계약 일부 통과 |
| 전체 Research/Welfare Parlant HTTP smoke | 미완료 | customer/session/message 왕복 증거가 없음 |
| 전체 핵심 API·브라우저 흐름 | 미완료 | 실제 서비스 사용자 여정의 통합 증거가 부족함 |

`tasks/plan.md`와 `tasks/todo.md`의 체크리스트는 계획 문서이며, 체크되지 않은 항목을 실행 증거로 간주하지 않는다.

## 6. 운영 판정

현재 시스템은 **내부 개발·QA 데모 전용**이다. 공개 운영과 외부 파일럿은 NO-GO다.
특히 access token의 `localStorage` 저장·복원과 token/user console logging은
`CACHE_POLICY.md`의 민감정보 규칙을 현재 위반한다. 다음이 먼저 필요하다.

1. Research/Welfare 실제 HTTP customer → session → message 흐름
2. `/api/chat/message`, `/api/chat/stream` end-to-end 흐름
3. 의료 안전·provider 장애·Mongo 재시도 시나리오
4. token 저장·로그 위반 제거와 실제 request/provider redaction 증거
5. CI와 릴리스 gate
6. ADR-004 임상시험 생성형 해석 제거, ADR-006 daily quota 구현 또는 정합성 결정

이 문서에서 “현재 adapter가 존재한다”는 표현은 “provider 교체가 완전히 검증됐다”는 의미가 아니다.
