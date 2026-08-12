/**
 * @fileoverview Diet Care API Service Layer
 * @module services/dietCareApi
 *
 * Production-ready API service for Diet Care feature.
 */

import api from './api';
import type {
  CreateSessionResponse,
  NutritionAnalysisRequest,
  NutritionAnalysisResponse,
  CreateMealRequest,
  MealResponse,
  MealQueryParams,
  MealListResponse,
  GoalsResponse,
  UpdateGoalsRequest,
  DailyProgressResponse,
  WeeklyProgressResponse,
  StreakResponse,
} from '../types/diet-care';

// ============================================================================
// API Endpoints
// ============================================================================

const ENDPOINTS = {
  SESSION_CREATE: '/api/diet-care/session/create',
  NUTRI_COACH: '/api/diet-care/nutri-coach',
  MEALS: '/api/diet-care/meals',
  GOALS: '/api/diet-care/goals',
  PROGRESS_DAILY: '/api/diet-care/progress/daily',
  PROGRESS_WEEKLY: '/api/diet-care/progress/weekly',
  STREAK: '/api/diet-care/streak',
} as const;

// ============================================================================
// Session Management
// ============================================================================

/**
 * Create a new analysis session
 */
export async function createSession(userId?: string): Promise<CreateSessionResponse> {
  const response = await api.post<CreateSessionResponse>(
    ENDPOINTS.SESSION_CREATE,
    null,
    { params: userId ? { user_id: userId } : undefined }
  );
  return response.data;
}

// ============================================================================
// Nutrition Analysis
// ============================================================================

/**
 * Analyze food image with AI
 */
export async function analyzeNutrition(
  request: NutritionAnalysisRequest
): Promise<NutritionAnalysisResponse> {
  const formData = new FormData();
  formData.append('session_id', request.session_id);

  if (request.image) {
    formData.append('image', request.image);
  }
  if (request.text) {
    formData.append('text', request.text);
  }
  if (request.age !== undefined) {
    formData.append('age', String(request.age));
  }
  if (request.weight_kg !== undefined) {
    formData.append('weight_kg', String(request.weight_kg));
  }
  if (request.height_cm !== undefined) {
    formData.append('height_cm', String(request.height_cm));
  }
  if (request.ckd_stage !== undefined) {
    formData.append('ckd_stage', String(request.ckd_stage));
  }
  if (request.activity_level) {
    formData.append('activity_level', request.activity_level);
  }

  // Set Content-Type to undefined to remove the default 'application/json' header.
  // This allows axios to automatically set the correct multipart/form-data with boundary.
  const response = await api.post<NutritionAnalysisResponse>(
    ENDPOINTS.NUTRI_COACH,
    formData,
    {
      headers: { 'Content-Type': undefined },
    }
  );
  return response.data;
}

// ============================================================================
// Meal Logging
// ============================================================================

/**
 * Log a new meal
 */
export async function createMeal(meal: CreateMealRequest): Promise<MealResponse> {
  const response = await api.post<MealResponse>(ENDPOINTS.MEALS, meal);
  return response.data;
}

/**
 * Get meal history
 */
export async function getMeals(params?: MealQueryParams): Promise<MealListResponse> {
  const response = await api.get<MealListResponse>(ENDPOINTS.MEALS, { params });
  return response.data;
}

/**
 * Delete a meal
 */
export async function deleteMeal(mealId: string): Promise<void> {
  await api.delete(`${ENDPOINTS.MEALS}/${mealId}`);
}

// ============================================================================
// Goals Management
// ============================================================================

/**
 * Get user's nutrition goals
 */
export async function getGoals(): Promise<GoalsResponse> {
  const response = await api.get<GoalsResponse>(ENDPOINTS.GOALS);
  return response.data;
}

/**
 * Update user's nutrition goals
 */
export async function updateGoals(goals: UpdateGoalsRequest): Promise<GoalsResponse> {
  const response = await api.put<GoalsResponse>(ENDPOINTS.GOALS, goals);
  return response.data;
}

// ============================================================================
// Progress Tracking
// ============================================================================

/**
 * Get daily progress
 */
export async function getDailyProgress(date?: string): Promise<DailyProgressResponse> {
  const response = await api.get<DailyProgressResponse>(ENDPOINTS.PROGRESS_DAILY, {
    params: date ? { date_str: date } : undefined,
  });
  return response.data;
}

/**
 * Get weekly progress
 */
export async function getWeeklyProgress(weekStart?: string): Promise<WeeklyProgressResponse> {
  const response = await api.get<WeeklyProgressResponse>(ENDPOINTS.PROGRESS_WEEKLY, {
    params: weekStart ? { week_start: weekStart } : undefined,
  });
  return response.data;
}

/**
 * Get logging streak
 */
export async function getStreak(): Promise<StreakResponse> {
  const response = await api.get<StreakResponse>(ENDPOINTS.STREAK);
  return response.data;
}

// ============================================================================
// Export all functions
// ============================================================================

export const dietCareApi = {
  createSession,
  analyzeNutrition,
  createMeal,
  getMeals,
  deleteMeal,
  getGoals,
  updateGoals,
  getDailyProgress,
  getWeeklyProgress,
  getStreak,
};

export default dietCareApi;
