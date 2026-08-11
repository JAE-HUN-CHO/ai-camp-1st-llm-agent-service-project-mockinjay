# API Compatibility Test Report

**Generated:** 2025-11-28T04:12:33.714Z
**Backend:** http://localhost:8000

## Summary

| Metric | Count |
|--------|-------|
| Total Tests | 41 |
| Passed | 21 |
| Failed | 10 |
| Missing | 2 |
| Errors | 8 |
| Pass Rate | 51.2% |

## Health & Basic

| Endpoint | Method | Status | Code | Time | Message |
|----------|--------|--------|------|------|----------|
| `/` | GET | ✓ PASS | 200 | 20ms | Root endpoint |
| `/health` | GET | ✓ PASS | 200 | 2ms | Health check |
| `/db-check` | GET | ✗ FAIL | 500 | 8ms | Database connection check - Expected 200, got 500 |

## Authentication

| Endpoint | Method | Status | Code | Time | Message |
|----------|--------|--------|------|------|----------|
| `/api/auth/check-email` | GET | ! ERROR | - | 3ms | Check email availability - socket hang up |
| `/api/auth/check-username` | GET | ✓ PASS | 200 | 9ms | Check username availability |
| `/api/auth/dev-login` | POST | ✓ PASS | 200 | 3ms | Dev login (auto user creation) |
| `/api/auth/login` | POST | ✓ PASS | 200 | 243ms | Login with credentials |
| `/api/auth/me` | GET | ✓ PASS | 200 | 3ms | Get current user info |
| `/api/auth/register` | POST | ? MISSING | 404 | 2ms | Register new user - Endpoint not found |
| `/api/auth/profile` | PATCH | ✓ PASS | 200 | 7ms | Update user profile type |

## Terms & Conditions

| Endpoint | Method | Status | Code | Time | Message |
|----------|--------|--------|------|------|----------|
| `/api/terms/all` | GET | ✓ PASS | 200 | 2ms | Get all terms and conditions |

## Chat & Messaging

| Endpoint | Method | Status | Code | Time | Message |
|----------|--------|--------|------|------|----------|
| `/api/chat/info` | GET | ✓ PASS | 200 | - | Get chat service info |
| `/api/chat/rooms` | GET | ✓ PASS | 200 | 8ms | Get user chat rooms (deprecated) |
| `/api/chat/history` | GET | ✓ PASS | 200 | 2ms | Get chat history |

## Rooms Management

| Endpoint | Method | Status | Code | Time | Message |
|----------|--------|--------|------|------|----------|
| `/api/rooms` | POST | ✗ FAIL | 201 | 6ms | Create chat room - Expected 200, got 201 |
| `/api/rooms` | GET | ✗ FAIL | 401 | 1ms | Get user rooms list - Expected 200, got 401 |

## Session Management

| Endpoint | Method | Status | Code | Time | Message |
|----------|--------|--------|------|------|----------|
| `/api/session/create` | POST | ✗ FAIL | 201 | 1ms | Create analysis session - Expected 200, got 201 |

## Diet Care

| Endpoint | Method | Status | Code | Time | Message |
|----------|--------|--------|------|------|----------|
| `/api/diet-care/session/create` | POST | ✗ FAIL | 500 | 4ms | Create diet care session - Expected 200, got 500 |
| `/api/diet-care/goals` | GET | ! ERROR | - | 1ms | Get nutrition goals - socket hang up |
| `/api/diet-care/goals` | PUT | ✗ FAIL | 500 | 6ms | Update nutrition goals - Expected 200, got 500 |
| `/api/diet-care/meals` | GET | ! ERROR | - | - | Get meal history - socket hang up |
| `/api/diet-care/meals` | POST | ✗ FAIL | 500 | 11ms | Create meal entry - Expected 201, got 500 |
| `/api/diet-care/progress/daily` | GET | ! ERROR | - | - | Get daily progress - socket hang up |
| `/api/diet-care/progress/weekly` | GET | ✗ FAIL | 500 | 10ms | Get weekly progress - Expected 200, got 500 |
| `/api/diet-care/streak` | GET | ! ERROR | - | - | Get logging streak - socket hang up |

## Community

| Endpoint | Method | Status | Code | Time | Message |
|----------|--------|--------|------|------|----------|
| `/api/community/posts` | GET | ✓ PASS | 200 | 5ms | Get community posts |
| `/api/community/posts` | POST | ✗ FAIL | 422 | 2ms | Create community post - Expected 201, got 422 |
| `/api/community/search` | GET | ? MISSING | 404 | 1ms | Search community posts - Endpoint not found |

