# 복지 검색 기능 프로젝트 인덱스

**작성일**: 2025-11-19
**프로젝트**: CareGuide - 복지 정보 검색 및 상담 기능
**상태**: 계획 완료, 구현 대기

---

## 📂 생성된 문서

### 1. WELFARE_IMPLEMENTATION_PLAN.md (997줄)
**목적**: 복지 검색 기능 기본 구현 계획

**주요 내용**:
- 복지 관련 작업 추출 요약
- 기본 구현 목표
- WelfareManager 기본 구조
- Journey 7 기본 구조
- Welfare API 엔드포인트
- 10시간 구현 일정

**주요 섹션**:
- 문서에서 발견된 복지 관련 항목
- 복지 검색 기능 구현 목표
- 현재 가용 데이터 (병원 104,836개)
- 구현 작업 목록 (4개 작업)
- 구현 일정 (10시간)

### 2. WELFARE_DETAILED_IMPLEMENTATION.md (2,224줄)
**목적**: 복지 검색 기능 상세 구현 가이드

**주요 내용**:
- 전체 아키텍처 다이어그램
- 데이터베이스 설계 (15개 복지 프로그램 전체 데이터)
- WelfareManager 완전판 (7개 메서드)
- Parlant Journey 7 완전판 (5개 분기)
- 프론트엔드 WelfarePage 완전판
- API 엔드포인트 (4개)

**주요 섹션**:
1. 전체 아키텍처
2. 데이터베이스 설계
3. 백엔드 구현 (WelfareManager)
4. Parlant Journey 구현 (Journey 7)
5. 프론트엔드 구현 (WelfarePage)
6. 테스트 계획 (예정)
7. 배포 및 모니터링 (예정)

### 3. WELFARE_PROJECT_INDEX.md (본 파일)
**목적**: 복지 프로젝트 전체 인덱스 및 가이드

---

## 🎯 프로젝트 목표

### 핵심 기능
1. **복지 정보 검색** - 15개 복지 프로그램 텍스트 검색
2. **AI 대화 상담** - Parlant Journey 7로 복지 안내
3. **카테고리별 탐색** - 10개 카테고리 분류
4. **사용자 맞춤 추천** - CKD 단계, 투석 여부 기반

### 목표 성과
- **투석 환자 연간 복지 혜택**: 약 2,970만원
- **의도 분류 정확도**: WELFARE_INFO 90% 이상
- **검색 응답 시간**: < 1초

---

## 📊 구현 현황

### 완료된 작업
- ✅ **병원 데이터 업로드**: 104,836개 (MongoDB - hospitals 컬렉션)
- ✅ **HospitalManager 구현**: backend/app/db/hospital_manager.py
- ✅ **복지 구현 계획서 작성**: 2개 문서 (3,221줄)

### 진행 예정 작업
- ⏳ **복지 데이터 로딩**: 15개 프로그램 MongoDB 업로드
- ⏳ **WelfareManager 구현**: backend/app/db/welfare_manager.py
- ⏳ **Welfare API 구현**: backend/app/api/welfare.py
- ⏳ **Journey 7 구현**: Parlant 복지 상담
- ⏳ **WelfarePage 구현**: frontend/src/pages/WelfarePage.tsx

---

## 🗂️ 파일 구조

### 백엔드

```
backend/
├── app/
│   ├── db/
│   │   ├── hospital_manager.py          ✅ 완료 (병원 검색)
│   │   ├── welfare_manager.py           ⏳ 예정 (복지 검색)
│   │   ├── mongodb_manager.py           ✅ 완료
│   │   └── __init__.py                  ✅ 완료 (HospitalManager 추가됨)
│   │
│   ├── api/
│   │   ├── welfare.py                   ⏳ 예정 (복지 API)
│   │   ├── chat.py                      ✅ 완료
│   │   └── trends.py                    ✅ 완료
│   │
│   └── models/
│       └── welfare.py                   ⏳ 예정 (Pydantic 모델)
│
├── Agent/research_paper/server/
│   └── healthcare_v2_en.py              ⏳ 수정 필요 (Journey 7 추가)
│
└── data/
    └── welfare/
        ├── welfare_programs_full.json   ⏳ 예정 (15개 프로그램 데이터)
        └── load_welfare_data.py         ⏳ 예정 (MongoDB 로딩 스크립트)
```

