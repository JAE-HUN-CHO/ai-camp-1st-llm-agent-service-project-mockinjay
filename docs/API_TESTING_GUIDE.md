# API Compatibility Testing Guide

## Quick Start

### Running the Tests

```bash
# Navigate to frontend directory
cd frontend

# Run API compatibility tests
npm run test:api
```

The tests will:
1. Test all critical API endpoints
2. Display colored results in the console
3. Generate a detailed report at `./api-compatibility-report.md`

### Prerequisites

Before running tests:
- Backend must be running on `http://localhost:8000`
- MongoDB must be running and connected
- No special authentication required (tests use dev-login)

### Environment Variables

```bash
# Optional: Change backend URL
export API_BASE_URL=http://localhost:8000

# Then run tests
npm run test:api
```

---

## Understanding Test Results

### Console Output

Tests display colored symbols:
- ✓ Green = **PASS** - Endpoint working as expected
- ✗ Red = **FAIL** - Endpoint exists but returns wrong status/format
- ? Yellow = **MISSING** - Endpoint not found (404)
- ! Red = **ERROR** - Connection error or timeout

### Pass Rates by Feature

Current status (as of 2025-11-28):

| Feature | Pass Rate | Status |
|---------|-----------|--------|
| MyPage | 100% (8/8) | ✅ Ready |
| Terms | 100% (1/1) | ✅ Ready |
| Chat | 100% (3/3) | ✅ Ready |
| Auth | 71.4% (5/7) | ⚠️ Mostly Ready |
| Health | 66.7% (2/3) | ⚠️ Minor Issues |
| Community | 33.3% (1/3) | ⚠️ Needs Work |
| Trends | 25% (1/4) | ⚠️ Performance Issues |
| Rooms | 0% (0/2) | ❌ Broken |
| Session | 0% (0/1) | ❌ Minor Fix Needed |
| Diet Care | 0% (0/8) | ❌ Critical Issues |
| Quiz | 0% (0/1) | ❌ Broken |

---

## Common Issues and Fixes

### Issue 1: Database Connection Errors

**Symptom:**
```
✗ Create diet care session - Expected 200, got 500
Detail: 'NoneType' object has no attribute 'insert_one'
```

**Cause:** MongoDB collections not initialized

**Fix:**
```python
# In backend/app/db/connection.py
diet_sessions_collection = None
diet_meals_collection = None
diet_goals_collection = None

async def init_legacy_collections():
    global diet_sessions_collection, diet_meals_collection, diet_goals_collection
    diet_sessions_collection = db["diet_sessions"]
    diet_meals_collection = db["diet_meals"]
    diet_goals_collection = db["diet_goals"]
```

### Issue 2: Socket Hang Up Errors

**Symptom:**
```
! Get nutrition goals - socket hang up
```

**Causes:**
1. Backend crashed or restarted during test
2. Endpoint taking too long (>5 seconds)
3. Database connection lost

**Fix:**
- Check backend logs for errors
- Restart backend server
- Check MongoDB connection
- Increase timeout in test script if needed

### Issue 3: Request Validation Errors (422)

**Symptom:**
```
✗ Create community post - Expected 201, got 422
Field required: postType
```

**Cause:** Frontend and backend using different field names

**Fix Options:**

Option A - Update backend model:
```python
# Add alias in Pydantic model
class PostCreate(BaseModel):
    post_type: str = Field(..., alias="postType")
```

Option B - Update frontend request:
```typescript
// Change frontend to match backend
{ postType: 'BOARD' }  // instead of post_type
```

### Issue 4: Authentication Errors (401)

**Symptom:**
```
✗ Get user rooms list - Expected 200, got 401
Detail: 인증 정보가 없습니다
```

**Cause:** Auth middleware not accepting token for this endpoint

**Fix:**
```python
# In backend/app/middleware/auth.py
# Ensure /api/rooms is in protected paths
PROTECTED_PATHS = [
    "/api/mypage/",
    "/api/rooms",  # Add this
    # ... other paths
]
```

### Issue 5: Timeout Errors (Trends API)

**Symptom:**
```
! Analyze temporal trends - timeout of 5000ms exceeded
```

**Cause:** Long-running data analysis operations

**Fix Options:**

Option A - Optimize backend:
```python
# Add caching
from functools import lru_cache

@lru_cache(maxsize=100)
async def get_temporal_trends(query: str):
    # ... expensive operation
```

Option B - Increase timeout:
```typescript
// In test script or frontend API client
timeout: 15000  // 15 seconds for trends endpoints
```

Option C - Make async:
```python
# Return job ID immediately, poll for results
@router.post("/trends/temporal")
async def analyze_temporal_trends_async():
    job_id = create_background_job(analyze_trends)
    return {"job_id": job_id, "status": "processing"}
```

---

## Modifying Tests

### Adding New Endpoints

