# Architecture Decision Records (ADR) Index

이 디렉토리는 CareGuide 프로젝트의 **아키텍처 의사결정 기록**을 보관합니다.

## How to use this index

- AI 에이전트(Verdent / Claude Code / Codex 등)는 작업 시작 전에 **모든 `Accepted` ADR을 먼저 읽어야** 합니다.
- `Accepted` 상태의 ADR은 **편집하지 않습니다**. 변경이 필요하면 새 ADR을 작성해 기존 ADR을 `Superseded` 처리하세요.
- 새 ADR은 다음 번호(`ADR-008-<slug>.md`)로 작성합니다.
- ADR Status: `Proposed` → `Accepted` → (필요 시) `Superseded`

## Status legend

| Symbol | Meaning |
|---|---|
| ✅ | Accepted — binding, do not edit |
| 🟡 | Proposed — open for discussion |
| ⚠️ | Superseded — historical reference only |

## Index

| # | Title | Status | Decision summary |
|---|---|---|---|
| [ADR-001](./ADR-001-canonical-frontend.md) | Canonical Frontend | 🟡 Proposed | `new_frontend/` 를 단일 canonical 프론트엔드로 지정 (`frontend/`, `stitch_frontend/`은 deprecated) |
| [ADR-002](./ADR-002-parlant-orchestration.md) | Parlant SDK Orchestration | 🟡 Proposed | 4개 Parlant Agent (Medical_Welfare / Nutrition / Research_Paper / Quiz) 분리, intent classifier가 라우팅 |
| [ADR-003](./ADR-003-image-upload-policy.md) | Image Upload Policy | 🟡 Proposed | 이미지 업로드 정책 (REQ-016) — 사용자 확정 대기 |
| [ADR-004](./ADR-004-clinical-trials-scope.md) | Clinical Trials Feature Scope | ✅ Accepted (Option B) | ClinicalTrials.gov 데이터를 **정보 제공** 모드로 MVP에 포함 (개인 매칭 알고리즘은 제외) |
| [ADR-005](./ADR-005-vector-db.md) | Vector Database Selection | ✅ Accepted (revised) | **로컬 Docker `mongodb-atlas-local`** 이미지 사용 (1536d cosine, text-embedding-3-small). Atlas 클라우드는 MVP 범위 밖 |
| [ADR-006](./ADR-006-payment-mvp-scope.md) | Payment & Point System MVP Scope | ✅ Accepted (revised) | **결제 완전 미구현** (Mock 버튼/UI 포함 모든 진입점 제거). 포인트 적립/소진 사이클은 유지 |
| [ADR-007](./ADR-007-session-management.md) | Session Management (Parlant + JWT) | 🟡 Proposed | Parlant 세션과 JWT 인증 세션 통합 모델 |
| [ADR-008](./ADR-008-single-frontend-root.md) | Single Frontend Root Directory | 🟡 Proposed | `frontend/`, `new_frontend/`, `stitch_frontend/`를 최종 `frontend/` 하나로 통합하는 제안 |
| [ADR-009](./ADR-009-local-first-runtime.md) | Local-First Runtime and Package Policy | 🟡 Proposed | 최신 호환 패키지를 lock하고 로컬 모델·로컬 MongoDB를 기본 실행 경로로 삼는 제안 |
| [ADR-010](./ADR-010-local-embedding-dimension-policy.md) | Local Embedding Dimension Compatibility | 🟡 Proposed | ADR-005의 1536d 계약을 local provider와 cache에서 fail-closed로 보호 |

## Hard constraints (binding for all agents)

다음은 `Accepted` ADR에서 파생된 강제 규칙입니다. AI 에이전트와 기여자 모두 위반 금지:

1. **결제 SDK 도입 금지** (ADR-006) — Stripe / KCP / Toss / Kakao Pay 등 결제 라이브러리 설치 및 결제 관련 신규 파일 작성 금지.
2. **임상시험은 정보 제공만** (ADR-004) — "추천드립니다" 류 능동적 권유 카피 금지. 영문 원문 병기 + 의료 면책 고지 필수.
3. **MongoDB는 로컬 Docker** (ADR-005) — `mongodb/mongodb-atlas-local` 이미지 고정. `community` 이미지는 `$vectorSearch` 미지원이므로 사용 금지.
4. **새 프론트엔드 프레임워크 도입 금지** (ADR-001 Proposed지만 운영 규칙으로 적용) — `frontend/`, `stitch_frontend/`에 신규 기능 추가 금지.

## Cross-reference

- 진입 가이드: [`AGENTS.md`](../../AGENTS.md)
- 도메인 언어: [`docs/agents/domain.md`](../agents/domain.md)
- 이슈 트래커 정책: [`docs/agents/issue-tracker.md`](../agents/issue-tracker.md)
- 트리아지 라벨: [`docs/agents/triage-labels.md`](../agents/triage-labels.md)