### 프론트엔드

```
frontend/src/
├── pages/
│   ├── WelfarePage.tsx                  ⏳ 예정 (복지 검색 페이지)
│   ├── ChatPage.tsx                     ✅ 완료
│   └── MyPage.tsx                       🔄 수정 필요 (북마크 추가)
│
├── components/
│   └── welfare/
│       ├── WelfareCard.tsx              ⏳ 예정
│       ├── WelfareDetailModal.tsx       ⏳ 예정
│       └── CategoryFilter.tsx           ⏳ 예정
│
└── App.tsx                              🔄 수정 필요 (라우트 추가)
```

### 데이터베이스

```
MongoDB (careguide DB)
├── hospitals                            ✅ 완료 (104,836개)
├── welfare_programs                     ⏳ 예정 (15개)
├── bookmarks                            ⏳ 예정
├── users                                ✅ 완료
├── qa_kidney                            ✅ 완료
├── papers_kidney                        ✅ 완료
├── medical_kidney                       ✅ 완료
└── guidelines_kidney                    ✅ 완료
```

---

## 📋 구현 체크리스트

### Phase 1: 데이터 및 백엔드 (8시간)

- [ ] **복지 데이터 생성** (2시간)
  - [ ] `data/welfare/welfare_programs_full.json` 작성 (15개 프로그램)
  - [ ] `data/welfare/load_welfare_data.py` 스크립트 작성
  - [ ] MongoDB 업로드 실행
  - [ ] 데이터 검증 (count, 인덱스 확인)

- [ ] **WelfareManager 구현** (3시간)
  - [ ] `backend/app/db/welfare_manager.py` 작성
  - [ ] 7개 메서드 구현
  - [ ] 테스트 코드 작성
  - [ ] `__init__.py`에 추가

- [ ] **Welfare API 구현** (2시간)
  - [ ] `backend/app/api/welfare.py` 작성
  - [ ] 4개 엔드포인트 구현 (search, categories, category/{id}, /{program_id})
  - [ ] `backend/app/models/welfare.py` Pydantic 모델 작성
  - [ ] `main.py`에 라우터 등록

- [ ] **API 테스트** (1시간)
  - [ ] Postman/cURL 테스트
  - [ ] 각 엔드포인트 작동 확인
  - [ ] 응답 시간 측정 (< 1초 목표)

### Phase 2: Parlant Journey 7 (4시간)

- [ ] **Journey 7 함수 작성** (2시간)
  - [ ] `create_welfare_support_journey()` 작성
  - [ ] 5개 복지 카테고리 분기 구현
  - [ ] 복지 혜택 총정리 State 추가
  - [ ] 종료 State 구현

- [ ] **search_welfare_programs Tool 추가** (1시간)
  - [ ] Tool 함수 작성
  - [ ] WelfareManager 연동
  - [ ] 결과 포맷팅

- [ ] **Journey 등록 및 테스트** (1시간)
  - [ ] `main()` 함수에 Journey 등록
  - [ ] Parlant 서버 재시작
  - [ ] Journey ID 확인
  - [ ] 테스트 대화 (5가지 분기 확인)

### Phase 3: 프론트엔드 (6시간)

- [ ] **WelfarePage 컴포넌트** (4시간)
  - [ ] 기본 구조 생성
  - [ ] 검색 기능 구현
  - [ ] 카테고리 필터 구현
  - [ ] 프로그램 카드 목록
  - [ ] 상세 모달 구현
  - [ ] 로딩 상태 처리

- [ ] **라우팅 설정** (30분)
  - [ ] `App.tsx`에 `/welfare` 라우트 추가
  - [ ] Header 네비게이션 메뉴 추가

