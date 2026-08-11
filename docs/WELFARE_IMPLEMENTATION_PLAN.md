# 복지 관련 검색 기능 구현 계획서

**작성일**: 2025-11-19
**출처**: EXECUTION_STATUS.md, IMPLEMENTATION_AND_TEST_PLAN.md
**현재 상태**: 병원 데이터 업로드 완료 (104,836개)

---

## 📋 복지 관련 작업 추출 요약

### 1. 문서에서 발견된 복지 관련 항목

#### EXECUTION_STATUS.md

**Section 3.1 - Journey 구현 상태**:
```
├─ ⏳ Journey 7: 복지 지원 (미착수)
```

**Section 6.1 - 의도 분류 매트릭스**:
```
WELFARE_INFO - 복지 정보 상담
```

#### IMPLEMENTATION_AND_TEST_PLAN.md

**Test Suite 2 - 의도 분류**:
```json
{
  "WELFARE_INFO": [
    "산정특례 신청 방법은?",
    "장애인 복지 혜택은?",
    "의료비 지원 받을 수 있나요?",
    // ... 기타 복지 관련 질문들
  ]
}
```

---

## 🎯 복지 검색 기능 구현 목표

### 핵심 기능
1. **복지 정보 검색** - 산정특례, 장애인 복지, 의료비 지원
2. **병원 검색 연동** - HospitalManager 활용
3. **Journey 7 구현** - 복지 지원 대화 흐름
4. **의도 분류** - WELFARE_INFO 정확한 감지

---

## 📊 현재 가용 데이터

### 1. 병원 데이터 (MongoDB - hospitals 컬렉션)
- **총 104,836개** 병원/약국/투석 시설
- **필드**:
  - name, address, phone, region, type
  - dialysis_machines, has_dialysis_unit, night_dialysis
  - lat, lng, naver_map_url, kakao_map_url

### 2. HospitalManager 기능 (backend/app/db/hospital_manager.py)
- ✅ `search_by_text()` - 텍스트 검색
- ✅ `search_by_region()` - 지역별 검색
- ✅ `search_nearby()` - 근처 병원 검색
- ✅ `get_dialysis_centers()` - 투석 병원 검색
- ✅ `get_stats()` - 통계 조회

---

## 🛠️ 구현 작업 목록

### 작업 1: 복지 정보 데이터 구축 (P1)

#### 목표
복지 제도 정보를 MongoDB에 저장하고 검색 가능하게 만들기

#### 데이터 구조

**컬렉션**: `welfare_programs`

```json
{
  "_id": "ObjectId",
  "programId": "sangjung_2024_001",
  "title": "신장질환 산정특례 제도",
  "category": "sangjung_special",  // 산정특례
  "target_disease": ["CKD", "ESRD", "dialysis"],
  "eligibility": {
    "disease_code": "V001",
    "ckd_stage": [4, 5],
    "dialysis_required": true
  },
  "benefits": {
    "copay_reduction": "90%",  // 본인부담금 10%
    "max_monthly_cap": 200000,  // 월 최대 본인부담금
    "coverage_items": ["투석", "검사", "약제"]
  },
  "application": {
    "required_documents": [
      "진단서 (희귀난치성질환 등록 신청용)",
      "검사결과지",
      "신분증"
    ],
    "application_place": "국민건강보험공단 지사",
    "processing_time": "7-14일",
    "validity_period": "5년"
  },
  "contact": {
    "phone": "1577-1000",
    "website": "https://www.nhis.or.kr",
    "online_application": true
  },
  "description": "만성콩팥병 환자의 의료비 부담을 경감하기 위한 제도...",
  "keywords": ["산정특례", "본인부담금", "의료비지원", "CKD"],
  "created_at": "2024-11-19T00:00:00Z",
  "updated_at": "2024-11-19T00:00:00Z"
}
```

#### 초기 데이터 항목 (15개)

1. **산정특례 제도** (3개)
   - 만성콩팥병 산정특례 (V001)
   - 혈액투석 산정특례
   - 복막투석 산정특례

