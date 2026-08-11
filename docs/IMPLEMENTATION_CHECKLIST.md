# Implementation Checklist: Backend API Improvements

## Quick Start

This checklist guides you through integrating the new backend API improvements into the CareGuide application.

---

## Phase 1: Setup and Configuration (30 minutes)

### 1.1 Update Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 1.2 Include New Routers in Main App

**File**: `/backend/app/main.py`

```python
# Add these imports at the top
from app.api.health_tracking import router as health_router
from app.api.auth_enhanced import router as auth_enhanced_router

# Add these router includes (around line 115)
app.include_router(health_router)
app.include_router(auth_enhanced_router)
```

### 1.3 Verify Database Connection

```bash
# Start MongoDB if not running
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Test connection
curl http://localhost:8000/db-check
```

### 1.4 Test Server Startup

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Expected Output**:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## Phase 2: Enhanced Authentication (1 hour)

### 2.1 Test Email Validation Endpoint

```bash
# Test email availability
curl -X POST http://localhost:8000/api/auth/check-email \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Expected response:
# {"available": true/false, "message": "...", "suggestions": null}
```

### 2.2 Test Username Validation Endpoint

```bash
curl -X POST http://localhost:8000/api/auth/check-username \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser"}'
```

### 2.3 Update Frontend Auth Service

**File**: `/new_frontend/src/services/authApi.ts`

Add these functions:

```typescript
export async function checkEmailAvailability(email: string): Promise<boolean> {
  try {
    const response = await api.post('/api/auth/check-email', { email });
    return response.data.available;
  } catch (error) {
    return false;
  }
}

export async function checkUsernameAvailability(username: string) {
  try {
    const response = await api.post('/api/auth/check-username', { username });
    return response.data;
  } catch (error) {
    return { available: false, suggestions: [] };
  }
}
```

### 2.4 Integrate into Signup Form

**File**: `/new_frontend/src/pages/SignupPage.tsx`

Add debounced email/username validation:

```typescript
import { useDebouncedCallback } from 'use-debounce';
import { checkEmailAvailability, checkUsernameAvailability } from '../services/authApi';

const [emailAvailable, setEmailAvailable] = useState<boolean | null>(null);
const [usernameAvailable, setUsernameAvailable] = useState<boolean | null>(null);

const checkEmail = useDebouncedCallback(async (email: string) => {
  if (!email || !email.includes('@')) return;
  const available = await checkEmailAvailability(email);
  setEmailAvailable(available);
}, 500);

// Add to email input onChange
onChange={(e) => {
  setEmail(e.target.value);
  checkEmail(e.target.value);
}}

// Add validation indicator
{emailAvailable === false && (
  <p className="text-red-500 text-sm">이미 사용 중인 이메일입니다</p>
)}
{emailAvailable === true && (
  <p className="text-green-500 text-sm">사용 가능한 이메일입니다</p>
)}
```

### 2.5 Testing Checklist

- [ ] Email validation works with debounce
- [ ] Username validation works with suggestions
- [ ] Error handling works properly
- [ ] UI feedback is clear and helpful

---

## Phase 3: Health Tracking API (2 hours)

### 3.1 Create Health API Service

**File**: `/new_frontend/src/services/healthApi.ts` (new file)

```typescript
import api from './api';

export interface LabResult {
  test_date: string;
  creatinine_mg_dl?: number;
  gfr_ml_min?: number;
  bun_mg_dl?: number;
  potassium_meq_l?: number;
  phosphorus_mg_dl?: number;
  notes?: string;
  doctor_name?: string;
}

export async function createLabResult(data: LabResult) {
  const response = await api.post('/api/health/labs', data);
  return response.data;
}

export async function getLabResults(startDate?: string, endDate?: string) {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);

  const response = await api.get(`/api/health/labs?${params.toString()}`);
  return response.data;
}

export async function getLabTrend(testType: string, months: number = 6) {
  const response = await api.get(`/api/health/labs/trends/${testType}?months=${months}`);
  return response.data;
}

export async function createMedication(data: any) {
  const response = await api.post('/api/health/medications', data);
  return response.data;
}

export async function getMedications(activeOnly: boolean = true) {
  const response = await api.get(`/api/health/medications?active_only=${activeOnly}`);
  return response.data;
}
```

