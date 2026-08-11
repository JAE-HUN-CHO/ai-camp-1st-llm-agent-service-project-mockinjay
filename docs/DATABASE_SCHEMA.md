# CareGuide Database Schema Documentation

**Database**: MongoDB 7.0+
**Driver**: Motor (Async Python Driver)
**Last Updated**: 2025-11-28

---

## Overview

The CareGuide database uses MongoDB collections to store user data, health records, nutrition tracking, community interactions, and AI agent sessions. The schema is designed for flexibility, scalability, and healthcare compliance (HIPAA-ready).

### Collection Summary

| Collection | Purpose | Indexes | Estimated Size |
|------------|---------|---------|----------------|
| `users` | User accounts and authentication | 5 | 1-10K docs |
| `lab_results` | Lab test results (creatinine, GFR, etc.) | 3 | 10-100K docs |
| `medications` | Medication schedules and adherence | 2 | 1-10K docs |
| `vital_signs` | Blood pressure, weight, fluid intake | 2 | 100K-1M docs |
| `health_events` | Hospitalizations, procedures | 2 | 1-10K docs |
| `diet_meals` | Meal logging and nutrition data | 2 | 100K-1M docs |
| `diet_goals` | User dietary targets per CKD stage | 1 | 1-10K docs |
| `scheduled_notifications` | Future notification delivery queue | 3 | 10-100K docs |
| `notifications` | Past notifications | 5 | 100K-1M docs |
| `posts` | Community forum posts | 3 | 10-100K docs |
| `bookmarks` | Saved research papers | 2 | 10-100K docs |
| `audit_logs` | Security and compliance logs | 4 | 1M+ docs |

---

## Core Collections

### 1. users

**Purpose**: User accounts, authentication, and profile information

**Schema**:
```javascript
{
  "_id": ObjectId,
  "username": String,        // Unique username
  "email": String,           // Unique email
  "password": String,        // Bcrypt hashed
  "fullName": String,
  "profile": String,         // "general", "patient", "researcher"
  "role": String,            // "user", "admin"
  "parlant_customer_id": String,  // Parlant AI chat customer ID

  // Extended health profile (NEW)
  "health_profile": {
    "ckd_stage": String,     // "1", "2", "3a", "3b", "4", "5"
    "diagnosis_date": ISODate,
    "primary_nephrologist": String,
    "hospital": String,
    "comorbidities": [String],  // e.g., ["hypertension", "diabetes_type_2"]
    "dialysis_status": String,  // "not_on_dialysis", "hemodialysis", "peritoneal_dialysis"
    "transplant_status": String // "not_transplanted", "on_waitlist", "transplanted"
  },

  // Notification preferences (NEW)
  "notification_preferences": {
    "medication_reminders": Boolean,
    "lab_test_reminders": Boolean,
    "health_alerts": Boolean,
    "community_updates": Boolean,
    "newsletter": Boolean,
    "sms_enabled": Boolean,
    "email_enabled": Boolean,
    "push_enabled": Boolean
  },

  // Privacy settings (NEW)
  "privacy": {
    "data_sharing_consent": Boolean,
    "research_participation": Boolean,
    "anonymized_data_sharing": Boolean
  },

  "created_at": ISODate,
  "updated_at": ISODate,
  "last_login": ISODate
}
```

**Indexes**:
```javascript
db.users.createIndex({ "email": 1 }, { unique: true })
db.users.createIndex({ "username": 1 }, { unique: true })
db.users.createIndex({ "role": 1 })
db.users.createIndex({ "created_at": -1 })
db.users.createIndex({ "profile": 1, "role": 1 })
```

**Sample Document**:
```javascript
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "username": "johndoe",
  "email": "john@example.com",
  "password": "$2b$12$...",  // Bcrypt hash
  "fullName": "John Doe",
  "profile": "patient",
  "role": "user",
  "health_profile": {
    "ckd_stage": "3b",
    "diagnosis_date": ISODate("2023-05-15"),
    "primary_nephrologist": "Dr. Kim",
    "hospital": "Seoul Medical Center",
    "comorbidities": ["hypertension", "diabetes_type_2"],
    "dialysis_status": "not_on_dialysis",
    "transplant_status": "not_transplanted"
  },
  "created_at": ISODate("2025-01-15T10:00:00Z"),
  "last_login": ISODate("2025-11-28T08:00:00Z")
}
```