Edit `/Users/apple/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/frontend/scripts/test-api-compatibility.ts`:

```typescript
// Add new test function
async function testNewFeatureEndpoints() {
  logSection('Testing New Feature Endpoints');

  const suite: TestSuite = { name: 'New Feature', results: [] };

  // Test endpoint
  suite.results.push(await testEndpoint(suite.name, 'GET', '/api/new/endpoint', {
    requireAuth: true,  // If requires authentication
    expectedStatus: 200,
    description: 'Get new feature data',
  }));

  testResults.push(suite);
}

// Add to runAllTests()
async function runAllTests() {
  // ... existing tests
  await testNewFeatureEndpoints();  // Add here
  // ...
}
```

### Adjusting Timeouts

```typescript
// At top of file
const TEST_TIMEOUT = 5000; // Change this value (milliseconds)
```

Or for specific endpoints:
```typescript
suite.results.push(await testEndpoint(suite.name, 'POST', '/api/slow/endpoint', {
  timeout: 15000,  // Override timeout for this endpoint
  description: 'Slow operation',
}));
```

### Skipping Tests

```typescript
// Comment out tests you want to skip
async function runAllTests() {
  await testHealthEndpoints();
  await testAuthEndpoints();
  // await testDietCareEndpoints();  // Skip diet care for now
  await testCommunityEndpoints();
}
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/api-tests.yml
name: API Compatibility Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mongodb:
        image: mongo:latest
        ports:
          - 27017:27017

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Backend Dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Start Backend
        run: |
          cd backend
          uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          sleep 10

      - name: Install Frontend Dependencies
        run: |
          cd frontend
          npm install

      - name: Run API Tests
        run: |
          cd frontend
          npm run test:api

      - name: Upload Test Report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: api-compatibility-report
          path: frontend/api-compatibility-report.md
```

---

## Troubleshooting

### Tests Won't Run

**Problem:** `command not found: tsx`

**Solution:**
```bash
cd frontend
npm install
```

**Problem:** `Cannot find module 'axios'`

**Solution:**
```bash
cd frontend
npm install axios
```

### Backend Not Responding

**Check if backend is running:**
```bash
curl http://localhost:8000/health
```

**Should return:**
```json
{"status": "healthy"}
```

**If not, start backend:**
```bash
cd backend
uvicorn app.main:app --reload
```

### MongoDB Connection Issues

**Check MongoDB status:**
```bash
# If using Docker
docker ps | grep mongo

# If using local MongoDB
mongosh --eval "db.adminCommand('ping')"
```

**Start MongoDB:**
```bash
# Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or use existing container
docker start mongodb
```

### Timeout Issues

**Temporary fix - increase timeout:**
```typescript
// In test-api-compatibility.ts line ~12
const TEST_TIMEOUT = 10000; // Increase to 10 seconds
```

**Permanent fix:**
- Optimize slow endpoints
- Add caching
- Use async processing

---

## Best Practices

### Before Committing Backend Changes

```bash
# Always run API tests before committing
cd frontend
npm run test:api

# Check pass rate - should be >80%
# Review report for any regressions
```

### Before Frontend Migration

1. Run full test suite
2. Ensure pass rate ≥ 90%
3. All critical endpoints passing (Auth, MyPage, Chat)
4. No P1 or P2 issues remaining

### Regression Testing

After fixing an endpoint:
```bash
# Run tests
npm run test:api

# Compare with previous report
diff api-compatibility-report.md api-compatibility-report.old.md
```

---

## Performance Benchmarks

Expected response times for healthy API:

| Endpoint Type | Target | Acceptable | Slow |
|--------------|--------|------------|------|
| Simple GET | <50ms | <200ms | >500ms |
| Database Query | <100ms | <500ms | >1s |
| POST/PUT | <200ms | <1s | >2s |
| Search | <500ms | <2s | >5s |
| Analytics | <2s | <5s | >10s |

Current performance issues:
- Trends endpoints: 5+ seconds (timeout)
- Paper search: ~2 seconds (acceptable but slow)

---

## Related Documentation

- **Full Report:** `./api-compatibility-report.md` - Detailed test results
- **Summary:** `./API_COMPATIBILITY_SUMMARY.md` - Executive summary
- **Backend API:** `/backend/API_DESIGN.md` - API specifications
- **Frontend Services:** `/new_frontend/src/services/api.ts` - Frontend API client

---

## Getting Help

**Test Suite Issues:**
- Check this guide first
- Review error messages in console output
- Check backend logs: `backend/logs/`

**Backend Issues:**
- Review API documentation
- Check MongoDB connection
- Enable debug logging in backend

**Need to modify tests:**
- Test script location: `/frontend/scripts/test-api-compatibility.ts`
- Written in TypeScript
- Uses axios for HTTP requests
- Generates markdown reports

---

*Last Updated: 2025-11-28*
*Test Suite Version: 1.0.0*
