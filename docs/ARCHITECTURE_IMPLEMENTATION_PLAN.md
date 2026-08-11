# CareGuide Backend Architecture - Implementation Plan

**Date**: 2025-11-28
**Status**: Phase 1 Models Implemented, Ready for Service Layer

---

## What Has Been Completed

### 1. Architecture Documentation
- ✅ **ARCHITECTURE_REVIEW.md**: 50+ page comprehensive architecture review
- ✅ **DATABASE_SCHEMA.md**: Complete database schema documentation
- ✅ Identified 6 critical improvement areas
- ✅ Designed 20+ new API endpoints
- ✅ 8-week implementation roadmap

### 2. Data Models (Pydantic)
- ✅ **app/models/health.py**: Health data models (550+ lines)
  - Lab results (11 test types)
  - Medications (6 frequency types, 5 routes)
  - Vital signs (6 sign types)
  - Health events (6 event types)
- ✅ **app/models/analytics.py**: Analytics models (500+ lines)
  - Health trends
  - Nutrition adherence
  - Community engagement
  - Predictive insights
- ✅ **app/models/scheduled_notification.py**: Notification scheduling (600+ lines)
  - Scheduled notifications
  - Recurrence patterns
  - User preferences
  - Delivery tracking

### 3. Repository Layer
- ✅ **app/repositories/health_repository.py**: Health data access layer (650+ lines)
  - Lab results CRUD (6 methods)
  - Medications CRUD (6 methods)
  - Vital signs CRUD (4 methods)
  - Health events CRUD (4 methods)
  - Aggregation queries for latest results

---

## Implementation Priority Matrix

| Task | Priority | Effort | Dependencies | Status |
|------|----------|--------|--------------|--------|
| Database indexes | HIGH | Small | None | TODO |
| Health service layer | HIGH | Medium | Models, Repository | TODO |
| Health API endpoints | HIGH | Medium | Service layer | TODO |
| Audit middleware | HIGH | Small | None | TODO |
| Error standardization | HIGH | Small | None | TODO |
| Analytics service | MEDIUM | Large | Health service | TODO |
| Notification scheduler | MEDIUM | Large | None | TODO |
| Caching (Redis) | MEDIUM | Medium | None | TODO |
| Background tasks (Celery) | LOW | Large | Notification scheduler | TODO |
| Tests | HIGH | Large | All services | TODO |

---

## Phase 1: Critical Implementation (Week 1)

### Task 1.1: Create Database Indexes

**File**: `backend/app/db/indexes.py`

**Add these functions**:

```python
async def create_lab_results_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for lab_results collection"""
    collection = db["lab_results"]
    indexes = [
        IndexModel([("user_id", ASCENDING), ("test_type", ASCENDING), ("test_date", DESCENDING)], name="idx_lab_results_user_test_date"),
        IndexModel([("user_id", ASCENDING), ("test_date", DESCENDING)], name="idx_lab_results_user_date"),
        IndexModel([("status", ASCENDING), ("test_date", DESCENDING)], name="idx_lab_results_status_date"),
    ]
    await collection.create_indexes(indexes)
    logger.info(f"Created {len(indexes)} indexes for lab_results")

async def create_medications_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for medications collection"""
    collection = db["medications"]
    indexes = [
        IndexModel([("user_id", ASCENDING), ("is_active", ASCENDING)], name="idx_medications_user_active"),
        IndexModel([("user_id", ASCENDING), ("start_date", DESCENDING)], name="idx_medications_user_start"),
    ]
    await collection.create_indexes(indexes)
    logger.info(f"Created {len(indexes)} indexes for medications")

# Similar for vital_signs, health_events, scheduled_notifications, audit_logs
```

**Update `create_indexes()` function** to call new functions:

