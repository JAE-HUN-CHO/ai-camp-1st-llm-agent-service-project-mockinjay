# Backend Fixes Required for Frontend Migration
## Critical Issues - Must Fix Before Migration

**Date:** 2025-11-28
**Priority:** URGENT
**Estimated Effort:** 4-6 hours

---

## Summary

API compatibility testing revealed **10 failing endpoints** and **2 missing endpoints** that must be fixed before the new frontend can be migrated. The most critical issue is the **Diet Care feature** (0% pass rate) due to uninitialized MongoDB collections.

**Current Status:** 51.2% pass rate (21/41 tests)
**Target:** 90% pass rate minimum
**Blocking Issues:** 3 critical, 4 high priority

---

## CRITICAL Priority (Must Fix Immediately)

### 1. Diet Care Database Initialization

**Severity:** CRITICAL - Complete feature broken
**Pass Rate:** 0/8 (0%)
**Affected Endpoints:** All Diet Care endpoints
**Test Results:** 500 errors - `'NoneType' object has no attribute 'insert_one'`

**Root Cause:**
MongoDB collections for Diet Care feature are not initialized in the database connection module.

**Files to Modify:**
- `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/backend/app/db/connection.py`

**Fix:**

```python
# In backend/app/db/connection.py

# Add global collection variables
diet_sessions_collection = None
diet_meals_collection = None
diet_goals_collection = None

# Update init_legacy_collections function
async def init_legacy_collections():
    """Initialize legacy collection variables for backward compatibility"""
    global users_collection, community_collection, bookmarks_collection
    global diet_sessions_collection, diet_meals_collection, diet_goals_collection

    # Existing collections
    users_collection = Database.db["users"]
    community_collection = Database.db["community_posts"]
    bookmarks_collection = Database.db["bookmarks"]

    # ADD THESE LINES:
    diet_sessions_collection = Database.db["diet_sessions"]
    diet_meals_collection = Database.db["diet_meals"]
    diet_goals_collection = Database.db["diet_goals"]

    logger.info("✅ All legacy collections initialized")
```

**Verification:**
```bash
# After fix, run these tests:
curl -X POST http://localhost:8000/api/diet-care/session/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"

# Should return 201 with session_id
```

**Estimated Time:** 15 minutes

---

### 2. Community Post Field Name Mismatch

**Severity:** HIGH
**Test Result:** 422 Validation Error
**Endpoint:** `POST /api/community/posts`

**Issue:**
Frontend sends `post_type` but backend expects `postType` (or vice versa)

**Error Message:**
```json
{
  "field": "body.postType",
  "message": "Field required",
  "type": "missing"
}
```

**Files to Modify:**
- `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/backend/app/models/community.py`

**Fix Option A (Recommended) - Add Field Alias:**

```python
# In backend/app/models/community.py
from pydantic import BaseModel, Field

class PostCreate(BaseModel):
    title: str
    content: str
    # Add alias to accept both formats
    post_type: PostType = Field(..., alias="postType")
    tags: Optional[List[str]] = None

    class Config:
        populate_by_name = True  # Allow both post_type and postType
```

**Fix Option B - Update Frontend:**
If backend naming is correct, update frontend to use `postType` instead of `post_type`.

**Verification:**
```bash
curl -X POST http://localhost:8000/api/community/posts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Post",
    "content": "Test content",
    "post_type": "BOARD",
    "tags": ["test"]
  }'

# Should return 201 with post data
```

**Estimated Time:** 10 minutes

---

### 3. Quiz Session Type Validation

**Severity:** HIGH
**Test Result:** 422 Validation Error
**Endpoint:** `POST /api/quiz/session/start`

**Issue:**
Frontend sends `sessionType: 'DAILY'` but backend expects different values.

**Error Message:**
```json
{
  "field": "body.sessionType",
  "message": "Input should be 'level_test', 'learn', 'daily'"
}
```

**Files to Modify:**
- `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/backend/app/models/quiz.py`

**Current Backend Model:**
```python
class SessionType(str, Enum):
    LEVEL_TEST = "level_test"
    LEARN = "learn"
    DAILY = "daily"
```

**Frontend Sends:**
```json
{
  "sessionType": "DAILY"  # Uppercase
}
```

**Fix - Make Enum Case-Insensitive:**

```python
# In backend/app/models/quiz.py
from enum import Enum
from pydantic import field_validator

class SessionType(str, Enum):
    LEVEL_TEST = "level_test"
    LEARN = "learn"
    DAILY = "daily"

class QuizSessionStart(BaseModel):
    userId: str
    sessionType: SessionType
    category: Optional[QuizCategory] = None
    difficulty: Optional[DifficultyLevel] = None

    @field_validator('sessionType', mode='before')
    @classmethod
    def normalize_session_type(cls, v):
        """Accept both uppercase and lowercase session types"""
        if isinstance(v, str):
            return v.lower()
        return v
```

**Verification:**
```bash
curl -X POST http://localhost:8000/api/quiz/session/start \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test123",
    "sessionType": "DAILY"
  }'

# Should return 201 with quiz session
```