- [ ] **스타일링 및 반응형** (1시간)
  - [ ] Tailwind CSS 스타일링
  - [ ] 모바일 반응형 디자인
  - [ ] 다크모드 지원 (선택)

- [ ] **프론트엔드 테스트** (30분)
  - [ ] 검색 기능 테스트
  - [ ] 카테고리 필터 테스트
  - [ ] 상세 모달 테스트

### Phase 4: 통합 테스트 (6시간)

- [ ] **WELFARE_INFO 의도 분류 테스트** (2시간)
  - [ ] 테스트 케이스 10개 작성
  - [ ] 정확도 측정 (≥90% 목표)
  - [ ] 오분류 케이스 분석

- [ ] **Journey 7 기능 테스트** (2시간)
  - [ ] 5가지 분기 모두 테스트
  - [ ] search_welfare_programs Tool 작동 확인
  - [ ] 응답 품질 검증

- [ ] **E2E 테스트** (2시간)
  - [ ] 사용자 시나리오 테스트
  - [ ] 검색 → 상세 → 신청 흐름
  - [ ] Chat → WelfarePage 이동
  - [ ] 성능 테스트 (응답 시간)

---

## 📅 구현 일정 (3일)

### Day 1: 데이터 및 백엔드 (8시간)
```
09:00-11:00  복지 데이터 생성 및 MongoDB 업로드
11:00-14:00  WelfareManager 구현 (점심 1시간 포함)
14:00-16:00  Welfare API 구현
16:00-17:00  API 테스트
```

### Day 2: Parlant Journey 7 (4시간)
```
09:00-11:00  create_welfare_support_journey() 작성
11:00-12:00  search_welfare_programs Tool 추가
13:00-14:00  Journey 등록 및 테스트 (점심 1시간 후)
```

### Day 3: 프론트엔드 및 테스트 (12시간)
```
09:00-13:00  WelfarePage 컴포넌트 (점심 1시간 포함)
13:00-15:00  라우팅 및 스타일링
15:00-17:00  WELFARE_INFO 의도 분류 테스트
17:00-19:00  Journey 7 기능 테스트
19:00-21:00  E2E 테스트
```

**총 예상 시간**: 24시간 (3일)

---

## 🎯 완료 기준

### 데이터 품질
- [ ] 15개 복지 프로그램 MongoDB 로딩
- [ ] 각 프로그램별 FAQ 3개 이상
- [ ] 카테고리 10개 분류
- [ ] 한글 텍스트 인덱스 생성

### 백엔드 기능
- [ ] WelfareManager 7개 메서드 작동
- [ ] Welfare API 4개 엔드포인트 작동
- [ ] 검색 응답 시간 < 1초
- [ ] 사용자 프로필 기반 추천 작동

### Parlant Journey
- [ ] Journey 7 생성 확인
- [ ] 5가지 복지 카테고리 분기 작동
- [ ] search_welfare_programs Tool 작동
- [ ] 복지 혜택 총정리 기능 작동

### 프론트엔드
- [ ] WelfarePage 렌더링
- [ ] 검색 기능 작동
- [ ] 카테고리 필터 작동
- [ ] 상세 모달 표시

### 테스트
- [ ] WELFARE_INFO 의도 분류 정확도 ≥90%
- [ ] Journey 7 모든 분기 테스트 통과
- [ ] API 응답 시간 < 1초
- [ ] E2E 테스트 통과

---

## 📚 복지 프로그램 데이터 목록 (15개)

### 카테고리 1: 산정특례 (3개)
1. **만성콩팥병 산정특례 (V001)**
   - 본인부담금 10%, CKD 3기 이상, 유효기간 5년

2. **혈액투석 산정특례 (V003)**
   - 본인부담금 5%, 정기 혈액투석, 투석 중단 시까지

3. **복막투석 산정특례 (V005)**
   - 본인부담금 5%, CAPD/APD, 투석 중단 시까지

