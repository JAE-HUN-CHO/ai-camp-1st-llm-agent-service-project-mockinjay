# CareGuide API Integration Guide

## Overview

This guide provides practical examples and best practices for integrating with the CareGuide backend API from the React TypeScript frontend.

## Base Configuration

### API Client Setup (`src/services/api.ts`)

The current implementation already includes:
- ✅ Axios instance with base URL configuration
- ✅ JWT token injection via interceptors
- ✅ CSRF protection for mutations
- ✅ Error handling with user-friendly toasts
- ✅ Automatic 401 handling and redirects

**Current Configuration:**
```typescript
import axios from 'axios';
import { env } from '../config/env';

const api = axios.create({
  baseURL: env.apiBaseUrl,  // Default: http://localhost:8000
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - adds JWT token
api.interceptors.request.use((config) => {
  const token = secureTokenStorage.get() || storage.get<string>('careguide_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

---

## Authentication & User Management

### 1. Registration

**Endpoint**: `POST /api/auth/register`

**Frontend Implementation**:
```typescript
// src/services/authApi.ts
import api from './api';

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  fullName?: string;
  profile: 'general' | 'patient' | 'researcher';
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    username: string;
    email: string;
    fullName?: string;
    profile: string;
    parlant_customer_id?: string;
  };
}

export async function register(data: RegisterData): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/api/auth/register', data);

  // Store token
  storage.set('careguide_token', response.data.access_token);
  storage.set('careguide_user', response.data.user);

  return response.data;
}
```

**Usage in Component**:
```typescript
// src/pages/SignupPage.tsx
import { register } from '../services/authApi';
import { toast } from 'sonner';

const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();

  try {
    const result = await register({
      username: formData.username,
      email: formData.email,
      password: formData.password,
      fullName: formData.fullName,
      profile: formData.profile,
    });

    toast.success('회원가입이 완료되었습니다!');
    navigate('/chat');
  } catch (error: any) {
    if (error.response?.status === 400) {
      toast.error(error.response.data.detail);
    } else {
      toast.error('회원가입 중 오류가 발생했습니다');
    }
  }
};
```

### 2. Email/Username Validation (NEW)

**Endpoint**: `POST /api/auth/check-email`

**Frontend Implementation**:
```typescript
// src/services/authApi.ts
export async function checkEmailAvailability(email: string): Promise<boolean> {
  try {
    const response = await api.post('/api/auth/check-email', { email });
    return response.data.available;
  } catch (error) {
    return false;
  }
}

export async function checkUsernameAvailability(username: string): Promise<{
  available: boolean;
  suggestions?: string[];
}> {
  try {
    const response = await api.post('/api/auth/check-username', { username });
    return response.data;
  } catch (error) {
    return { available: false };
  }
}
```

**Usage with Debounce**:
```typescript
// src/components/auth/EmailInput.tsx
import { useDebouncedCallback } from 'use-debounce';
import { checkEmailAvailability } from '../../services/authApi';

const [emailAvailable, setEmailAvailable] = useState<boolean | null>(null);
const [isChecking, setIsChecking] = useState(false);

const checkEmail = useDebouncedCallback(async (email: string) => {
  if (!email || !email.includes('@')) return;

  setIsChecking(true);
  const available = await checkEmailAvailability(email);
  setEmailAvailable(available);
  setIsChecking(false);
}, 500);

<input
  type="email"
  value={email}
  onChange={(e) => {
    setEmail(e.target.value);
    checkEmail(e.target.value);
  }}
/>
{isChecking && <span>확인 중...</span>}
{emailAvailable === false && <span className="text-red-500">이미 사용 중인 이메일입니다</span>}
{emailAvailable === true && <span className="text-green-500">사용 가능한 이메일입니다</span>}
```

### 3. Password Reset Flow (NEW)

**Step 1: Request Reset**

```typescript
// src/services/authApi.ts
export async function forgotPassword(email: string): Promise<void> {
  await api.post('/api/auth/forgot-password', { email });
}

// Usage
const handleForgotPassword = async () => {
  try {
    await forgotPassword(email);
    toast.success('비밀번호 재설정 링크가 이메일로 전송되었습니다');
    setShowResetSent(true);
  } catch (error) {
    toast.error('오류가 발생했습니다');
  }
};
```

**Step 2: Reset with Token**

```typescript
// src/services/authApi.ts
export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await api.post('/api/auth/reset-password', {
    token,
    new_password: newPassword,
    confirm_password: newPassword,
  });
}

