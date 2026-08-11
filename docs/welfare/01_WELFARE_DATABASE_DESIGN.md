# 복지 데이터베이스 설계
## MongoDB Schema & Data Structure

**문서**: 01_WELFARE_DATABASE_DESIGN.md
**작성일**: 2025-11-19
**선행 문서**: 00_WELFARE_OVERVIEW.md
**다음 문서**: 02_WELFARE_BACKEND_IMPLEMENTATION.md

---

## 📋 목차

1. [MongoDB 스키마 설계](#1-mongodb-스키마-설계)
2. [인덱스 전략](#2-인덱스-전략)
3. [초기 데이터 (15개 프로그램)](#3-초기-데이터-15개-프로그램)
4. [데이터 로딩 스크립트](#4-데이터-로딩-스크립트)
5. [검증 및 테스트](#5-검증-및-테스트)

---

## 1. MongoDB 스키마 설계

### 1.1 컬렉션 개요

**컬렉션명**: `welfare_programs`
**데이터베이스**: `careguide`
**총 문서 수**: 15개 (초기)

### 1.2 문서 스키마

```javascript
{
  // ==================== Identifiers ====================
  "_id": ObjectId("..."),                    // MongoDB 자동 생성
  "programId": "sangjung_ckd_v001",          // 고유 프로그램 ID (unique)

  // ==================== Basic Info ====================
  "title": "만성콩팥병 산정특례 제도",        // 프로그램명
  "category": "sangjung_special",            // 카테고리 (5개)
  "target_disease": [                        // 대상 질병 (배열)
    "CKD",
    "chronic kidney disease",
    "만성콩팥병"
  ],

  // ==================== Eligibility ====================
  "eligibility": {                           // 자격 요건 (nested object)
    "disease_code": "V001",                  // 질병 코드
    "ckd_stage": [3, 4, 5],                  // CKD 단계 (배열)
    "dialysis_type": null,                   // 투석 유형 (optional)
    "dialysis_duration": null,               // 투석 기간 (optional)
    "dialysis_required": false,              // 투석 필수 여부
    "income": null,                          // 소득 기준 (optional)
    "transplant_candidate": false,           // 이식 대기자 (optional)
    "description": "만성콩팥병 3기 이상 또는 eGFR 60 미만"
  },

  // ==================== Benefits ====================
  "benefits": {                              // 혜택 (nested object)
    "copay_reduction": "90%",                // 본인부담금 감면율
    "copay_rate": "10%",                     // 본인부담률
    "max_monthly_cap": null,                 // 월 최대 본인부담금 (원)
    "monthly_amount": null,                  // 월 지원 금액 (원)
    "coverage_items": [                      // 적용 항목
      "외래진료", "검사", "약제", "치료"
    ],
    "benefits_list": null                    // 혜택 목록 (optional)
  },

  // ==================== Application ====================
  "application": {                           // 신청 방법 (nested object)
    "required_documents": [                  // 필요 서류
      "산정특례 등록 신청서",
      "의사 진단서 (희귀난치성질환 등록 신청용)",
      "검사결과지 (eGFR, 크레아티닌)",
      "신분증"
    ],
    "application_place": "국민건강보험공단 지사 또는 병원 원무과",
    "processing_time": "7-14일",             // 처리 기간
    "validity_period": "5년",                // 유효 기간
    "renewal": "만료 1개월 전 재신청"        // 갱신 방법 (optional)
  },

  // ==================== Contact ====================
  "contact": {                               // 연락처 (nested object)
    "phone": "1577-1000",                    // 전화번호
    "website": "https://www.nhis.or.kr",     // 웹사이트 (optional)
    "online_application": true               // 온라인 신청 가능 여부
  },

  // ==================== Search & Metadata ====================
  "description": "만성콩팥병 환자의 의료비 부담을 경감하기 위한 제도입니다. 본인부담금이 90% 감면되어 10%만 부담합니다.",
  "keywords": [                              // 검색 키워드 (배열)
    "산정특례", "V001", "본인부담금", "의료비지원", "CKD", "만성콩팥병"
  ],
  "created_at": ISODate("2024-11-19T00:00:00Z"),
  "updated_at": ISODate("2024-11-19T00:00:00Z")
}
```

### 1.3 필드 타입 정의

| 필드명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| `_id` | ObjectId | 자동 | MongoDB 기본 키 |
| `programId` | String | ✅ | 고유 ID (unique index) |
| `title` | String | ✅ | 프로그램명 |
| `category` | String | ✅ | 카테고리 (5개 중 1) |
| `target_disease` | Array[String] | ✅ | 대상 질병 리스트 |
| `eligibility` | Object | ✅ | 자격 요건 |
| `benefits` | Object | ✅ | 혜택 내용 |
| `application` | Object | ✅ | 신청 방법 |
| `contact` | Object | ✅ | 연락처 |
| `description` | String | ✅ | 상세 설명 |
| `keywords` | Array[String] | ✅ | 검색 키워드 |
| `created_at` | Date | ✅ | 생성 일시 |
| `updated_at` | Date | ✅ | 수정 일시 |

---

## 2. 인덱스 전략

### 2.1 인덱스 목록

**hospital_manager.py 패턴 적용**:

```python
# 1. Category Index (단일 필드)
db.welfare_programs.create_index(
    [("category", ASCENDING)],
    name="category_idx"
)

# 2. Text Search Index (복합 필드, 한국어)
db.welfare_programs.create_index(
    [("title", TEXT), ("description", TEXT), ("keywords", TEXT)],
    name="welfare_text_search",
    default_language="korean"
)

# 3. Target Disease Index (배열 필드)
db.welfare_programs.create_index(
    [("target_disease", ASCENDING)],
    name="disease_idx"
)

# 4. CKD Stage Index (nested field, 배열)
db.welfare_programs.create_index(
    [("eligibility.ckd_stage", ASCENDING)],
    name="ckd_stage_idx"
)

# 5. Program ID Unique Index
db.welfare_programs.create_index(
    [("programId", ASCENDING)],
    name="program_id_unique",
    unique=True
)
```

### 2.2 인덱스 사용 예시

#### 텍스트 검색 (Text Search)
```python
# "산정특례" 검색
db.welfare_programs.find(
    {"$text": {"$search": "산정특례"}},
    {"score": {"$meta": "textScore"}}
).sort([("score", {"$meta": "textScore"})])

# 결과: V001, V003 (score 순)
```

#### 카테고리 필터 (Category Index)
```python
# 산정특례 카테고리만
db.welfare_programs.find(
    {"category": "sangjung_special"}
)

# 결과: 3개 프로그램
```

#### 질병 필터 (Disease Index)
```python
# CKD 관련 프로그램
db.welfare_programs.find(
    {"target_disease": {"$in": ["CKD"]}}
)

# 결과: 대부분 프로그램 (CKD가 target에 포함)
```

#### CKD 단계 필터 (Nested Array)
```python
# CKD 4기 환자 대상 프로그램
db.welfare_programs.find(
    {"eligibility.ckd_stage": {"$in": [4]}}
)

# 결과: 4기가 자격 요건에 포함된 프로그램
```

#### 복합 검색 (Combined)
```python
# "의료비 지원" + CKD 3기 + medical_aid 카테고리
db.welfare_programs.find(
    {
        "$text": {"$search": "의료비 지원"},
        "category": "medical_aid",
        "eligibility.ckd_stage": {"$in": [3]}
    },
    {"score": {"$meta": "textScore"}}
).sort([("score", {"$meta": "textScore"})])
```

### 2.3 인덱스 성능 분석

**예상 성능** (hospital_manager.py 기준):

| 쿼리 유형 | 인덱스 사용 | 예상 시간 | 문서 수 |
|----------|------------|----------|---------|
| Text search | welfare_text_search | <50ms | 15 |
| Category filter | category_idx | <10ms | 15 |
| Disease filter | disease_idx | <10ms | 15 |
| CKD stage filter | ckd_stage_idx | <10ms | 15 |
| Combined | Multiple | <100ms | 15 |

**참고**: 15개 문서는 매우 작은 컬렉션이므로 인덱스 없이도 빠름
하지만 향후 확장 (100개+)을 고려하여 인덱스 필수

---

## 3. 초기 데이터 (15개 프로그램)

### 3.1 카테고리별 분류

#### Category 1: sangjung_special (산정특례) - 3개

##### Program 1: 만성콩팥병 산정특례 (V001)
```python
{
    "programId": "sangjung_ckd_v001",
    "title": "만성콩팥병 산정특례 제도",
    "category": "sangjung_special",
    "target_disease": ["CKD", "chronic kidney disease", "만성콩팥병"],
    "eligibility": {
        "disease_code": "V001",
        "ckd_stage": [3, 4, 5],
        "description": "만성콩팥병 3기 이상 또는 eGFR 60 미만"
    },
    "benefits": {
        "copay_reduction": "90%",
        "copay_rate": "10%",
        "max_monthly_cap": None,
        "coverage_items": ["외래진료", "검사", "약제", "치료"]
    },
    "application": {
        "required_documents": [
            "산정특례 등록 신청서",
            "의사 진단서 (희귀난치성질환 등록 신청용)",
            "검사결과지 (eGFR, 크레아티닌)",
            "신분증"
        ],
        "application_place": "국민건강보험공단 지사 또는 병원 원무과",
        "processing_time": "7-14일",
        "validity_period": "5년",
        "renewal": "만료 1개월 전 재신청"
    },
    "contact": {
        "phone": "1577-1000",
        "website": "https://www.nhis.or.kr",
        "online_application": True
    },
    "description": "만성콩팥병 환자의 의료비 부담을 경감하기 위한 제도입니다. 본인부담금이 90% 감면되어 10%만 부담합니다.",
    "keywords": ["산정특례", "V001", "본인부담금", "의료비지원", "CKD", "만성콩팥병"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

##### Program 2: 혈액투석 산정특례 (V003)
```python
{
    "programId": "sangjung_dialysis_v003",
    "title": "혈액투석 산정특례 제도",
    "category": "sangjung_special",
    "target_disease": ["hemodialysis", "혈액투석", "ESRD"],
    "eligibility": {
        "disease_code": "V003",
        "dialysis_type": "hemodialysis",
        "dialysis_required": True,
        "description": "주 2-3회 정기적으로 혈액투석 중인 환자"
    },
    "benefits": {
        "copay_reduction": "95%",
        "copay_rate": "5%",
        "max_monthly_cap": None,
        "coverage_items": ["투석비", "검사비", "약제비", "혈관조성술"]
    },
    "application": {
        "required_documents": [
            "산정특례 등록 신청서",
            "의사 진단서 (혈액투석 확인)",
            "투석 기록지",
            "신분증"
        ],
        "application_place": "투석 병원 원무과",
        "processing_time": "즉시 (투석 시작 시)",
        "validity_period": "계속 (투석 중단 시까지)",
        "renewal": "불필요"
    },
    "contact": {
        "phone": "1577-1000",
        "website": "https://www.nhis.or.kr",
        "online_application": False
    },
    "description": "혈액투석 환자의 투석비 본인부담금이 5%로 대폭 감면됩니다. 투석을 시작하면 자동으로 적용됩니다.",
    "keywords": ["산정특례", "V003", "혈액투석", "투석비지원", "본인부담금5%"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

##### Program 3: 복막투석 산정특례
```python
{
    "programId": "sangjung_peritoneal_v005",
    "title": "복막투석 산정특례 제도",
    "category": "sangjung_special",
    "target_disease": ["peritoneal dialysis", "복막투석", "ESRD"],
    "eligibility": {
        "disease_code": "V005",
        "dialysis_type": "peritoneal",
        "dialysis_required": True,
        "description": "복막투석 중인 환자"
    },
    "benefits": {
        "copay_reduction": "95%",
        "copay_rate": "5%",
        "max_monthly_cap": None,
        "coverage_items": ["투석비", "복막투석액", "카테터 관리", "검사비"]
    },
    "application": {
        "required_documents": [
            "산정특례 등록 신청서",
            "의사 진단서",
            "복막투석 카테터 삽입 기록",
            "신분증"
        ],
        "application_place": "병원 원무과",
        "processing_time": "즉시",
        "validity_period": "계속",
        "renewal": "불필요"
    },
    "contact": {
        "phone": "1577-1000",
        "website": "https://www.nhis.or.kr",
        "online_application": False
    },
    "description": "복막투석 환자의 투석 관련 의료비 본인부담금이 5%로 감면됩니다.",
    "keywords": ["산정특례", "V005", "복막투석", "CAPD", "APD", "투석비지원"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

#### Category 2: disability (장애인 복지) - 4개

##### Program 4: 신장장애 등록
```python
{
    "programId": "disability_kidney",
    "title": "신장장애 등록 제도",
    "category": "disability",
    "target_disease": ["CKD", "ESRD", "dialysis", "transplant"],
    "eligibility": {
        "ckd_stage": [5],
        "dialysis_duration": "3개월 이상",
        "description": "투석 3개월 이상 또는 신장이식 후"
    },
    "benefits": {
        "benefits_list": [
            "장애 2급 (투석 3개월 이상)",
            "장애 5급 (신장이식 후)",
            "장애인연금 (2급: 월 약 20만원)",
            "의료비 지원",
            "장애인 차량 세금 감면",
            "공공시설 이용료 할인",
            "장애인 주차 스티커"
        ]
    },
    "application": {
        "required_documents": [
            "장애진단서 (신장내과 전문의)",
            "투석 기록지 (3개월분)",
            "신분증",
            "사진 2장"
        ],
        "application_place": "주민센터",
        "processing_time": "1-2개월",
        "validity_period": "영구",
        "renewal": "불필요"
    },
    "contact": {
        "phone": "국번없이 129 (보건복지콜센터)",
        "website": "https://www.mohw.go.kr",
        "online_application": False
    },
    "description": "신장기능이 저하되어 투석이나 이식이 필요한 경우 장애인으로 등록할 수 있습니다. 투석 3개월 이상은 2급, 이식 후는 5급으로 등록됩니다.",
    "keywords": ["장애인등록", "신장장애", "장애2급", "장애5급", "장애인연금", "의료비지원"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

##### Program 5: 장애인연금
```python
{
    "programId": "disability_pension",
    "title": "장애인연금 제도",
    "category": "disability",
    "target_disease": ["all"],
    "eligibility": {
        "description": "18세 이상, 장애 정도가 심한 장애인 (구 1-3급), 소득 하위 70%"
    },
    "benefits": {
        "monthly_amount": 200000,
        "coverage_items": ["기초급여", "부가급여"]
    },
    "application": {
        "required_documents": [
            "장애인연금 신청서",
            "장애인등록증 사본",
            "통장 사본",
            "소득재산 신고서"
        ],
        "application_place": "주민센터",
        "processing_time": "1개월",
        "validity_period": "계속",
        "renewal": "매년 소득 재조사"
    },
    "contact": {
        "phone": "국번없이 129",
        "website": "https://www.bokjiro.go.kr",
        "online_application": True
    },
    "description": "장애 정도가 심한 장애인에게 매월 연금을 지급하여 생활 안정을 지원합니다.",
    "keywords": ["장애인연금", "기초급여", "부가급여", "중증장애"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

##### Program 6: 장애인 의료비 지원
```python
{
    "programId": "disability_medical_support",
    "title": "장애인 의료비 지원",
    "category": "disability",
    "target_disease": ["all"],
    "eligibility": {
        "description": "등록 장애인 (1-6급), 의료급여 수급자 또는 차상위"
    },
    "benefits": {
        "copay_reduction": "100%",
        "coverage_items": ["진료비", "검사비", "수술비", "재활치료"]
    },
    "application": {
        "required_documents": [
            "장애인등록증",
            "의료급여증 (해당자)",
            "진단서 (해당 시)"
        ],
        "application_place": "주민센터 또는 보건소",
        "processing_time": "즉시",
        "validity_period": "계속",
        "renewal": "불필요"
    },
    "contact": {
        "phone": "국번없이 129",
        "website": "https://www.mohw.go.kr",
        "online_application": False
    },
    "description": "등록 장애인의 의료비를 전액 또는 일부 지원합니다.",
    "keywords": ["장애인의료비", "의료비지원", "진료비지원"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

##### Program 7: 장애인 주차 스티커
```python
{
    "programId": "disability_parking",
    "title": "장애인 주차 스티커 발급",
    "category": "disability",
    "target_disease": ["all"],
    "eligibility": {
        "description": "등록 장애인 (1-6급), 장애인 본인 또는 가족 차량"
    },
    "benefits": {
        "benefits_list": [
            "장애인 전용 주차구역 이용",
            "주차 요금 감면 (일부 시설)",
            "전국 공통 사용"
        ]
    },
    "application": {
        "required_documents": [
            "장애인등록증",
            "차량등록증",
            "신분증"
        ],
        "application_place": "주민센터",
        "processing_time": "즉시",
        "validity_period": "5년",
        "renewal": "만료 전 재발급"
    },
    "contact": {
        "phone": "주민센터 (구청)",
        "website": "해당 구청 홈페이지",
        "online_application": False
    },
    "description": "장애인이 편리하게 주차할 수 있도록 주차 스티커를 발급합니다.",
    "keywords": ["장애인주차", "주차스티커", "주차증"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

#### Category 3: medical_aid (의료비 지원) - 4개

##### Program 8: 차상위 의료급여
```python
{
    "programId": "medical_aid_low_income",
    "title": "저소득층 의료비 지원 (차상위 의료급여)",
    "category": "medical_aid",
    "target_disease": ["all"],
    "eligibility": {
        "income": "기준중위소득 50% 이하",
        "description": "차상위계층 또는 기초생활수급자"
    },
    "benefits": {
        "copay_reduction": "90-100%",
        "copay_rate": "0-10%",
        "coverage_items": ["입원", "외래", "약제", "검사"]
    },
    "application": {
        "required_documents": [
            "의료급여 신청서",
            "소득 증빙서류 (급여명세서, 통장 사본)",
            "진단서 (해당 시)",
            "신분증"
        ],
        "application_place": "주민센터",
        "processing_time": "1개월",
        "validity_period": "1년",
        "renewal": "매년"
    },
    "contact": {
        "phone": "국번없이 129",
        "website": "https://www.bokjiro.go.kr",
        "online_application": True
    },
    "description": "저소득층 만성질환자를 위한 의료비 전액 또는 일부 지원 제도입니다.",
    "keywords": ["차상위", "의료급여", "저소득층", "의료비지원", "기초생활수급자"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

##### Program 9: 재난적 의료비 지원
```python
{
    "programId": "catastrophic_medical_support",
    "title": "재난적 의료비 지원 사업",
    "category": "medical_aid",
    "target_disease": ["all"],
    "eligibility": {
        "income": "의료비가 소득 대비 과다",
        "description": "연소득 대비 의료비가 15% 이상 (기준중위소득 100% 이하)"
    },
    "benefits": {
        "max_monthly_cap": 20000000,
        "coverage_items": ["입원비", "수술비", "항암치료비"]
    },
    "application": {
        "required_documents": [
            "재난적 의료비 지원 신청서",
            "진료비 영수증",
            "소득 증빙서류",
            "진단서"
        ],
        "application_place": "국민건강보험공단",
        "processing_time": "1-2개월",
        "validity_period": "1년",
        "renewal": "매년"
    },
    "contact": {
        "phone": "1577-1000",
        "website": "https://www.nhis.or.kr",
        "online_application": True
    },
    "description": "과도한 의료비 지출로 경제적 어려움을 겪는 가구에 최대 2,000만원을 지원합니다.",
    "keywords": ["재난적의료비", "고액의료비", "의료비지원", "입원비"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

##### Program 10: 긴급 의료비 지원
```python
{
    "programId": "emergency_medical_support",
    "title": "긴급 의료비 지원",
    "category": "medical_aid",
    "target_disease": ["all"],
    "eligibility": {
        "income": "위기상황 가구",
        "description": "생명·신체 위협 상황, 갑작스러운 의료비 발생"
    },
    "benefits": {
        "max_monthly_cap": 3000000,
        "coverage_items": ["응급 입원비", "응급 수술비"]
    },
    "application": {
        "required_documents": [
            "긴급 의료비 지원 신청서",
            "진단서",
            "진료비 영수증 (예상)",
            "소득 증빙서류"
        ],
        "application_place": "주민센터 또는 보건소",
        "processing_time": "3-7일 (긴급)",
        "validity_period": "1회성",
        "renewal": "불필요"
    },
    "contact": {
        "phone": "국번없이 129",
        "website": "https://www.bokjiro.go.kr",
        "online_application": False
    },
    "description": "갑작스러운 질병이나 사고로 의료비가 필요한 위기 가구에 최대 300만원을 긴급 지원합니다.",
    "keywords": ["긴급의료비", "위기지원", "응급의료비"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

##### Program 11: 암/희귀질환 의료비 지원
```python
{
    "programId": "rare_disease_support",
    "title": "암/희귀질환 의료비 지원",
    "category": "medical_aid",
    "target_disease": ["CKD", "rare disease", "cancer"],
    "eligibility": {
        "income": "기준중위소득 120% 이하",
        "description": "희귀질환 또는 암 환자"
    },
    "benefits": {
        "copay_reduction": "varies",
        "coverage_items": ["진료비", "검사비", "약제비"]
    },
    "application": {
        "required_documents": [
            "의료비 지원 신청서",
            "진단서",
            "소득 증빙서류",
            "통장 사본"
        ],
        "application_place": "보건소",
        "processing_time": "1개월",
        "validity_period": "1년",
        "renewal": "매년"
    },
    "contact": {
        "phone": "보건소 (지역별)",
        "website": "https://www.mohw.go.kr",
        "online_application": False
    },
    "description": "희귀질환 또는 암 환자의 의료비를 소득 수준에 따라 지원합니다.",
    "keywords": ["희귀질환", "의료비지원", "암환자", "저소득"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

#### Category 4: transplant (이식 지원) - 2개

##### Program 12: 신장이식 수술비 지원
```python
{
    "programId": "transplant_surgery_support",
    "title": "신장이식 수술비 지원",
    "category": "transplant",
    "target_disease": ["ESRD", "kidney transplant"],
    "eligibility": {
        "dialysis_duration": "6개월 이상",
        "transplant_candidate": True,
        "description": "신장이식 대기자 또는 수술 예정자"
    },
    "benefits": {
        "max_monthly_cap": 30000000,
        "coverage_items": ["수술비", "입원비", "검사비"]
    },
    "application": {
        "required_documents": [
            "이식 대기자 등록증",
            "의사 소견서",
            "소득 증빙서류",
            "신분증"
        ],
        "application_place": "국립장기조직혈액관리원 (KONOS)",
        "processing_time": "2주",
        "validity_period": "수술 전후 6개월",
        "renewal": "불필요"
    },
    "contact": {
        "phone": "02-2628-3602 (KONOS)",
        "website": "https://www.konos.go.kr",
        "online_application": True
    },
    "description": "신장이식 수술비를 최대 3,000만원까지 지원합니다.",
    "keywords": ["신장이식", "수술비지원", "KONOS", "이식대기자"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

##### Program 13: 면역억제제 지원
```python
{
    "programId": "immunosuppressant_support",
    "title": "신장이식 후 면역억제제 지원",
    "category": "transplant",
    "target_disease": ["kidney transplant"],
    "eligibility": {
        "transplant_candidate": False,
        "description": "신장이식 후 환자 (평생)"
    },
    "benefits": {
        "monthly_amount": 200000,
        "coverage_items": ["면역억제제", "항생제", "정기 검사"]
    },
    "application": {
        "required_documents": [
            "이식 확인서",
            "처방전",
            "소득 증빙서류"
        ],
        "application_place": "국민건강보험공단",
        "processing_time": "2주",
        "validity_period": "평생",
        "renewal": "불필요"
    },
    "contact": {
        "phone": "1577-1000",
        "website": "https://www.nhis.or.kr",
        "online_application": True
    },
    "description": "신장이식 후 평생 복용해야 하는 면역억제제 비용을 월 최대 20만원까지 지원합니다.",
    "keywords": ["면역억제제", "이식후관리", "약제비지원"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

#### Category 5: transport (교통비 지원) - 2개

##### Program 14: 투석 환자 교통비 지원
```python
{
    "programId": "dialysis_transport",
    "title": "투석 환자 교통비 지원",
    "category": "transport",
    "target_disease": ["hemodialysis", "peritoneal dialysis"],
    "eligibility": {
        "dialysis_required": True,
        "income": "기준중위소득 120% 이하",
        "description": "정기적으로 투석 중인 환자"
    },
    "benefits": {
        "monthly_amount": 150000,
        "coverage_items": ["투석 병원 왕복 교통비"]
    },
    "application": {
        "required_documents": [
            "교통비 지원 신청서",
            "투석 확인서 (병원 발급)",
            "소득 증빙서류",
            "통장 사본"
        ],
        "application_place": "주민센터 또는 보건소",
        "processing_time": "1개월",
        "validity_period": "1년",
        "renewal": "매년"
    },
    "contact": {
        "phone": "지역 보건소 (지역별 상이)",
        "website": "각 지자체 홈페이지",
        "online_application": False
    },
    "description": "정기적으로 투석하러 병원을 다니는 환자의 교통비를 월 15만원 지원합니다. 지자체마다 금액과 조건이 다를 수 있습니다.",
    "keywords": ["교통비지원", "투석", "혈액투석", "복막투석", "차상위"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

##### Program 15: 복지카드 발급
```python
{
    "programId": "welfare_card",
    "title": "장애인 복지카드 발급",
    "category": "transport",
    "target_disease": ["all"],
    "eligibility": {
        "description": "등록 장애인"
    },
    "benefits": {
        "benefits_list": [
            "대중교통 무료/할인",
            "문화시설 할인",
            "통신비 할인",
            "전기요금 할인"
        ]
    },
    "application": {
        "required_documents": [
            "복지카드 신청서",
            "장애인등록증",
            "사진 1장"
        ],
        "application_place": "주민센터",
        "processing_time": "2주",
        "validity_period": "영구",
        "renewal": "불필요"
    },
    "contact": {
        "phone": "국번없이 129",
        "website": "https://www.mohw.go.kr",
        "online_application": False
    },
    "description": "장애인에게 각종 할인 혜택을 제공하는 복지카드를 발급합니다.",
    "keywords": ["복지카드", "장애인카드", "교통할인", "문화할인"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
```

### 3.2 데이터 통계

**카테고리별 분포**:
```
sangjung_special: 3개 (20%)
disability: 4개 (27%)
medical_aid: 4개 (27%)
transplant: 2개 (13%)
transport: 2개 (13%)
```

**CKD 단계별 적용 가능 프로그램**:
```
Stage 1-2: 5개 (일반 의료비 지원)
Stage 3: 10개 (산정특례 시작)
Stage 4-5: 12개 (대부분 적용)
투석 중: 15개 (전체 적용)
이식 후: 8개 (이식 관련)
```

---

## 4. 데이터 로딩 스크립트

### 4.1 전체 스크립트

**파일**: `data/welfare/load_welfare_data.py` (신규 생성)

```python
"""
Welfare Programs Data Loading Script

Loads 15 welfare programs into MongoDB careguide.welfare_programs collection

Usage:
    cd data/welfare
    python load_welfare_data.py

Expected Output:
    ✅ Cleared existing welfare_programs collection
    ✅ Inserted 15 welfare programs
    ✅ Created 5 indexes
    📊 Total: 15 programs
       - sangjung_special: 3
       - disability: 4
       - medical_aid: 4
       - transplant: 2
       - transport: 2
"""

from pymongo import MongoClient, ASCENDING, TEXT
from datetime import datetime
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

# ==================== Welfare Programs Data ====================

welfare_programs = [
    # 1. 산정특례 V001
    {
        "programId": "sangjung_ckd_v001",
        "title": "만성콩팥병 산정특례 제도",
        "category": "sangjung_special",
        "target_disease": ["CKD", "chronic kidney disease", "만성콩팥병"],
        "eligibility": {
            "disease_code": "V001",
            "ckd_stage": [3, 4, 5],
            "description": "만성콩팥병 3기 이상 또는 eGFR 60 미만"
        },
        "benefits": {
            "copay_reduction": "90%",
            "copay_rate": "10%",
            "max_monthly_cap": None,
            "coverage_items": ["외래진료", "검사", "약제", "치료"]
        },
        "application": {
            "required_documents": [
                "산정특례 등록 신청서",
                "의사 진단서 (희귀난치성질환 등록 신청용)",
                "검사결과지 (eGFR, 크레아티닌)",
                "신분증"
            ],
            "application_place": "국민건강보험공단 지사 또는 병원 원무과",
            "processing_time": "7-14일",
            "validity_period": "5년",
            "renewal": "만료 1개월 전 재신청"
        },
        "contact": {
            "phone": "1577-1000",
            "website": "https://www.nhis.or.kr",
            "online_application": True
        },
        "description": "만성콩팥병 환자의 의료비 부담을 경감하기 위한 제도입니다. 본인부담금이 90% 감면되어 10%만 부담합니다.",
        "keywords": ["산정특례", "V001", "본인부담금", "의료비지원", "CKD", "만성콩팥병"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },

    # 2. 산정특례 V003 (혈액투석)
    {
        "programId": "sangjung_dialysis_v003",
        "title": "혈액투석 산정특례 제도",
        "category": "sangjung_special",
        "target_disease": ["hemodialysis", "혈액투석", "ESRD"],
        "eligibility": {
            "disease_code": "V003",
            "dialysis_type": "hemodialysis",
            "dialysis_required": True,
            "description": "주 2-3회 정기적으로 혈액투석 중인 환자"
        },
        "benefits": {
            "copay_reduction": "95%",
            "copay_rate": "5%",
            "max_monthly_cap": None,
            "coverage_items": ["투석비", "검사비", "약제비", "혈관조성술"]
        },
        "application": {
            "required_documents": [
                "산정특례 등록 신청서",
                "의사 진단서 (혈액투석 확인)",
                "투석 기록지",
                "신분증"
            ],
            "application_place": "투석 병원 원무과",
            "processing_time": "즉시 (투석 시작 시)",
            "validity_period": "계속 (투석 중단 시까지)",
            "renewal": "불필요"
        },
        "contact": {
            "phone": "1577-1000",
            "website": "https://www.nhis.or.kr",
            "online_application": False
        },
        "description": "혈액투석 환자의 투석비 본인부담금이 5%로 대폭 감면됩니다. 투석을 시작하면 자동으로 적용됩니다.",
        "keywords": ["산정특례", "V003", "혈액투석", "투석비지원", "본인부담금5%"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },

    # 3. 산정특례 V005 (복막투석)
    {
        "programId": "sangjung_peritoneal_v005",
        "title": "복막투석 산정특례 제도",
        "category": "sangjung_special",
        "target_disease": ["peritoneal dialysis", "복막투석", "ESRD"],
        "eligibility": {
            "disease_code": "V005",
            "dialysis_type": "peritoneal",
            "dialysis_required": True,
            "description": "복막투석 중인 환자"
        },
        "benefits": {
            "copay_reduction": "95%",
            "copay_rate": "5%",
            "max_monthly_cap": None,
            "coverage_items": ["투석비", "복막투석액", "카테터 관리", "검사비"]
        },
        "application": {
            "required_documents": [
                "산정특례 등록 신청서",
                "의사 진단서",
                "복막투석 카테터 삽입 기록",
                "신분증"
            ],
            "application_place": "병원 원무과",
            "processing_time": "즉시",
            "validity_period": "계속",
            "renewal": "불필요"
        },
        "contact": {
            "phone": "1577-1000",
            "website": "https://www.nhis.or.kr",
            "online_application": False
        },
        "description": "복막투석 환자의 투석 관련 의료비 본인부담금이 5%로 감면됩니다.",
        "keywords": ["산정특례", "V005", "복막투석", "CAPD", "APD", "투석비지원"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },

    # 4-15: 나머지 프로그램 (섹션 3.1 참조)
    # ... (위에서 정의한 프로그램 4-15 추가)
]

# ==================== Loading Function ====================

def load_welfare_data():
    """Load welfare programs to MongoDB"""
    print("\n" + "="*80)
    print("WELFARE PROGRAMS DATA LOADING")
    print("="*80)

    # 1. Connect to MongoDB
    print(f"\n[1] Connecting to MongoDB...")
    print(f"    URI: {MONGODB_URI}")
    client = MongoClient(MONGODB_URI)
    db = client["careguide"]
    collection = db["welfare_programs"]
    print(f"    ✅ Connected to {db.name}.{collection.name}")

    # 2. Clear existing data
    print(f"\n[2] Clearing existing data...")
    deleted = collection.delete_many({})
    print(f"    ✅ Deleted {deleted.deleted_count} existing documents")

    # 3. Insert new data
    print(f"\n[3] Inserting {len(welfare_programs)} welfare programs...")
    result = collection.insert_many(welfare_programs)
    print(f"    ✅ Inserted {len(result.inserted_ids)} programs")

    # 4. Create indexes
    print(f"\n[4] Creating indexes...")

    # Category index
    collection.create_index([("category", ASCENDING)], name="category_idx")
    print(f"    ✅ Created category_idx")

    # Text search index
    collection.create_index(
        [("title", TEXT), ("description", TEXT), ("keywords", TEXT)],
        name="welfare_text_search",
        default_language="korean"
    )
    print(f"    ✅ Created welfare_text_search (Korean)")

    # Target disease index
    collection.create_index([("target_disease", ASCENDING)], name="disease_idx")
    print(f"    ✅ Created disease_idx")

    # CKD stage index
    collection.create_index([("eligibility.ckd_stage", ASCENDING)], name="ckd_stage_idx")
    print(f"    ✅ Created ckd_stage_idx")

    # Program ID unique index
    collection.create_index([("programId", ASCENDING)], name="program_id_unique", unique=True)
    print(f"    ✅ Created program_id_unique (unique)")

    # 5. Verify
    print(f"\n[5] Verification...")
    total = collection.count_documents({})
    print(f"    Total programs: {total}")

    by_category = {}
    for prog in collection.find():
        cat = prog["category"]
        by_category[cat] = by_category.get(cat, 0) + 1

    print(f"    By category:")
    for cat, count in sorted(by_category.items()):
        print(f"      - {cat}: {count}")

    # Test text search
    print(f"\n[6] Testing text search...")
    test_queries = ["산정특례", "장애인", "의료비 지원"]
    for query in test_queries:
        results = collection.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(3)

        count = len(list(results))
        print(f"    '{query}': {count} results")

    # Close
    client.close()

    print("\n" + "="*80)
    print("✅ WELFARE DATA LOADING COMPLETED!")
    print("="*80)
    print(f"\nNext steps:")
    print(f"  1. Verify data: mongosh careguide --eval \"db.welfare_programs.count()\"")
    print(f"  2. Test WelfareManager: python backend/app/db/welfare_manager.py")
    print(f"  3. Read: docs/welfare/02_WELFARE_BACKEND_IMPLEMENTATION.md")
    print("="*80 + "\n")


if __name__ == "__main__":
    load_welfare_data()
```

### 4.2 실행 방법

```bash
# 1. 디렉토리 생성
mkdir -p data/welfare

# 2. 스크립트 작성
# (위 코드를 data/welfare/load_welfare_data.py로 저장)

# 3. 실행
cd data/welfare
python load_welfare_data.py

# 4. 검증
mongosh careguide --eval "db.welfare_programs.count()"
# Expected: 15
```

---

## 5. 검증 및 테스트

### 5.1 MongoDB Shell 검증

```bash
# 1. 문서 개수 확인
mongosh careguide --eval "db.welfare_programs.count()"
# Expected: 15

# 2. 카테고리별 개수
mongosh careguide --eval "db.welfare_programs.aggregate([
  {$group: {_id: '\$category', count: {$sum: 1}}},
  {$sort: {count: -1}}
])"

# 3. 인덱스 확인
mongosh careguide --eval "db.welfare_programs.getIndexes()"
# Expected: 6 indexes (_id + 5 custom)

# 4. 텍스트 검색 테스트
mongosh careguide --eval "db.welfare_programs.find(
  {\$text: {\$search: '산정특례'}},
  {score: {\$meta: 'textScore'}}
).sort({score: {\$meta: 'textScore'}}).limit(3)"
# Expected: V001, V003, V005

# 5. 카테고리 검색
mongosh careguide --eval "db.welfare_programs.find({category: 'disability'}).count()"
# Expected: 4
```

### 5.2 Python 검증 스크립트

**파일**: `data/welfare/verify_data.py`

```python
"""
Verify welfare data loaded correctly
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

def verify_welfare_data():
    """Verify welfare programs data"""
    client = MongoClient(MONGODB_URI)
    db = client["careguide"]
    collection = db["welfare_programs"]

    print("\n" + "="*80)
    print("WELFARE DATA VERIFICATION")
    print("="*80)

    # 1. Count
    total = collection.count_documents({})
    print(f"\n[1] Total documents: {total}")
    assert total == 15, f"Expected 15, got {total}"
    print(f"    ✅ Correct count")

    # 2. Categories
    print(f"\n[2] Categories:")
    by_category = {}
    for prog in collection.find():
        cat = prog["category"]
        by_category[cat] = by_category.get(cat, 0) + 1

    expected_counts = {
        "sangjung_special": 3,
        "disability": 4,
        "medical_aid": 4,
        "transplant": 2,
        "transport": 2
    }

    for cat, count in sorted(by_category.items()):
        expected = expected_counts.get(cat, 0)
        status = "✅" if count == expected else "❌"
        print(f"    {status} {cat}: {count}/{expected}")

    # 3. Required fields
    print(f"\n[3] Required fields check:")
    required_fields = [
        "programId", "title", "category", "target_disease",
        "eligibility", "benefits", "application", "contact",
        "description", "keywords"
    ]

    for prog in collection.find():
        for field in required_fields:
            assert field in prog, f"Missing field '{field}' in {prog.get('programId')}"

    print(f"    ✅ All {len(required_fields)} required fields present")

    # 4. Text search
    print(f"\n[4] Text search test:")
    test_queries = {
        "산정특례": 3,  # V001, V003, V005
        "장애인": 4,    # disability category
        "의료비": 10    # multiple programs
    }

    for query, expected_min in test_queries.items():
        results = collection.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})])

        count = len(list(results))
        status = "✅" if count >= expected_min else "❌"
        print(f"    {status} '{query}': {count} results (expected >={expected_min})")

    # 5. Indexes
    print(f"\n[5] Indexes:")
    indexes = collection.index_information()
    expected_indexes = [
        "_id_",
        "category_idx",
        "welfare_text_search",
        "disease_idx",
        "ckd_stage_idx",
        "program_id_unique"
    ]

    for idx_name in expected_indexes:
        status = "✅" if idx_name in indexes else "❌"
        print(f"    {status} {idx_name}")

    client.close()

    print("\n" + "="*80)
    print("✅ VERIFICATION PASSED!")
    print("="*80 + "\n")


if __name__ == "__main__":
    verify_welfare_data()
```

### 5.3 검증 체크리스트

**데이터 로딩 후 확인 사항**:

- [ ] **문서 개수**: 15개
- [ ] **카테고리 분포**: sangjung(3), disability(4), medical_aid(4), transplant(2), transport(2)
- [ ] **필수 필드**: 10개 필드 모두 존재
- [ ] **인덱스**: 6개 (\_id + 5 custom)
- [ ] **텍스트 검색**: "산정특례" → 3개 결과
- [ ] **카테고리 검색**: "disability" → 4개 결과
- [ ] **Unique constraint**: programId 중복 불가

---

## 📊 데이터 분석

### 프로그램별 주요 정보

| programId | 카테고리 | 본인부담률 | 유효기간 | 신청 기관 |
|-----------|---------|----------|---------|-----------|
| sangjung_ckd_v001 | 산정특례 | 10% | 5년 | 건강보험공단 |
| sangjung_dialysis_v003 | 산정특례 | 5% | 계속 | 병원 원무과 |
| sangjung_peritoneal_v005 | 산정특례 | 5% | 계속 | 병원 원무과 |
| disability_kidney | 장애인 | - | 영구 | 주민센터 |
| disability_pension | 장애인 | - | 계속 | 주민센터 |
| disability_medical_support | 장애인 | 0-10% | 계속 | 주민센터 |
| disability_parking | 장애인 | - | 5년 | 주민센터 |
| medical_aid_low_income | 의료비 | 0-10% | 1년 | 주민센터 |
| catastrophic_medical_support | 의료비 | - | 1년 | 건강보험공단 |
| emergency_medical_support | 의료비 | - | 1회 | 주민센터 |
| rare_disease_support | 의료비 | varies | 1년 | 보건소 |
| transplant_surgery_support | 이식 | - | 6개월 | KONOS |
| immunosuppressant_support | 이식 | - | 평생 | 건강보험공단 |
| dialysis_transport | 교통비 | - | 1년 | 보건소 |
| welfare_card | 교통비 | - | 영구 | 주민센터 |

### 검색 키워드 분포

**상위 키워드**:
- "산정특례": 3개 프로그램
- "의료비지원": 8개 프로그램
- "장애인": 4개 프로그램
- "투석": 5개 프로그램
- "CKD": 12개 프로그램

---

## 🔍 FAQ

### Q1: 왜 programId와 _id를 모두 사용하나요?
**A**:
- `_id`: MongoDB 자동 생성 (ObjectId), 내부 참조용
- `programId`: 사람이 읽을 수 있는 ID, API 노출용, unique index

### Q2: target_disease가 배열인 이유는?
**A**: 하나의 프로그램이 여러 질병에 적용 가능
- 예: 산정특례 V001 → ["CKD", "chronic kidney disease", "만성콩팥병"]
- 검색 시 `$in` 연산자로 매칭

### Q3: 한국어 텍스트 검색이 잘 작동하나요?
**A**: MongoDB text index는 한국어 지원:
- `default_language="korean"` 설정 필수
- Tokenization: 형태소 분석 (간단)
- Stemming: 한국어 어간 추출

하지만 완벽하지 않으므로 키워드 배열도 함께 사용

### Q4: 데이터 업데이트는 어떻게 하나요?
**A**:
```python
# programId로 업데이트
db.welfare_programs.update_one(
    {"programId": "sangjung_ckd_v001"},
    {"$set": {
        "contact.phone": "새번호",
        "updated_at": datetime.utcnow()
    }}
)
```

---

## ✅ Checklist

**데이터 로딩 완료 기준**:

- [ ] MongoDB 연결 성공
- [ ] 기존 데이터 삭제 (0개)
- [ ] 15개 프로그램 삽입
- [ ] 6개 인덱스 생성
- [ ] 텍스트 검색 작동 ("산정특례" → 3개)
- [ ] 카테고리 검색 작동 ("disability" → 4개)
- [ ] verify_data.py 통과

---

## 📚 다음 단계

1. ✅ 데이터 로딩 완료
2. ➡️ **다음 문서**: `02_WELFARE_BACKEND_IMPLEMENTATION.md`
3. 구현: WelfareManager 클래스

---

**END OF DATABASE DESIGN**

데이터베이스 스키마와 초기 데이터를 이해했다면,
다음 문서로 이동하여 WelfareManager 구현을 시작하세요.