2. **장애인 복지** (4개)
   - 신장장애 등급 기준
   - 장애인 등록 절차
   - 장애인 의료비 지원
   - 장애인 주차 스티커 발급

3. **의료비 지원** (4개)
   - 저소득층 의료비 지원 (차상위)
   - 긴급 의료비 지원
   - 재난적 의료비 지원
   - 암/희귀질환 의료비 지원

4. **이식 관련** (2개)
   - 신장이식 수술비 지원
   - 이식 대기자 등록

5. **교통 및 기타** (2개)
   - 투석 환자 교통비 지원
   - 복지카드 발급

#### 구현 스크립트

**파일**: `data/welfare/load_welfare_data.py`

```python
"""
복지 정보 데이터 로딩 스크립트
"""

from pymongo import MongoClient
from datetime import datetime

MONGODB_URI = "mongodb://appUser:asdf1234@192.168.129.32:27017/careguide?authSource=careguide"

welfare_programs = [
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
    {
        "programId": "sangjung_dialysis_v003",
        "title": "혈액투석 산정특례 제도",
        "category": "sangjung_special",
        "target_disease": ["hemodialysis", "혈액투석", "ESRD"],
        "eligibility": {
            "disease_code": "V003",
            "dialysis_type": "hemodialysis",
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
        "description": "혈액투석 환자의 투석비 본인부담금이 5%로 대폭 감면됩니다.",
        "keywords": ["산정특례", "V003", "혈액투석", "투석비지원", "본인부담금5%"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "programId": "disability_kidney",
        "title": "신장장애 등록 제도",
        "category": "disability",
        "target_disease": ["CKD", "ESRD", "dialysis", "transplant"],
        "eligibility": {
            "ckd_stage": [5],
            "dialysis_duration": "3개월 이상",
            "or_condition": "신장이식 후",
            "description": "투석 3개월 이상 또는 신장이식 후"
        },
        "benefits": {
            "disability_grade": "2급 (투석), 5급 (이식)",
            "monthly_allowance": 200000,  # 2급 기준
            "benefits_list": [
                "장애인연금 (2급)",
                "의료비 지원",
                "장애인 차량 구입 세금 감면",
                "공공시설 이용료 할인",
                "장애인 주차 스티커"
            ]
        },
        "application": {
            "required_documents": [
                "장애진단서 (신장내과 전문의)",
                "투석 기록지 (3개월)",
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
        "description": "신장기능이 저하되어 투석이나 이식이 필요한 경우 장애인으로 등록할 수 있습니다.",
        "keywords": ["장애인등록", "신장장애", "장애2급", "장애인연금", "의료비지원"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "programId": "medical_aid_low_income",
        "title": "저소득층 의료비 지원 (차상위)",
        "category": "medical_aid",
        "target_disease": ["all"],
        "eligibility": {
            "income": "기준중위소득 50% 이하",
            "description": "차상위계층 또는 기초생활수급자"
        },
        "benefits": {
            "copay_reduction": "100%",
            "copay_rate": "0-10%",
            "coverage_items": ["입원", "외래", "약제", "검사"]
        },
        "application": {
            "required_documents": [
                "의료급여 신청서",
                "소득 증빙서류",
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
    },
    {
        "programId": "transplant_support",
        "title": "신장이식 수술비 지원",
        "category": "transplant",
        "target_disease": ["ESRD", "kidney transplant"],
        "eligibility": {
            "dialysis_duration": "6개월 이상",
            "transplant_candidate": True,
            "description": "신장이식 대기자 또는 수술 예정자"
        },
        "benefits": {
            "surgery_support": "최대 3,000만원",
            "immunosuppressant_support": "월 최대 20만원",
            "duration": "평생 (면역억제제)"
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
            "renewal": "면역억제제는 지속"
        },
        "contact": {
            "phone": "02-2628-3602 (KONOS)",
            "website": "https://www.konos.go.kr",
            "online_application": True
        },
        "description": "신장이식 수술비 및 평생 복용해야 하는 면역억제제 비용을 지원합니다.",
        "keywords": ["신장이식", "수술비지원", "면역억제제", "KONOS", "이식대기자"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
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
            "usage": "투석 병원 �왕복 교통비"
        },
        "application": {
            "required_documents": [
                "교통비 지원 신청서",
                "투석 확인서",
                "소득 증빙서류",
                "통장 사본"
            ],
            "application_place": "주민센터 또는 보건소",
            "processing_time": "1개월",
            "validity_period": "1년",
            "renewal": "매년"
        },
        "contact": {
            "phone": "지역 보건소",
            "website": "각 지자체 홈페이지",
            "online_application": False
        },
        "description": "정기적으로 투석하러 병원을 다니는 환자의 교통비를 지원합니다.",
        "keywords": ["교통비지원", "투석", "혈액투석", "복막투석", "차상위"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
]

def load_welfare_data():
    """복지 데이터 MongoDB에 로딩"""
    client = MongoClient(MONGODB_URI)
    db = client["careguide"]
    collection = db["welfare_programs"]

    # 기존 데이터 삭제
    collection.delete_many({})
    print(f"기존 데이터 삭제 완료")

    # 새 데이터 삽입
    result = collection.insert_many(welfare_programs)
    print(f"✅ {len(result.inserted_ids)}개 복지 프로그램 로딩 완료")

    # 인덱스 생성
    collection.create_index("category")
    collection.create_index("keywords")
    collection.create_index([("title", "text"), ("description", "text"), ("keywords", "text")])
    print("✅ 인덱스 생성 완료")

    # 통계
    stats = collection.count_documents({})
    by_category = {}
    for program in collection.find():
        cat = program["category"]
        by_category[cat] = by_category.get(cat, 0) + 1

    print(f"\n총 {stats}개 프로그램")
    print("카테고리별:")
    for cat, count in by_category.items():
        print(f"  - {cat}: {count}개")

    client.close()

if __name__ == "__main__":
    load_welfare_data()
```