---

## Health Data Collections (NEW)

### 2. lab_results

**Purpose**: Lab test results for monitoring kidney function

**Schema**:
```javascript
{
  "_id": ObjectId,
  "user_id": String,         // Reference to users._id
  "test_type": String,       // "creatinine", "gfr", "potassium", "phosphorus", etc.
  "value": Number,           // Test result value
  "unit": String,            // "mg/dL", "mL/min/1.73m²", etc.
  "test_date": ISODate,      // When the test was performed
  "lab_name": String,        // Name of testing laboratory
  "reference_range": {
    "min": Number,
    "max": Number,
    "unit": String
  },
  "status": String,          // "normal", "borderline", "elevated", "low", "critical"
  "notes": String,           // Optional notes
  "verified": Boolean,       // Whether result is verified by healthcare provider
  "created_at": ISODate,
  "updated_at": ISODate
}
```

**Indexes**:
```javascript
db.lab_results.createIndex({ "user_id": 1, "test_type": 1, "test_date": -1 })
db.lab_results.createIndex({ "user_id": 1, "test_date": -1 })
db.lab_results.createIndex({ "status": 1, "test_date": -1 })
```

**Sample Document**:
```javascript
{
  "_id": ObjectId("507f1f77bcf86cd799439099"),
  "user_id": "507f1f77bcf86cd799439011",
  "test_type": "creatinine",
  "value": 1.8,
  "unit": "mg/dL",
  "test_date": ISODate("2025-11-28T10:30:00Z"),
  "lab_name": "Seoul Medical Center",
  "reference_range": {
    "min": 0.7,
    "max": 1.3,
    "unit": "mg/dL"
  },
  "status": "elevated",
  "notes": "Fasting test",
  "verified": true,
  "created_at": ISODate("2025-11-28T11:00:00Z"),
  "updated_at": ISODate("2025-11-28T11:00:00Z")
}
```

### 3. medications

**Purpose**: Track user medications, schedules, and adherence

**Schema**:
```javascript
{
  "_id": ObjectId,
  "user_id": String,
  "medication_name": String,
  "generic_name": String,
  "dosage": String,          // e.g., "40mg"
  "frequency": String,       // "once_daily", "twice_daily", etc.
  "schedule": [String],      // ["09:00", "21:00"]
  "route": String,           // "oral", "injection", "topical"
  "start_date": ISODate,
  "end_date": ISODate,       // null for ongoing
  "prescribing_doctor": String,
  "purpose": String,
  "side_effects": [String],
  "is_active": Boolean,
  "adherence_rate": Number,  // 0-100 percentage
  "created_at": ISODate,
  "updated_at": ISODate
}
```

**Indexes**:
```javascript
db.medications.createIndex({ "user_id": 1, "is_active": 1 })
db.medications.createIndex({ "user_id": 1, "start_date": -1 })
```

**Sample Document**:
```javascript
{
  "_id": ObjectId("507f1f77bcf86cd799439100"),
  "user_id": "507f1f77bcf86cd799439011",
  "medication_name": "Furosemide",
  "generic_name": "Furosemide",
  "dosage": "40mg",
  "frequency": "twice_daily",
  "schedule": ["09:00", "21:00"],
  "route": "oral",
  "start_date": ISODate("2025-11-28T00:00:00Z"),
  "end_date": null,
  "prescribing_doctor": "Dr. Kim",
  "purpose": "Manage fluid retention",
  "side_effects": ["dizziness", "increased urination"],
  "is_active": true,
  "adherence_rate": 95.0,
  "created_at": ISODate("2025-11-28T11:00:00Z"),
  "updated_at": ISODate("2025-11-28T11:00:00Z")
}
```

### 4. vital_signs

**Purpose**: Track vital signs like blood pressure, weight, fluid intake