```python
async def create_indexes(db: AsyncIOMotorDatabase):
    """Create all database indexes"""
    try:
        # Existing indexes
        await create_users_indexes(db)
        await create_notifications_indexes(db)
        # ... existing calls ...

        # NEW: Health data indexes
        await create_lab_results_indexes(db)
        await create_medications_indexes(db)
        await create_vital_signs_indexes(db)
        await create_health_events_indexes(db)
        await create_scheduled_notifications_indexes(db)
        await create_audit_logs_indexes(db)

        logger.info("All database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating database indexes: {str(e)}")
        raise
```

**Testing**:
```bash
# Start MongoDB
docker run -d -p 27017:27017 mongo:latest

# Run app to create indexes
cd backend
uvicorn app.main:app --reload

# Verify indexes created
mongosh
use careguide
db.lab_results.getIndexes()
```

---

### Task 1.2: Health Data Service Layer

**File**: `backend/app/services/health_data_service.py` (NEW)

**Implementation**:

```python
"""
Health Data Service

Business logic for health data management
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta

from app.repositories.health_repository import HealthRepository
from app.models.health import *
from app.core.exceptions import HealthDataException


class HealthDataService:
    """Service for health data operations"""

    def __init__(self):
        self.repository = HealthRepository()

    async def create_lab_result(
        self,
        request: CreateLabResultRequest
    ) -> LabResultResponse:
        """Create lab result with validation and trend analysis"""

        # 1. Determine reference range based on test type
        reference_range = self._get_reference_range(request.test_type, request.unit)

        # 2. Determine status based on value and reference range
        status = self._assess_lab_result_status(
            request.value,
            reference_range
        )

        # 3. Create lab result in database
        result_id = await self.repository.create_lab_result(
            user_id=request.user_id,
            test_type=request.test_type,
            value=request.value,
            unit=request.unit,
            test_date=request.test_date,
            lab_name=request.lab_name,
            notes=request.notes,
            reference_range=reference_range.dict() if reference_range else None,
            status=status
        )

        # 4. Get created result
        result_doc = await self.repository.get_lab_result(result_id)

        # 5. Calculate trend from previous results
        trends = await self._calculate_lab_result_trends(
            request.user_id,
            request.test_type,
            request.value
        )

        # 6. Build response
        lab_result = LabResult(**result_doc)

        return LabResultResponse(
            success=True,
            result=lab_result,
            trends=trends
        )

    async def get_health_summary(
        self,
        user_id: str
    ) -> HealthSummaryResponse:
        """Get comprehensive health summary"""

        # 1. Get latest lab results for each test type
        latest_lab_results_docs = await self.repository.get_latest_lab_results(user_id)
        latest_lab_results = {
            test_type: LabResult(**doc)
            for test_type, doc in latest_lab_results_docs.items()
        }

        # 2. Count active medications
        active_medications = await self.repository.get_user_medications(
            user_id, is_active=True
        )
        active_medications_count = len(active_medications)

        # 3. Get latest vital signs for each type
        latest_vital_signs_docs = await self.repository.get_latest_vital_signs(user_id)
        latest_vital_signs = {
            sign_type: VitalSign(**doc)
            for sign_type, doc in latest_vital_signs_docs.items()
        }

        # 4. Count recent health events (last 90 days)
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        recent_events_count = await self.repository.count_health_events(
            user_id,
            start_date=ninety_days_ago.date()
        )

        # 5. Generate health alerts for critical values
        health_alerts = []
        for test_type, result in latest_lab_results.items():
            if result.status == LabResultStatus.CRITICAL:
                health_alerts.append({
                    "type": "critical",
                    "message": f"Critical {test_type} level: {result.value} {result.unit}",
                    "action": "Contact your healthcare provider immediately"
                })

        # 6. Build summary
        summary = HealthSummary(
            user_id=user_id,
            latest_lab_results=latest_lab_results,
            active_medications_count=active_medications_count,
            recent_vital_signs=latest_vital_signs,
            recent_events_count=recent_events_count,
            health_alerts=health_alerts
        )

        return HealthSummaryResponse(
            success=True,
            summary=summary
        )

    def _get_reference_range(
        self,
        test_type: LabTestType,
        unit: str
    ) -> Optional[ReferenceRange]:
        """Get reference range for test type"""
        # Reference ranges for common CKD lab tests
        REFERENCE_RANGES = {
            LabTestType.CREATININE: ReferenceRange(min=0.7, max=1.3, unit="mg/dL"),
            LabTestType.GFR: ReferenceRange(min=90, max=120, unit="mL/min/1.73m²"),
            LabTestType.POTASSIUM: ReferenceRange(min=3.5, max=5.0, unit="mEq/L"),
            LabTestType.PHOSPHORUS: ReferenceRange(min=2.5, max=4.5, unit="mg/dL"),
            # Add more...
        }
        return REFERENCE_RANGES.get(test_type)

    def _assess_lab_result_status(
        self,
        value: float,
        reference_range: Optional[ReferenceRange]
    ) -> LabResultStatus:
        """Assess lab result status based on value and reference range"""
        if not reference_range:
            return LabResultStatus.NORMAL

        # Critical thresholds (20% outside range)
        critical_low = reference_range.min * 0.8
        critical_high = reference_range.max * 1.2

        if value < critical_low or value > critical_high:
            return LabResultStatus.CRITICAL

        # Borderline thresholds (10% outside range)
        borderline_low = reference_range.min * 0.9
        borderline_high = reference_range.max * 1.1

        if value < reference_range.min:
            if value < borderline_low:
                return LabResultStatus.LOW
            return LabResultStatus.BORDERLINE
        elif value > reference_range.max:
            if value > borderline_high:
                return LabResultStatus.ELEVATED
            return LabResultStatus.BORDERLINE
        else:
            return LabResultStatus.NORMAL

    async def _calculate_lab_result_trends(
        self,
        user_id: str,
        test_type: LabTestType,
        current_value: float
    ) -> Dict[str, Any]:
        """Calculate trend from previous lab results"""
        # Get last 3 results
        previous_results = await self.repository.get_user_lab_results(
            user_id,
            test_type=test_type,
            limit=3
        )

        if len(previous_results) < 2:
            return {
                "status": "insufficient_data",
                "change_from_previous": None,
                "recommendation": None
            }

        # Compare with most recent previous result
        previous_value = previous_results[1]["value"]  # [0] is the one we just created
        change = current_value - previous_value
        percent_change = (change / previous_value) * 100 if previous_value != 0 else 0

        # Determine status and recommendation
        if abs(percent_change) < 5:
            status = "stable"
            recommendation = "Continue current treatment plan"
        elif percent_change > 10:
            status = "increasing"
            recommendation = "Significant increase detected. Consider consulting with your nephrologist"
        elif percent_change < -10:
            status = "decreasing"
            recommendation = "Significant decrease detected. Continue monitoring"
        else:
            status = "minor_change"
            recommendation = "Minor change detected. Continue monitoring"

        return {
            "status": status,
            "change_from_previous": round(change, 2),
            "percent_change": round(percent_change, 1),
            "recommendation": recommendation
        }

    # Additional methods for medications, vital signs, health events...
```