### 카테고리 2: 장애인 복지 (4개)
4. **신장장애 등록 제도**
   - 투석 3개월 → 장애 2급, 이식 후 → 장애 5급

5. **장애인 주차 스티커**
   - 장애 1-6급, 주차 무료/할인

6. **장애인연금**
   - 중증장애인 월 최대 40만원 (소득 기준 충족 시)

7. **장애인 고용 지원**
   - 직업 훈련, 취업 알선, 출퇴근 비용 지원

### 카테고리 3: 의료비 지원 (4개)
8. **저소득층 의료급여**
   - 차상위계층 본인부담금 0-10%

9. **재난적 의료비 지원**
   - 소득 대비 의료비 과다 시 최대 2,000만원

10. **긴급 의료비 지원**
    - 위기상황 즉시 최대 300만원 (24시간 이내)

11. **희귀난치성질환 지원**
    - 희귀질환 진료비, 간병비, 호흡보조기 지원

### 카테고리 4: 이식 지원 (1개)
12. **신장이식 수술비 및 면역억제제 지원**
    - 수술비 최대 3,000만원, 면역억제제 월 20만원 (평생)

### 카테고리 5: 교통비 지원 (1개)
13. **투석 환자 교통비 지원**
    - 월 15만원 (지자체별 10-20만원)

### 카테고리 6: 기타 (2개)
14. **건강검진 무료 지원**
    - 일반 건강검진 (2년마다), 암검진

15. **기타 복지 혜택**
    - 추가 발굴 예정

---

## 💰 복지 혜택 계산 예시

### 투석 환자 (CKD 5기) - 연간 총 혜택: 약 2,970만원

| 복지 프로그램 | 월 혜택 | 연 혜택 | 비고 |
|--------------|---------|---------|------|
| 산정특례 (투석 95% 감면) | 171만원 | 2,052만원 | 투석비 180만원 → 9만원 |
| 장애인연금 (2급) | 20만원 | 240만원 | 소득 기준 충족 시 |
| 교통비 지원 | 15만원 | 180만원 | 주 3회 통원 |
| 장애인 교통 무료 | 2.5만원 | 30만원 | 지하철·버스 |
| 통신/공과금 할인 | 1.5만원 | 18만원 | 통신 1만원, 공과금 5천원 |
| 차량 세금 감면 | - | 500만원 | 1회성 |
| **합계** | **210만원** | **3,020만원** | |

### CKD 3기 환자 (투석 전) - 연간 총 혜택: 약 120만원

| 복지 프로그램 | 월 혜택 | 연 혜택 | 비고 |
|--------------|---------|---------|------|
| 산정특례 (CKD 90% 감면) | 10만원 | 120만원 | 월 진료비 50만원 가정 |
| 건강검진 무료 | - | 10만원 | 2년마다 1회 |
| **합계** | **10만원** | **130만원** | |

### 신장이식 환자 - 총 혜택: 약 3,500만원 (수술비) + 평생

| 복지 프로그램 | 1회성 혜택 | 월 혜택 | 연 혜택 | 비고 |
|--------------|-----------|---------|---------|------|
| 이식 수술비 지원 | 3,000만원 | - | - | 1회성 |
| 면역억제제 지원 | - | 20만원 | 240만원 | 평생 |
| 장애인 5급 혜택 | - | 5만원 | 60만원 | 교통, 공과금 할인 |
| **합계** | **3,000만원** | **25만원** | **300만원** | |

---

## 🔧 기술 스택

### 백엔드
- **FastAPI**: REST API 서버
- **Motor**: MongoDB 비동기 드라이버
- **Parlant SDK**: AI 대화 Journey
- **Pydantic**: 데이터 검증

### 프론트엔드
- **React 18**: UI 프레임워크
- **TypeScript**: 타입 안전성
- **Tailwind CSS**: 스타일링
- **React Router**: 라우팅

### 데이터베이스
- **MongoDB**: NoSQL 데이터베이스
- **Text Index**: 한글 텍스트 검색
- **Compound Index**: 복합 필터링

---

## 🚀 다음 단계

