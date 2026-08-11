# CareGuide Welfare API Reference

**버전**: v1.0
**작성일**: 2025-11-19
**Base URL**: `http://localhost:8000`

---

## 📑 목차

1. [개요](#1-개요)
2. [인증](#2-인증)
3. [공통 응답 형식](#3-공통-응답-형식)
4. [Welfare API](#4-welfare-api)
5. [Hospital API](#5-hospital-api)
6. [에러 코드](#6-에러-코드)
7. [예제 코드](#7-예제-코드)

---

## 1. 개요

### 1.1 API 개요

CareGuide Welfare API는 만성콩팥병 환자를 위한 복지 정보를 제공합니다.

**주요 기능**:
- 복지 프로그램 검색
- 카테고리별 조회
- 병원/투석센터 검색
- 사용자 맞춤 추천

### 1.2 엔드포인트 목록

| 카테고리 | 엔드포인트 | 메서드 | 인증 필요 |
|---------|-----------|--------|----------|
| **복지 검색** | `/api/welfare/search` | GET | ❌ |
| **카테고리 목록** | `/api/welfare/categories` | GET | ❌ |
| **카테고리별 조회** | `/api/welfare/category/{category}` | GET | ❌ |
| **프로그램 상세** | `/api/welfare/{programId}` | GET | ❌ |
| **맞춤 추천** | `/api/welfare/recommend` | GET | ✅ |
| **병원 검색** | `/api/hospitals/search` | GET | ❌ |
| **투석센터 검색** | `/api/hospitals/dialysis` | GET | ❌ |
| **근처 병원** | `/api/hospitals/nearby` | GET | ❌ |

---

## 2. 인증

### 2.1 JWT 토큰 인증

일부 엔드포인트는 JWT 토큰이 필요합니다.

**헤더 형식**:
```http
Authorization: Bearer <JWT_TOKEN>
```

**토큰 발급**:
```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 3. 공통 응답 형식

### 3.1 성공 응답

```json
{
  "success": true,
  "data": { ... },
  "message": "성공 메시지"
}
```

### 3.2 에러 응답

```json
{
  "detail": "에러 메시지",
  "status_code": 400
}
```

---

## 4. Welfare API

### 4.1 복지 프로그램 검색

복지 프로그램을 텍스트로 검색합니다.

#### Endpoint
```http
GET /api/welfare/search
```

#### Parameters

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `query` | string | ✅ | - | 검색어 |
| `limit` | integer | ❌ | 10 | 결과 개수 (1-50) |
| `category` | string | ❌ | - | 카테고리 필터 |

#### Request Example

```bash
# 기본 검색
GET /api/welfare/search?query=산정특례&limit=5

# 카테고리 필터링
GET /api/welfare/search?query=지원&category=medical_aid&limit=10
```

#### Response Schema

```typescript
interface WelfareSearchResponse {
  success: boolean
  count: number
  programs: Array<{
    programId: string
    title: string
    category: string
    category_name: string
    description: string
    benefits: {
      copay_reduction?: string
      copay_rate?: string
      monthly_allowance?: number
      // ... 기타 혜택
    }
    application: {
      required_documents: string[]
      application_place: string
      processing_time: string
      validity_period: string
    }
    contact: {
      phone: string
      website: string
      online_application: boolean
    }
    keywords: string[]
    priority: number
    score?: number  // 검색 점수
  }>
}
```

#### Response Example

```json
{
  "success": true,
  "count": 2,
  "programs": [
    {
      "programId": "sangjung_ckd_v001",
      "title": "만성콩팥병 산정특례 제도",
      "category": "sangjung_special",
      "category_name": "산정특례",
      "description": "만성콩팥병 환자의 의료비 부담을 경감하기 위한 제도입니다. 본인부담금이 90% 감면되어 10%만 부담합니다.",
      "benefits": {
        "copay_reduction": "90%",
        "copay_rate": "10%",
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
        "validity_period": "5년"
      },
      "contact": {
        "phone": "1577-1000",
        "website": "https://www.nhis.or.kr",
        "online_application": true
      },
      "keywords": ["산정특례", "V001", "본인부담금", "의료비지원"],
      "priority": 10,
      "score": 8.5
    },
    {
      "programId": "sangjung_dialysis_v003",
      "title": "혈액투석 산정특례 제도",
      "category": "sangjung_special",
      "category_name": "산정특례",
      "description": "혈액투석 환자의 투석비 본인부담금이 5%로 대폭 감면됩니다.",
      "benefits": {
        "copay_reduction": "95%",
        "copay_rate": "5%",
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
        "validity_period": "계속 (투석 중단 시까지)"
      },
      "contact": {
        "phone": "1577-1000",
        "website": "https://www.nhis.or.kr",
        "online_application": false
      },
      "keywords": ["산정특례", "V003", "혈액투석"],
      "priority": 9,
      "score": 7.2
    }
  ]
}
```

#### cURL Example

```bash
curl -X GET "http://localhost:8000/api/welfare/search?query=산정특례&limit=5" \
  -H "accept: application/json"
```

#### Python Example

```python
import httpx

async def search_welfare(query: str, limit: int = 10):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/welfare/search",
            params={"query": query, "limit": limit}
        )
        return response.json()

# 사용
result = await search_welfare("산정특례", limit=5)
print(f"검색 결과: {result['count']}개")
```

---

### 4.2 카테고리 목록 조회

모든 복지 카테고리 목록을 조회합니다.

#### Endpoint
```http
GET /api/welfare/categories
```

#### Parameters
없음

#### Response Schema

```typescript
interface CategoryListResponse {
  success: boolean
  count: number
  categories: Array<{
    id: string          // 카테고리 ID
    name: string        // 한글 이름
    count: number       // 프로그램 개수
  }>
}
```

#### Response Example

```json
{
  "success": true,
  "count": 10,
  "categories": [
    {
      "id": "sangjung_special",
      "name": "산정특례",
      "count": 3
    },
    {
      "id": "disability",
      "name": "장애인 복지",
      "count": 4
    },
    {
      "id": "medical_aid",
      "name": "의료비 지원",
      "count": 4
    },
    {
      "id": "transplant",
      "name": "신장이식 지원",
      "count": 1
    },
    {
      "id": "transport",
      "name": "교통비 지원",
      "count": 1
    },
    {
      "id": "emergency_support",
      "name": "긴급 지원",
      "count": 1
    },
    {
      "id": "employment",
      "name": "고용 지원",
      "count": 1
    }
  ]
}
```

#### cURL Example

```bash
curl -X GET "http://localhost:8000/api/welfare/categories" \
  -H "accept: application/json"
```

---

### 4.3 카테고리별 프로그램 조회

특정 카테고리의 모든 프로그램을 조회합니다.

#### Endpoint
```http
GET /api/welfare/category/{category}
```

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `category` | string | ✅ | 카테고리 ID |

**유효한 카테고리**:
- `sangjung_special` - 산정특례
- `disability` - 장애인 복지
- `medical_aid` - 의료비 지원
- `transplant` - 신장이식 지원
- `transport` - 교통비 지원
- `emergency_support` - 긴급 지원
- `housing` - 주거 지원
- `employment` - 고용 지원
- `education` - 교육 지원
- `other` - 기타

#### Query Parameters

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `limit` | integer | ❌ | 20 | 결과 개수 (1-50) |

#### Request Example

```bash
GET /api/welfare/category/sangjung_special?limit=10
GET /api/welfare/category/disability
```

#### Response Schema

```typescript
interface CategoryProgramsResponse {
  success: boolean
  category: string
  category_name: string
  count: number
  programs: WelfareProgram[]  // 4.1과 동일한 구조
}
```

#### Response Example

```json
{
  "success": true,
  "category": "sangjung_special",
  "category_name": "산정특례",
  "count": 3,
  "programs": [
    {
      "programId": "sangjung_ckd_v001",
      "title": "만성콩팥병 산정특례 제도",
      "category": "sangjung_special",
      "category_name": "산정특례",
      "description": "만성콩팥병 환자의 의료비 부담을 경감하기 위한 제도입니다...",
      "benefits": { /* ... */ },
      "application": { /* ... */ },
      "contact": { /* ... */ },
      "priority": 10
    },
    {
      "programId": "sangjung_dialysis_v003",
      "title": "혈액투석 산정특례 제도",
      /* ... */
    },
    {
      "programId": "sangjung_peritoneal_v005",
      "title": "복막투석 산정특례 제도",
      /* ... */
    }
  ]
}
```

#### cURL Example

```bash
curl -X GET "http://localhost:8000/api/welfare/category/sangjung_special?limit=10" \
  -H "accept: application/json"
```

---

### 4.4 프로그램 상세 조회

특정 복지 프로그램의 상세 정보를 조회합니다.

#### Endpoint
```http
GET /api/welfare/{programId}
```

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `programId` | string | ✅ | 프로그램 ID |

#### Request Example

```bash
GET /api/welfare/sangjung_ckd_v001
GET /api/welfare/disability_kidney
```

#### Response Schema

```typescript
interface WelfareProgramDetail {
  success: boolean
  program: {
    programId: string
    title: string
    category: string
    category_name: string
    target_disease: string[]

    // 수급 자격
    eligibility: {
      disease_code?: string
      ckd_stage?: number[]
      dialysis_required?: boolean
      dialysis_type?: string
      dialysis_duration?: string
      income?: string
      description: string
    }

    // 혜택 내용
    benefits: {
      copay_reduction?: string
      copay_rate?: string
      max_monthly_cap?: number
      coverage_items?: string[]
      monthly_allowance?: number
      benefits_list?: string[]
      surgery_support?: string
      immunosuppressant_support?: string
      monthly_amount?: number
      duration?: string
      usage?: string
      disability_grade?: string
    }

    // 신청 방법
    application: {
      required_documents: string[]
      application_place: string
      processing_time: string
      validity_period: string
      renewal?: string
      online_application?: boolean
    }

    // 연락처
    contact: {
      phone: string
      website: string
      online_application: boolean
    }

    // 상세 설명
    description: string
    detailed_description?: string
    keywords: string[]
    priority: number
    is_active: boolean

    // 추가 정보
    related_programs?: string[]
    faq?: Array<{
      question: string
      answer: string
    }>
    examples?: Array<{
      title: string
      description: string
    }>
  }
}
```

#### Response Example

```json
{
  "success": true,
  "program": {
    "programId": "sangjung_ckd_v001",
    "title": "만성콩팥병 산정특례 제도",
    "category": "sangjung_special",
    "category_name": "산정특례",
    "target_disease": ["CKD", "chronic kidney disease", "만성콩팥병"],

    "eligibility": {
      "disease_code": "V001",
      "ckd_stage": [3, 4, 5],
      "description": "만성콩팥병 3기 이상 또는 eGFR 60 미만"
    },

    "benefits": {
      "copay_reduction": "90%",
      "copay_rate": "10%",
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
      "online_application": true
    },

    "description": "만성콩팥병 환자의 의료비 부담을 경감하기 위한 제도입니다. 본인부담금이 90% 감면되어 10%만 부담합니다.",

    "detailed_description": "만성콩팥병(CKD) 산정특례는 만성 신장 질환으로 인해 지속적인 치료가 필요한 환자들의 경제적 부담을 줄이기 위해 마련된 제도입니다...",

    "keywords": ["산정특례", "V001", "본인부담금", "의료비지원", "CKD"],
    "priority": 10,
    "is_active": true,

    "related_programs": ["sangjung_dialysis_v003", "medical_aid_low_income"],

    "faq": [
      {
        "question": "CKD 2기는 산정특례 대상인가요?",
        "answer": "아니요. CKD 3기 이상(eGFR 60 미만)부터 산정특례 대상입니다."
      },
      {
        "question": "산정특례 승인 전 진료비도 적용되나요?",
        "answer": "신청일로부터 30일 이내 승인 시, 신청일부터 소급 적용됩니다."
      }
    ],

    "examples": [
      {
        "title": "CKD 4기 환자 A씨 사례",
        "description": "월 평균 진료비 50만원 → 산정특례 적용 후 5만원 (월 45만원 절감)"
      }
    ]
  }
}
```

#### cURL Example

```bash
curl -X GET "http://localhost:8000/api/welfare/sangjung_ckd_v001" \
  -H "accept: application/json"
```

#### Error Responses

**404 Not Found**:
```json
{
  "detail": "프로그램을 찾을 수 없습니다 (programId: invalid_id)",
  "status_code": 404
}
```

---

### 4.5 맞춤 추천 (인증 필요)

사용자 프로필 기반 복지 프로그램을 추천합니다.

#### Endpoint
```http
GET /api/welfare/recommend
```

#### Headers

```http
Authorization: Bearer <JWT_TOKEN>
```

#### Query Parameters

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `limit` | integer | ❌ | 5 | 결과 개수 (1-10) |

#### Request Example

```bash
GET /api/welfare/recommend?limit=5
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Response Schema

```typescript
interface RecommendedProgramsResponse {
  success: boolean
  user_profile: {
    profile_type: "general" | "patient" | "researcher"
    ckd_stage?: number
    is_dialysis?: boolean
    income_level?: "low" | "middle" | "high"
  }
  count: number
  recommended: WelfareProgram[]
  recommendation_reason: string
}
```

#### Response Example

```json
{
  "success": true,
  "user_profile": {
    "profile_type": "patient",
    "ckd_stage": 5,
    "is_dialysis": true,
    "income_level": "middle"
  },
  "count": 3,
  "recommended": [
    {
      "programId": "sangjung_dialysis_v003",
      "title": "혈액투석 산정특례 제도",
      /* ... */
    },
    {
      "programId": "disability_kidney",
      "title": "신장장애 등록 제도",
      /* ... */
    },
    {
      "programId": "dialysis_transport",
      "title": "투석 환자 교통비 지원",
      /* ... */
    }
  ],
  "recommendation_reason": "투석 중인 환자에게 추천하는 필수 복지 프로그램입니다."
}
```

#### cURL Example

```bash
curl -X GET "http://localhost:8000/api/welfare/recommend?limit=5" \
  -H "accept: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Error Responses

**401 Unauthorized**:
```json
{
  "detail": "인증이 필요합니다",
  "status_code": 401
}
```

---

### 4.6 관련 프로그램 조회

특정 프로그램과 관련된 다른 프로그램을 조회합니다.

#### Endpoint
```http
GET /api/welfare/{programId}/related
```

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `programId` | string | ✅ | 프로그램 ID |

#### Query Parameters

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `limit` | integer | ❌ | 3 | 결과 개수 (1-10) |

#### Request Example

```bash
GET /api/welfare/sangjung_ckd_v001/related?limit=3
```

#### Response Example

```json
{
  "success": true,
  "base_program": {
    "programId": "sangjung_ckd_v001",
    "title": "만성콩팥병 산정특례 제도"
  },
  "count": 2,
  "related": [
    {
      "programId": "sangjung_dialysis_v003",
      "title": "혈액투석 산정특례 제도",
      "category_name": "산정특례",
      "description": "혈액투석 환자의 투석비 본인부담금이 5%로 대폭 감면됩니다.",
      "relation_type": "same_category"
    },
    {
      "programId": "medical_aid_low_income",
      "title": "저소득층 의료급여 제도",
      "category_name": "의료비 지원",
      "description": "저소득층 만성질환자를 위한 의료비 전액 또는 일부 지원 제도입니다.",
      "relation_type": "complementary"
    }
  ]
}
```

#### cURL Example

```bash
curl -X GET "http://localhost:8000/api/welfare/sangjung_ckd_v001/related?limit=3" \
  -H "accept: application/json"
```

---

### 4.7 통계 조회

복지 프로그램 통계를 조회합니다.

#### Endpoint
```http
GET /api/welfare/stats
```

#### Query Parameters

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `use_cache` | boolean | ❌ | true | 캐시 사용 여부 |

#### Response Schema

```typescript
interface WelfareStatsResponse {
  success: boolean
  stats: {
    total: number
    active: number
    by_category: {
      [key: string]: number  // 카테고리명: 개수
    }
  }
  cache_age?: number  // 캐시된 시간 (초)
}
```

#### Response Example

```json
{
  "success": true,
  "stats": {
    "total": 15,
    "active": 15,
    "by_category": {
      "산정특례": 3,
      "장애인 복지": 4,
      "의료비 지원": 4,
      "신장이식 지원": 1,
      "교통비 지원": 1,
      "긴급 지원": 1,
      "고용 지원": 1
    }
  },
  "cache_age": 120
}
```

#### cURL Example

```bash
# 캐시 사용
curl -X GET "http://localhost:8000/api/welfare/stats" \
  -H "accept: application/json"

# 캐시 무시 (최신 데이터)
curl -X GET "http://localhost:8000/api/welfare/stats?use_cache=false" \
  -H "accept: application/json"
```

---

## 5. Hospital API

### 5.1 병원 텍스트 검색

병원/약국을 이름, 주소로 검색합니다.

#### Endpoint
```http
GET /api/hospitals/search
```

#### Query Parameters

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `query` | string | ✅ | - | 검색어 (병원명, 주소) |
| `limit` | integer | ❌ | 20 | 결과 개수 (1-100) |
| `type` | string | ❌ | - | 유형 필터 (병원/의원, 약국) |
| `region` | string | ❌ | - | 지역 필터 (서울, 부산 등) |
| `has_dialysis` | boolean | ❌ | - | 투석 가능 여부 |

#### Request Example

```bash
# 기본 검색
GET /api/hospitals/search?query=신촌&limit=10

# 필터링
GET /api/hospitals/search?query=병원&region=서울&has_dialysis=true&limit=20
```

#### Response Schema

```typescript
interface HospitalSearchResponse {
  success: boolean
  count: number
  hospitals: Array<{
    _id: string
    name: string
    address: string
    phone: string
    region: string
    type: string
    dialysis_machines: number
    has_dialysis_unit: boolean
    night_dialysis: boolean
    dialysis_days: string
    lat: number
    lng: number
    naver_map_url: string
    kakao_map_url: string
    score?: number  // 검색 점수
  }>
}
```

#### Response Example

```json
{
  "success": true,
  "count": 5,
  "hospitals": [
    {
      "_id": "673c5e8f9a1b2c3d4e5f6789",
      "name": "(의) 열린의료재단 연신내열린의원",
      "address": "서울특별시 은평구 통일로 855-10, 3층 (대조동)",
      "phone": "02-388-7582",
      "region": "서울",
      "type": "병원/의원",
      "dialysis_machines": 32,
      "has_dialysis_unit": true,
      "night_dialysis": false,
      "dialysis_days": "월,화,수,목,금,토",
      "lat": 37.6195,
      "lng": 126.9209,
      "naver_map_url": "https://map.naver.com/v5/search/...",
      "kakao_map_url": "https://map.kakao.com/?q=...",
      "score": 8.5
    },
    {
      "_id": "673c5e8f9a1b2c3d4e5f678a",
      "name": "(의) 열린의료재단 서초열린의원",
      "address": "서울특별시 서초구 서초중앙로 230, 4층",
      "phone": "02-3477-2582",
      "region": "서울",
      "type": "병원/의원",
      "dialysis_machines": 29,
      "has_dialysis_unit": true,
      "night_dialysis": false,
      "dialysis_days": "월,화,수,목,금,토",
      "lat": 37.4876,
      "lng": 127.0142,
      "score": 7.8
    }
  ]
}
```

#### cURL Example

```bash
curl -X GET "http://localhost:8000/api/hospitals/search?query=신촌&limit=10" \
  -H "accept: application/json"
```

---

### 5.2 투석센터 검색

투석 가능한 병원만 검색합니다.

#### Endpoint
```http
GET /api/hospitals/dialysis
```

#### Query Parameters

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `region` | string | ❌ | - | 지역 필터 |
| `night_only` | boolean | ❌ | false | 야간 투석만 |
| `min_machines` | integer | ❌ | 0 | 최소 투석기 대수 |
| `limit` | integer | ❌ | 50 | 결과 개수 (1-100) |

#### Request Example

```bash
# 서울 투석센터
GET /api/hospitals/dialysis?region=서울&limit=20

# 야간 투석 가능 센터
GET /api/hospitals/dialysis?night_only=true

# 투석기 20대 이상
GET /api/hospitals/dialysis?min_machines=20&limit=30
```

#### Response Example

```json
{
  "success": true,
  "count": 18,
  "dialysis_centers": [
    {
      "_id": "673c5e8f9a1b2c3d4e5f6789",
      "name": "(의) 열린의료재단 상봉열린의원",
      "address": "서울특별시 중랑구 동일로 932, 2-3층 (상봉동)",
      "phone": "02-434-7582",
      "region": "서울",
      "type": "병원/의원",
      "dialysis_machines": 33,
      "has_dialysis_unit": true,
      "night_dialysis": false,
      "dialysis_days": "월,화,수,목,금,토",
      "lat": 37.5965,
      "lng": 127.0852,
      "naver_map_url": "https://map.naver.com/...",
      "kakao_map_url": "https://map.kakao.com/..."
    }
    /* ... 더 많은 결과 ... */
  ]
}
```

#### cURL Example

```bash
curl -X GET "http://localhost:8000/api/hospitals/dialysis?region=서울&limit=20" \
  -H "accept: application/json"
```

---

### 5.3 근처 병원 검색

좌표 기반으로 근처 병원을 검색합니다.

#### Endpoint
```http
GET /api/hospitals/nearby
```

#### Query Parameters

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `latitude` | float | ✅ | - | 위도 |
| `longitude` | float | ✅ | - | 경도 |
| `max_distance_km` | float | ❌ | 5.0 | 최대 거리 (km) |
| `type` | string | ❌ | - | 유형 필터 |
| `has_dialysis` | boolean | ❌ | - | 투석 가능 여부 |
| `limit` | integer | ❌ | 20 | 결과 개수 |

#### Request Example

```bash
# 시청역 근처 병원
GET /api/hospitals/nearby?latitude=37.5665&longitude=126.9780&max_distance_km=2.0&limit=10

# 근처 투석센터
GET /api/hospitals/nearby?latitude=37.5665&longitude=126.9780&has_dialysis=true&max_distance_km=5.0
```

#### Response Example

```json
{
  "success": true,
  "search_location": {
    "latitude": 37.5665,
    "longitude": 126.9780
  },
  "max_distance_km": 2.0,
  "count": 5,
  "hospitals": [
    {
      "_id": "673c5e8f9a1b2c3d4e5f6790",
      "name": "덕수한의원",
      "address": "서울특별시 중구 덕수궁길 15",
      "phone": "02-771-xxxx",
      "region": "서울",
      "type": "병원/의원",
      "dialysis_machines": 0,
      "has_dialysis_unit": false,
      "night_dialysis": false,
      "lat": 37.5658,
      "lng": 126.9752,
      "distance_km": 0.09,
      "naver_map_url": "https://map.naver.com/...",
      "kakao_map_url": "https://map.kakao.com/..."
    },
    {
      "_id": "673c5e8f9a1b2c3d4e5f6791",
      "name": "프레스치과의원",
      "address": "서울특별시 중구 남대문로 120",
      "phone": "02-752-xxxx",
      "region": "서울",
      "type": "병원/의원",
      "dialysis_machines": 0,
      "has_dialysis_unit": false,
      "night_dialysis": false,
      "lat": 37.5662,
      "lng": 126.9768,
      "distance_km": 0.10
    }
  ]
}
```

#### cURL Example

```bash
curl -X GET "http://localhost:8000/api/hospitals/nearby?latitude=37.5665&longitude=126.9780&max_distance_km=2.0&limit=10" \
  -H "accept: application/json"
```

---

### 5.4 지역 목록 조회

모든 지역 목록을 조회합니다.

#### Endpoint
```http
GET /api/hospitals/regions
```

#### Response Example

```json
{
  "success": true,
  "count": 17,
  "regions": [
    "강원", "경기", "경남", "경북", "광주", "대구", "대전",
    "부산", "서울", "세종시", "울산", "인천", "전남", "전북",
    "제주", "충남", "충북"
  ]
}
```

---

## 6. 에러 코드

### 6.1 HTTP 상태 코드

| 상태 코드 | 설명 | 예시 |
|----------|------|------|
| **200** | 성공 | 정상적인 응답 |
| **201** | 생성 성공 | 북마크 추가 |
| **400** | 잘못된 요청 | 파라미터 누락, 유효성 검증 실패 |
| **401** | 인증 필요 | JWT 토큰 없음 또는 만료 |
| **403** | 권한 없음 | 접근 권한 부족 |
| **404** | 찾을 수 없음 | 프로그램 ID 없음 |
| **422** | 유효성 검증 실패 | 파라미터 타입 오류 |
| **500** | 서버 오류 | 내부 서버 에러 |

### 6.2 에러 응답 예시

#### 400 Bad Request

```json
{
  "detail": "query 파라미터가 필요합니다",
  "status_code": 400
}
```

#### 404 Not Found

```json
{
  "detail": "프로그램을 찾을 수 없습니다 (programId: invalid_id)",
  "status_code": 404
}
```

#### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ],
  "status_code": 422
}
```

#### 500 Internal Server Error

```json
{
  "detail": "데이터베이스 연결 오류",
  "status_code": 500
}
```

---

## 7. 예제 코드

### 7.1 JavaScript/TypeScript (fetch)

```typescript
// Welfare API Client
class WelfareAPIClient {
  private baseURL: string = 'http://localhost:8000'

  // 검색
  async searchPrograms(query: string, limit: number = 10) {
    const response = await fetch(
      `${this.baseURL}/api/welfare/search?query=${encodeURIComponent(query)}&limit=${limit}`
    )

    if (!response.ok) {
      throw new Error(`Search failed: ${response.status}`)
    }

    return await response.json()
  }

  // 카테고리 목록
  async getCategories() {
    const response = await fetch(`${this.baseURL}/api/welfare/categories`)
    return await response.json()
  }

  // 카테고리별 조회
  async getProgramsByCategory(category: string, limit: number = 20) {
    const response = await fetch(
      `${this.baseURL}/api/welfare/category/${category}?limit=${limit}`
    )
    return await response.json()
  }

  // 프로그램 상세
  async getProgramDetail(programId: string) {
    const response = await fetch(`${this.baseURL}/api/welfare/${programId}`)

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('프로그램을 찾을 수 없습니다')
      }
      throw new Error(`Request failed: ${response.status}`)
    }

    return await response.json()
  }

  // 맞춤 추천 (인증 필요)
  async getRecommended(token: string, limit: number = 5) {
    const response = await fetch(
      `${this.baseURL}/api/welfare/recommend?limit=${limit}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('로그인이 필요합니다')
      }
      throw new Error(`Request failed: ${response.status}`)
    }

    return await response.json()
  }
}

// 사용 예시
const client = new WelfareAPIClient()

// 산정특례 검색
const result = await client.searchPrograms('산정특례', 5)
console.log(`검색 결과: ${result.count}개`)
result.programs.forEach((p: any) => {
  console.log(`- ${p.title}`)
})

// 카테고리별 조회
const sangjungPrograms = await client.getProgramsByCategory('sangjung_special')
console.log(`산정특례 프로그램: ${sangjungPrograms.count}개`)

// 상세 조회
const detail = await client.getProgramDetail('sangjung_ckd_v001')
console.log(`제목: ${detail.program.title}`)
console.log(`신청 장소: ${detail.program.application.application_place}`)
```

### 7.2 Python (httpx)

```python
import httpx
from typing import List, Dict, Optional

class WelfareAPIClient:
    """복지 API 클라이언트"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def search_programs(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None
    ) -> Dict:
        """복지 프로그램 검색"""
        params = {"query": query, "limit": limit}
        if category:
            params["category"] = category

        response = await self.client.get(
            f"{self.base_url}/api/welfare/search",
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def get_categories(self) -> Dict:
        """카테고리 목록"""
        response = await self.client.get(f"{self.base_url}/api/welfare/categories")
        response.raise_for_status()
        return response.json()

    async def get_programs_by_category(
        self,
        category: str,
        limit: int = 20
    ) -> Dict:
        """카테고리별 조회"""
        response = await self.client.get(
            f"{self.base_url}/api/welfare/category/{category}",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()

    async def get_program_detail(self, program_id: str) -> Dict:
        """프로그램 상세"""
        response = await self.client.get(f"{self.base_url}/api/welfare/{program_id}")
        response.raise_for_status()
        return response.json()

    async def get_recommended(self, token: str, limit: int = 5) -> Dict:
        """맞춤 추천 (인증 필요)"""
        response = await self.client.get(
            f"{self.base_url}/api/welfare/recommend",
            params={"limit": limit},
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()


# 사용 예시
async def main():
    client = WelfareAPIClient()

    try:
        # 검색
        result = await client.search_programs("산정특례", limit=5)
        print(f"검색 결과: {result['count']}개")
        for prog in result['programs']:
            print(f"- {prog['title']}")

        # 카테고리 목록
        categories = await client.get_categories()
        print(f"\n카테고리: {categories['count']}개")
        for cat in categories['categories']:
            print(f"- {cat['name']}: {cat['count']}개")

        # 상세 조회
        detail = await client.get_program_detail("sangjung_ckd_v001")
        program = detail['program']
        print(f"\n제목: {program['title']}")
        print(f"설명: {program['description']}")
        print(f"신청 장소: {program['application']['application_place']}")

    finally:
        await client.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 7.3 cURL 스크립트

```bash
#!/bin/bash

# 설정
BASE_URL="http://localhost:8000"

# 1. 복지 프로그램 검색
echo "=== 복지 프로그램 검색 ==="
curl -s "${BASE_URL}/api/welfare/search?query=산정특례&limit=5" | jq '.programs[] | {title, category_name}'

# 2. 카테고리 목록
echo -e "\n=== 카테고리 목록 ==="
curl -s "${BASE_URL}/api/welfare/categories" | jq '.categories[] | {name, count}'

# 3. 산정특례 카테고리 프로그램
echo -e "\n=== 산정특례 프로그램 ==="
curl -s "${BASE_URL}/api/welfare/category/sangjung_special" | jq '.programs[] | .title'

# 4. 프로그램 상세
echo -e "\n=== 만성콩팥병 산정특례 상세 ==="
curl -s "${BASE_URL}/api/welfare/sangjung_ckd_v001" | jq '.program | {title, description, benefits}'

# 5. 투석센터 검색
echo -e "\n=== 서울 투석센터 ==="
curl -s "${BASE_URL}/api/hospitals/dialysis?region=서울&limit=5" | jq '.dialysis_centers[] | {name, dialysis_machines}'

# 6. 근처 병원
echo -e "\n=== 시청역 근처 병원 ==="
curl -s "${BASE_URL}/api/hospitals/nearby?latitude=37.5665&longitude=126.9780&max_distance_km=1.0&limit=5" | jq '.hospitals[] | {name, distance_km}'
```

### 7.4 React Hook 예시

```typescript
// hooks/useWelfare.ts
import { useState, useEffect } from 'react'

interface WelfareProgram {
  programId: string
  title: string
  category_name: string
  description: string
  // ... 기타 필드
}

export function useWelfareSearch(query: string, limit: number = 10) {
  const [programs, setPrograms] = useState<WelfareProgram[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!query) {
      setPrograms([])
      return
    }

    const search = async () => {
      try {
        setLoading(true)
        setError(null)

        const response = await fetch(
          `http://localhost:8000/api/welfare/search?query=${encodeURIComponent(query)}&limit=${limit}`
        )

        if (!response.ok) {
          throw new Error(`Search failed: ${response.status}`)
        }

        const data = await response.json()
        setPrograms(data.programs)
      } catch (err) {
        setError(err as Error)
      } finally {
        setLoading(false)
      }
    }

    search()
  }, [query, limit])

  return { programs, loading, error }
}

// 사용
function WelfareSearchComponent() {
  const [query, setQuery] = useState('')
  const { programs, loading, error } = useWelfareSearch(query)

  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="검색어 입력"
      />

      {loading && <div>검색 중...</div>}
      {error && <div>에러: {error.message}</div>}

      <div>
        {programs.map((p) => (
          <div key={p.programId}>
            <h3>{p.title}</h3>
            <p>{p.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## 8. API 구현 코드

### 8.1 FastAPI Router

#### 파일: `backend/app/api/welfare.py`

```python
"""
복지 정보 API
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from app.db.welfare_manager import WelfareManager
from app.api.dependencies import get_current_user
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/welfare", tags=["welfare"])

# MongoDB Manager 싱글톤
_welfare_instance = None

def get_welfare_manager():
    """WelfareManager 싱글톤"""
    global _welfare_instance
    if _welfare_instance is None:
        _welfare_instance = WelfareManager()
    return _welfare_instance


@router.get("/search", response_model=Dict)
async def search_welfare(
    query: str = Query(..., description="검색어"),
    limit: int = Query(10, ge=1, le=50, description="결과 개수"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    manager: WelfareManager = Depends(get_welfare_manager)
):
    """
    복지 프로그램 검색

    텍스트 검색으로 관련 복지 프로그램을 찾습니다.

    Args:
        query: 검색어 (예: "산정특례", "장애인 등록")
        limit: 결과 개수 (1-50)
        category: 카테고리 필터 (선택)

    Returns:
        검색 결과 목록
    """
    try:
        await manager.connect()

        results = await manager.search_by_text(
            query=query,
            limit=limit,
            category=category
        )

        logger.info(f"Welfare search: query='{query}', results={len(results)}")

        return {
            "success": True,
            "count": len(results),
            "programs": results
        }

    except Exception as e:
        logger.error(f"Welfare search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories", response_model=Dict)
async def get_categories(
    manager: WelfareManager = Depends(get_welfare_manager)
):
    """
    카테고리 목록 조회

    모든 복지 카테고리와 각 카테고리별 프로그램 개수를 반환합니다.

    Returns:
        카테고리 목록
    """
    try:
        await manager.connect()

        categories = await manager.get_all_categories()

        return {
            "success": True,
            "count": len(categories),
            "categories": categories
        }

    except Exception as e:
        logger.error(f"Get categories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category/{category}", response_model=Dict)
async def get_by_category(
    category: str,
    limit: int = Query(20, ge=1, le=50),
    manager: WelfareManager = Depends(get_welfare_manager)
):
    """
    카테고리별 프로그램 조회

    특정 카테고리의 모든 복지 프로그램을 조회합니다.

    Args:
        category: 카테고리 ID
        limit: 결과 개수 (1-50)

    Returns:
        프로그램 목록
    """
    try:
        await manager.connect()

        results = await manager.search_by_category(
            category=category,
            limit=limit
        )

        logger.info(f"Category search: category='{category}', results={len(results)}")

        return {
            "success": True,
            "category": category,
            "category_name": manager.CATEGORY_NAMES.get(category, category),
            "count": len(results),
            "programs": results
        }

    except Exception as e:
        logger.error(f"Category search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{program_id}", response_model=Dict)
async def get_program(
    program_id: str,
    manager: WelfareManager = Depends(get_welfare_manager)
):
    """
    프로그램 상세 조회

    특정 복지 프로그램의 상세 정보를 조회합니다.

    Args:
        program_id: 프로그램 ID

    Returns:
        프로그램 상세 정보

    Raises:
        HTTPException 404: 프로그램을 찾을 수 없음
    """
    try:
        await manager.connect()

        result = await manager.get_by_id(program_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"프로그램을 찾을 수 없습니다 (programId: {program_id})"
            )

        logger.info(f"Program detail: programId='{program_id}'")

        return {
            "success": True,
            "program": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get program error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{program_id}/related", response_model=Dict)
async def get_related_programs(
    program_id: str,
    limit: int = Query(3, ge=1, le=10),
    manager: WelfareManager = Depends(get_welfare_manager)
):
    """
    관련 프로그램 조회

    특정 프로그램과 관련된 다른 프로그램을 조회합니다.

    Args:
        program_id: 프로그램 ID
        limit: 결과 개수 (1-10)

    Returns:
        관련 프로그램 목록
    """
    try:
        await manager.connect()

        # 기준 프로그램 조회
        base_program = await manager.get_by_id(program_id)
        if not base_program:
            raise HTTPException(
                status_code=404,
                detail=f"프로그램을 찾을 수 없습니다 (programId: {program_id})"
            )

        # 관련 프로그램 조회
        related = await manager.get_related_programs(program_id, limit=limit)

        return {
            "success": True,
            "base_program": {
                "programId": base_program["programId"],
                "title": base_program["title"]
            },
            "count": len(related),
            "related": related
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get related programs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommend", response_model=Dict)
async def get_recommended(
    limit: int = Query(5, ge=1, le=10),
    user_id: str = Depends(get_current_user),
    manager: WelfareManager = Depends(get_welfare_manager)
):
    """
    맞춤 추천 (인증 필요)

    사용자 프로필을 기반으로 복지 프로그램을 추천합니다.

    Args:
        limit: 결과 개수 (1-10)
        user_id: 사용자 ID (JWT에서 추출)

    Returns:
        추천 프로그램 목록
    """
    try:
        await manager.connect()

        # TODO: 사용자 프로필 조회
        # user = await get_user_profile(user_id)
        # user_profile = {
        #     "ckd_stage": user.ckd_stage,
        #     "is_dialysis": user.is_dialysis,
        #     "income_level": user.income_level
        # }

        # 임시로 None 사용 (우선순위순 추천)
        user_profile = None

        recommended = await manager.get_recommended(
            user_profile=user_profile,
            limit=limit
        )

        logger.info(f"Recommended programs: user={user_id}, count={len(recommended)}")

        return {
            "success": True,
            "user_profile": user_profile or {},
            "count": len(recommended),
            "recommended": recommended,
            "recommendation_reason": "사용자 프로필 기반 추천 프로그램입니다."
        }

    except Exception as e:
        logger.error(f"Get recommended error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=Dict)
async def get_stats(
    use_cache: bool = Query(True, description="캐시 사용 여부"),
    manager: WelfareManager = Depends(get_welfare_manager)
):
    """
    통계 조회

    복지 프로그램 통계를 조회합니다.

    Args:
        use_cache: 캐시 사용 여부 (기본 True)

    Returns:
        통계 정보
    """
    try:
        await manager.connect()

        stats = await manager.get_stats(use_cache=use_cache)

        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 9. Rate Limiting

### 9.1 요청 제한

현재는 Rate Limiting이 적용되지 않았습니다.

**향후 계획**:
- 검색 API: 초당 10회
- 상세 조회: 초당 20회
- 인증된 사용자: 제한 없음

---

## 10. 버전 관리

### 10.1 API 버전

현재 버전: **v1.0**

**변경 이력**:
- 2025-11-19: v1.0 초기 릴리스

### 10.2 Deprecation 정책

- API 변경 시 최소 3개월 사전 공지
- 구 버전 지원 기간: 6개월

---

## 11. 테스트 케이스

### 11.1 Postman Collection

```json
{
  "info": {
    "name": "CareGuide Welfare API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Search - 산정특례",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/api/welfare/search?query=산정특례&limit=5",
          "host": ["{{base_url}}"],
          "path": ["api", "welfare", "search"],
          "query": [
            {"key": "query", "value": "산정특례"},
            {"key": "limit", "value": "5"}
          ]
        }
      }
    },
    {
      "name": "Categories",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/api/welfare/categories",
          "host": ["{{base_url}}"],
          "path": ["api", "welfare", "categories"]
        }
      }
    },
    {
      "name": "Category - 산정특례",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/api/welfare/category/sangjung_special?limit=10",
          "host": ["{{base_url}}"],
          "path": ["api", "welfare", "category", "sangjung_special"],
          "query": [
            {"key": "limit", "value": "10"}
          ]
        }
      }
    },
    {
      "name": "Program Detail",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/api/welfare/sangjung_ckd_v001",
          "host": ["{{base_url}}"],
          "path": ["api", "welfare", "sangjung_ckd_v001"]
        }
      }
    },
    {
      "name": "Recommend (Auth)",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{jwt_token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/api/welfare/recommend?limit=5",
          "host": ["{{base_url}}"],
          "path": ["api", "welfare", "recommend"],
          "query": [
            {"key": "limit", "value": "5"}
          ]
        }
      }
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    },
    {
      "key": "jwt_token",
      "value": "YOUR_JWT_TOKEN_HERE"
    }
  ]
}
```

### 11.2 자동화 테스트

#### 파일: `tests/test_welfare_api.py`

```python
"""
Welfare API 자동화 테스트
"""

import pytest
import httpx
from typing import Dict

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_search_welfare():
    """복지 검색 테스트"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/welfare/search",
            params={"query": "산정특례", "limit": 5}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["count"] > 0
        assert len(data["programs"]) <= 5
        assert all("title" in p for p in data["programs"])

        print(f"✅ Search test passed: {data['count']} results")


@pytest.mark.asyncio
async def test_get_categories():
    """카테고리 목록 테스트"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/welfare/categories")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["count"] > 0
        assert all("name" in c and "count" in c for c in data["categories"])

        print(f"✅ Categories test passed: {data['count']} categories")


@pytest.mark.asyncio
async def test_get_by_category():
    """카테고리별 조회 테스트"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/welfare/category/sangjung_special",
            params={"limit": 10}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["category"] == "sangjung_special"
        assert data["category_name"] == "산정특례"
        assert data["count"] >= 0

        print(f"✅ Category test passed: {data['count']} programs")


@pytest.mark.asyncio
async def test_get_program_detail():
    """프로그램 상세 조회 테스트"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/welfare/sangjung_ckd_v001")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "program" in data

        program = data["program"]
        assert program["programId"] == "sangjung_ckd_v001"
        assert "title" in program
        assert "benefits" in program
        assert "application" in program

        print(f"✅ Detail test passed: {program['title']}")


@pytest.mark.asyncio
async def test_get_program_not_found():
    """존재하지 않는 프로그램 테스트"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/welfare/invalid_id_12345")

        assert response.status_code == 404
        data = response.json()

        assert "detail" in data
        assert "찾을 수 없습니다" in data["detail"]

        print(f"✅ Not found test passed")


@pytest.mark.asyncio
async def test_search_empty_result():
    """결과 없는 검색 테스트"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/welfare/search",
            params={"query": "zxcvbnmasdfghjkl", "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["count"] == 0
        assert len(data["programs"]) == 0

        print(f"✅ Empty result test passed")


if __name__ == "__main__":
    import asyncio

    async def run_all_tests():
        await test_search_welfare()
        await test_get_categories()
        await test_get_by_category()
        await test_get_program_detail()
        await test_get_program_not_found()
        await test_search_empty_result()

        print("\n" + "="*60)
        print("🎉 모든 테스트 통과!")
        print("="*60)

    asyncio.run(run_all_tests())
```

실행:
```bash
cd tests
python test_welfare_api.py
```

---

## 12. 성능 지표

### 12.1 목표 성능

| 엔드포인트 | 목표 응답 시간 | 목표 처리량 |
|-----------|--------------|-----------|
| `/api/welfare/search` | < 500ms | 100 req/s |
| `/api/welfare/categories` | < 100ms | 200 req/s |
| `/api/welfare/category/{id}` | < 300ms | 150 req/s |
| `/api/welfare/{programId}` | < 200ms | 200 req/s |
| `/api/welfare/recommend` | < 800ms | 50 req/s |

### 12.2 최적화 전략

**1. MongoDB 인덱스**:
- Text Index: 한글 검색 최적화
- Category Index: 카테고리 필터링
- Compound Index: 복합 쿼리

**2. 캐싱**:
- 통계: 1시간 TTL
- 카테고리 목록: 1시간 TTL
- 프로그램 상세: 메모리 캐시

**3. 연결 풀**:
- MongoDB 연결 풀: 10-100 connections
- 비동기 처리: Motor 사용

---

## 13. 보안

### 13.1 보안 고려사항

**1. 입력 검증**:
- Query 파라미터 길이 제한 (최대 200자)
- XSS 방지: HTML 이스케이핑
- SQL Injection 방지: MongoDB NoSQL 사용

**2. 인증**:
- JWT 토큰 검증
- 토큰 만료 시간: 24시간
- Refresh 토큰: 7일

**3. CORS**:
```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://192.168.129.32:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

---

## 14. 참고 자료

### 14.1 관련 문서
- **WELFARE_PROJECT_INDEX.md** - 프로젝트 인덱스
- **WELFARE_DETAILED_IMPLEMENTATION.md** - 상세 구현 가이드
- **EXECUTION_STATUS.md** - 프로젝트 전체 상태

### 14.2 외부 리소스
- FastAPI 문서: https://fastapi.tiangolo.com
- MongoDB Text Search: https://docs.mongodb.com/manual/text-search/
- Motor 문서: https://motor.readthedocs.io

---

## 15. 변경 로그

### v1.0 (2025-11-19)
- ✅ 초기 릴리스
- ✅ 6개 Welfare 엔드포인트
- ✅ 3개 Hospital 엔드포인트
- ✅ 15개 복지 프로그램 데이터

### 향후 계획
- [ ] v1.1: 북마크 API 추가
- [ ] v1.2: 신청 알림 기능
- [ ] v1.3: 신청 현황 추적

---

## 16. FAQ

### Q1: 인증 없이 사용 가능한 API는?
A: 검색, 카테고리, 상세 조회는 인증 없이 사용 가능합니다. 맞춤 추천만 인증이 필요합니다.

### Q2: 검색 결과 개수를 늘릴 수 있나요?
A: limit 파라미터로 최대 50개까지 조회 가능합니다.

### Q3: 캐시를 비활성화하려면?
A: `use_cache=false` 파라미터를 전달하세요.

### Q4: 지역 목록은 어디서 확인하나요?
A: `/api/hospitals/regions` 엔드포인트를 사용하세요.

### Q5: API 응답 시간이 느린 경우?
A: MongoDB 인덱스 생성 여부를 확인하세요. WelfareManager 초기화 시 자동 생성됩니다.

---

**END OF API REFERENCE**

**작성자**: Claude Code
**최종 업데이트**: 2025-11-19
**문의**: CareGuide 개발팀
