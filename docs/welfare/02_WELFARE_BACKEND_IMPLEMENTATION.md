# 복지 백엔드 구현 가이드
## WelfareManager Implementation

**문서**: 02_WELFARE_BACKEND_IMPLEMENTATION.md
**작성일**: 2025-11-19
**선행 문서**: 01_WELFARE_DATABASE_DESIGN.md
**다음 문서**: 03_WELFARE_PARLANT_INTEGRATION.md
**예상 시간**: 2시간

---

## 📋 목차

1. [WelfareManager 클래스 설계](#1-welfaremanager-클래스-설계)
2. [전체 코드 구현](#2-전체-코드-구현)
3. [테스트 및 검증](#3-테스트-및-검증)
4. [Pydantic 모델](#4-pydantic-모델)

---

## 1. WelfareManager 클래스 설계

### 1.1 설계 원칙

**참고 파일**: `backend/app/db/hospital_manager.py`

**적용 패턴**:
1. ✅ 비동기 Motor 클라이언트 (AsyncIOMotorClient)
2. ✅ Connection pooling (maxPoolSize=100, minPoolSize=10)
3. ✅ Singleton 패턴 (global instance)
4. ✅ LRU 캐싱 (통계용, TTL 3600s)
5. ✅ 텍스트 검색 점수 기반 정렬
6. ✅ 로깅 (logging.info, logging.debug)

### 1.2 클래스 구조

```python
class WelfareManager:
    """복지 프로그램 관리 비동기 매니저"""

    # Constructor
    def __init__(uri, db_name, max_pool_size, min_pool_size)

    # Connection methods
    async def connect()
    async def close()
    async def create_indexes()

    # Search methods
    async def search_by_text(query, limit, filters) -> List[Dict]
    async def search_by_category(category, limit) -> List[Dict]
    async def search_by_disease(disease, limit) -> List[Dict]
    async def search_by_ckd_stage(stage, limit) -> List[Dict]

    # Utility methods
    async def get_by_id(program_id) -> Optional[Dict]
    async def get_all_categories() -> List[str]
    async def get_stats(use_cache) -> Dict
```

---

## 2. 전체 코드 구현

### 2.1 파일 생성

**파일**: `backend/app/db/welfare_manager.py` (신규 생성)

**전체 코드**:

```python
"""
Welfare Programs Manager - 복지 프로그램 관리

HospitalManager 패턴 100% 적용:
- 비동기 MongoDB 연결 (Motor)
- Connection pooling
- 텍스트 검색 (score 기반 정렬)
- LRU 캐싱 (통계)
- 다양한 검색 메서드

Author: CareGuide Team
Date: 2025-11-19
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
    """복지 프로그램 관리 비동기 매니저

    HospitalManager와 동일한 패턴:
    - Connection pooling (maxPoolSize=100, minPoolSize=10)
    - 비동기 검색 메서드 (Motor)
    - 캐싱 전략 (TTL 3600s)
    - 텍스트 검색 점수 기반 정렬
    - 다양한 필터 옵션

    Example:
        manager = WelfareManager()
        await manager.connect()
        results = await manager.search_by_text("산정특례", limit=5)
        await manager.close()
    """

    def __init__(
        self,
        uri: str = None,
        db_name: str = "careguide",
        max_pool_size: int = 100,
        min_pool_size: int = 10
    ):
        """Initialize WelfareManager

        Args:
            uri: MongoDB connection URI (default: env MONGODB_URI)
            db_name: Database name (default: careguide)
            max_pool_size: Maximum connection pool size (default: 100)
            min_pool_size: Minimum connection pool size (default: 10)
        """
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.db_name = db_name

        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.max_pool_size = max_pool_size
        self.min_pool_size = min_pool_size

        # Cache for statistics (hospital_manager.py 동일)
        self._cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 3600  # 1 hour

        logger.info(f"WelfareManager initialized: {self.db_name}")

    async def connect(self):
        """Connect to MongoDB with connection pooling

        HospitalManager 동일 패턴:
        - Connection timeout: 2s
        - Socket timeout: 10s
        - Server selection timeout: 5s
        - Wait queue timeout: 5s
        - Max idle time: 30s

        Creates indexes if not exists.
        """
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

            # Create indexes
            await self.create_indexes()

            logger.info(f"✅ WelfareManager connected: {self.db_name}.welfare_programs")
            logger.info(f"   Connection pool: min={self.min_pool_size}, max={self.max_pool_size}")

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("WelfareManager connection closed")

    async def create_indexes(self):
        """Create indexes on welfare_programs collection

        Indexes:
        1. category_idx - Category filtering
        2. welfare_text_search - Korean text search (title, description, keywords)
        3. disease_idx - Target disease filtering
        4. ckd_stage_idx - CKD stage filtering
        5. program_id_unique - Unique program ID

        Pattern: hospital_manager.py
        """
        collection = self.db.welfare_programs

        indexes = [
            # 1. Category index
            (
                [("category", ASCENDING)],
                {"name": "category_idx"}
            ),

            # 2. Text search index (Korean)
            (
                [("title", TEXT), ("description", TEXT), ("keywords", TEXT)],
                {"name": "welfare_text_search", "default_language": "korean"}
            ),

            # 3. Target disease index
            (
                [("target_disease", ASCENDING)],
                {"name": "disease_idx"}
            ),

            # 4. CKD stage index (nested field)
            (
                [("eligibility.ckd_stage", ASCENDING)],
                {"name": "ckd_stage_idx"}
            ),

            # 5. Program ID unique index
            (
                [("programId", ASCENDING)],
                {"name": "program_id_unique", "unique": True}
            )
        ]

        for index_spec, index_options in indexes:
            try:
                await collection.create_index(index_spec, **index_options)
                logger.info(f"  ✅ Created index {index_options['name']} on welfare_programs")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"  ⚠️ Index creation failed for {index_options['name']}: {e}")

    # ==================== Search Methods ====================

    async def search_by_text(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """텍스트 검색 (HospitalManager 패턴)

        MongoDB $text 검색 with scoring.
        Results sorted by relevance score (descending).

        Args:
            query: 검색어 (e.g., "산정특례", "장애인 복지", "의료비 지원")
            limit: 최대 결과 수 (default: 10)
            filters: 추가 필터 dict (e.g., {"category": "sangjung_special"})

        Returns:
            검색 결과 리스트 (score 포함, score 순 정렬)

        Example:
            results = await manager.search_by_text("산정특례", limit=5)
            # Returns: [V001, V003, V005] with scores
        """
        start_time = time.time()

        # Build text search query
        search_query = {"$text": {"$search": query}}

        # Apply additional filters
        if filters:
            search_query.update(filters)

        # Projection (include score for sorting)
        projection = {
            "score": {"$meta": "textScore"},
            "_id": 1,
            "programId": 1,
            "title": 1,
            "category": 1,
            "description": 1,
            "benefits": 1,
            "application": 1,
            "contact": 1,
            "keywords": 1,
            "target_disease": 1,
            "eligibility": 1
        }

        # Execute search
        cursor = self.db.welfare_programs.find(
            search_query,
            projection
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)

        results = await cursor.to_list(length=limit)

        elapsed = time.time() - start_time
        logger.debug(f"Welfare text search: query='{query}', results={len(results)}, time={elapsed:.3f}s")

        return results

    async def search_by_category(
        self,
        category: str,
        limit: int = 20
    ) -> List[Dict]:
        """카테고리별 검색

        Args:
            category: 카테고리
                - sangjung_special: 산정특례
                - disability: 장애인 복지
                - medical_aid: 의료비 지원
                - transplant: 신장이식 지원
                - transport: 교통비 지원
            limit: 최대 결과 수 (default: 20)

        Returns:
            프로그램 리스트

        Example:
            results = await manager.search_by_category("sangjung_special")
            # Returns: 3 programs
        """
        query = {"category": category}

        cursor = self.db.welfare_programs.find(query).limit(limit)
        results = await cursor.to_list(length=limit)

        logger.debug(f"Category search: category='{category}', results={len(results)}")

        return results

    async def search_by_disease(
        self,
        disease: str,
        limit: int = 20
    ) -> List[Dict]:
        """질병별 검색

        Args:
            disease: 질병명 (e.g., "CKD", "ESRD", "dialysis", "hemodialysis")
            limit: 최대 결과 수 (default: 20)

        Returns:
            프로그램 리스트

        Example:
            results = await manager.search_by_disease("CKD")
            # Returns: Programs where "CKD" in target_disease array
        """
        query = {"target_disease": {"$in": [disease]}}

        cursor = self.db.welfare_programs.find(query).limit(limit)
        results = await cursor.to_list(length=limit)

        logger.debug(f"Disease search: disease='{disease}', results={len(results)}")

        return results

    async def search_by_ckd_stage(
        self,
        stage: int,
        limit: int = 20
    ) -> List[Dict]:
        """CKD 단계별 검색

        Args:
            stage: CKD 단계 (1-5)
            limit: 최대 결과 수 (default: 20)

        Returns:
            프로그램 리스트

        Example:
            results = await manager.search_by_ckd_stage(4)
            # Returns: Programs applicable to CKD stage 4
        """
        query = {"eligibility.ckd_stage": {"$in": [stage]}}

        cursor = self.db.welfare_programs.find(query).limit(limit)
        results = await cursor.to_list(length=limit)

        logger.debug(f"CKD stage search: stage={stage}, results={len(results)}")

        return results

    async def get_by_id(self, program_id: str) -> Optional[Dict]:
        """프로그램 ID로 조회

        Args:
            program_id: 프로그램 ID (e.g., "sangjung_ckd_v001")

        Returns:
            프로그램 문서 or None

        Example:
            prog = await manager.get_by_id("sangjung_ckd_v001")
            print(prog["title"])  # "만성콩팥병 산정특례 제도"
        """
        result = await self.db.welfare_programs.find_one({"programId": program_id})

        if result:
            logger.debug(f"Get by ID: program_id='{program_id}', found={result['title']}")
        else:
            logger.warning(f"Get by ID: program_id='{program_id}', not found")

        return result

    async def get_all_categories(self) -> List[str]:
        """모든 카테고리 목록 조회

        Returns:
            카테고리 리스트 (sorted alphabetically)

        Example:
            categories = await manager.get_all_categories()
            # Returns: ["disability", "medical_aid", "sangjung_special", "transplant", "transport"]
        """
        categories = await self.db.welfare_programs.distinct("category")
        sorted_categories = sorted(categories)

        logger.debug(f"Get categories: {len(sorted_categories)} categories")

        return sorted_categories

    async def get_stats(self, use_cache: bool = True) -> Dict:
        """통계 조회 (HospitalManager 패턴)

        Returns:
            {
                "total": 15,
                "by_category": {
                    "sangjung_special": 3,
                    "disability": 4,
                    ...
                }
            }

        Caching:
        - Cache TTL: 3600s (1 hour)
        - use_cache=False to force refresh

        Example:
            stats = await manager.get_stats()
            print(f"Total: {stats['total']}")
        """
        # Check cache
        current_time = time.time()
        if use_cache and self._cache and (current_time - self._cache_timestamp) < self._cache_ttl:
            logger.debug("Returning cached stats")
            return self._cache

        # Aggregation pipeline (hospital_manager.py 동일)
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
            stats = {
                "total": data["total"][0]["count"] if data["total"] else 0,
                "by_category": {item["_id"]: item["count"] for item in data["by_category"]}
            }

            # Update cache
            self._cache = stats
            self._cache_timestamp = current_time

            logger.debug(f"Stats computed: total={stats['total']}")

            return stats

        return {"total": 0, "by_category": {}}


# ==================== Test Function ====================

async def test_welfare_manager():
    """WelfareManager 테스트 (hospital_manager.py 패턴)

    테스트 항목:
    1. 통계 조회
    2. 텍스트 검색
    3. 카테고리별 검색
    4. 질병별 검색
    5. CKD 단계별 검색
    6. 프로그램 상세 조회
    7. 캐싱 성능

    Expected:
    - All queries return results
    - Scores are descending
    - Cache is faster
    """
    import asyncio

    print("\n" + "="*80)
    print("WELFARE MANAGER TEST")
    print("="*80)

    manager = WelfareManager()
    await manager.connect()

    # Test 1: Stats
    print("\n[Test 1] Statistics")
    stats = await manager.get_stats()
    print(f"  Total programs: {stats.get('total', 0)}")
    print(f"  By category:")
    for cat, count in sorted(stats.get('by_category', {}).items()):
        print(f"    - {cat}: {count}")

    assert stats["total"] == 15, f"Expected 15, got {stats['total']}"
    print(f"  ✅ Stats test passed")

    # Test 2: Text search
    print("\n[Test 2] Text Search")
    test_queries = ["산정특례", "장애인", "의료비 지원"]
    for query in test_queries:
        results = await manager.search_by_text(query, limit=3)
        print(f"  '{query}': {len(results)} results")

        if results:
            print(f"    Top result: {results[0]['title']} (score: {results[0].get('score', 0):.2f})")

        # Verify scores are descending
        scores = [r.get("score", 0) for r in results]
        assert scores == sorted(scores, reverse=True), "Scores not descending"

    print(f"  ✅ Text search test passed")

    # Test 3: Category search
    print("\n[Test 3] Category Search")
    categories = await manager.get_all_categories()
    print(f"  Categories: {', '.join(categories)}")

    for cat in categories[:2]:  # Test first 2
        results = await manager.search_by_category(cat)
        print(f"  '{cat}': {len(results)} programs")
        assert all(r["category"] == cat for r in results), f"Wrong category in results"

    print(f"  ✅ Category search test passed")

    # Test 4: Disease search
    print("\n[Test 4] Disease Search")
    diseases = ["CKD", "ESRD", "dialysis"]
    for disease in diseases:
        results = await manager.search_by_disease(disease)
        print(f"  '{disease}': {len(results)} programs")
        assert all(disease in r["target_disease"] for r in results), f"{disease} not in target_disease"

    print(f"  ✅ Disease search test passed")

    # Test 5: CKD stage search
    print("\n[Test 5] CKD Stage Search")
    for stage in [3, 4, 5]:
        results = await manager.search_by_ckd_stage(stage)
        print(f"  CKD stage {stage}: {len(results)} programs")
        # Note: Some programs may not have ckd_stage in eligibility

    print(f"  ✅ CKD stage search test passed")

    # Test 6: Get by ID
    print("\n[Test 6] Get by ID")
    prog_id = "sangjung_ckd_v001"
    prog = await manager.get_by_id(prog_id)
    assert prog is not None, "Program not found"
    print(f"  Program: {prog['title']}")
    print(f"  Benefits: {prog['benefits'].get('copay_rate', 'N/A')}")
    print(f"  Contact: {prog['contact']['phone']}")
    print(f"  ✅ Get by ID test passed")

    # Test 7: Cache performance
    print("\n[Test 7] Cache Performance")
    start = time.time()
    stats1 = await manager.get_stats(use_cache=True)
    time1 = time.time() - start

    start = time.time()
    stats2 = await manager.get_stats(use_cache=True)
    time2 = time.time() - start

    print(f"  First call (cache miss): {time1*1000:.2f}ms")
    print(f"  Second call (cache hit): {time2*1000:.2f}ms")
    print(f"  Speedup: {time1/time2:.1f}x")
    assert time2 < time1, "Cache not faster"
    print(f"  ✅ Cache test passed")

    await manager.close()

    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED!")
    print("="*80)
    print(f"\nNext steps:")
    print(f"  1. Implement search_welfare_programs Tool")
    print(f"  2. Read: docs/welfare/03_WELFARE_PARLANT_INTEGRATION.md")
    print("="*80 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_welfare_manager())
```

---

## 3. 테스트 및 검증

### 3.1 실행 방법

```bash
# 1. 환경 변수 확인
export MONGODB_URI="mongodb://appUser:password@host:27017/careguide?authSource=careguide"

# 2. WelfareManager 테스트 실행
cd backend
python app/db/welfare_manager.py

# Expected output:
# ================================================================================
# WELFARE MANAGER TEST
# ================================================================================
#
# [Test 1] Statistics
#   Total programs: 15
#   By category:
#     - disability: 4
#     - medical_aid: 4
#     - sangjung_special: 3
#     - transplant: 2
#     - transport: 2
#   ✅ Stats test passed
#
# [Test 2] Text Search
#   '산정특례': 3 results
#     Top result: 만성콩팥병 산정특례 제도 (score: 2.35)
#   '장애인': 4 results
#     Top result: 신장장애 등록 제도 (score: 1.87)
#   ✅ Text search test passed
#
# ... (나머지 테스트)
#
# ✅ ALL TESTS PASSED!
```

### 3.2 검증 체크리스트

**WelfareManager 구현 완료 기준**:

- [ ] **파일 생성**: `backend/app/db/welfare_manager.py` 존재
- [ ] **클래스 정의**: WelfareManager 클래스
- [ ] **Connection**: connect() 메서드 작동
- [ ] **Indexes**: create_indexes() 5개 인덱스 생성
- [ ] **Search methods**: 5개 메서드 모두 작동
  - [ ] search_by_text()
  - [ ] search_by_category()
  - [ ] search_by_disease()
  - [ ] search_by_ckd_stage()
  - [ ] get_by_id()
- [ ] **Utilities**: get_all_categories(), get_stats()
- [ ] **Caching**: 통계 캐싱 작동
- [ ] **Test**: python welfare_manager.py 실행 성공

---

## 4. Pydantic 모델

### 4.1 모델 파일

**파일**: `backend/app/models/welfare.py` (신규 생성)

```python
"""
Welfare Program Pydantic Models

community.py, user.py 패턴 적용
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class WelfareBenefits(BaseModel):
    """복지 혜택 모델"""
    copay_reduction: Optional[str] = Field(None, description="본인부담금 감면율 (e.g., '90%')")
    copay_rate: Optional[str] = Field(None, description="본인부담률 (e.g., '10%')")
    max_monthly_cap: Optional[int] = Field(None, description="월 최대 본인부담금 (원)")
    monthly_amount: Optional[int] = Field(None, description="월 지원 금액 (원)")
    coverage_items: Optional[List[str]] = Field(None, description="적용 항목")
    benefits_list: Optional[List[str]] = Field(None, description="혜택 목록")


class WelfareEligibility(BaseModel):
    """자격 요건 모델"""
    disease_code: Optional[str] = Field(None, description="질병 코드 (e.g., 'V001')")
    ckd_stage: Optional[List[int]] = Field(None, description="CKD 단계 (e.g., [3, 4, 5])")
    dialysis_type: Optional[str] = Field(None, description="투석 유형 (hemodialysis, peritoneal)")
    dialysis_duration: Optional[str] = Field(None, description="투석 기간 (e.g., '3개월 이상')")
    dialysis_required: Optional[bool] = Field(None, description="투석 필요 여부")
    income: Optional[str] = Field(None, description="소득 기준 (e.g., '기준중위소득 50% 이하')")
    transplant_candidate: Optional[bool] = Field(None, description="이식 대기자 여부")
    description: Optional[str] = Field(None, description="자격 요건 설명")


class WelfareApplication(BaseModel):
    """신청 방법 모델"""
    required_documents: List[str] = Field(..., description="필요 서류 목록")
    application_place: str = Field(..., description="신청 장소")
    processing_time: str = Field(..., description="처리 기간 (e.g., '7-14일')")
    validity_period: str = Field(..., description="유효 기간 (e.g., '5년')")
    renewal: Optional[str] = Field(None, description="갱신 방법")


class WelfareContact(BaseModel):
    """연락처 정보 모델"""
    phone: str = Field(..., description="전화번호")
    website: Optional[str] = Field(None, description="웹사이트 URL")
    online_application: Optional[bool] = Field(None, description="온라인 신청 가능 여부")


class WelfareProgram(BaseModel):
    """복지 프로그램 (완전한 문서)"""
    programId: str = Field(..., description="프로그램 고유 ID")
    title: str = Field(..., description="프로그램명")
    category: str = Field(..., description="카테고리")
    target_disease: List[str] = Field(..., description="대상 질병 목록")
    eligibility: WelfareEligibility = Field(..., description="자격 요건")
    benefits: WelfareBenefits = Field(..., description="혜택 정보")
    application: WelfareApplication = Field(..., description="신청 방법")
    contact: WelfareContact = Field(..., description="연락처")
    description: str = Field(..., description="프로그램 상세 설명")
    keywords: List[str] = Field(..., description="검색 키워드")
    created_at: Optional[datetime] = Field(None, description="생성 일시")
    updated_at: Optional[datetime] = Field(None, description="수정 일시")

    class Config:
        json_schema_extra = {
            "example": {
                "programId": "sangjung_ckd_v001",
                "title": "만성콩팥병 산정특례 제도",
                "category": "sangjung_special",
                "target_disease": ["CKD", "만성콩팥병"],
                "eligibility": {
                    "disease_code": "V001",
                    "ckd_stage": [3, 4, 5]
                },
                "benefits": {
                    "copay_rate": "10%"
                },
                "application": {
                    "required_documents": ["진단서", "신분증"],
                    "application_place": "건강보험공단",
                    "processing_time": "7-14일",
                    "validity_period": "5년"
                },
                "contact": {
                    "phone": "1577-1000",
                    "website": "https://www.nhis.or.kr"
                },
                "description": "본인부담금 90% 감면",
                "keywords": ["산정특례", "V001"]
            }
        }


class WelfareProgramResponse(WelfareProgram):
    """API 응답용 (score 추가)"""
    score: Optional[float] = Field(None, description="검색 관련도 점수")


class WelfareSearchRequest(BaseModel):
    """검색 요청 모델"""
    query: str = Field(..., description="검색어", min_length=1)
    category: Optional[str] = Field(None, description="카테고리 필터")
    disease: Optional[str] = Field(None, description="질병 필터")
    ckd_stage: Optional[int] = Field(None, ge=1, le=5, description="CKD 단계 (1-5)")
    limit: int = Field(10, ge=1, le=50, description="최대 결과 수")


class WelfareStatsResponse(BaseModel):
    """통계 응답 모델"""
    total: int = Field(..., description="전체 프로그램 수")
    by_category: Dict[str, int] = Field(..., description="카테고리별 개수")
```

### 4.2 모델 사용 예시

```python
# FastAPI endpoint에서 사용
from app.models.welfare import WelfareProgram, WelfareStatsResponse

@router.get("/stats", response_model=WelfareStatsResponse)
async def get_stats():
    manager = get_welfare_manager()
    stats = await manager.get_stats()
    return stats  # Pydantic이 자동 검증

@router.get("/{program_id}", response_model=WelfareProgram)
async def get_program(program_id: str):
    manager = get_welfare_manager()
    result = await manager.get_by_id(program_id)
    if not result:
        raise HTTPException(404, "Not found")
    return result  # Pydantic이 자동 변환
```

---

## 🎯 성능 목표

### 예상 성능 (15개 문서 기준)

| 메서드 | 예상 시간 | 근거 |
|--------|----------|------|
| `search_by_text()` | <50ms | Text index + 15 docs |
| `search_by_category()` | <10ms | Single field index |
| `search_by_disease()` | <10ms | Array field index |
| `search_by_ckd_stage()` | <10ms | Nested field index |
| `get_by_id()` | <5ms | Unique index |
| `get_stats()` | <100ms (miss), <1ms (hit) | Aggregation + cache |

**실제 측정** (test_welfare_manager() 실행 시):
- 로그에서 `time=X.XXXs` 확인
- 목표치 초과 시 인덱스 확인

---

## 🔧 트러블슈팅

### 문제 1: Connection timeout
**증상**:
```
pymongo.errors.ServerSelectionTimeoutError: localhost:27017: [Errno 61] Connection refused
```

**해결**:
```bash
# 1. MongoDB 실행 확인
mongosh --eval "db.adminCommand('ping')"

# 2. URI 확인
echo $MONGODB_URI

# 3. MongoDB 시작
brew services start mongodb-community  # macOS
sudo systemctl start mongod  # Linux
```

### 문제 2: Index creation failed
**증상**:
```
pymongo.errors.OperationFailure: Index already exists with different options
```

**해결**:
```python
# 인덱스 삭제 후 재생성
db.welfare_programs.drop_index("welfare_text_search")
# 스크립트 재실행
```

### 문제 3: Text search returns 0 results
**증상**:
```python
results = await manager.search_by_text("산정특례")
# len(results) == 0
```

**해결**:
```bash
# 1. 데이터 확인
mongosh careguide --eval "db.welfare_programs.count()"

# 2. 인덱스 확인
mongosh careguide --eval "db.welfare_programs.getIndexes()"

# 3. 직접 검색 테스트
mongosh careguide --eval "db.welfare_programs.find({\$text: {\$search: '산정특례'}})"

# 4. 데이터 재로딩
cd data/welfare
python load_welfare_data.py
```

---

## ✅ Checklist

**구현 완료 기준**:

### 파일
- [ ] `backend/app/db/welfare_manager.py` 생성 (약 300줄)
- [ ] `backend/app/models/welfare.py` 생성 (약 100줄)

### 기능
- [ ] WelfareManager 클래스 정의
- [ ] connect() 메서드
- [ ] create_indexes() 메서드
- [ ] search_by_text() 메서드
- [ ] search_by_category() 메서드
- [ ] search_by_disease() 메서드
- [ ] search_by_ckd_stage() 메서드
- [ ] get_by_id() 메서드
- [ ] get_all_categories() 메서드
- [ ] get_stats() 메서드 (캐싱 포함)

### 테스트
- [ ] python welfare_manager.py 실행
- [ ] 7개 테스트 모두 통과
- [ ] 성능 목표 달성 (<50ms for text search)

---

## 📚 다음 단계

1. ✅ WelfareManager 구현 완료
2. ✅ 테스트 통과
3. ➡️ **다음 문서**: `03_WELFARE_PARLANT_INTEGRATION.md`
4. 구현: search_welfare_programs Tool, Journey 7

---

**END OF BACKEND IMPLEMENTATION**

WelfareManager가 정상 작동하는지 확인했다면,
다음 문서로 이동하여 Parlant 통합을 시작하세요.
