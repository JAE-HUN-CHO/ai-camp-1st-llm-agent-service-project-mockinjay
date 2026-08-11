# REST API 명세서
## Welfare Programs API Reference

**문서**: 04_WELFARE_API_REFERENCE.md
**작성일**: 2025-11-19
**선행 문서**: 03_WELFARE_PARLANT_INTEGRATION.md
**다음 문서**: 05_WELFARE_TESTING_GUIDE.md
**예상 시간**: 1시간

**참고**: 이 REST API는 **선택 사항**입니다. Parlant Journey만으로도 충분히 작동합니다.
프론트엔드에서 직접 복지 정보를 조회하려면 구현하세요.

---

## 📋 목차

1. [API 개요](#1-api-개요)
2. [Endpoints](#2-endpoints)
3. [구현 코드](#3-구현-코드)
4. [프론트엔드 통합](#4-프론트엔드-통합)

---

## 1. API 개요

### 1.1 Base URL

```
http://localhost:8000/api/welfare
```

### 1.2 Endpoints 요약

| Method | Endpoint | 설명 | 인증 |
|--------|----------|------|------|
| GET | `/search` | 텍스트 검색 | Optional |
| GET | `/categories` | 카테고리 목록 | No |
| GET | `/category/{category}` | 카테고리별 조회 | No |
| GET | `/stats` | 통계 조회 | No |
| GET | `/{program_id}` | 프로그램 상세 | No |
| GET | `/health` | 헬스 체크 | No |

### 1.3 패턴

**참고 파일**:
- `backend/app/api/community.py` - Router, singleton pattern
- `backend/app/api/trends.py` - Query parameters, response models

---

## 2. Endpoints

### 2.1 GET /api/welfare/search

**설명**: 복지 프로그램 텍스트 검색

**Query Parameters**:
```typescript
{
  query: string           // 필수, 검색어
  category?: string       // 선택, 카테고리 필터
  disease?: string        // 선택, 질병 필터
  ckd_stage?: number      // 선택, CKD 단계 (1-5)
  limit?: number          // 선택, 최대 결과 수 (default: 10, max: 50)
}
```

**Response**:
```typescript
[
  {
    "_id": "...",
    "programId": "sangjung_ckd_v001",
    "title": "만성콩팥병 산정특례 제도",
    "category": "sangjung_special",
    "description": "...",
    "benefits": {
      "copay_rate": "10%",
      ...
    },
    "application": {...},
    "contact": {...},
    "score": 2.35  // Text search score
  },
  ...
]
```

**예시**:
```bash
# 기본 검색
curl "http://localhost:8000/api/welfare/search?query=산정특례"

# 카테고리 필터
curl "http://localhost:8000/api/welfare/search?query=의료비&category=medical_aid"

# CKD 단계 필터
curl "http://localhost:8000/api/welfare/search?query=지원&ckd_stage=4&limit=5"
```

### 2.2 GET /api/welfare/categories

**설명**: 모든 카테고리 목록 조회

**Response**:
```json
{
  "categories": [
    "disability",
    "medical_aid",
    "sangjung_special",
    "transplant",
    "transport"
  ]
}
```

**예시**:
```bash
curl http://localhost:8000/api/welfare/categories
```

### 2.3 GET /api/welfare/category/{category}

**설명**: 특정 카테고리의 모든 프로그램 조회

**Path Parameters**:
- `category`: 카테고리명 (sangjung_special, disability, etc.)

**Query Parameters**:
- `limit`: 최대 결과 수 (default: 20, max: 50)

**Response**:
```typescript
[
  {
    "programId": "sangjung_ckd_v001",
    "title": "만성콩팥병 산정특례 제도",
    "category": "sangjung_special",
    ...
  },
  ...
]
```

**예시**:
```bash
# 산정특례 프로그램 전체
curl http://localhost:8000/api/welfare/category/sangjung_special

# 장애인 복지 프로그램
curl http://localhost:8000/api/welfare/category/disability
```

### 2.4 GET /api/welfare/stats

**설명**: 복지 프로그램 통계 조회

**Response**:
```json
{
  "total": 15,
  "by_category": {
    "sangjung_special": 3,
    "disability": 4,
    "medical_aid": 4,
    "transplant": 2,
    "transport": 2
  }
}
```

**예시**:
```bash
curl http://localhost:8000/api/welfare/stats
```

### 2.5 GET /api/welfare/{program_id}

**설명**: 프로그램 상세 정보 조회

**Path Parameters**:
- `program_id`: 프로그램 ID (e.g., "sangjung_ckd_v001")

**Response**:
```json
{
  "programId": "sangjung_ckd_v001",
  "title": "만성콩팥병 산정특례 제도",
  "category": "sangjung_special",
  "target_disease": ["CKD", "만성콩팥병"],
  "eligibility": {
    "disease_code": "V001",
    "ckd_stage": [3, 4, 5],
    "description": "..."
  },
  "benefits": {...},
  "application": {...},
  "contact": {...},
  "description": "...",
  "keywords": [...]
}
```

**예시**:
```bash
curl http://localhost:8000/api/welfare/sangjung_ckd_v001
```

### 2.6 GET /api/welfare/health

**설명**: API 헬스 체크

**Response**:
```json
{
  "status": "healthy",
  "service": "welfare"
}
```

**예시**:
```bash
curl http://localhost:8000/api/welfare/health
```

---

## 3. 구현 코드

### 3.1 welfare.py 전체 코드

**파일**: `backend/app/api/welfare.py` (신규 생성)

```python
"""
Welfare Programs API

Endpoints:
- GET /api/welfare/search - Search welfare programs
- GET /api/welfare/categories - Get all categories
- GET /api/welfare/category/{category} - Get programs by category
- GET /api/welfare/stats - Get statistics
- GET /api/welfare/{program_id} - Get program by ID
- GET /api/welfare/health - Health check

Patterns:
- FastAPI router with prefix /api/welfare (community.py 패턴)
- Singleton WelfareManager instance (community.py 패턴)
- Async handlers
- HTTPException for errors (trends.py 패턴)
- Pydantic response models (user.py 패턴)
"""

from fastapi import APIRouter, Query, HTTPException, Path
from app.db.welfare_manager import WelfareManager
from app.models.welfare import (
    WelfareProgram,
    WelfareProgramResponse,
    WelfareStatsResponse
)
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# ==================== Router ====================

router = APIRouter(prefix="/api/welfare", tags=["welfare"])

# ==================== Singleton Instance ====================

_welfare_instance: Optional[WelfareManager] = None

def get_welfare_manager() -> WelfareManager:
    """Get WelfareManager singleton instance (community.py 패턴)"""
    global _welfare_instance
    if _welfare_instance is None:
        _welfare_instance = WelfareManager()
    return _welfare_instance


# ==================== Endpoints ====================

@router.get("/search", response_model=List[WelfareProgramResponse])
async def search_welfare(
    query: str = Query(..., description="검색어 (e.g., '산정특례', '장애인 복지')"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    disease: Optional[str] = Query(None, description="질병 필터 (e.g., 'CKD', 'ESRD')"),
    ckd_stage: Optional[int] = Query(None, ge=1, le=5, description="CKD 단계 (1-5)"),
    limit: int = Query(10, ge=1, le=50, description="최대 결과 수")
):
    """복지 프로그램 텍스트 검색

    Example:
        GET /api/welfare/search?query=산정특례&limit=5
        GET /api/welfare/search?query=의료비&category=medical_aid
    """
    try:
        manager = get_welfare_manager()
        await manager.connect()

        # Build filters (trends.py 패턴)
        filters = {}
        if category:
            filters["category"] = category
        if disease:
            filters["target_disease"] = {"$in": [disease]}
        if ckd_stage:
            filters["eligibility.ckd_stage"] = {"$in": [ckd_stage]}

        # Execute search
        results = await manager.search_by_text(
            query=query,
            limit=limit,
            filters=filters if filters else None
        )

        logger.info(f"Welfare search: query='{query}', filters={bool(filters)}, results={len(results)}")

        return results

    except Exception as e:
        logger.error(f"Welfare search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/categories")
async def get_categories():
    """카테고리 목록 조회"""
    try:
        manager = get_welfare_manager()
        await manager.connect()

        categories = await manager.get_all_categories()

        return {"categories": categories}

    except Exception as e:
        logger.error(f"Get categories error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category/{category}", response_model=List[WelfareProgram])
async def get_by_category(
    category: str = Path(..., description="카테고리"),
    limit: int = Query(20, ge=1, le=50, description="최대 결과 수")
):
    """카테고리별 프로그램 조회"""
    try:
        manager = get_welfare_manager()
        await manager.connect()

        results = await manager.search_by_category(category=category, limit=limit)

        if not results:
            raise HTTPException(status_code=404, detail=f"No programs found in category '{category}'")

        logger.info(f"Get by category: category='{category}', results={len(results)}")

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get by category error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=WelfareStatsResponse)
async def get_stats():
    """통계 조회 (캐싱 적용)"""
    try:
        manager = get_welfare_manager()
        await manager.connect()

        stats = await manager.get_stats(use_cache=True)

        return stats

    except Exception as e:
        logger.error(f"Get stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{program_id}", response_model=WelfareProgram)
async def get_program(
    program_id: str = Path(..., description="프로그램 ID (e.g., 'sangjung_ckd_v001')")
):
    """프로그램 상세 조회"""
    try:
        manager = get_welfare_manager()
        await manager.connect()

        result = await manager.get_by_id(program_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Program not found: {program_id}")

        logger.info(f"Get program: program_id='{program_id}'")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get program error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """헬스 체크 (trends.py 패턴)"""
    return {
        "status": "healthy",
        "service": "welfare",
        "version": "1.0"
    }
```

### 3.2 main.py 등록

**파일**: `backend/app/main.py`
**라인**: 43 근처

```python
# Routers import
from app.api import chat, trends, auth, user, community, nutri
from app.api import welfare  # 추가

# ... app 생성 ...

# Include routers
app.include_router(chat_router)
app.include_router(trends_router)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(community.router)
app.include_router(nutri.router)
app.include_router(welfare.router)  # 추가

logger.info("✅ All routers registered (including welfare)")
```

---

## 4. 프론트엔드 통합

### 4.1 API Client

**파일**: `frontend/src/api/welfareApi.ts` (신규 생성)

```typescript
/**
 * Welfare Programs API Client
 *
 * Pattern: community.ts
 */

import { apiClient } from './apiClient'

// ==================== Types ====================

export interface WelfareBenefits {
  copay_reduction?: string
  copay_rate?: string
  max_monthly_cap?: number
  monthly_amount?: number
  coverage_items?: string[]
  benefits_list?: string[]
}

export interface WelfareEligibility {
  disease_code?: string
  ckd_stage?: number[]
  dialysis_type?: string
  dialysis_duration?: string
  dialysis_required?: boolean
  income?: string
  transplant_candidate?: boolean
  description?: string
}

export interface WelfareApplication {
  required_documents: string[]
  application_place: string
  processing_time: string
  validity_period: string
  renewal?: string
}

export interface WelfareContact {
  phone: string
  website?: string
  online_application?: boolean
}

export interface WelfareProgram {
  programId: string
  title: string
  category: string
  target_disease: string[]
  eligibility: WelfareEligibility
  benefits: WelfareBenefits
  application: WelfareApplication
  contact: WelfareContact
  description: string
  keywords: string[]
  score?: number
}

export interface WelfareSearchParams {
  query: string
  category?: string
  disease?: string
  ckd_stage?: number
  limit?: number
}

export interface WelfareStats {
  total: number
  by_category: Record<string, number>
}

// ==================== API Functions ====================

export const welfareApi = {
  /**
   * Search welfare programs by text
   */
  search: async (params: WelfareSearchParams): Promise<WelfareProgram[]> => {
    const queryParams = new URLSearchParams()
    queryParams.append('query', params.query)
    if (params.category) queryParams.append('category', params.category)
    if (params.disease) queryParams.append('disease', params.disease)
    if (params.ckd_stage) queryParams.append('ckd_stage', params.ckd_stage.toString())
    if (params.limit) queryParams.append('limit', params.limit.toString())

    const response = await apiClient.get(`/api/welfare/search?${queryParams}`)
    return response.data
  },

  /**
   * Get all categories
   */
  getCategories: async (): Promise<string[]> => {
    const response = await apiClient.get('/api/welfare/categories')
    return response.data.categories
  },

  /**
   * Get programs by category
   */
  getByCategory: async (category: string, limit: number = 20): Promise<WelfareProgram[]> => {
    const response = await apiClient.get(`/api/welfare/category/${category}?limit=${limit}`)
    return response.data
  },

  /**
   * Get statistics
   */
  getStats: async (): Promise<WelfareStats> => {
    const response = await apiClient.get('/api/welfare/stats')
    return response.data
  },

  /**
   * Get program by ID
   */
  getProgram: async (programId: string): Promise<WelfareProgram> => {
    const response = await apiClient.get(`/api/welfare/${programId}`)
    return response.data
  },

  /**
   * Health check
   */
  healthCheck: async (): Promise<{status: string, service: string}> => {
    const response = await apiClient.get('/api/welfare/health')
    return response.data
  }
}
```

### 4.2 ChatPage 통합 (선택)

**파일**: `frontend/src/pages/chat/ChatPage.tsx`

**추가 컴포넌트** (PaperList 패턴):

```typescript
/**
 * Welfare Program List Component
 */

interface WelfareProgramListProps {
  programs: WelfareProgram[]
}

function WelfareProgramList({ programs }: WelfareProgramListProps) {
  if (!programs.length) return null

  return (
    <div className="mt-6 border border-gray-200 rounded-xl bg-white shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-800">
          🎗️ 복지 프로그램 ({programs.length})
        </h3>
      </div>
      <div className="divide-y divide-gray-100">
        {programs.map((prog) => (
          <div key={prog.programId} className="px-4 py-3">
            {/* 프로그램명 */}
            <div className="font-medium text-gray-900">{prog.title}</div>

            {/* 카테고리 배지 */}
            <div className="mt-1">
              <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                {getCategoryLabel(prog.category)}
              </span>
            </div>

            {/* 설명 */}
            <div className="text-sm text-gray-700 mt-2 line-clamp-2">
              {prog.description}
            </div>

            {/* 혜택 */}
            {prog.benefits && (
              <div className="text-xs text-gray-600 mt-2">
                {prog.benefits.copay_rate && (
                  <span className="mr-3">💰 본인부담금: {prog.benefits.copay_rate}</span>
                )}
                {prog.benefits.monthly_amount && (
                  <span className="mr-3">💵 월 지원: {prog.benefits.monthly_amount.toLocaleString()}원</span>
                )}
              </div>
            )}

            {/* 연락처 */}
            <div className="text-xs text-gray-500 mt-2 flex gap-3">
              <span>📞 {prog.contact.phone}</span>
              {prog.contact.website && (
                <a
                  href={prog.contact.website}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-600 underline hover:text-blue-800"
                >
                  웹사이트 →
                </a>
              )}
            </div>

            {/* 신청 장소 */}
            {prog.application && (
              <div className="text-xs text-gray-500 mt-1">
                📍 신청: {prog.application.application_place}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// Helper function
function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    'sangjung_special': '산정특례',
    'disability': '장애인복지',
    'medical_aid': '의료비지원',
    'transplant': '이식지원',
    'transport': '교통비'
  }
  return labels[category] || category
}
```

**ChatPage에서 사용**:

```typescript
// State 추가
const [welfarePrograms, setWelfarePrograms] = useState<WelfareProgram[]>([])

// Tool 이벤트에서 복지 프로그램 추출
useEffect(() => {
  const extractWelfare = () => {
    // SSE events에서 tool_state=search_welfare_programs 찾기
    // results 필드 추출
    const welfare = events
      .filter(e => e.type === 'tool' && e.tool === 'search_welfare_programs')
      .flatMap(e => e.data?.results || [])

    setWelfarePrograms(welfare)
  }

  extractWelfare()
}, [events])

// Render
return (
  <div>
    {messages.map(msg => ...)}

    {/* 복지 프로그램 목록 */}
    <WelfareProgramList programs={welfarePrograms} />

    {/* 논문 목록 (기존) */}
    <PaperList papers={papers} />
  </div>
)
```

---

## 📊 API 사용 예시

### TypeScript (Frontend)

```typescript
import { welfareApi } from '../api/welfareApi'

// 1. 검색
const programs = await welfareApi.search({
  query: '산정특례',
  limit: 5
})
console.log(programs)  // [V001, V003, V005]

// 2. 카테고리별
const disability = await welfareApi.getByCategory('disability')
console.log(disability.length)  // 4

// 3. 통계
const stats = await welfareApi.getStats()
console.log(stats.total)  // 15

// 4. 상세 조회
const program = await welfareApi.getProgram('sangjung_ckd_v001')
console.log(program.title)  // "만성콩팥병 산정특례 제도"
```

### Python (Backend)

```python
import httpx

async def test_api():
    async with httpx.AsyncClient() as client:
        # 검색
        response = await client.get(
            "http://localhost:8000/api/welfare/search",
            params={"query": "산정특례", "limit": 5}
        )
        data = response.json()
        print(f"Found {len(data)} programs")

        # 통계
        response = await client.get("http://localhost:8000/api/welfare/stats")
        stats = response.json()
        print(f"Total: {stats['total']}")
```

---

## ✅ Checklist

**API 구현 완료 기준**:

### 파일
- [ ] `backend/app/api/welfare.py` 생성 (약 200줄)
- [ ] `frontend/src/api/welfareApi.ts` 생성 (약 150줄)

### Endpoints
- [ ] GET /api/welfare/search 작동
- [ ] GET /api/welfare/categories 작동
- [ ] GET /api/welfare/category/{category} 작동
- [ ] GET /api/welfare/stats 작동
- [ ] GET /api/welfare/{program_id} 작동
- [ ] GET /api/welfare/health 작동

### main.py
- [ ] welfare.router 등록
- [ ] 서버 재시작 성공

### 테스트
- [ ] curl 테스트 6개 성공
- [ ] 프론트엔드 welfareApi 테스트 성공

---

## 📚 다음 단계

1. ✅ REST API 구현 완료 (선택)
2. ➡️ **다음 문서**: `05_WELFARE_TESTING_GUIDE.md`
3. 테스트: Unit, Integration, E2E

---

**END OF API REFERENCE**

REST API를 구현했다면 테스트 가이드로 이동하세요.
Parlant만 사용한다면 이 섹션은 건너뛰어도 됩니다.