### 즉시 실행 (이번 주)
1. ✅ **복지 플랜 문서 작성** (완료)
2. ⏳ **복지 데이터 생성** (다음)
3. ⏳ **WelfareManager 구현** (다음)

### 단기 목표 (2주 내)
1. ⏳ **Backend 완성**: WelfareManager + API
2. ⏳ **Journey 7 완성**: Parlant 복지 상담
3. ⏳ **WelfarePage 완성**: 검색 UI

### 중기 목표 (1개월 내)
1. ⏳ **의도 분류 테스트**: ≥90% 정확도
2. ⏳ **E2E 테스트**: 전체 흐름 검증
3. ⏳ **사용자 테스트**: 실제 피드백 수집

---

## 📞 참고 연락처

### 복지 문의
- **국민건강보험공단**: 1577-1000
- **보건복지콜센터**: 국번없이 129
- **장애인고용공단**: 1588-1519
- **KONOS (장기이식)**: 02-2628-3602

### 온라인 자원
- **복지로**: https://www.bokjiro.go.kr
- **건강보험공단**: https://www.nhis.or.kr
- **보건복지부**: https://www.mohw.go.kr
- **KONOS**: https://www.konos.go.kr

---

## 📖 문서 읽는 순서

### 1. 빠른 시작 (30분)
1. **WELFARE_PROJECT_INDEX.md** (본 파일) - 전체 개요
2. **WELFARE_IMPLEMENTATION_PLAN.md** - 기본 계획
3. **구현 시작!**

### 2. 상세 구현 (2시간)
1. **WELFARE_DETAILED_IMPLEMENTATION.md** - 전체 읽기
   - Section 1: 아키텍처
   - Section 2: 데이터베이스 (15개 프로그램 데이터)
   - Section 3: WelfareManager
   - Section 4: Journey 7
   - Section 5: 프론트엔드
2. **코드 복사하여 구현 시작**

### 3. 테스트 및 검증 (1시간)
1. **IMPLEMENTATION_AND_TEST_PLAN.md** - 테스트 계획
2. **테스트 실행 및 검증**

---

## 🎓 학습 자료

### CKD 환자 복지 혜택 이해하기

**투석 전 (CKD 3-4기)**:
- 산정특례 (V001): 본인부담금 10%
- 정기 검진 및 약물 치료
- 연간 약 120만원 절감

**투석 시작 (CKD 5기/ESRD)**:
- 산정특례 (V003/V005): 본인부담금 5%
- 투석 3개월 후 → 장애 2급 등록
- 교통비 지원 월 15만원
- 연간 약 2,970만원 절감

**신장이식 후**:
- 이식 수술비 3,000만원 지원
- 면역억제제 월 20만원 지원 (평생)
- 장애 5급 유지 (혜택 지속)
- 삶의 질 크게 향상

---

## ⚠️ 주의사항

### 법적 고지
- 본 문서의 복지 정보는 2024-2025년 기준입니다
- 실제 신청 시 최신 정보를 확인하세요
- 지자체별로 지원 내용이 다를 수 있습니다

### 개발 유의사항
- 복지 정보는 정기적으로 업데이트 필요 (연 1-2회)
- 법률 자문 없이 복지 상담은 "참고용"임을 명시
- False Negative 방지: 신청 자격 미달로 판단하지 말 것

---

## 🔗 관련 문서

1. **EXECUTION_STATUS.md** - 전체 프로젝트 상태
2. **IMPLEMENTATION_AND_TEST_PLAN.md** - 구현 및 테스트 계획
3. **WELFARE_IMPLEMENTATION_PLAN.md** - 복지 기본 계획
4. **WELFARE_DETAILED_IMPLEMENTATION.md** - 복지 상세 가이드
5. **WELFARE_PROJECT_INDEX.md** (본 파일) - 프로젝트 인덱스

---

**END OF INDEX**

**작성자**: Claude Code
**최종 업데이트**: 2025-11-19
**다음 리뷰**: 구현 완료 후
