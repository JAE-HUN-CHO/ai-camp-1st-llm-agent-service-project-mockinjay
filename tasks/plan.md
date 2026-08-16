# CareGuide 리팩토링 실행 계획

## 현재 판정

- Phase 0~1: 완료·검증됨.
- ADR-013: Accepted. Option B Feature-first Hexagonal Modular Monolith 채택.
- 다음 실행 범위: Phase 2 Chat vertical slice만 승인됨.
- Phase 3 이후: 승인되지 않음. Phase 2 결과 보고 후 중단.

Phase 0~1 runtime evidence는
`logs/verification/fda93b9dbb8107ecbffa593041c9417f822a6688/20260815T143102Z/manifest.json`
(worktree fingerprint `d5f1f73380f1f107e6ed2861032fc89b929f32553e5fe5ee3145a85fa45dfb04`)에 있다.
`logs/`는 git-ignored이므로 manifest, Git SHA, fingerprint를 함께 대조한다.

## 완료된 Phase 0~1

- [x] API·route/service/schema/test·feature/port/adapter/Agent inventory
- [x] ATAM-lite risk → scenario → test → artifact traceability
- [x] ClinicalTrials 생성형 해석 제거와 source-faithful contract
- [x] 단일 EmergencySafetyPolicy와 ActorContext owner gate
- [x] browser/log/artifact PII canary gate
- [x] Research/Welfare customer → session → message 실제 HTTP
- [x] Chat message/stream smoke, strict readiness, timeout/non-zero 계약
- [x] ADR-013 owner 결정과 Phase 2 Chat 승인

## Phase 2 — Chat vertical slice

1. 기존 REST/SSE v1 facade와 payload/status/cancel 의미를 characterization test로 고정한다.
2. `ChatRoom`, `ChatMessage`, `ChatSafetyPolicy`와 application use case를 feature 내부에 둔다.
3. `ChatRepository`, `ChatGenerator`, `AgentRouter` port를 중복 없이 정의한다.
4. MongoDB/Ollama/legacy Agent를 outbound adapter로 조립한다.
5. `CHAT_IMPLEMENTATION=legacy|hex` selector는 composition root에서 한 번만 평가하고 기본값은
   `legacy`로 둔다.
6. ActorContext owner 확인과 EmergencySafetyPolicy를 model/provider/DB write 전에 유지한다.
7. legacy/hex contract parity, cross-user, failure, cancellation, idempotency를 검증한다.
8. local MongoDB + Ollama 실제 HTTP로 message/stream terminal과 `[DONE]`을 분리 검증한다.
9. legacy/new call telemetry와 rollback drill을 증거로 남긴다.

## 보존해야 할 ADR-013 결정

- PointLedger owner: `rewards`
- ClinicalTrialsInformation, DailySearchQuota owner: `research`
- HealthProfile과 HealthRecord 분리; dormant health 신규 쓰기는 Phase 3까지 금지
- 구현 owner `diet`, 공개 capability `nutrition`
- 기존 REST/SSE v1 동결, selector 기본값 `legacy`
- RemoteAgent와 compatibility facade는 telemetry 확인 전 삭제 금지
- Parlant 별도 프로세스 유지; worker 분리는 장시간 작업에만 적용

## Phase 2 완료 gate

- 변경 Python Ruff 0 error
- backend unit + 명시적 integration 통과
- frontend test/build/lint 통과
- architecture dependency와 doc-link gate 통과
- 실제 local HTTP artifact와 동일 SHA manifest 존재
- hosted provider call 0, PII canary 0, cross-user unauthorized write 0
- `git diff --check` 통과

Phase 2가 실패하거나 최종 HTTP artifact가 없으면 Phase 3으로 진행하지 않고 마지막 성공 지점,
재현 명령, 오류, 다음 조치를 보고한다.
