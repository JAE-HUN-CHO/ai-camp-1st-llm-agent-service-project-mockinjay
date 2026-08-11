# ADR-007: Session Management (Parlant + JWT 통합)

- **Status**: Proposed
- **Date**: 2026-05-23
- **Related**: Requirements v0.96 정책서, `backend/app/api/auth.py`, recent commit `9398218 feat: Parlant 세션을 미리 생성하는 채팅방 생성 기능 추가`

## Context

CareGuide는 두 종류의 세션이 동시에 운영된다:

1. **사용자 인증 세션** (JWT)
   - Access token: 1시간 만료
   - Refresh token: 7일 만료
   - 비로그인 사용자: GUID 캐시 세션 20분 (재접속 시 자동 복원)

2. **Parlant 대화 세션** (Parlant SDK)
   - Agent별 대화 컨텍스트 유지
   - 멀티턴 5턴 컨텍스트 보존 (REQ-019)
   - Parlant 서버(8800)에서 별도 관리

쟁점:
- 두 세션의 **lifecycle을 어떻게 동기화**할 것인가
- 비로그인 사용자가 로그인 시 Parlant 세션을 **이어받을 것인가, 새로 만들 것인가**
- Parlant 세션 ID를 어디에 저장하고 누가 발급할 것인가
- 채팅방(room) 단위와 Parlant 세션의 매핑

## Decision

### 1. Session Key는 프론트엔드 발급, UUID v4 사용
- FE가 채팅방 생성 시 `session_key = uuidv4()` 생성
- 백엔드는 이 키로 Parlant 세션을 미리 생성(precreate)하여 매핑 저장
- 동일 `session_key` 재사용 시 기존 Parlant 세션 재연결

### 2. Parlant 세션 ↔ chat_room ↔ user_id 3중 매핑

```
Collection: chat_rooms
{
  _id: ObjectId,
  session_key: str (uuid),       // FE 생성
  parlant_session_id: str,        // Parlant 서버가 발급
  user_id: str | null,           // null = 비로그인 (GUID)
  guid: str | null,              // 비로그인 사용자 GUID
  agent_type: "Medical_Welfare" | "Nutrition" | "Research_Paper" | "Quiz",
  title: str,
  created_at: datetime,
  last_active_at: datetime,
  expires_at: datetime           // 비로그인은 20분 후 만료
}
```

### 3. JWT ↔ Parlant 세션 lifecycle 분리
- JWT 만료가 곧 Parlant 세션 만료를 의미하지 않는다.
- Refresh token으로 JWT 재발급 시 동일 Parlant 세션 재연결.
- **로그인 전후 세션 승계**: 비로그인 GUID 세션에서 로그인 시 → 해당 chat_rooms의 `user_id` 필드를 업데이트하고 `guid` 필드는 null로 (옵션: 사용자 동의 후 승계).

### 4. 비로그인 → 로그인 승계 정책 (UX)
- 로그인 시 GUID에 연결된 chat_room이 있으면 모달로 사용자에게 묻는다: "이전 대화를 계정에 연결하시겠습니까?"
- 동의 시 `user_id` 업데이트 + GUID 세션 종료
- 거부 시 GUID 세션은 20분 만료 흐름 그대로 유지

### 5. Parlant 세션 정리 (TTL)
- `expires_at` TTL index로 만료된 chat_rooms 자동 삭제 + Parlant 서버에 세션 종료 호출(soft cleanup job).
- 로그인 사용자의 chat_rooms는 무기한 보관 (사용자가 명시적으로 삭제하지 않는 한).

## Rationale

- **FE 발급 UUID**: 백엔드 round-trip 없이 즉시 채팅방 UI 생성 가능. 충돌 확률 무시.
- **3중 매핑**: 채팅방·사용자·Parlant 세션이 N:1:1로 묶이므로 인덱스만 잘 잡으면 단일 컬렉션으로 충분.
- **Lifecycle 분리**: JWT 갱신마다 Parlant 세션 재생성하면 컨텍스트 손실. 분리가 정합.
- **명시적 승계 동의**: 개인정보 보호 관점에서 비로그인 데이터의 로그인 계정 승계는 사용자 동의 필수.

## Consequences

**Positive**
- JWT 갱신·로그아웃과 무관하게 대화 컨텍스트 유지
- 채팅방 단위로 Agent별 컨텍스트 격리 가능
- 비로그인 사용자도 Parlant 풀 기능 사용 가능

**Negative**
- chat_rooms 컬렉션 커짐 → 인덱스 설계·아카이빙 정책 필요
- Parlant 서버와 백엔드 간 세션 동기화 실패 시 stale 세션 정리 잡 필요

**Follow-up tasks**
1. `chat_rooms` 컬렉션 인덱스: `{user_id, last_active_at}`, `{guid, expires_at}`, `{session_key} unique`
2. TTL index 추가: `{expires_at: 1}` (partial filter: `user_id = null`만)
3. Parlant 서버 dead session cleanup 잡 작성
4. 로그인 시 GUID 승계 모달 UI 구현
5. `auth.py`의 refresh token flow에서 Parlant 세션 보존 검증 테스트 추가