**Schema**:
```javascript
{
  "_id": ObjectId,
  "user_id": String,
  "sign_type": String,       // "blood_pressure", "weight", "fluid_intake", etc.
  "recorded_at": ISODate,

  // Type-specific fields
  "systolic": Number,        // For blood_pressure
  "diastolic": Number,       // For blood_pressure
  "weight_kg": Number,       // For weight
  "fluid_ml": Number,        // For fluid_intake or urine_output
  "heart_rate_bpm": Number,  // For heart_rate
  "temperature_c": Number,   // For temperature

  "notes": String,
  "status": String,          // "normal", "borderline_high", "high", "critical"
  "created_at": ISODate
}
```

**Indexes**:
```javascript
db.vital_signs.createIndex({ "user_id": 1, "sign_type": 1, "recorded_at": -1 })
db.vital_signs.createIndex({ "user_id": 1, "recorded_at": -1 })
```

**Sample Document**:
```javascript
{
  "_id": ObjectId("507f1f77bcf86cd799439101"),
  "user_id": "507f1f77bcf86cd799439011",
  "sign_type": "blood_pressure",
  "recorded_at": ISODate("2025-11-28T08:00:00Z"),
  "systolic": 135,
  "diastolic": 85,
  "notes": "Morning reading before medication",
  "status": "borderline_high",
  "created_at": ISODate("2025-11-28T08:05:00Z")
}
```

### 5. health_events

**Purpose**: Record significant health events (hospitalizations, procedures)

**Schema**:
```javascript
{
  "_id": ObjectId,
  "user_id": String,
  "event_type": String,      // "hospitalization", "emergency_visit", "procedure", etc.
  "title": String,
  "description": String,
  "event_date": ISODate,
  "duration_days": Number,
  "facility": String,
  "attending_physician": String,
  "outcome": String,
  "severity": String,        // "mild", "moderate", "severe", "critical"
  "related_lab_results": [String],    // Array of lab_result IDs
  "related_medications": [String],    // Array of medication IDs
  "created_at": ISODate,
  "updated_at": ISODate
}
```

**Indexes**:
```javascript
db.health_events.createIndex({ "user_id": 1, "event_date": -1 })
db.health_events.createIndex({ "user_id": 1, "event_type": 1, "event_date": -1 })
```

**Sample Document**:
```javascript
{
  "_id": ObjectId("507f1f77bcf86cd799439103"),
  "user_id": "507f1f77bcf86cd799439011",
  "event_type": "hospitalization",
  "title": "Kidney Function Evaluation",
  "description": "Admitted for comprehensive kidney function assessment",
  "event_date": ISODate("2025-11-20T00:00:00Z"),
  "duration_days": 3,
  "facility": "Seoul National University Hospital",
  "attending_physician": "Dr. Park",
  "outcome": "Stabilized, adjusted medication dosage",
  "severity": "moderate",
  "related_lab_results": ["507f1f77bcf86cd799439099"],
  "related_medications": ["507f1f77bcf86cd799439100"],
  "created_at": ISODate("2025-11-23T10:00:00Z"),
  "updated_at": ISODate("2025-11-23T10:00:00Z")
}
```

---

## Notification System Collections

### 6. scheduled_notifications (NEW)

**Purpose**: Queue for future notification delivery

**Schema**:
```javascript
{
  "_id": ObjectId,
  "user_id": String,
  "type": String,            // "medication_reminder", "lab_reminder", "health_alert", etc.
  "title": String,
  "message": String,
  "scheduled_time": ISODate,
  "recurrence": {
    "pattern": String,       // "once", "daily", "weekly", "monthly"
    "times": [String],       // ["09:00", "21:00"]
    "days_of_week": [Number],// [1,2,3,4,5] for Mon-Fri
    "day_of_month": Number,  // 15 for monthly
    "end_date": ISODate
  },
  "priority": String,        // "low", "medium", "high", "urgent"
  "channels": [String],      // ["push", "email", "sms"]
  "action_url": String,
  "metadata": Object,        // e.g., { "medication_id": "..." }
  "status": String,          // "scheduled", "sent", "failed", "cancelled"
  "sent_at": ISODate,
  "delivery_attempts": Number,
  "is_active": Boolean,
  "created_at": ISODate,
  "updated_at": ISODate
}
```