## Trends & Research

| Endpoint | Method | Status | Code | Time | Message |
|----------|--------|--------|------|------|----------|
| `/api/trends/temporal` | POST | ! ERROR | - | 5005ms | Analyze temporal trends - timeout of 5000ms exceeded |
| `/api/trends/papers` | POST | ✓ PASS | 200 | 1877ms | Search research papers |
| `/api/trends/geographic` | POST | ! ERROR | - | 5001ms | Analyze geographic distribution - timeout of 5000ms exceeded |
| `/api/trends/mesh` | POST | ! ERROR | - | 5002ms | Analyze MeSH categories - timeout of 5000ms exceeded |

## MyPage

| Endpoint | Method | Status | Code | Time | Message |
|----------|--------|--------|------|------|----------|
| `/api/mypage/profile` | GET | ✓ PASS | 200 | 8ms | Get user profile |
| `/api/mypage/profile` | PUT | ✓ PASS | 200 | 13ms | Update user profile |
| `/api/mypage/health-profile` | GET | ✓ PASS | 200 | 8ms | Get health profile |
| `/api/mypage/health-profile` | PUT | ✓ PASS | 200 | 8ms | Update health profile |
| `/api/mypage/preferences` | GET | ✓ PASS | 200 | 5ms | Get user preferences |
| `/api/mypage/preferences` | PUT | ✓ PASS | 200 | 6ms | Update user preferences |
| `/api/mypage/bookmarks` | GET | ✓ PASS | 200 | 8ms | Get bookmarked papers |
| `/api/mypage/posts` | GET | ✓ PASS | 200 | 6ms | Get user posts |

## Quiz

| Endpoint | Method | Status | Code | Time | Message |
|----------|--------|--------|------|------|----------|
| `/api/quiz/session/start` | POST | ✗ FAIL | 422 | 3ms | Start quiz session - Expected 201, got 422 |

## Recommendations

### Missing Endpoints (2)

The following endpoints are required by the frontend but not implemented:

**Authentication:**
- `POST /api/auth/register`: Register new user - Endpoint not found

**Community:**
- `GET /api/community/search`: Search community posts - Endpoint not found

### Failed Tests (10)

The following endpoints exist but returned unexpected responses:

**Health & Basic:**
- `GET /db-check` [500]: Database connection check - Expected 200, got 500

**Rooms Management:**
- `POST /api/rooms` [201]: Create chat room - Expected 200, got 201
- `GET /api/rooms` [401]: Get user rooms list - Expected 200, got 401

**Session Management:**
- `POST /api/session/create` [201]: Create analysis session - Expected 200, got 201

**Diet Care:**
- `POST /api/diet-care/session/create` [500]: Create diet care session - Expected 200, got 500
- `PUT /api/diet-care/goals` [500]: Update nutrition goals - Expected 200, got 500
- `POST /api/diet-care/meals` [500]: Create meal entry - Expected 201, got 500
- `GET /api/diet-care/progress/weekly` [500]: Get weekly progress - Expected 200, got 500

**Community:**
- `POST /api/community/posts` [422]: Create community post - Expected 201, got 422

**Quiz:**
- `POST /api/quiz/session/start` [422]: Start quiz session - Expected 201, got 422

### Connection Errors (8)

The following tests encountered connection or runtime errors:

**Authentication:**
- `GET /api/auth/check-email`: Check email availability - socket hang up

**Diet Care:**
- `GET /api/diet-care/goals`: Get nutrition goals - socket hang up
- `GET /api/diet-care/meals`: Get meal history - socket hang up
- `GET /api/diet-care/progress/daily`: Get daily progress - socket hang up
- `GET /api/diet-care/streak`: Get logging streak - socket hang up

**Trends & Research:**
- `POST /api/trends/temporal`: Analyze temporal trends - timeout of 5000ms exceeded
- `POST /api/trends/geographic`: Analyze geographic distribution - timeout of 5000ms exceeded
- `POST /api/trends/mesh`: Analyze MeSH categories - timeout of 5000ms exceeded

## Next Steps

1. Implement missing endpoints marked with '?' status
2. Fix failed endpoints to return expected response formats
3. Ensure authentication middleware is properly configured
4. Review and update API documentation
5. Add backend unit tests for new endpoints
