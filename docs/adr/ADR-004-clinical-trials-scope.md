# ADR-004: Clinical Trials Feature Scope

- **Status**: Accepted (Option B)
- **Date**: 2026-05-23
- **Decided by**: Project owner, 2026-05-23
- **Related**: `backend/app/api/clinical_trials.py`, `docs/converted/_ANALYSIS_REPORT.md` Section 5 RED FLAG #2

## Context

코드베이스에 `backend/app/api/clinical_trials.py` 라우터가 존재하지만:

- **PRD v0.95**: 임상시험 매칭 기능 언급 없음
- **Requirements v0.96**: 임상시험 관련 REQ 항목 없음
- **Knowledge_Search_Flow.md**: 언급 없음
- **Patient_JourneyMap.md**: 언급 없음

즉, **공식 스펙에 없는 기능이 코드에 존재**하는 상황. 이는 다음 중 하나다:

(a) 이전 버전(v0.94 이전) 스펙의 잔재
(b) 개발 중 의욕적으로 추가한 비공식 기능
(c) 향후 로드맵 항목의 사전 구현

이 모호성은:
- QA 범위 산정 불가 (테스트 작성/제외 판단 필요)
- 사용자에게 노출할지/숨길지 UI 결정 막힘
- 외부 데이터 소스(ClinicalTrials.gov 등) 연동 비용 평가 불가

## Decision

**Option B 채택**: 임상시험 데이터를 MVP에 **포함**하고 사용자에게 노출한다.

- `clinical_trials.py` 라우터를 `main.py`에 정상 include 유지.
- ClinicalTrials.gov 데이터를 조회·캐싱·표시하되 **추천(매칭)이 아닌 정보 제공**으로 포지셔닝.
- 후속으로 PRD에 §11 Clinical Trials 섹션을 추가하고 REQ-CT-001~을 신설한다.

## Scope (Option B 가드레일)

| 포함 | 제외 |
|---|---|
| ClinicalTrials.gov 공개 API 조회 | 환자 개인 매칭 알고리즘 (의료 안전 책임) |
| 키워드/조건/지역 필터 검색 | 등록 신청 자동화 |
| 캐싱 (`clinical_trials_cache` 컬렉션) | 임상시험 결과 해석 LLM 생성 |
| 한국어 메타데이터(질환명) 보조 표시 | "추천드립니다" 류 능동적 권유 카피 |

UI 카피 원칙:
- "공개 임상시험 정보를 보여드립니다" (정보 제공)
- ❌ "당신에게 적합한 임상시험을 추천합니다" (의료 행위 유사 표현)

## Rationale

1. **사용자 결정**: 프로젝트 오너가 임상시험 데이터 표시를 명시적으로 승인.
2. **이미 코드 존재**: `clinical_trials.py` 라우터가 작성되어 있어 추가 비용 낮음.
3. **의료 안전 책임 분리**: 정보 제공 모드로 한정하면 직접적 의사결정 유도 위험을 회피.
4. **CKD 환자 가치**: 만성질환 임상시험 정보는 환자에게 실질적 효용.

## Consequences

**Positive**
- 코드 자산 활용
- 사용자 가치 확장

**Negative**
- ClinicalTrials.gov API 안정성·rate limit 모니터링 필요
- 한국어 메타데이터 품질 책임 (영문 원문 병기 필수)
- 의료 면책 고지(disclaimer) UI 필수

**Follow-up tasks**
1. PRD §11 Clinical Trials 신설 (REQ-CT-001~) — `docs/converted/PRD_clinical_trials.md`
2. `clinical_trials_cache` 컬렉션 스키마 확정 + TTL 정책
3. UI 면책 문구 추가 (`new_frontend/src/pages/ClinicalTrials*.tsx`)
4. ClinicalTrials.gov rate limit 대응 (지수 backoff + cache-first)
5. GitHub label `area:clinical-trials` 사용 (이미 `triage-labels.md`에 등록됨)