**Indexes**:
```javascript
db.scheduled_notifications.createIndex({ "user_id": 1, "scheduled_time": 1 })
db.scheduled_notifications.createIndex({ "scheduled_time": 1, "status": 1 })
db.scheduled_notifications.createIndex({ "is_active": 1, "scheduled_time": 1 })
```

**Sample Document**:
```javascript
{
  "_id": ObjectId("507f1f77bcf86cd799439102"),
  "user_id": "507f1f77bcf86cd799439011",
  "type": "medication_reminder",
  "title": "Time to take Furosemide",
  "message": "Take 40mg Furosemide with water",
  "scheduled_time": ISODate("2025-11-28T09:00:00Z"),
  "recurrence": {
    "pattern": "daily",
    "times": ["09:00", "21:00"]
  },
  "priority": "high",
  "channels": ["push", "email"],
  "action_url": "/medications",
  "metadata": {
    "medication_id": "507f1f77bcf86cd799439100"
  },
  "status": "scheduled",
  "sent_at": null,
  "delivery_attempts": 0,
  "is_active": true,
  "created_at": ISODate("2025-11-27T10:00:00Z"),
  "updated_at": ISODate("2025-11-27T10:00:00Z")
}
```

---

## Compliance Collections (NEW)

### 7. audit_logs

**Purpose**: HIPAA-compliant audit trail for PHI access

**Schema**:
```javascript
{
  "_id": ObjectId,
  "timestamp": ISODate,
  "user_id": String,
  "action": String,          // "VIEW", "CREATE", "UPDATE", "DELETE", "EXPORT", "LOGIN"
  "resource_type": String,   // "lab_results", "medications", "vital_signs", etc.
  "resource_id": String,
  "ip_address": String,
  "user_agent": String,
  "request_method": String,  // "GET", "POST", "PUT", "DELETE"
  "request_path": String,
  "status_code": Number,
  "changes": {               // For UPDATE actions
    "before": Object,
    "after": Object
  },
  "metadata": {
    "session_id": String,
    "location": String
  }
}
```

**Indexes**:
```javascript
db.audit_logs.createIndex({ "user_id": 1, "timestamp": -1 })
db.audit_logs.createIndex({ "action": 1, "timestamp": -1 })
db.audit_logs.createIndex({ "timestamp": -1 })
db.audit_logs.createIndex({ "resource_type": 1, "resource_id": 1 })
```

**Sample Document**:
```javascript
{
  "_id": ObjectId("507f1f77bcf86cd799439200"),
  "timestamp": ISODate("2025-11-28T11:00:00Z"),
  "user_id": "507f1f77bcf86cd799439011",
  "action": "VIEW_LAB_RESULTS",
  "resource_type": "lab_results",
  "resource_id": "507f1f77bcf86cd799439099",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "request_method": "GET",
  "request_path": "/api/health/lab-results/507f1f77bcf86cd799439011",
  "status_code": 200,
  "changes": null,
  "metadata": {
    "session_id": "sess_abc123",
    "location": "Seoul, Korea"
  }
}
```

**Retention Policy**: Keep audit logs for minimum 6 years (HIPAA requirement)

---

## Existing Collections (Summary)

### diet_meals
Stores meal logging data with nutritional breakdowns. See `app/models/diet.py` for schema.

### diet_goals
User dietary targets based on CKD stage. See `app/models/diet.py` for schema.

### notifications
Past notifications (community, quiz, level-up, etc.). See `app/models/notification.py` for schema.

### posts
Community forum posts and comments. See `app/models/community.py` for schema.

### bookmarks
Saved research papers. See `app/models/bookmark.py` for schema.

### user_levels, user_badges, user_points, points_history
Gamification features. See `app/models/gamification.py` for schema.

---

## Data Relationships

### User → Health Data
- One user has many lab results
- One user has many medications
- One user has many vital signs
- One user has many health events