**Estimated Time:** 15 minutes

---

## HIGH Priority (Fix Before Launch)

### 4. Missing Registration Endpoint

**Severity:** HIGH
**Test Result:** 404 Not Found
**Endpoint:** `POST /api/auth/register`

**Issue:**
Frontend expects `/api/auth/register` but backend only has `/api/auth/signup`

**Files to Modify:**
- `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/backend/app/api/auth.py`

**Fix - Add Alias Endpoint:**

```python
# In backend/app/api/auth.py
# Add after existing /signup endpoint (around line 241)

@router.post("/register")
async def register_alias(user_data: RegisterRequest):
    """Alias for /signup - Frontend compatibility"""
    # Reuse the existing register logic
    return await register(user_data)
```

**Note:** The backend already has a `register` function at line 44. Just add the route alias.

**Estimated Time:** 5 minutes

---

### 5. Rooms API Authentication

**Severity:** HIGH
**Test Result:** 401 Unauthorized
**Endpoint:** `GET /api/rooms`

**Issue:**
Endpoint requires authentication but auth token not being accepted.

**Files to Modify:**
- `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/backend/app/middleware/auth.py`

**Current Issue:**
The GET endpoint uses query parameter `user_id` instead of JWT token.

**Fix - Update Endpoint to Use JWT:**

```python
# In backend/app/api/rooms.py (around line 60)

from app.services.auth import get_current_user
from fastapi import Depends

@router.get("")
async def get_rooms_list(
    current_user: dict = Depends(get_current_user),  # Use JWT instead of query param
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> RoomsListResponse:
    """Get all rooms for authenticated user"""
    user_id = str(current_user["_id"])  # Get user ID from token

    # ... rest of function
```

**Estimated Time:** 20 minutes

---

### 6. Community Search Endpoint

**Severity:** MEDIUM
**Test Result:** 404 Not Found
**Endpoint:** `GET /api/community/search`

**Issue:**
Frontend expects search endpoint but it doesn't exist.

**Files to Modify:**
- `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/backend/app/api/community.py`

**Fix - Add Search Endpoint:**

```python
# In backend/app/api/community.py
# Add after existing endpoints

@router.get("/search")
async def search_posts(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    request: Request = None,
) -> dict:
    """
    Search community posts by title or content
    검색어로 게시글 검색
    """
    # Get user info
    user_id, is_authenticated, username = get_user_id_from_request(request)

    # Build search query
    search_filter = {
        "$or": [
            {"title": {"$regex": q, "$options": "i"}},
            {"content": {"$regex": q, "$options": "i"}},
            {"tags": {"$in": [q]}}
        ]
    }

    # Get total count
    total = await db.community_posts.count_documents(search_filter)

    # Get posts
    cursor = db.community_posts.find(search_filter)
    cursor.skip(offset).limit(limit).sort("created_at", -1)
    posts_data = await cursor.to_list(length=limit)

    # Convert to response format
    posts = []
    for post_doc in posts_data:
        posts.append({
            "id": str(post_doc["_id"]),
            "title": post_doc["title"],
            "content": post_doc["content"],
            "postType": post_doc.get("post_type", "BOARD"),
            "author": {
                "id": post_doc["author_id"],
                "username": post_doc.get("author_username", "Unknown")
            },
            "likes": post_doc.get("likes", 0),
            "commentCount": post_doc.get("comment_count", 0),
            "createdAt": post_doc["created_at"].isoformat(),
            "tags": post_doc.get("tags", [])
        })

    return {
        "posts": posts,
        "total": total,
        "query": q,
        "limit": limit,
        "offset": offset
    }
```

**Estimated Time:** 30 minutes

---

## MEDIUM Priority (Performance & UX)

### 7. Database Connection Check

**Severity:** MEDIUM
**Test Result:** 500 Internal Server Error
**Endpoint:** `GET /db-check`

**Issue:**
Database check endpoint returns 500 error with coroutine iteration error.

**Files to Modify:**
- `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/backend/app/main.py`

**Current Code (around line 136):**
```python
@app.get("/db-check")
def database_check():
    """MongoDB 연결 상태 확인"""
    return check_connection()
```

**Fix - Make Async:**
```python
@app.get("/db-check")
async def database_check():
    """MongoDB 연결 상태 확인"""
    return await check_connection()
```

**Also check `/backend/app/db/connection.py`:**
```python
async def check_connection():
    """Check MongoDB connection status"""
    try:
        # Use await for async ping
        await Database.client.admin.command('ping')
        return {
            "status": "connected",
            "database": Database.db.name,
            "collections": await Database.db.list_collection_names()
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e)
        }
```

**Estimated Time:** 10 minutes

---

### 8. Trends API Performance

**Severity:** MEDIUM (Performance Issue)
**Test Result:** Timeout (>5 seconds)
**Affected Endpoints:**
- `POST /api/trends/temporal`
- `POST /api/trends/geographic`
- `POST /api/trends/mesh`

