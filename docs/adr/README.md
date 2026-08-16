# Architecture Decision Records (ADR) Index

이 디렉토리는 CareGuide 프로젝트의 **아키텍처 의사결정 기록**을 보관합니다.

## How to use this index

현재 계약의 우선순위는 [`DOCUMENT_CONSISTENCY_MATRIX.md`](../agents/DOCUMENT_CONSISTENCY_MATRIX.md)와 가장 최근의
명시적 Accepted ADR에 있다. Accepted ADR-004/005/006/011/013은 직접 수정하지 않으며, 결정
변경이 필요하면 다음 ADR을 추가한다.

- AI 에이전트(Verdent / Claude Code / Codex 등)는 작업 시작 전에 **모든 `Accepted` ADR을 먼저 읽어야** 합니다.
- `Accepted` 상태의 ADR은 **편집하지 않습니다**. 변경이 필요하면 새 ADR을 작성해 기존 ADR을 `Superseded` 처리하세요.
- 새 ADR은 현재 최대 번호 다음(`ADR-014-<slug>.md`)으로 작성합니다.
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
| [ADR-001](./ADR-001-canonical-frontend.md) | Canonical Frontend | ⚠️ Superseded by ADR-011 | 과거 `new_frontend/` 제안 |
| [ADR-002](./ADR-002-parlant-orchestration.md) | Parlant SDK Orchestration | 🟡 Proposed | 4개 Parlant Agent (Medical_Welfare / Nutrition / Research_Paper / Quiz) 분리, intent classifier가 라우팅 |
| [ADR-003](./ADR-003-image-upload-policy.md) | Image Upload Policy | 🟡 Proposed | 이미지 업로드 정책 (REQ-016) — 사용자 확정 대기 |
| [ADR-004](./ADR-004-clinical-trials-scope.md) | Clinical Trials Feature Scope | ✅ Accepted (Option B) | ClinicalTrials.gov 데이터를 **정보 제공** 모드로 MVP에 포함 (개인 매칭 알고리즘은 제외) |
| [ADR-005](./ADR-005-vector-db.md) | Vector Database Selection | ✅ Accepted (revised) | **로컬 Docker MongoDB Atlas Local** 사용 (1536d cosine). 현재 Ollama embedding 호환은 ADR-011 기준이며 hosted Atlas는 MVP 범위 밖 |
| [ADR-006](./ADR-006-payment-mvp-scope.md) | Payment & Point System MVP Scope | ✅ Accepted (revised) | **결제 완전 미구현** (Mock 버튼/UI 포함 모든 진입점 제거). 포인트 적립/소진 사이클은 유지 |
| [ADR-007](./ADR-007-session-management.md) | Session Management (Parlant + JWT) | 🟡 Proposed | Parlant 세션과 JWT 인증 세션 통합 모델 |
| [ADR-008](./ADR-008-single-frontend-root.md) | Single Frontend Root Directory | ⚠️ Superseded by ADR-011 | 현재 `frontend/` 단일 계약으로 대체됨 |
| [ADR-009](./ADR-009-local-first-runtime.md) | Local-First Runtime and Package Policy | ⚠️ Superseded by ADR-011 | 현재 Ollama/local Mongo 계약으로 대체됨 |
| [ADR-010](./ADR-010-local-embedding-dimension-policy.md) | Local Embedding Dimension Compatibility | ⚠️ Superseded by ADR-011 | 현재 embedding 호환 계약으로 대체됨 |
| [ADR-011](./ADR-011-current-runtime-contract.md) | Current Runtime and Product Contract | ✅ Accepted | `frontend/`, Ollama-only, local MongoDB, 5개 runtime agent의 현재 계약 |
| [ADR-012](./ADR-012-notification-outbox-and-runtime-toggle.md) | Notification Outbox and Explicit Ollama Toggle | 🟡 Proposed | 커뮤니티 알림 실패 재시도와 명시적 Ollama 가용성 계약 |
| [ADR-013](./ADR-013-feature-first-hexagonal-modular-monolith.md) | Feature-First Hexagonal Modular Monolith | ✅ Accepted (Option B) | feature-first hexagonal modular-monolith로 점진 전환; 다음 범위는 Phase 2 Chat |

## Hard constraints (binding for all agents)

다음은 `Accepted` ADR에서 파생된 강제 규칙입니다. AI 에이전트와 기여자 모두 위반 금지:

1. **결제 SDK 도입 금지** (ADR-006) — Stripe / KCP / Toss / Kakao Pay 등 결제 라이브러리 설치 및 결제 관련 신규 파일 작성 금지.
2. **임상시험은 정보 제공만** (ADR-004) — "추천드립니다" 류 능동적 권유 카피 금지. 영문 원문 병기 + 의료 면책 고지 필수.
3. **MongoDB는 로컬 Docker** (ADR-005) — `mongodb/mongodb-atlas-local` 이미지 고정. `community` 이미지는 `$vectorSearch` 미지원이므로 사용 금지.
4. **단일 제품 frontend** (ADR-011) — 신규 기능은 `frontend/`에만 추가한다. `new_frontend/`, `stitch_frontend/`는 historical rollback material이며 수정하지 않는다.
5. **점진적 구조 전환** (ADR-013) — frozen REST/SSE v1과 `legacy` 기본 selector를 유지하며 승인된 vertical slice만 전환한다.

## Cross-reference

- 진입 가이드: [`AGENTS.md`](../../AGENTS.md)
- 도메인 언어: [`docs/agents/domain.md`](../agents/domain.md)
- 이슈 트래커 정책: [`docs/agents/issue-tracker.md`](../agents/issue-tracker.md)
- 트리아지 라벨: [`docs/agents/triage-labels.md`](../agents/triage-labels.md)