### 3.2 Test Health API Endpoints

```bash
# Get auth token first
TOKEN=$(curl -X POST http://localhost:8000/api/auth/dev-login | jq -r .access_token)

# Create lab result
curl -X POST http://localhost:8000/api/health/labs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_date": "2024-01-15",
    "creatinine_mg_dl": 1.8,
    "gfr_ml_min": 42,
    "bun_mg_dl": 25
  }'

# Get lab results
curl -X GET http://localhost:8000/api/health/labs \
  -H "Authorization: Bearer $TOKEN"

# Get trend
curl -X GET "http://localhost:8000/api/health/labs/trends/creatinine?months=6" \
  -H "Authorization: Bearer $TOKEN"
```

### 3.3 Create Lab Results Component

**File**: `/new_frontend/src/components/health/LabResultsManager.tsx` (new file)

```typescript
import { useState, useEffect } from 'react';
import { getLabResults, createLabResult, getLabTrend } from '../../services/healthApi';
import { toast } from 'sonner';

export const LabResultsManager = () => {
  const [labs, setLabs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLabs();
  }, []);

  const loadLabs = async () => {
    try {
      const data = await getLabResults();
      setLabs(data.results);
    } catch (error) {
      toast.error('검사 결과를 불러올 수 없습니다');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (formData: any) => {
    try {
      await createLabResult(formData);
      toast.success('검사 결과가 저장되었습니다');
      loadLabs();
    } catch (error) {
      toast.error('저장 중 오류가 발생했습니다');
    }
  };

  return (
    <div>
      {/* Lab results form and list */}
    </div>
  );
};
```

### 3.4 Add Health Tracking Route

**File**: `/new_frontend/src/routes/AppRoutes.tsx`

```typescript
import { LabResultsManager } from '../components/health/LabResultsManager';

// Add route
<Route path="/health/labs" element={<LabResultsManager />} />
```

### 3.5 Testing Checklist

- [ ] Can create lab results
- [ ] Can view lab results history
- [ ] Can see lab trends chart
- [ ] Can create medications
- [ ] Can view medication list
- [ ] Error handling works
- [ ] Loading states work

---

## Phase 4: Integration Testing (1 hour)

### 4.1 API Health Checks

```bash
# Check all new endpoints
curl http://localhost:8000/api/auth/health
curl http://localhost:8000/api/health/health
```

### 4.2 End-to-End Flow Testing

**Test 1: Complete Registration Flow**
1. Go to signup page
2. Enter email → see validation in real-time
3. Enter username → see validation
4. Complete registration
5. Verify redirect to chat page

**Test 2: Lab Results Flow**
1. Login to application
2. Navigate to health tracking
3. Add new lab result
4. View lab results list
5. Check trend chart

**Test 3: Medication Management**
1. Login to application
2. Navigate to medications
3. Add new medication with reminder
4. View medication list
5. Update medication
6. Delete medication

### 4.3 Browser DevTools Checks

- [ ] No console errors
- [ ] Network requests successful (200/201 status)
- [ ] JWT tokens attached to requests
- [ ] Response data matches expected format
- [ ] Error states handled gracefully

### 4.4 Performance Checks

```bash
# Use Apache Bench for basic load testing
ab -n 100 -c 10 http://localhost:8000/api/health/labs \
  -H "Authorization: Bearer $TOKEN"

# Expected: < 200ms average response time
```

---

## Phase 5: Documentation & Deployment (30 minutes)

### 5.1 Update API Documentation

**File**: `/backend/README.md`

Add section:

```markdown
## New API Features

### Health Tracking
- Lab results tracking (creatinine, GFR, etc.)
- Medication management with reminders
- Vital signs tracking
- Trend analysis

See [API_DESIGN.md](./API_DESIGN.md) for full documentation.

### Enhanced Authentication
- Real-time email/username validation
- Password reset flow
- Account deletion

See [API_INTEGRATION_GUIDE.md](./API_INTEGRATION_GUIDE.md) for integration examples.
```