// src/pages/ResetPasswordPage.tsx
const token = new URLSearchParams(location.search).get('token');

const handleResetPassword = async () => {
  try {
    await resetPassword(token!, newPassword);
    toast.success('비밀번호가 재설정되었습니다');
    navigate('/login');
  } catch (error) {
    toast.error('재설정 링크가 유효하지 않거나 만료되었습니다');
  }
};
```

---

## Health Tracking (NEW)

### 1. Lab Results

**Endpoint**: `POST /api/health/labs`

**Frontend Implementation**:
```typescript
// src/services/healthApi.ts
export interface LabResult {
  test_date: string;
  creatinine_mg_dl?: number;
  gfr_ml_min?: number;
  bun_mg_dl?: number;
  potassium_meq_l?: number;
  phosphorus_mg_dl?: number;
  hemoglobin_g_dl?: number;
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
```

**Usage in Component**:
```typescript
// src/components/health/LabResultsChart.tsx
import { useEffect, useState } from 'react';
import { getLabTrend } from '../../services/healthApi';
import { Line } from 'react-chartjs-2';

const LabResultsChart = ({ testType }: { testType: string }) => {
  const [trendData, setTrendData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTrend();
  }, [testType]);

  const loadTrend = async () => {
    try {
      const data = await getLabTrend(testType, 6);
      setTrendData(data);
    } catch (error) {
      toast.error('데이터를 불러올 수 없습니다');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  const chartData = {
    labels: trendData.data_points.map(p => new Date(p.date).toLocaleDateString()),
    datasets: [{
      label: testType,
      data: trendData.data_points.map(p => p.value),
      borderColor: getTrendColor(trendData.trend),
      fill: false,
    }]
  };

  return (
    <div>
      <Line data={chartData} />
      <div className={`trend-indicator ${trendData.trend}`}>
        추세: {getTrendLabel(trendData.trend)}
      </div>
    </div>
  );
};
```

### 2. Medications

**Endpoint**: `POST /api/health/medications`

```typescript
// src/services/healthApi.ts
export interface Medication {
  name: string;
  medication_type: string;
  dosage: string;
  frequency: string;
  start_date?: string;
  prescribing_doctor?: string;
  purpose?: string;
  reminder_enabled?: boolean;
  reminder_times?: string[];
}

export async function createMedication(data: Medication) {
  const response = await api.post('/api/health/medications', data);
  return response.data;
}

export async function getMedications(activeOnly: boolean = true) {
  const response = await api.get(`/api/health/medications?active_only=${activeOnly}`);
  return response.data;
}

export async function updateMedication(id: string, updates: Partial<Medication>) {
  const response = await api.patch(`/api/health/medications/${id}`, updates);
  return response.data;
}

export async function deleteMedication(id: string) {
  await api.delete(`/api/health/medications/${id}`);
}
```

**Usage in Component**:
```typescript
// src/components/health/MedicationList.tsx
import { useEffect, useState } from 'react';
import { getMedications, deleteMedication } from '../../services/healthApi';

const MedicationList = () => {
  const [medications, setMedications] = useState([]);

  useEffect(() => {
    loadMedications();
  }, []);

  const loadMedications = async () => {
    const data = await getMedications(true);
    setMedications(data.medications);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('정말 삭제하시겠습니까?')) return;

    try {
      await deleteMedication(id);
      toast.success('약물이 삭제되었습니다');
      loadMedications();
    } catch (error) {
      toast.error('삭제 중 오류가 발생했습니다');
    }
  };

  return (
    <div className="medication-list">
      {medications.map(med => (
        <div key={med.id} className="medication-card">
          <h3>{med.name}</h3>
          <p>용량: {med.dosage}</p>
          <p>복용 빈도: {med.frequency}</p>
          <button onClick={() => handleDelete(med.id)}>삭제</button>
        </div>
      ))}
    </div>
  );
};
```

---

## Community

### 1. Create Post with Images

**Endpoint**: `POST /api/community/posts`

```typescript
// src/services/communityApi.ts
export interface CreatePostData {
  title: string;
  content: string;
  postType: 'BOARD' | 'CHALLENGE' | 'SURVEY';
  isAnonymous: boolean;
  imageUrls?: string[];
  anonymousId?: string;
}

export async function uploadImage(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/api/community/uploads', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  return response.data.url;
}

export async function createPost(data: CreatePostData) {
  const response = await api.post('/api/community/posts', data);
  return response.data;
}
```

**Usage in Component**:
```typescript
// src/components/community/CreatePostForm.tsx
import { useState } from 'react';
import { createPost, uploadImage } from '../../services/communityApi';

const CreatePostForm = () => {
  const [images, setImages] = useState<File[]>([]);
  const [uploadedUrls, setUploadedUrls] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setImages(prev => [...prev, ...files].slice(0, 3)); // Max 3 images
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      // Upload images first
      setIsUploading(true);
      const urls = await Promise.all(
        images.map(img => uploadImage(img))
      );
      setUploadedUrls(urls);

      // Create post with image URLs
      await createPost({
        title: formData.title,
        content: formData.content,
        postType: 'BOARD',
        isAnonymous: formData.isAnonymous,
        imageUrls: urls,
      });

      toast.success('게시글이 작성되었습니다');
      navigate('/community');
    } catch (error) {
      toast.error('게시글 작성 중 오류가 발생했습니다');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input type="text" placeholder="제목" />
      <textarea placeholder="내용" />
      <input type="file" accept="image/*" multiple onChange={handleImageSelect} />
      <div className="image-preview">
        {images.map((img, i) => (
          <img key={i} src={URL.createObjectURL(img)} alt={`Preview ${i}`} />
        ))}
      </div>
      <button type="submit" disabled={isUploading}>
        {isUploading ? '업로드 중...' : '작성하기'}
      </button>
    </form>
  );
};
```

### 2. Infinite Scroll Pagination

**Endpoint**: `GET /api/community/posts?limit=20&cursor={cursor}`

```typescript
// src/hooks/useCommunityPosts.ts
import { useState, useEffect } from 'react';
import { getCommunityPosts } from '../services/communityApi';

