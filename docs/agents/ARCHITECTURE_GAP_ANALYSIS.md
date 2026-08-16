# CareGuide 아키텍처 갭 분석

**작성일:** 2026-08-15
**비교 기준:** [`ARCHITECTURE_CURRENT_STATE.md`](./ARCHITECTURE_CURRENT_STATE.md)와 [`ARCHITECTURE_REFACTORING_DESIGN.md`](./ARCHITECTURE_REFACTORING_DESIGN.md)
**방법 근거:** [`ARCHITECTURE_REFERENCE_ALIGNMENT.md`](./ARCHITECTURE_REFERENCE_ALIGNMENT.md)의 ATAM-lite·SSDF·risk-based verification

## 1. 요약

현재는 API/service/repository/adapter와 Agent core뿐 아니라 `app/features`와 `app/ports`도 존재하므로 리팩토링의 출발점은 있다. 그러나 기존 seam이 모든 use case의 중심은 아니고 의존성 방향도 통일되지 않았으며, 같은 책임의 구현·cache·Mongo connection seam이 중복되어 있다.

가장 큰 갭은 다음 여섯 가지다.

1. ADR-004 임상시험 정보 제공 범위와 실제 생성형 해석 API가 충돌함
2. 응급 pre-filter, chat room/session 소유권, token/PII 보안이 모든 경로에서 강제되지 않음
3. Research/Welfare 및 핵심 Chat의 실제 HTTP 흐름이 증명되지 않음
4. 기본 Chat은 5개 Agent Router를 우회하고, port는 정의만 되어 있어 목표 migration 기준이 불명확함
5. health/rewards/quota의 schema·aggregate owner가 분산되거나 미구현임
6. runtime state, cache, persistence의 소유자가 분산됨

## 2. 갭 목록

| 우선순위 | 영역 | 현재 | 목표 | 영향 | 해결 방향 |
|---|---|---|---|---|---|
| P0 | 실제 통합 증거 | 내부 초기화·단위 테스트 중심 | customer/session/message와 API 전체 왕복 | 운영 준비도 판단 불가 | real HTTP smoke와 artifact 저장 |
| P0 | 임상시험 안전 | `/detail`이 eligibility·clinical significance LLM 해석을 공개 반환 | ADR-004의 원문·충실한 번역·정보 제공만 | Accepted ADR 위반 | 생성형 해석 제거/비활성화와 contract test |
| P0 | 응급 안전 | direct Ollama/Router/Parlant의 keyword·종료 동작 불일치 | 모든 entrypoint 전 단일 fail-closed pre-filter | false-negative 위험 | `EmergencySafetyPolicy`와 전 경로 contract/eval |
| P0 | 접근제어 | chat `room_id`/`session_id` owner 검증 누락 경로 | `ActorContext`와 owner-bound repository | 타 사용자 room 주입 위험 | 모델/저장 전 403/404, 교차 사용자 테스트 |
| P0 | 민감정보 | token/chat/응답이 localStorage·console·log에 남음 | allowlist log, memory/cookie auth, PII canary 0건 | 계정·건강정보 노출 | 외부 파일럿 NO-GO, storage/log 제거 |
| P0 | 직접 infrastructure 의존 | Agent/router/service가 Mongo/Ollama를 직접 import | application은 port만 의존 | provider 교체·단위 테스트 어려움 | port 정의와 adapter 주입 |
| P0 | SSE 호환성 | 상태/payload/오류 의미가 backend와 frontend parser마다 다름 | frozen v1 frame/state matrix | 오류를 성공으로 오인 | fixture 계약, 전/후-header 오류 분리 |
| P1 | 설계 승인 | 설계 문서만 있고 Accepted ADR이 없음 | ADR-013 승인 후 구조 구현 | 결정·대안·롤백 추적 불가 | ADR-013 Proposed → review → Accepted |
| P1 | 기존 seam mapping | `app/features`, `app/ports`가 이미 존재 | 재사용·확장·대체 mapping 명시 | 중복 port/feature 생성 | Phase 0 inventory와 mapping 표 |
| P1 | 기본 Chat behavior | direct `OllamaChatService`가 Router를 우회 | `ollama_rag` 유지/대체를 명시 | 의도치 않은 behavior change | selector와 characterization test |
| P1 | runtime capability | ADR-011의 5개 Agent 중 일부 목표 module mapping 불명확 | 5개 capability 모두 목표 module/facade에 mapping | 기능 누락 위험 | Quiz/Trend 포함 mapping 고정 |
| P1 | domain/data ownership | health 3경로, points schema 중복, quota 부재 | aggregate별 단일 owner/schema | 데이터 유실·불변식 위반 | route/collection/schema matrix와 별도 migration 결정 |
| P1 | 대형 모듈 | chat/community/research 파일이 transport·DB·provider를 혼합 | inbound/application/outbound 분리 | 변경 영향 범위 큼 | vertical slice별 strangler refactor |
| P1 | Agent 중복 | `backend/Agent`와 `backend/agents`에 Nutrition 경로 공존 | 하나의 source of truth + compatibility facade | 동작 불일치 | canonical implementation 결정 후 facade 유지 |
| P1 | Mongo seam | `connection.py`, `mongodb_manager.py`, 각 client가 lifecycle 공유 | 단일 composition root와 repository port | transaction/lifecycle 혼란 | container에서 연결·repository 조립 |
| P1 | cache/state | process-global cache와 active stream 혼재 | persistent cache, computation cache, runtime state 분리 | 다중 인스턴스 불일치 | 소유자·TTL·scope를 명시하고 주입 |
| P1 | ADR-006 quota | `daily_search_counter` 코드/index 없음 | research-owned 10/day quota | binding 계약 미구현 | canonical schema·TTL·테스트 추가 |
| P1 | 오류 계약 | provider별 예외와 API 오류 매핑이 균일하지 않음 | 내부 오류 taxonomy와 API envelope | 장애 시 사용자 경험 불일치 | exception mapper와 request_id |
| P2 | frontend 계약 | typed client는 있으나 큰 service/module과 hook 경고 존재 | feature별 client/use case boundary | 변경·회귀 추적 어려움 | API contract와 feature client 정리 |
| P2 | 관측성 | 로그·smoke 스크립트는 있으나 전체 correlation 부족 | request/agent/provider/job trace | 장애 원인 추적 지연 | structured log와 metrics |
| P2 | 릴리스 | 계획·체크리스트는 존재하지만 일부 미실행 | 단계별 gate와 clean artifact | 완료 판단 과장 위험 | acceptance evidence ledger |
| P2 | quality measure | 일반적인 `통과` 조건 중심 | source/stimulus/response/measure scenario | tradeoff·회귀 판단이 주관적 | quality scenario와 test/artifact traceability |

