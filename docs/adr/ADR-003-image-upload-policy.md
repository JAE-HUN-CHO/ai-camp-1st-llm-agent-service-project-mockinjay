# ADR-003: Image Upload Policy

- **Status**: Proposed (NEEDS USER CONFIRMATION)
- **Date**: 2026-05-23
- **Related**: REQ-016, Requirements v0.96 정책서 시트, `docs/converted/_ANALYSIS_REPORT.md` Section 5 RED FLAG #1

## Context

문서 간 이미지 업로드 정책이 충돌한다:

| 출처 | 정책 |
|---|---|
| **REQ-016** (Requirements v0.96) | "챗봇 공통: PDF만, 5MB 이하" |
| **정책서 시트** (Requirements v0.96) | "Nutrition agent는 png/jpg/svg 추가 허용. 식사 이미지 분석 핵심 기능" |
| **PRD v0.95** | 이미지 분석 기능 명시 (NutriCoach OCR/식별) |
| **현재 코드** | `dietCareApi.ts`에 multipart/form-data 이미지 업로드 구현 (`ChatPageEnhanced` 영양 분석 결과 표시) |

이 충돌을 해소하지 않으면:
- 프론트엔드 UI(이미지 첨부 버튼)가 어느 화면에 노출돼야 하는지 불분명
- 백엔드 validator가 어떤 mime-type을 허용해야 하는지 불분명
- 보안 정책(얼굴 자동 거부 등)이 어디에 적용되는지 불분명

## Decision

**Agent별 차등 업로드 정책**을 공식화한다:

| Agent / 화면 | 허용 형식 | 최대 크기 | 추가 검증 |
|---|---|---|---|
| Medical_Welfare | PDF only | 5MB | OCR 후 민감정보 감지 시 거부 |
| **Nutrition** | **PDF + png + jpg (svg 제외)** | **5MB** | 얼굴 감지 시 전체 거부, EXIF 위치정보 제거 |
| Research_Paper | PDF only | 10MB (논문 1편 기준) | 텍스트 추출 가능 여부 검증 |
| Quiz | 업로드 불가 | - | - |

**SVG 제외 이유**: SVG는 임의 JS 실행이 가능한 XML이라 XSS 벡터. 정책서의 svg는 오기로 간주.

**구현 위치**:
- Frontend: 화면별 `accept` attribute 분기 (`ChatPageEnhanced`의 nutrition 모드 시 `image/png,image/jpeg,application/pdf`).
- Backend: 라우터별 mime-type validator + sniff(파일 시그니처 검증).
- 보안: `backend/app/services/sensitive_filter.py` (가칭) 신설 → 얼굴 감지(Vision API or local model) + 텍스트 OCR 마스킹.

## Rationale

- REQ-016의 "PDF only"는 **Medical_Welfare 등 일반 대화 챗봇**에 한정된 안전 기본값으로 해석.
- 정책서의 png/jpg는 **Nutrition agent의 핵심 기능**(식사 이미지 분석)이므로 명시적 예외로 인정.
- SVG는 보안 위험으로 제외(정책서 표기 오류로 처리).
- Agent별 차등은 보안과 UX의 균형점.

## Consequences

**Positive**
- 정책 충돌 해소 → 명확한 구현 기준
- 보안 위험(SVG XSS) 차단

**Negative**
- 프론트엔드에서 화면별 분기 코드 필요
- 백엔드 라우터별 validator 중복 가능 → 공통 dependency로 추상화 권장

**Follow-up tasks**
1. 사용자 확인: "Nutrition만 이미지 허용 + SVG 제외" 안 승인 여부
2. `image_upload_validator` 공통 dependency 작성
3. 얼굴 감지 라이브러리 선택 (OpenCV Haar / MediaPipe / 외부 API)
4. EXIF 제거 처리 추가