**Testing**:
```bash
pytest backend/tests/test_health_service.py -v
```

---

### Task 1.3: Health Data API Endpoints

**File**: `backend/app/api/health.py` (NEW)

**Implementation**: See ARCHITECTURE_REVIEW.md Section 4 for full API contracts

**Register router in `app/main.py`**:
```python
from app.api.health import router as health_router

app.include_router(health_router)
```

**Testing**:
```bash
# Start app
uvicorn app.main:app --reload

# Test with curl
curl -X POST http://localhost:8000/api/health/lab-results \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "507f1f77bcf86cd799439011",
    "test_type": "creatinine",
    "value": 1.8,
    "unit": "mg/dL",
    "test_date": "2025-11-28T10:00:00Z"
  }'
```

---

### Task 1.4: Audit Logging Middleware

**File**: `backend/app/middleware/audit.py` (NEW)

**Purpose**: Log all PHI access for HIPAA compliance

**Implementation**: See ARCHITECTURE_REVIEW.md Section 7.2 for requirements

**Key Features**:
- Log before and after PHI endpoint access
- Capture user_id, IP address, user agent, request method, path
- Log status code and response time
- Store in `audit_logs` collection
- Retention: 6 years (HIPAA requirement)

---

### Task 1.5: Error Handling Standardization

