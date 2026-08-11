# CareGuide 재구성 실행 프롬프트

아래 프롬프트를 새 Codex/Claude 작업에 그대로 전달해 실행한다.

```text
당신은 CareGuide 저장소의 lead architect/executor다.

목표:
기준 통일 → 테스트 고정 → 위험 제거 → 구조 분리 → 성능 개선 순서로 프로젝트를 정리한다.
최종 top-level은 data/, docs/, scripts/, tests/, frontend/, backend/, logs/, eval/만 사용한다.

반드시 먼저 읽을 문서:
- AGENTS.md
- docs/agents/domain.md
- docs/agents/BOUNDARY_MAP.md
- docs/agents/BASELINE_INVENTORY.md
- docs/agents/CACHE_POLICY.md
- docs/adr/README.md
- docs/adr/ADR-004-clinical-trials-scope.md
- docs/adr/ADR-005-vector-db.md
- docs/adr/ADR-006-payment-mvp-scope.md
- docs/adr/ADR-008-single-frontend-root.md
- docs/adr/ADR-009-local-first-runtime.md
- docs/agents/CARE_GUIDE_REORGANIZATION_EXECUTION_PLAN.md

참고 worktree:
- .worktrees/MiniMax-M2.7-1779124465965/
- worktree의 compose/Dockerfile은 참고만 한다. mongo:7은 ADR-005의 vector 요구와 다르므로 그대로 복사하지 않는다.

강제 규칙:
1. 현재 git status/diff/untracked를 먼저 기록한다.
2. 기존 사용자 변경을 되돌리지 않는다.
3. frontend/, new_frontend/, stitch_frontend/를 바로 삭제하지 않는다.
4. new_frontend를 기능 원본으로 삼되 최종 디렉터리는 frontend/로 통일한다.
5. route/API/asset/test parity가 통과하기 전에는 frontend 폴더를 삭제·덮어쓰지 않는다.
6. cache는 domain-persistent, provider-computation, frontend UX, test fixture로 분류한다.
7. cache와 source of truth를 혼동하지 않는다.
8. LLM/embedding은 local-first adapter를 기본값으로 둔다. Ollama를 우선 검증한다.
9. DB/vector는 로컬 MongoDB를 기본값으로 둔다. mongodb/mongodb-atlas-local을 검증한다.
10. 외부 provider는 opt-in adapter로 유지한다.
11. 패키지는 최신 안정 호환 버전을 조사한 뒤 lockfile/compiled requirements로 고정한다. 무제한 latest를 사용하지 않는다.
12. 결제 SDK, 결제 UI, 결제 endpoint를 추가하지 않는다.
13. Accepted ADR을 직접 수정하지 않는다. 결정 변경은 새 ADR로 기록한다.
14. 큰 module을 분리할 때 regression test를 먼저 추가한다.
15. 한 줄짜리 pass-through module을 만들지 않는다. 실제 seam과 책임이 있을 때만 분리한다.

실행 순서:

PHASE 0 — inventory
- 세 frontend route/API/asset/test parity 표 작성
- backend feature → endpoint → data → test 표 작성
- cache key/TTL/owner/invalidation 표 작성
- data/preprocess/backend/scripts 이동 후보를 기록

PHASE 1 — local runtime/package
- docker info 확인
- mongodb/mongodb-atlas-local image와 compose 가능 여부 확인
- MongoDB healthcheck와 vector index setup 경로 작성
- Ollama health endpoint와 local generation/embedding 모델 확인
- root/backend requirements 중복을 정리할 후보 제시
- 최종 frontend 확정 후에만 package upgrade
- upgrade 전후 build/lint/test 결과 기록

PHASE 2 — tests
- auth, chat stream, emergency filter, health PATCH/null, diet upload, research quota,
  quiz points, community ownership, clinical trial cache fallback을 고정
- frontend protected route, chat stream, diet, health, trends, account를 고정
- live localhost test는 integration/e2e로 이동하고 unit은 fake adapter 사용

PHASE 3 — risk
- PII/secret/logging
- auth ownership
- upload validation
- NoSQL injection
- point idempotency
- TTL/index
- cache clear authorization
- global mutable state
- provider timeout/retry
- payment residue

PHASE 4 — frontend consolidation
- new_frontend를 source로 삼아 최종 frontend로 이전
- frontend/src/features/{chat,diet,health,research,community,quiz,account}
- frontend/src/shared/{ui,http,auth,cache}
- cross-feature 내부 import 금지
- parity test 통과 후 구 frontend/prototype 제거를 별도 커밋

PHASE 5 — backend/data/cache
- backend/app/features/{chat,diet,health,research,community,quiz,account}
- backend/app/ports와 backend/app/adapters를 실제 두 구현이 필요한 seam에만 도입
- chat의 stream/context/persistence 분리
- vector provider, embedding, cache 분리
- Mongo connection seam 하나로 통합
- Agent registry import-order/global state 제거
- Nutrition 이중 구현 parity 후 하나 선택

PHASE 6 — performance
- query profile, index, N+1
- cache hit/miss/expiry
- LLM latency/token
- frontend bundle/re-render
- stream p50/p95

매 단계 산출물:
- 변경 파일 목록
- 테스트 결과
- 남은 risk
- 다음 단계의 전제

중단 조건:
- 사용자 변경을 안전하게 구분할 수 없음
- parity 기준이 정의되지 않음
- 데이터 삭제/이동이 되돌릴 수 없음
- 동일한 실패가 세 번 반복됨

완료 조건:
- 최종 frontend/ 하나
- local MongoDB와 local model smoke
- package lock 재현
- CRITICAL/HIGH 0건
- backend/frontend/integration/e2e 검증 결과 기록
- 기존 구현 유지 또는 문서 기반 rebuild decision gate 결과 기록
```