---

### 작업 2: WelfareManager 구현 (P1)

#### 목표
복지 정보 검색 및 관리 클래스 구현

#### 파일
**파일**: `backend/app/db/welfare_manager.py`

```python
"""
Welfare Programs Manager - 복지 정보 관리
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from pymongo import ASCENDING, TEXT
import logging
import time

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WelfareManager:
    """복지 정보 관리 비동기 매니저"""

    def __init__(
        self,
        uri: str = None,
        db_name: str = "careguide",
        max_pool_size: int = 100,
        min_pool_size: int = 10
    ):
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.db_name = db_name

        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.max_pool_size = max_pool_size
        self.min_pool_size = min_pool_size

        # Cache
        self._cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 3600  # 1 hour

    async def connect(self):
        """Connect to MongoDB"""
        if not self.client:
            self.client = AsyncIOMotorClient(
                self.uri,
                maxPoolSize=self.max_pool_size,
                minPoolSize=self.min_pool_size,
                maxIdleTimeMS=30000,
                waitQueueTimeoutMS=5000,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=2000,
                socketTimeoutMS=10000
            )
            self.db = self.client[self.db_name]

            await self.create_indexes()

            logger.info(f"✅ Welfare Manager connected: {self.db_name}")

    async def close(self):
        """Close connection"""
        if self.client:
            self.client.close()
            logger.info("Welfare Manager connection closed")

    async def create_indexes(self):
        """Create indexes"""
        collection = self.db.welfare_programs

        indexes = [
            ([("category", ASCENDING)], {"name": "category_idx"}),
            ([("title", TEXT), ("description", TEXT), ("keywords", TEXT)], {"name": "welfare_text_search"}),
        ]

        for index_spec, index_options in indexes:
            try:
                await collection.create_index(index_spec, **index_options)
                logger.info(f"✅ Created index {index_options['name']} on welfare_programs")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"⚠️ Index creation failed: {e}")

    # ==================== Search Methods ====================

    async def search_by_text(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict]:
        """텍스트 검색"""
        start_time = time.time()

        projection = {
            "score": {"$meta": "textScore"},
            "programId": 1,
            "title": 1,
            "category": 1,
            "description": 1,
            "benefits": 1,
            "application": 1,
            "contact": 1,
            "keywords": 1,
            "_id": 1
        }

        cursor = self.db.welfare_programs.find(
            {"$text": {"$search": query}},
            projection
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)

        results = await cursor.to_list(length=limit)

        elapsed = time.time() - start_time
        logger.debug(f"Welfare search completed in {elapsed:.3f}s ({len(results)} results)")

        return results

    async def search_by_category(
        self,
        category: str,
        limit: int = 20
    ) -> List[Dict]:
        """카테고리별 검색"""
        query = {"category": category}

        cursor = self.db.welfare_programs.find(query).limit(limit)
        results = await cursor.to_list(length=limit)

        return results

    async def get_by_id(self, program_id: str) -> Optional[Dict]:
        """ID로 프로그램 조회"""
        result = await self.db.welfare_programs.find_one({"programId": program_id})
        return result

    async def get_all_categories(self) -> List[str]:
        """모든 카테고리 목록"""
        categories = await self.db.welfare_programs.distinct("category")
        return sorted(categories)

    async def get_stats(self) -> Dict:
        """통계 조회"""
        pipeline = [
            {
                "$facet": {
                    "total": [{"$count": "count"}],
                    "by_category": [
                        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}}
                    ]
                }
            }
        ]

        cursor = self.db.welfare_programs.aggregate(pipeline)
        results = await cursor.to_list(length=1)

        if results:
            data = results[0]
            return {
                "total": data["total"][0]["count"] if data["total"] else 0,
                "by_category": {item["_id"]: item["count"] for item in data["by_category"]}
            }

        return {}


# Test
async def test_welfare_manager():
    import asyncio

    print("\n" + "="*80)
    print("WELFARE MANAGER TEST")
    print("="*80)

    manager = WelfareManager()
    await manager.connect()

    # 통계
    stats = await manager.get_stats()
    print(f"\n총 복지 프로그램: {stats.get('total', 0)}")

    # 텍스트 검색
    results = await manager.search_by_text("산정특례", limit=3)
    print(f"\n'산정특례' 검색 결과: {len(results)}개")
    for prog in results:
        print(f"  - {prog['title']}")

    # 카테고리별 검색
    categories = await manager.get_all_categories()
    print(f"\n카테고리: {', '.join(categories)}")

    await manager.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_welfare_manager())
```

