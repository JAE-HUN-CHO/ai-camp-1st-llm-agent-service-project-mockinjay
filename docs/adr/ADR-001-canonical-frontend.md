# ADR-001: Canonical Frontend

- **Status**: Superseded by ADR-011
- **Date**: 2026-05-23
- **Deciders**: TBD (요청자 확인 필요)
- **Related**: PRD v0.95 §10, `docs/converted/_ANALYSIS_REPORT.md` Section 5 RED FLAG #4

## Context

레포에 3개의 프론트엔드 디렉터리가 공존한다:

| 디렉터리 | 상태 | 특징 |
|---|---|---|
| `frontend/` | 초기 버전 (구버전) | 기본 React + TS |
| `new_frontend/` | **Enhanced 시리즈** 존재 | `ChatPageEnhanced.tsx`, `CommunityPageEnhanced.tsx`, `quizApi.ts`, `trendsApi.ts` 포함. 최근 활발히 수정됨 |
| `stitch_frontend/` | Stitch MCP로 생성된 실험본 | 디자인 시스템 탐색용. 백엔드 연동 일부만 됨 |

이 상태로는:
- 어느 코드를 수정해야 할지 매번 판단 필요 → 인지 부하
- CI/CD 빌드 대상 모호
- 신규 기여자 온보딩 시 혼란
- 동일 기능이 3곳에 중복 구현될 위험

## Decision

**`new_frontend/`를 단일 canonical frontend로 채택한다.**

- `new_frontend/`만 빌드·배포 대상으로 한다.
- `frontend/` 와 `stitch_frontend/`는 `archive/` 디렉터리로 이동하거나 별도 브랜치로 분리한 뒤 main에서 제거한다.
- README, CI 스크립트, dev 가이드의 모든 경로를 `new_frontend/` 기준으로 업데이트한다.
- 디자인 영감이 필요한 경우 `stitch_frontend/`의 컴포넌트를 `new_frontend/`로 이식하고 원본을 삭제한다.

## Rationale

1. **`new_frontend/`가 가장 완성도 높음**: Enhanced 컴포넌트, 서비스 레이어(`intentRouter.ts`, `quizApi.ts`, `trendsApi.ts`), Context API 상태관리가 안정화됨.
2. **PRD v0.95**: 사용 기술 스택은 React + TypeScript + Tailwind + Vite로 명시. `new_frontend/`가 이 스택에 가장 부합.
3. **백엔드 연동 검증 완료**: `new_frontend`는 `/api/chat/stream`, `/api/quiz/session/start` 등 실제 백엔드 엔드포인트 호출이 검증됨.
4. **중복 제거 비용 < 유지 비용**: 3중화 유지 비용이 일회성 정리 비용보다 크다.

## Consequences

**Positive**
- 빌드·배포 단일화
- 신규 기여자 온보딩 명확화
- 중복 구현 방지

**Negative**
- 일회성 마이그레이션 작업 필요
- `stitch_frontend/`에만 있던 디자인 자산 일부 손실 가능 → 사전 인벤토리 후 이식 필요

**Follow-up tasks**
1. `frontend/`, `stitch_frontend/` 의존성 인벤토리 작성
2. 가치 있는 컴포넌트·디자인 토큰을 `new_frontend/`로 이식
3. 두 디렉터리를 `archive/legacy-frontends/` 또는 별도 브랜치로 이동
4. 모든 문서·CI 경로 업데이트
