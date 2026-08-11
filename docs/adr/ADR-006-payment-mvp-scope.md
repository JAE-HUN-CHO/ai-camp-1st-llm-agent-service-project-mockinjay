# ADR-006: Payment & Point System MVP Scope

- **Status**: Accepted (revised: payment fully out of scope)
- **Date**: 2026-05-23
- **Decided by**: Project owner, 2026-05-23
- **Related**: PRD v0.95 §1.3 (Gamification), Requirements v0.96 정책서, KNO-006

## Context

게미피케이션 정책:
- 적립: 퀴즈 +10P, 커뮤니티 작성 +5P, 설문 +20P, 출석 +3P
- 전환: **100P = 100토큰**
- 사용처: 프리미엄 기능 (논문 검색 1일 10회 초과분, 추가 분석 등)
- KNO-006: 1일 검색 10회 제한 + 초과 시 토큰 소진 + 부족 시 결제 안내

이 시스템 구현은 다음을 요구한다:
- 포인트 적립·사용 트랜잭션 (감사 가능)
- 1일 검색 횟수 추적 (Redis or DB 카운터)
- 결제 게이트웨이 (KCP / 토스페이 / 카카오페이 / Stripe 등)
- 환불·정산·세무 처리

MVP 단계에서 **모든 것을 구현**할지, **부분 구현**할지 결정 필요.

## Decision

**MVP에서 결제 관련 기능은 완전 미구현.** Mock 버튼·UI·문구도 만들지 않는다.

| 항목 | MVP 구현 | 비고 |
|---|---|---|
| 포인트 적립 (DB 기록) | ✅ 실구현 | KNO-006 충족 |
| 포인트 잔액 조회 | ✅ 실구현 | |
| 포인트 → 토큰 전환 | ✅ 실구현 | 내부 단위 변환만 |
| 1일 검색 10회 제한 | ✅ 실구현 (MongoDB TTL counter) | |
| 한도 초과 시 안내 | ✅ "내일 다시 이용해 주세요" 류 안내 | 결제 유도 카피 금지 |
| **실제 결제 게이트웨이** | ❌ 미구현 | 코드/SDK/스텁 추가 금지 |
| **Mock 결제 버튼/페이지** | ❌ 미구현 | UI에 결제 진입점 자체 없음 |
| 환불·정산·세금 | ❌ | |

## Rationale

1. **사용자 결정**: 프로젝트 오너가 결제 옵션 미구현을 명시적으로 지시.
2. **법적/회계 부담 회피**: 사업자등록·PG계약·약관·환불정책·세무 부담을 MVP에서 분리.
3. **혼란 방지**: Mock 결제 UI는 "준비 중" 표시여도 결제 의도 데이터 수집용으로만 가치 있음 → 본 결정에서 가치 < 구현/유지비용 + 사용자 혼란 비용으로 판단.
4. **포인트 시스템은 게미피케이션 목적으로 충분**: 결제 연동 없이도 KNO-006 한도/적립/소진 사이클은 닫힌다.

## Schema (MVP)

```
Collection: user_points
{
  _id: ObjectId,
  user_id: str,
  balance: int,         // 현재 포인트
  total_earned: int,
  total_spent: int,
  updated_at: datetime
}

Collection: point_transactions
{
  _id: ObjectId,
  user_id: str,
  type: "earn" | "spend" | "convert",
  source: "quiz" | "community" | "survey" | "attendance" | "research_search",
  amount: int,          // +/- 변경량
  balance_after: int,
  metadata: dict,       // {quiz_id, post_id, ...}
  created_at: datetime
}

Collection: daily_search_counter (TTL 24h)
{
  _id: "{user_id}:{YYYY-MM-DD}",
  count: int,
  expires_at: datetime  // TTL index
}
```

## Consequences

**Positive**
- MVP 출시 일정 보호
- 법적/회계 리스크 0
- UI 단순화 (결제 진입점 자체가 없으므로 분기 감소)

**Negative**
- 한도 초과 사용자가 그 자리에서 추가 사용 불가 → 안내 카피로 명확히 처리
- 후속에 결제를 도입할 때 별도 ADR + UI 신규 추가 필요

**Hard rules**
- `npm install stripe|@stripe/*|kcp|toss-payments|kakao-pay` 등 결제 SDK 추가 금지.
- `backend/app/api/payment*.py` 류 파일 신설 금지.
- `new_frontend/src/pages/Payment*.tsx` 류 페이지 신설 금지.
- 위 항목이 필요해질 경우 본 ADR을 Superseded 처리하는 신규 ADR을 먼저 작성.

**Follow-up tasks**
1. Point 트랜잭션 멱등성 보장 (unique index on `(user_id, source, metadata.<id>)`).
2. `daily_search_counter` TTL index 검증 (`expireAfterSeconds`).
3. 한도 초과 안내 카피 작성 (결제 유도 X, 정보 제공 O).