---

### 작업 3: Journey 7 (복지 지원) 구현 (P2)

#### 목표
복지 정보 상담 Journey 구현

**파일**: `backend/Agent/research_paper/server/healthcare_v2_en.py`

**함수**: `create_welfare_support_journey()`

```python
async def create_welfare_support_journey(server: p.ServerContext) -> p.Journey:
    """복지 지원 Journey

    - 산정특례 안내
    - 장애인 등록 안내
    - 의료비 지원 안내
    - 신장이식 지원 안내
    - 교통비 지원 안내
    """
    journey = await server.create_journey(
        title="Welfare Support Journey",
        description="Guide for welfare benefits and support programs"
    )

    # State 1: Welcome
    welcome = journey.initial_state.chat(
        action="""복지 지원 상담에 오신 것을 환영합니다! 🎗️

다음 분야의 복지 혜택을 안내해드립니다:

1. 💳 **산정특례** - 본인부담금 감면
2. 🦽 **장애인 등록** - 장애인 복지 혜택
3. 💰 **의료비 지원** - 저소득층 의료비
4. 🏥 **신장이식 지원** - 수술비 및 면역억제제
5. 🚗 **교통비 지원** - 투석 환자 교통비

어떤 복지 혜택에 대해 궁금하신가요?"""
    )

    # Fork: Category selection
    fork_category = fork(action="Determine which welfare category user is interested in")

    # Option 1: 산정특례
    sangjung = fork_category.chat(
        action="""💳 **산정특례 제도 안내**

산정특례는 희귀난치성질환 환자의 의료비 부담을 줄여주는 제도입니다.

**만성콩팥병 산정특례 (V001)**:
- 본인부담금: 10% (90% 감면)
- 대상: CKD 3기 이상, eGFR 60 미만
- 유효기간: 5년

**혈액투석 산정특례 (V003)**:
- 본인부담금: 5% (95% 감면)
- 대상: 정기 혈액투석 환자
- 유효기간: 투석 중단 시까지

**신청 방법**:
1. 병원에서 진단서 발급
2. 국민건강보험공단 또는 병원 원무과 신청
3. 7-14일 후 승인

**필요 서류**:
- 산정특례 등록 신청서
- 의사 진단서
- 검사결과지 (eGFR, 크레아티닌)
- 신분증

**문의**: 1577-1000 (국민건강보험공단)

다른 복지 혜택도 알아보시겠습니까?""",
        condition="User asks about 산정특례 or copay reduction",
        tools=["search_medical_qa"]
    )

    # Option 2: 장애인 등록
    disability = fork_category.chat(
        action="""🦽 **신장장애 등록 안내**

투석 또는 이식 환자는 장애인으로 등록할 수 있습니다.

**장애 등급**:
- 혈액투석/복막투석 3개월 이상: **2급**
- 신장이식 후: **5급**

**장애인 혜택 (2급 기준)**:
- 💰 장애인연금: 월 약 20만원
- 💊 의료비 지원
- 🚗 장애인 차량 세금 감면
- 🅿️ 장애인 주차 스티커
- 🎫 공공시설 할인

**신청 방법**:
1. 신장내과 전문의 장애진단서 발급
2. 투석 기록지 준비 (3개월분)
3. 주민센터 신청
4. 1-2개월 후 승인

**필요 서류**:
- 장애진단서
- 투석 기록지 (3개월)
- 신분증
- 사진 2장

**문의**: 국번없이 129 (보건복지콜센터)

다른 복지 혜택도 알아보시겠습니까?""",
        condition="User asks about disability registration",
        tools=["search_medical_qa"]
    )

    # Option 3: 의료비 지원
    medical_aid = fork_category.chat(
        action="""💰 **의료비 지원 제도 안내**

저소득층 만성질환자를 위한 의료비 지원입니다.

**차상위 의료급여**:
- 대상: 기준중위소득 50% 이하
- 본인부담금: 0-10%
- 적용: 입원, 외래, 약제, 검사

**재난적 의료비 지원**:
- 대상: 의료비가 소득의 일정 비율 초과
- 지원: 최대 2,000만원
- 적용: 입원비, 수술비

**긴급 의료비 지원**:
- 대상: 위기상황 가구
- 지원: 최대 300만원
- 적용: 생명·신체 위협 상황

**신청 방법**:
1. 주민센터 방문
2. 소득 증빙서류 제출
3. 1개월 후 승인

**필요 서류**:
- 신청서
- 소득 증빙서류
- 진단서 (해당 시)
- 신분증

**문의**: 국번없이 129 또는 복지로(bokjiro.go.kr)

다른 복지 혜택도 알아보시겠습니까?""",
        condition="User asks about medical aid or financial support",
        tools=["search_medical_qa"]
    )

    # Option 4: 신장이식 지원
    transplant = fork_category.chat(
        action="""🏥 **신장이식 지원 안내**

신장이식 수술비 및 평생 복용하는 면역억제제를 지원합니다.

**수술비 지원**:
- 금액: 최대 3,000만원
- 대상: 신장이식 대기자 또는 수술 예정자
- 조건: 투석 6개월 이상

**면역억제제 지원**:
- 금액: 월 최대 20만원
- 기간: 평생 (이식 후)
- 적용: 면역억제제 약제비

**이식 대기 등록**:
- 기관: 국립장기조직혈액관리원 (KONOS)
- 방법: 이식 병원에서 등록
- 비용: 무료

**신청 방법**:
1. KONOS 이식 대기자 등록
2. 지원 신청서 제출
3. 수술 전후 6개월 지원

**필요 서류**:
- 이식 대기자 등록증
- 의사 소견서
- 소득 증빙서류
- 신분증

**문의**: 02-2628-3602 (KONOS)
**웹사이트**: konos.go.kr

다른 복지 혜택도 알아보시겠습니까?""",
        condition="User asks about transplant support",
        tools=["search_medical_qa"]
    )

    # Option 5: 교통비 지원
    transport = fork_category.chat(
        action="""🚗 **투석 환자 교통비 지원 안내**

정기적으로 투석하러 다니는 환자의 교통비를 지원합니다.

**지원 내용**:
- 금액: 월 15만원
- 용도: 투석 병원 왕복 교통비
- 대상: 정기 투석 환자 (혈액/복막)
- 조건: 기준중위소득 120% 이하

**신청 방법**:
1. 주민센터 또는 보건소 방문
2. 신청서 및 서류 제출
3. 1개월 후 승인
4. 매년 갱신 필요

**필요 서류**:
- 교통비 지원 신청서
- 투석 확인서 (병원 발급)
- 소득 증빙서류
- 통장 사본

**문의**: 지역 보건소 또는 주민센터

**참고**: 지자체마다 지원 금액과 조건이 다를 수 있습니다.

다른 복지 혜택도 알아보시겠습니까?""",
        condition="User asks about transport support",
        tools=["search_medical_qa"]
    )

    # End
    end = fork_category.chat(
        action="""감사합니다! 복지 지원 상담을 종료합니다.

**추가 문의**:
- 국민건강보험공단: 1577-1000
- 보건복지콜센터: 국번없이 129
- 복지로: bokjiro.go.kr

건강하세요! 🍀""",
        condition="User wants to end the session"
    )

    return journey
```

