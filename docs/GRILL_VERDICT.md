# Grill Verdict — CareGuide 프로젝트 현황 판정

- **Date**: 2026-05-23
- **Source**: `docs/raw_docs/gdrive/` 최신 문서 (PRD v0.95, Requirements v0.96, 지식검색 흐름도) vs 현재 코드베이스
- **Companion docs**: `docs/CONTEXT.md`, `docs/adr/ADR-001 ~ ADR-007`

---

## 1. 종합 판정: 🟡 Yellow

코드베이스는 동작은 하지만 **공식 문서와 코드 사이의 정렬이 깨진 상태**다.
3개 프론트엔드 디렉터리, 문서에 없는 임상시험 모듈, 결제 모듈 빈 껍데기, 미구현 P0 3건이 동시에 존재한다. 출시 전 정리 필수.

| 영역 | 상태 | 비고 |
|---|---|---|
| 백엔드 골격 (FastAPI + Parlant) | 🟢 | 라우터 이중 등록 정리 후 안정화됨 |
| 프론트엔드 단일화 | 🔴 | `frontend/`, `new_frontend/`, `stitch_frontend/` 3중화 — ADR-001로 결정 |
| Parlant Agent 4종 | 🟡 | 골격 존재, Confidence/응급 pre-filter 후처리 미구현 |
| 식단 분석 | 🟢 | 이미지 OCR + NutriCoach 위험도 정상 |
| 의료/복지 통합 | 🟡 | 개별 API 존재, 통합 응답 패턴 미정립 |
| 다중 논문 비교 (KNO-005) | 🔴 | **P0 미구현** |
| 검색 제한 + 토큰 (KNO-006) | 🔴 | **P0 미구현** |
| 트렌드 분석 (KNO-007) | 🔴 | **P0 미구현** |
| 결제/포인트 | 🔴 | 빈 껍데기 — ADR-006으로 Mock 전환 권장 |
| 임상시험 모듈 | 🔴 | 공식 문서에 없음 — ADR-004로 비활성화 권장 |
| 벡터 DB | 🟡 | Atlas Vector Search 결정 필요 — ADR-005 |

---

## 2. 즉시 착수 가능한 구현 항목 (사용자 승인 불필요)

ADR 결정에 의존하지 않고 바로 진행 가능한 작업:

### 2.1 응급 키워드 Pre-filter 분리 [ADR-002]
- 위치: `backend/Agent/agent_manager.py`
- 작업: 의도분류기 호출 직전 keyword pre-filter 함수 분리, 흉통/호흡곤란/의식저하/경련 감지 → 119 안내 즉시 응답
- 회귀 테스트: `tests/test_emergency_filter.py` 신규
- 위험도: 낮음 (안전망 추가)

### 2.2 Confidence Score 후처리 미들웨어 [ADR-002]
- 위치: `backend/Agent/agent_manager.py` 응답 처리 단계
- 작업: 모든 Agent 응답에서 `confidence_score < 0.7`이면 "전문의 상담을 권장합니다" 자동 첨부
- 위험도: 낮음

### 2.3 의도분류 평가 CI 통합
- 위치: `eval/router_eval.py`
- 작업: GitHub Actions에 의도분류 정확도 ≥90% (REQ-056) gate 추가
- 위험도: 낮음

### 2.4 세션 lifecycle 명세 정리 [ADR-007]
- 위치: `backend/app/api/chat.py`, `new_frontend/src/services/api.ts`
- 작업: JWT 세션과 Parlant 세션 매핑 표를 `chat_rooms` 컬렉션에 영속화
- 위험도: 중간 (스키마 변경)

---

## 3. ⚠️ 사용자 확인이 필요한 미결 항목 (4건)

다음 ADR 4건은 정책 결정이 끼어 있으므로 사용자 승인 후에만 코드에 반영한다.

### 🔻 ADR-003: 이미지 업로드 정책
**충돌**: REQ-016은 "PDF only"로 명시. 정책서는 Nutrition Agent에 한해 png/jpg/svg 허용.
**제안**: Agent별 차등 정책 채택, SVG는 XSS 벡터로 제외, 얼굴감지·EXIF 제거 백엔드 공통 validator에서 강제.
**필요 결정**: SVG 제외에 동의하는가?