### Health Events → Related Records
- Health events reference lab_results (many-to-many)
- Health events reference medications (many-to-many)

### Medications → Notifications
- Active medications generate scheduled_notifications for reminders

### Users → Community
- One user has many posts
- One user has many bookmarks

---

## Performance Considerations

### Query Patterns

**Most Common Queries**:
1. Get user's latest lab results (by test type)
2. Get active medications for a user
3. Get recent vital signs (last 30 days)
4. Get pending scheduled notifications (for background job)

**Optimization Strategies**:
1. **Compound Indexes**: Use compound indexes for common filter combinations (e.g., `user_id + test_type + test_date`)
2. **Covered Queries**: Ensure indexes include all fields returned by query
3. **Aggregation Pipeline**: Use for analytics queries (trends, adherence rates)
4. **Caching**: Cache frequently accessed data (user profiles, diet goals) in Redis

### Data Size Estimates

| Collection | Growth Rate | Cleanup Strategy |
|------------|-------------|------------------|
| `lab_results` | ~10 records/user/month | Archive after 5 years |
| `medications` | ~5 records/user/year | Keep indefinitely |
| `vital_signs` | ~100 records/user/month | Archive after 2 years |
| `diet_meals` | ~90 records/user/month | Archive after 1 year |
| `audit_logs` | ~1000 records/user/year | Archive after 6 years |

---

## Migration Strategy

### Adding New Collections

When adding new collections (e.g., `lab_results`):

1. **Create Collection** (auto-created on first insert)
2. **Create Indexes** (via `app/db/indexes.py`)
3. **Add to Repository** (via `app/repositories/`)
4. **Add to Service Layer** (via `app/services/`)
5. **Add API Endpoints** (via `app/api/`)

### Schema Changes

MongoDB is schema-less, but Pydantic models enforce validation:

1. **Add Field**: Simply add to Pydantic model with default value
2. **Rename Field**: Migration script to update existing documents
3. **Remove Field**: Remove from Pydantic model (old docs still have it)
4. **Change Type**: Requires migration script

### Example Migration Script

```python
# Migration: Add health_profile to existing users
from app.db.connection import Database

async def migrate_add_health_profile():
    users_collection = Database.get_collection("users")

    result = await users_collection.update_many(
        {"health_profile": {"$exists": False}},
        {
            "$set": {
                "health_profile": {
                    "ckd_stage": "unknown",
                    "diagnosis_date": None,
                    "dialysis_status": "unknown",
                    "transplant_status": "not_transplanted"
                }
            }
        }
    )

    print(f"Updated {result.modified_count} user documents")
```

---

## Backup and Recovery

### Backup Strategy

1. **Full Backup**: Daily at 2:00 AM UTC (MongoDB Atlas automated)
2. **Point-in-Time Recovery**: Enabled (Atlas feature)
3. **Retention**: 30 days for daily backups

### Critical Collections (Priority Backup)

1. `users` - User accounts
2. `lab_results` - Health data (PHI)
3. `medications` - Health data (PHI)
4. `audit_logs` - Compliance requirement

### Recovery Plan

1. **Data Loss < 24h**: Restore from daily backup
2. **Data Corruption**: Point-in-time recovery to before incident
3. **Full Database Loss**: Restore from backup + replay audit logs

---

## Security Considerations

### Encryption

- **At Rest**: MongoDB encryption at rest enabled (Atlas feature)
- **In Transit**: TLS 1.2+ for all connections
- **Field-Level**: Sensitive fields (SSN, medical record numbers) encrypted

### Access Control

- **Authentication**: SCRAM-SHA-256 (MongoDB default)
- **Authorization**: Role-based access control (RBAC)
- **Network**: Whitelist IP addresses (production only)

### PHI Fields (Protected Health Information)

Collections containing PHI:
- `users` (name, email, health_profile)
- `lab_results` (all fields)
- `medications` (all fields)
- `vital_signs` (all fields)
- `health_events` (all fields)

PHI access is logged in `audit_logs`.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-28
**Maintained By**: Backend Team
