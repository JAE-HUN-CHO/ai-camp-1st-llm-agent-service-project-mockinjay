# ADR-008: Single Frontend Root Directory

- **Status**: Proposed
- **Date**: 2026-08-11
- **Related**: [ADR-001](./ADR-001-canonical-frontend.md), [`BOUNDARY_MAP.md`](../agents/BOUNDARY_MAP.md)

## Context

현재 저장소에는 `frontend/`, `new_frontend/`, `stitch_frontend/`가 공존한다. 구현·테스트·실행 경로가 분산되어 어느 디렉터리가 제품 코드인지 혼동이 발생한다.

## Proposed Decision

최종 제품 frontend의 최상위 디렉터리 이름을 `frontend/` 하나로 통일한다.

- `new_frontend/`를 기능 원본으로 삼아 최종 `frontend/`로 이전한다.
- 기존 `frontend/`는 기능별로 재사용·대체·폐기 판정한다.
- `stitch_frontend/`는 디자인 자산·토큰만 선별 이관한다.
- 세 디렉터리를 동시에 유지하는 기간은 parity test 통과 전까지로 제한한다.
- parity 검증 후 `new_frontend/`, `stitch_frontend/`는 별도 삭제 커밋으로 제거한다.
- 이 ADR이 Accepted 되기 전까지 기존 디렉터리를 삭제하지 않는다.

## Rationale

- 최상위 구조를 사용자가 제안한 `data/docs/scripts/tests/frontend/backend/logs/eval`로 단순화한다.
- 실행·CI·온보딩 경로를 하나로 만든다.
- 기능 원본은 현재 완성도가 높은 `new_frontend/`를 활용해 재작성 비용을 줄인다.

## Consequences

### Positive

- frontend 구현·테스트·배포 대상이 명확해진다.
- 중복 화면과 API client를 제거할 수 있다.
- 문서와 실행 명령이 단순해진다.

### Negative

- 디렉터리 이전 중 import/env/test 경로 수정이 필요하다.
- 기존 `frontend/`의 고유 기능을 잃지 않도록 inventory와 parity test가 필요하다.
- `new_frontend/`를 최종 경로로 유지하자는 ADR-001의 Proposed 방향과 조정이 필요하다.

## Acceptance Criteria

- 최종 문서·CI·실행 가이드가 `frontend/`만 참조한다.
- route, API client, asset, test parity 검증표가 작성된다.
- `frontend/`에서 build/lint/test가 통과한다.
- `new_frontend/`와 `stitch_frontend/` 삭제 전 기능 손실이 없음을 확인한다.

## Follow-ups

1. `BASELINE_INVENTORY.md`에 세 frontend 비교표 작성
2. 최종 frontend migration branch 생성
3. route/API/asset parity test 추가
4. 소유자가 제안 결정 승인 시 상태를 Accepted로 갱신하고 ADR-001과의 관계를 정리