**Issue:**
Long-running data analysis operations causing timeouts.

**Short-term Fix:**
Add timeout warnings in documentation and increase frontend timeout.

**Long-term Fix (Recommended):**

```python
# In backend/app/api/trends.py

from functools import lru_cache
from fastapi import BackgroundTasks

# Add caching for expensive operations
@lru_cache(maxsize=100)
def cache_key(query: str, start_year: int, end_year: int) -> str:
    return f"{query}:{start_year}:{end_year}"

# Option A: Add caching
@router.post("/temporal")
async def analyze_temporal_trends(request: TemporalTrendsRequest):
    cache_key = f"{request.query}:{request.start_year}:{request.end_year}"

    # Check cache first
    cached = await get_from_cache(cache_key)
    if cached:
        return cached

    # Run analysis
    result = await trend_agent.process(...)

    # Cache result
    await save_to_cache(cache_key, result, ttl=3600)

    return result

# Option B: Background processing
@router.post("/temporal/async")
async def analyze_temporal_trends_async(
    request: TemporalTrendsRequest,
    background_tasks: BackgroundTasks
):
    job_id = str(uuid.uuid4())

    # Start background task
    background_tasks.add_task(
        run_trend_analysis,
        job_id,
        request
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "poll_url": f"/api/trends/status/{job_id}"
    }
```

**Estimated Time:** 2-4 hours

---

## LOW Priority (Response Code Adjustments)

### 9. Status Code Standardization

**Issue:**
Some POST endpoints return 201 (Created) but tests expect 200 (OK).

**Affected:**
- `POST /api/rooms` - Returns 201
- `POST /api/session/create` - Returns 201

**Recommendation:**
These are actually correct! Update test expectations instead of backend.

**Action:**
No backend changes needed. Update test script to accept 201 for POST creation endpoints.

---

## Verification Checklist

After implementing fixes, verify each endpoint:

```bash
# 1. Diet Care
curl -X POST http://localhost:8000/api/diet-care/session/create \
  -H "Authorization: Bearer $TOKEN"

# 2. Community Post
curl -X POST http://localhost:8000/api/community/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","content":"Test","post_type":"BOARD"}'

# 3. Quiz Session
curl -X POST http://localhost:8000/api/quiz/session/start \
  -H "Content-Type: application/json" \
  -d '{"userId":"test","sessionType":"DAILY"}'

# 4. Registration
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"Test123!"}'

# 5. Rooms List
curl http://localhost:8000/api/rooms?user_id=test \
  -H "Authorization: Bearer $TOKEN"

# 6. Community Search
curl "http://localhost:8000/api/community/search?q=test"

# 7. Database Check
curl http://localhost:8000/db-check

# Then run full test suite
cd frontend && npm run test:api
```

---

## Testing After Fixes

### Step 1: Start Services

```bash
# Terminal 1 - MongoDB
docker start mongodb

# Terminal 2 - Backend
cd backend
uvicorn app.main:app --reload

# Terminal 3 - Run Tests
cd frontend
npm run test:api
```

### Step 2: Expected Results

After all fixes:
- Pass rate should be ≥ 85%
- All CRITICAL and HIGH priority endpoints passing
- Only performance warnings remaining

### Step 3: Generate Report

```bash
cd frontend
npm run test:api

# Check report
cat api-compatibility-report.md
```

---

## Summary of Changes

### Files to Modify (7 files)

1. **`backend/app/db/connection.py`**
   - Add diet care collection initialization
   - Fix async check_connection

2. **`backend/app/models/community.py`**
   - Add field alias for post_type/postType

3. **`backend/app/models/quiz.py`**
   - Add case-insensitive session type validator

4. **`backend/app/api/auth.py`**
   - Add /register endpoint alias

5. **`backend/app/api/rooms.py`**
   - Update GET to use JWT authentication

6. **`backend/app/api/community.py`**
   - Add search endpoint

7. **`backend/app/main.py`**
   - Make db-check async

### Estimated Total Time

- Critical fixes: 40 minutes
- High priority: 55 minutes
- Medium priority: 2-4 hours (if doing performance optimization)
- **Total (excluding performance):** ~1.5 hours
- **Total (including performance):** ~4-6 hours

---

## Migration Readiness

**Before fixes:**
- Pass Rate: 51.2%
- Status: ❌ NOT READY

**After fixes (expected):**
- Pass Rate: ~85-90%
- Status: ✅ READY for migration

**Remaining work:**
- Performance optimization (can be done post-migration)
- Enhanced caching (future improvement)
- API documentation updates

---

## Contact

**Questions about:**
- Test failures: Check `/frontend/api-compatibility-report.md`
- Implementation: See code comments in this document
- Architecture: Review `/backend/API_DESIGN.md`

**After implementing fixes:**
Re-run test suite and update status in project tracking.

---

*Document Generated: 2025-11-28*
*Priority: URGENT - Required for frontend migration*
*Est. Total Effort: 1.5 - 6 hours depending on scope*
