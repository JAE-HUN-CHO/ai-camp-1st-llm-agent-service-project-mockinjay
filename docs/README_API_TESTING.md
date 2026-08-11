# API Compatibility Testing - Quick Reference

## TL;DR

```bash
# Run API compatibility tests
cd frontend
npm run test:api
```

**Current Status:** 51.2% pass rate (21/41 tests)
**Target:** 90% pass rate
**Blocking:** Diet Care feature (0% pass), Quiz (0% pass)

---

## Key Documents

| Document | Purpose | Location |
|----------|---------|----------|
| **Test Report** | Detailed test results | `./api-compatibility-report.md` |
| **Summary** | Executive overview | `./API_COMPATIBILITY_SUMMARY.md` |
| **Testing Guide** | How to use test suite | `./API_TESTING_GUIDE.md` |
| **Backend Fixes** | Required backend changes | `../BACKEND_FIXES_REQUIRED.md` |
| **Test Script** | Source code | `./scripts/test-api-compatibility.ts` |

---

## Critical Issues (Must Fix)

### 1. Diet Care - Database Not Initialized
- **Impact:** Complete feature broken (0/8 tests passing)
- **Fix:** Initialize MongoDB collections in `backend/app/db/connection.py`
- **Time:** 15 minutes

### 2. Community Posts - Field Name Mismatch
- **Impact:** Cannot create posts
- **Fix:** Add field alias in `backend/app/models/community.py`
- **Time:** 10 minutes

### 3. Quiz - Session Type Validation
- **Impact:** Cannot start quiz
- **Fix:** Case-insensitive validation in `backend/app/models/quiz.py`
- **Time:** 15 minutes

**Total Critical Fix Time:** ~40 minutes

---

## Test Results Summary

### Ready to Migrate ✅
- MyPage (100%)
- Terms (100%)
- Chat (100%)
- Auth (71% - mostly working)

### Needs Fixes ⚠️
- Community (33%)
- Trends (25% - performance issues)
- Rooms (0% - auth issue)

### Broken ❌
- Diet Care (0% - critical)
- Quiz (0% - validation)
- Session (0% - minor)

---

## Quick Commands

```bash
# Run tests
npm run test:api

# Check backend health
curl http://localhost:8000/health

# View latest report
cat api-compatibility-report.md

# Test specific endpoint
curl -X GET http://localhost:8000/api/mypage/profile \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Next Steps

1. **Backend Team:** Fix critical issues (see `BACKEND_FIXES_REQUIRED.md`)
2. **Frontend Team:** Wait for backend fixes, adjust status code expectations
3. **QA Team:** Re-run tests after fixes, verify >85% pass rate

**Migration Timeline:**
- Fixes implemented: ~1-2 hours
- Re-test and verify: ~30 minutes
- Frontend migration can begin: After 85%+ pass rate

---

## Success Criteria

Before proceeding with frontend migration:
- [ ] Pass rate ≥ 85%
- [ ] All critical endpoints working
- [ ] Diet Care feature functional
- [ ] Auth flow tested end-to-end
- [ ] Performance acceptable (<5s for most endpoints)

---

For detailed information, see individual documentation files listed above.

*Last Updated: 2025-11-28*