### 5.2 Update Frontend README

**File**: `/new_frontend/README.md`

Add section:

```markdown
## New Features

### Health Tracking
Users can now track:
- Lab test results with trend analysis
- Medications with reminder support
- Vital signs (coming soon)
- Symptoms (coming soon)

### Enhanced Registration
- Real-time email/username validation
- Better user feedback
- Password reset functionality
```

### 5.3 Environment Configuration

**Production checklist**:

```bash
# Backend .env
ENVIRONMENT=production
CORS_ORIGINS=https://careguide.com,https://www.careguide.com
RATE_LIMIT_ENABLED=true
LOG_LEVEL=INFO

# Frontend .env
VITE_API_BASE_URL=https://api.careguide.com
VITE_ENVIRONMENT=production
```

### 5.4 Deployment Steps

1. **Backend Deployment**:
```bash
# Build and push Docker image
docker build -t careguide-backend:latest .
docker push careguide-backend:latest

# Deploy to server
kubectl apply -f k8s/backend-deployment.yaml
```

2. **Frontend Deployment**:
```bash
# Build production bundle
npm run build

# Deploy to CDN/hosting
vercel deploy --prod
```

3. **Database Migration**:
```bash
# Create indexes for new collections
python scripts/create_health_indexes.py
```

---

## Troubleshooting

### Issue 1: Import Errors

**Problem**: `ModuleNotFoundError: No module named 'app.models.health_tracking'`

**Solution**:
```bash
# Verify file exists
ls backend/app/models/health_tracking.py

# Check __init__.py
cat backend/app/models/__init__.py

# Restart server
pkill -f uvicorn
uvicorn app.main:app --reload
```

### Issue 2: CORS Errors

**Problem**: Frontend can't connect to backend

**Solution**:
```python
# In backend/app/main.py, verify CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue 3: 401 Unauthorized

**Problem**: Auth token not working

**Solution**:
```typescript
// Check token storage
console.log(localStorage.getItem('careguide_token'));

// Verify token is sent
// In browser DevTools > Network > Headers
// Should see: Authorization: Bearer eyJ...
```

### Issue 4: Database Connection

**Problem**: `pymongo.errors.ServerSelectionTimeoutError`

**Solution**:
```bash
# Check MongoDB is running
docker ps | grep mongodb

# If not running, start it
docker start mongodb

# Or create new instance
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

---

## Success Criteria

### Backend API
- [x] All new endpoints documented
- [ ] Health check endpoints return 200
- [ ] Authentication works with JWT
- [ ] CORS configured correctly
- [ ] Error responses are consistent
- [ ] No Python errors in logs

### Frontend Integration
- [ ] Can validate email/username in real-time
- [ ] Can create and view lab results
- [ ] Can manage medications
- [ ] Charts render correctly
- [ ] Error states handled gracefully
- [ ] Loading states work

### Performance
- [ ] API response time < 200ms (p95)
- [ ] No memory leaks
- [ ] Database queries optimized
- [ ] Frontend bundle size reasonable

### Documentation
- [ ] API endpoints documented
- [ ] Integration guide complete
- [ ] Code examples provided
- [ ] README files updated

---

## Next Steps

After completing this checklist:

1. **User Testing**: Get feedback from real users
2. **Performance Monitoring**: Set up monitoring (Prometheus, Grafana)
3. **Security Audit**: Review auth and data protection
4. **Rate Limiting**: Implement rate limits
5. **Caching**: Add Redis for performance
6. **Real-time Features**: Implement WebSocket support

---

## Support

- **API Documentation**: See `/backend/API_DESIGN.md`
- **Integration Guide**: See `/backend/API_INTEGRATION_GUIDE.md`
- **Summary**: See `/backend/API_IMPROVEMENTS_SUMMARY.md`

For issues or questions, contact the development team or create an issue in the repository.