## 3. 의존성 갭

### 현재

```text
API → Service/Feature runtime → 일부 Repository/Adapter
app/ports Protocol → production consumer 없음
Agent → DB/Client/Service 직접 호출
Parlant server → NLP/Search/Cache/Tool 직접 소유
FastAPI default chat → OllamaChatService 직접 호출
```

### 목표

```text
Inbound Adapter → Application Use Case → Port ← Outbound Adapter
FastAPI/Parlant handler ──────────────┘
Parlant HTTP client ───────────────────────────────┘
```

현재 구조의 가장 중요한 수정은 폴더를 옮기는 것이 아니라 **import 방향을 바꾸는 것**이다.

## 4. 검증 갭

현재 확인된 것은 다음 범위다.

- frontend build 통과
- frontend lint 오류 0개, 경고 70개
- backend 핵심 unit 8개 통과
- 일부 Ollama/MongoDB/embedding 초기화·adapter 검증

아직 release evidence로 인정할 수 없는 것:

- Research Parlant 전체 customer → session → message 흐름
- Welfare Parlant 전체 customer → session → message 흐름
- `/api/chat/message`와 `/api/chat/stream`의 실제 local runtime 왕복
- 브라우저 주요 여정과 네트워크 4xx/5xx 부재
- Ollama/MongoDB/Parlant 장애·재시도·fail-fast 시나리오
- 보안 로그에서 PII와 모델 원문이 제거됐다는 end-to-end 증거
- room/session 교차 사용자 접근 거부와 전 경로 emergency short-circuit
- ClinicalTrials 응답이 LLM 해석·추천 없이 원문/번역/면책만 제공한다는 계약
- ADR-006 10/day search quota의 TTL·동시성·우회 방지

## 5. 비기능 갭

### Reliability

- Parlant 서버는 별도 entrypoint/port를 가지지만 실제 readiness/liveness와 재시작 정책을 통합해야 한다.
- Chat `StreamRegistry`는 application-scoped process-local이고, Nutrition conversation state는 Agent instance-scoped이므로 수평 확장 시 공유·복구 정책이 필요하다.
- worker job의 idempotency와 retry evidence가 필요하다.
- `run_unified_server.py`는 local Ollama NLP 주입과 env port를 사용하지 않으므로 canonical
  entrypoint가 아니다. standalone Research/Welfare entrypoint를 기준으로 삼고 404가 아닌
  200+schema+agent identity로 readiness를 판정해야 한다.
- `/health`는 process liveness와 dependency/capability readiness로 분리해야 한다.

### Security and medical safety

- access token과 chat preview가 현재 localStorage에 있고 token/user/SSE가 console에 출력된다.
- chat room/session은 JWT subject와 owner-bound query로 모델 호출·저장 전에 검증해야 한다.
- emergency 정책은 `target_agent`를 포함한 모든 direct/router/Parlant 경로 앞에서 실행해야 한다.
- 로그 redaction은 실제 request/agent/provider 실패에 canary PII를 주입해 검증해야 한다.
- ClinicalTrials는 생성형 적합성·eligibility·임상적 의의 해석을 제공하면 안 된다.

### Maintainability

- lint warning과 Pydantic/FastAPI deprecation을 추적해야 한다.
- `backend/Agent`와 `backend/agents` 중복 경로의 source of truth를 정해야 한다.
- 문서의 과거 완료 보고와 현재 runtime contract가 충돌하지 않도록 historical 표기를 유지해야 한다.

## 6. 우선순위 결정

구조 구현 전에 P0 안전 위반을 막고 ADR-013 승인 조건과 기존 seam mapping을 완료한다. 그 다음
구조 리팩토링보다 먼저 P0 통합 증거를 확보한다. 실제 서비스가 끝까지 왕복되지 않은 상태에서
폴더를 재배치하면 실패 원인을 구조 변경과 runtime 문제로 구분하기 어렵다.

순서는 다음과 같다.

```text
ADR-004/006/security P0 정합성
  → ADR-013 + 기존 seam/domain/schema mapping
  → 실제 runtime gate
  → Chat vertical slice
  → Health/Welfare vertical slice
  → shared ports/adapter 정리
  → cache/state/worker 분리
  → frontend·release hardening
```