export function useCommunityPosts() {
  const [posts, setPosts] = useState([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);

  const loadPosts = async (refresh: boolean = false) => {
    if (loading) return;
    if (!refresh && !hasMore) return;

    setLoading(true);

    try {
      const data = await getCommunityPosts({
        limit: 20,
        cursor: refresh ? undefined : cursor,
      });

      setPosts(prev => refresh ? data.posts : [...prev, ...data.posts]);
      setCursor(data.nextCursor);
      setHasMore(data.hasMore);
    } catch (error) {
      toast.error('게시글을 불러올 수 없습니다');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPosts(true);
  }, []);

  return { posts, loadMore: () => loadPosts(false), hasMore, loading };
}

// src/pages/CommunityPage.tsx
import { useCommunityPosts } from '../hooks/useCommunityPosts';
import InfiniteScroll from 'react-infinite-scroll-component';

const CommunityPage = () => {
  const { posts, loadMore, hasMore } = useCommunityPosts();

  return (
    <InfiniteScroll
      dataLength={posts.length}
      next={loadMore}
      hasMore={hasMore}
      loader={<div>Loading...</div>}
    >
      {posts.map(post => (
        <PostCard key={post.id} post={post} />
      ))}
    </InfiniteScroll>
  );
};
```

---

## Nutrition & Diet Care

### 1. Image Analysis with Form Data

**Endpoint**: `POST /api/diet-care/nutri-coach` (multipart/form-data)

```typescript
// src/services/dietCareApi.ts
export interface NutriCoachRequest {
  sessionId: string;
  text?: string;
  image?: File;
  age?: number;
  weight_kg?: number;
  height_cm?: number;
  ckd_stage?: number;
}

export async function analyzeNutrition(data: NutriCoachRequest) {
  const formData = new FormData();
  formData.append('session_id', data.sessionId);
  if (data.text) formData.append('text', data.text);
  if (data.image) formData.append('image', data.image);
  if (data.age) formData.append('age', data.age.toString());
  if (data.weight_kg) formData.append('weight_kg', data.weight_kg.toString());
  if (data.ckd_stage) formData.append('ckd_stage', data.ckd_stage.toString());

  const response = await api.post('/api/diet-care/nutri-coach', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  return response.data;
}

export async function createAnalysisSession() {
  const response = await api.post('/api/diet-care/session/create');
  return response.data.session_id;
}
```

**Usage in Component**:
```typescript
// src/components/diet-care/FoodAnalyzer.tsx
import { useState } from 'react';
import { createAnalysisSession, analyzeNutrition } from '../../services/dietCareApi';

const FoodAnalyzer = () => {
  const [image, setImage] = useState<File | null>(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    if (!image) return;

    setLoading(true);

    try {
      // Create session first
      const sessionId = await createAnalysisSession();

      // Analyze food
      const data = await analyzeNutrition({
        sessionId,
        image,
        ckd_stage: 3, // Get from user profile
      });

      setResult(data.analysis);
      toast.success('분석이 완료되었습니다');
    } catch (error) {
      toast.error('분석 중 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="file"
        accept="image/*"
        onChange={(e) => setImage(e.target.files?.[0] || null)}
      />
      {image && <img src={URL.createObjectURL(image)} alt="Preview" />}
      <button onClick={handleAnalyze} disabled={!image || loading}>
        {loading ? '분석 중...' : '분석하기'}
      </button>

      {result && (
        <div className="analysis-result">
          <h3>영양 정보</h3>
          {result.foods.map((food, i) => (
            <div key={i} className="food-item">
              <h4>{food.name} ({food.amount})</h4>
              <p>칼로리: {food.calories} kcal</p>
              <p>단백질: {food.protein_g}g</p>
              <p>나트륨: {food.sodium_mg}mg</p>
              <p>칼륨: {food.potassium_mg}mg</p>
              <p>인: {food.phosphorus_mg}mg</p>
            </div>
          ))}

          <div className="recommendations">
            <h4>추천사항</h4>
            {result.recommendations.map((rec, i) => (
              <p key={i} className="text-green-600">{rec}</p>
            ))}
          </div>

          {result.warnings.length > 0 && (
            <div className="warnings">
              <h4>주의사항</h4>
              {result.warnings.map((warn, i) => (
                <p key={i} className="text-orange-600">{warn}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

---

## Error Handling Patterns

### 1. Global Error Handler (Already Implemented)

The `api.ts` interceptor already handles common errors. For specific cases:

```typescript
// src/utils/errorHandler.ts
export function handleApiError(error: any) {
  if (error.response) {
    switch (error.response.status) {
      case 400:
        // Validation error
        if (error.response.data.detail?.errors) {
          return error.response.data.detail.errors.join(', ');
        }
        return error.response.data.detail || 'Invalid request';

      case 404:
        return 'Resource not found';

      case 409:
        return 'This resource already exists';

      case 422:
        // FastAPI validation error
        const errors = error.response.data.detail;
        if (Array.isArray(errors)) {
          return errors.map(e => e.msg).join(', ');
        }
        return 'Validation error';

      default:
        return 'An error occurred';
    }
  }

  if (error.request) {
    return 'Network error. Please check your connection';
  }

  return 'An unexpected error occurred';
}

// Usage
try {
  await createPost(data);
} catch (error) {
  const message = handleApiError(error);
  toast.error(message);
}
```

---

## Performance Optimization

### 1. Request Caching with React Query

```bash
npm install @tanstack/react-query
```

```typescript
// src/main.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
    },
  },
});

<QueryClientProvider client={queryClient}>
  <App />
</QueryClientProvider>
```

```typescript
// src/hooks/useLabResults.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getLabResults, createLabResult } from '../services/healthApi';

export function useLabResults() {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['labResults'],
    queryFn: () => getLabResults(),
  });

  const createMutation = useMutation({
    mutationFn: createLabResult,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['labResults'] });
      toast.success('검사 결과가 저장되었습니다');
    },
  });

  return {
    labResults: data?.results || [],
    isLoading,
    error,
    createLabResult: createMutation.mutate,
  };
}
```

### 2. Optimistic Updates

```typescript
// src/hooks/useCommunityLike.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { likePost, unlikePost } from '../services/communityApi';

export function useCommunityLike(postId: string) {
  const queryClient = useQueryClient();

  const likeMutation = useMutation({
    mutationFn: () => likePost(postId),
    onMutate: async () => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['post', postId] });

      // Snapshot previous value
      const previousPost = queryClient.getQueryData(['post', postId]);

      // Optimistically update
      queryClient.setQueryData(['post', postId], (old: any) => ({
        ...old,
        likes: old.likes + 1,
        likedByMe: true,
      }));

      return { previousPost };
    },
    onError: (err, variables, context) => {
      // Rollback on error
      queryClient.setQueryData(['post', postId], context?.previousPost);
      toast.error('좋아요에 실패했습니다');
    },
  });

  return { like: likeMutation.mutate };
}
```

---

## Testing

### 1. API Mocking with MSW

```bash
npm install -D msw
```

```typescript
// src/mocks/handlers.ts
import { rest } from 'msw';

export const handlers = [
  rest.post('/api/auth/register', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: 'mock-token',
        user: {
          id: '123',
          username: 'testuser',
          email: 'test@example.com',
        },
      })
    );
  }),

  rest.get('/api/health/labs', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        results: [
          {
            id: '1',
            test_date: '2024-01-15',
            creatinine_mg_dl: 1.8,
            gfr_ml_min: 42,
          },
        ],
        total_count: 1,
      })
    );
  }),
];
```

---

## Best Practices

### 1. Type Safety

Always define TypeScript interfaces that match backend models:

```typescript
// src/types/health.ts
export interface LabResult {
  id: string;
  user_id: string;
  test_date: string;
  creatinine_mg_dl?: number;
  gfr_ml_min?: number;
  // ... other fields
  created_at: string;
  updated_at: string;
}

// Use Zod for runtime validation
import { z } from 'zod';

export const LabResultSchema = z.object({
  id: z.string(),
  test_date: z.string(),
  creatinine_mg_dl: z.number().optional(),
  // ...
});

// Validate API response
const data = LabResultSchema.parse(response.data);
```

### 2. Loading States

```typescript
const [state, setState] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');

// In component
{state === 'loading' && <Spinner />}
{state === 'error' && <ErrorMessage />}
{state === 'success' && <Content />}
```

### 3. Retry Logic

```typescript
async function fetchWithRetry<T>(
  fn: () => Promise<T>,
  retries: number = 3
): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    if (retries > 0) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      return fetchWithRetry(fn, retries - 1);
    }
    throw error;
  }
}

// Usage
const data = await fetchWithRetry(() => getLabResults());
```

---

## Common Issues & Solutions

### Issue 1: CORS Errors

**Solution**: Backend already configured CORS. Ensure `withCredentials: true` in axios config.

### Issue 2: Token Expiration

**Solution**: Interceptor already handles 401. Implement refresh token flow:

```typescript
let isRefreshing = false;
let failedQueue: any[] = [];

api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { access_token } = await refreshAccessToken();
        storage.set('careguide_token', access_token);

        failedQueue.forEach(({ resolve }) => resolve(access_token));
        failedQueue = [];

        return api(originalRequest);
      } catch (refreshError) {
        failedQueue.forEach(({ reject }) => reject(refreshError));
        failedQueue = [];

        // Redirect to login
        window.location.href = '/login';

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);
```

### Issue 3: File Upload Progress

```typescript
export async function uploadImageWithProgress(
  file: File,
  onProgress: (progress: number) => void
) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/api/community/uploads', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const progress = Math.round(
        (progressEvent.loaded * 100) / (progressEvent.total || 1)
      );
      onProgress(progress);
    },
  });

  return response.data.url;
}
```

---

## Conclusion

This integration guide covers the most common API integration patterns for the CareGuide frontend. For additional endpoints and detailed API specifications, refer to the [API_DESIGN.md](./API_DESIGN.md) document.

### Quick Reference

- **Base URL**: `http://localhost:8000` (dev), `https://api.careguide.com` (prod)
- **Auth**: JWT Bearer tokens in `Authorization` header
- **CSRF**: Automatic via interceptor for POST/PUT/DELETE
- **Error Format**: FastAPI standard (422 for validation, 400 for business logic)
- **Pagination**: Cursor-based for infinite scroll, offset-based for traditional
- **File Uploads**: multipart/form-data
- **Date Format**: ISO 8601 strings

### Support

For API issues or questions, contact the backend team or file an issue in the repository.