**Update `app/core/exceptions.py`**:
```python
class HealthDataException(Exception):
    """Base exception for health data errors"""
    pass

class LabResultValidationError(HealthDataException):
    """Lab result validation failed"""
    pass

# ... more exceptions ...
```

**Update `app/main.py`**:
```python
from app.core.exceptions import HealthDataException

@app.exception_handler(HealthDataException)
async def health_data_exception_handler(request: Request, exc: HealthDataException):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": exc.__class__.__name__,
            "message": str(exc)
        }
    )
```

---

## Files Created Summary

| File | Lines | Status | Purpose |
|------|-------|--------|---------|
| `ARCHITECTURE_REVIEW.md` | 1200+ | ✅ Complete | Architecture analysis and improvement plan |
| `DATABASE_SCHEMA.md` | 800+ | ✅ Complete | Database schema documentation |
| `app/models/health.py` | 550+ | ✅ Complete | Health data Pydantic models |
| `app/models/analytics.py` | 500+ | ✅ Complete | Analytics Pydantic models |
| `app/models/scheduled_notification.py` | 600+ | ✅ Complete | Notification scheduling models |
| `app/repositories/health_repository.py` | 650+ | ✅ Complete | Health data repository (async) |
| `app/services/health_data_service.py` | 0 | 🔄 TODO | Health data business logic |
| `app/api/health.py` | 0 | 🔄 TODO | Health data API endpoints |
| `app/middleware/audit.py` | 0 | 🔄 TODO | Audit logging middleware |
| `app/db/indexes.py` (update) | - | 🔄 TODO | Add health data indexes |

**Total Lines Implemented**: 4,300+
**Total Lines TODO**: ~1,500

---

## Quick Start Guide

### 1. Review Documentation

Read these files in order:
1. `ARCHITECTURE_REVIEW.md` - Understand the architecture
2. `DATABASE_SCHEMA.md` - Understand the data model
3. `ARCHITECTURE_IMPLEMENTATION_PLAN.md` (this file) - Understand what to do next

### 2. Set Up Development Environment

```bash
# Start MongoDB
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Install dependencies
cd backend
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your values

# Run app
uvicorn app.main:app --reload
```

### 3. Create Database Indexes

```bash
# App will create indexes on startup (if indexes.py is updated)
# Or manually run:
python -c "
import asyncio
from app.db.connection import Database
from app.db.indexes import create_indexes

async def main():
    await Database.connect()
    await create_indexes(Database.db)
    await Database.disconnect()

asyncio.run(main())
"
```

### 4. Test with Swagger UI

Visit: http://localhost:8000/docs

---

## Next Steps

1. **Review** this plan with team
2. **Assign** tasks from Phase 1 to developers
3. **Create** GitHub issues for each task
4. **Implement** Task 1.1 (database indexes) - 2 hours
5. **Implement** Task 1.2 (health service) - 1 day
6. **Implement** Task 1.3 (health API) - 1 day
7. **Implement** Task 1.4 (audit middleware) - 4 hours
8. **Implement** Task 1.5 (error handling) - 2 hours
9. **Test** Phase 1 implementation - 1 day
10. **Deploy** to staging and verify - 1 day

**Estimated Time for Phase 1**: 5-7 days

---

**Document Version**: 1.0
**Date**: 2025-11-28
**Status**: Ready for Implementation