---

### 작업 4: Welfare API 엔드포인트 (P2)

#### 목표
프론트엔드에서 복지 정보 검색 API 제공

**파일**: `backend/app/api/welfare.py`

```python
"""
복지 정보 API
"""

from fastapi import APIRouter, Query
from app.db.welfare_manager import WelfareManager
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/welfare", tags=["welfare"])

_welfare_instance = None

def get_welfare_manager():
    global _welfare_instance
    if _welfare_instance is None:
        _welfare_instance = WelfareManager()
    return _welfare_instance

@router.get("/search", response_model=List[Dict])
async def search_welfare(
    query: str = Query(..., description="검색어"),
    limit: int = Query(10, ge=1, le=50)
):
    """복지 정보 검색"""
    manager = get_welfare_manager()
    await manager.connect()

    results = await manager.search_by_text(query, limit=limit)

    return results

@router.get("/categories", response_model=List[str])
async def get_categories():
    """카테고리 목록"""
    manager = get_welfare_manager()
    await manager.connect()

    categories = await manager.get_all_categories()

    return categories

@router.get("/category/{category}", response_model=List[Dict])
async def get_by_category(
    category: str,
    limit: int = Query(20, ge=1, le=50)
):
    """카테고리별 조회"""
    manager = get_welfare_manager()
    await manager.connect()

    results = await manager.search_by_category(category, limit=limit)

    return results

@router.get("/{program_id}", response_model=Dict)
async def get_program(program_id: str):
    """프로그램 상세"""
    manager = get_welfare_manager()
    await manager.connect()

    result = await manager.get_by_id(program_id)

    if not result:
        raise HTTPException(status_code=404, detail="Program not found")

    return result
```

**main.py에 등록**:
```python
from app.api import welfare

app.include_router(welfare.router)
```

---

## 📅 구현 일정

| 작업 | 예상 시간 | 우선순위 |
|------|----------|---------|
| 복지 데이터 구축 | 2시간 | P1 |
| WelfareManager 구현 | 3시간 | P1 |
| Journey 7 구현 | 2시간 | P2 |
| Welfare API 구현 | 1시간 | P2 |
| 테스트 | 2시간 | P1 |

**총 예상 시간**: 10시간 (2일)

---

## ✅ 완료 기준

- [ ] 복지 데이터 6개 이상 MongoDB 로딩
- [ ] WelfareManager 구현 및 테스트
- [ ] Journey 7 구현
- [ ] Welfare API 4개 엔드포인트 작동
- [ ] 의도 분류 "WELFARE_INFO" 정확도 90% 이상

---

**END OF DOCUMENT**