### 🔻 ADR-004: 임상시험 모듈 처리
**문제**: `backend/app/api/clinical_trials.py`가 PRD v0.95·Requirements v0.96 어디에도 없음.
**제안**: feature flag 비활성화 (삭제 X), MVP 외 별도 트랙으로 격리.
**필요 결정**: feature flag 방식에 동의하는가? 또는 모듈 자체를 main에서 제거할 것인가?

### 🔻 ADR-005: 벡터 DB 선택
**충돌**: KidneyWise_TechSpec은 "1536-dim cosine" 명시. 정책서 카테고리 표기는 "Pinecone".
**제안**: MongoDB Atlas Vector Search 채택 (M10+ 클러스터 비용 상향 감수), 운영 단일화 우선.
**필요 결정**: M10 비용 상향 수용? Pinecone 분리 운영 선호?

### 🔻 ADR-006: 결제/포인트 MVP 범위
**문제**: 사업자등록·PG 심사·약관 검토 시간이 MVP 출시 일정을 차단.
**제안**: 포인트 적립 + 1일 검색 10회 제한(KNO-006)은 실구현, 결제 게이트웨이는 Mock("준비 중" 버튼).
**필요 결정**: Mock 결제로 출시 동의?

---

## 4. P0 구현 우선순위 로드맵

ADR 승인 후 즉시 착수할 P0 작업 순서:

```
1. ADR-001 실행: stitch_frontend/ 자산 인벤토리 → new_frontend/로 이식 → archive 처리
   ├─ Frontend 단일화 (모든 후속 FE 작업의 전제조건)
   └─ 1주

2. ADR-005 결정 후 벡터 DB 마이그레이션 스크립트 작성
   ├─ 기존 Pinecone/임시 인덱스 → Atlas Vector Search
   └─ 1.5주

3. KNO-006: 검색 제한 + 포인트 토큰 시스템 [P0]
   ├─ 일일 카운터 (Redis 또는 Mongo TTL)
   ├─ 포인트 차감/적립 트랜잭션
   ├─ ADR-006의 Mock 결제 페이지 연결
   └─ 1주

4. KNO-005: 다중 논문 비교 [P0]
   ├─ Research Agent에 비교 Journey 추가
   ├─ Atlas Vector Search 의존
   └─ 2주

5. KNO-007: 트렌드 분석 [P0]
   ├─ PubMed 메타데이터 시계열 인덱싱
   ├─ 차트 컴포넌트 (new_frontend/)
   └─ 2주

6. ADR-002 후처리 미들웨어 + 응급 pre-filter (Section 2 항목들)
   └─ KNO 작업과 병렬 가능
```

---

## 5. 권장 다음 액션

1. **사용자가 ADR-003/004/005/006 4건에 대해 결정** — 위 Section 3의 4개 질문에 답변
2. 답변 받은 즉시 ADR 문서 Status를 `Proposed → Accepted`로 변경
3. Section 2의 "즉시 착수 가능 항목" 4건은 ADR 승인과 병렬로 진행
4. Section 4 로드맵의 1단계(`new_frontend/` 단일화)부터 순차 실행

---

## 6. 문서 동기화 상태

다음 문서들이 이번 grill 세션에서 신규 생성/갱신됨:

- `docs/CONTEXT.md` — 도메인 어휘 + 아키텍처 다이어그램
- `docs/adr/ADR-001-canonical-frontend.md`
- `docs/adr/ADR-002-parlant-orchestration.md`
- `docs/adr/ADR-003-image-upload-policy.md` ⚠️ 사용자 확인 필요
- `docs/adr/ADR-004-clinical-trials-scope.md` ⚠️ 사용자 확인 필요
- `docs/adr/ADR-005-vector-db.md` ⚠️ 사용자 확인 필요
- `docs/adr/ADR-006-payment-point-mvp.md` ⚠️ 사용자 확인 필요
- `docs/adr/ADR-007-session-management.md`
- `docs/GRILL_VERDICT.md` (이 문서)

이전 세션에서 변환된 raw 문서:
- `docs/converted/PRD_v0.95.md`
- `docs/converted/Requirements_v0.96.md`
- `docs/converted/KnowledgeSearch_Flow.md`
- `docs/converted/_ANALYSIS_REPORT.md`
