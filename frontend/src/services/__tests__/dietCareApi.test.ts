import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import {
  analyzeNutrition,
  createMeal,
  createSession,
  deleteMeal,
  getDailyProgress,
  getGoals,
  getMeals,
  getStreak,
  getWeeklyProgress,
  updateGoals,
} from '../dietCareApi';
import { MealType } from '../../types/diet-care';

const response = <T,>(data: T) => ({ data });
const meal = {
  meal_type: MealType.Breakfast,
  foods: [{ name: '현미밥', amount: '210g', calories: 330, protein_g: 6.5, sodium_mg: 5, potassium_mg: 180, phosphorus_mg: 200 }],
};

describe('dietCareApi', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('creates a session and forwards an optional user id as a query parameter', async () => {
    vi.spyOn(api, 'post').mockResolvedValue(response({ session_id: 's1', created_at: 'now', expires_at: 'later' }));
    await expect(createSession('user-1')).resolves.toEqual({ session_id: 's1', created_at: 'now', expires_at: 'later' });
    expect(api.post).toHaveBeenCalledWith('/api/diet-care/session/create', null, { params: { user_id: 'user-1' } });
  });

  it('serializes nutrition analysis fields as multipart form data', async () => {
    vi.spyOn(api, 'post').mockResolvedValue(response({ session_id: 's1', analysis: {}, analyzed_at: 'now' }));
    await analyzeNutrition({ session_id: 's1', text: 'rice', age: 60, ckd_stage: 3 });
    const [, body, config] = (api.post as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get('session_id')).toBe('s1');
    expect((body as FormData).get('text')).toBe('rice');
    expect((body as FormData).get('ckd_stage')).toBe('3');
    expect(config).toEqual({ headers: { 'Content-Type': undefined } });
  });

  it('delegates meal, goal, progress, and streak operations to the API', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue(response(meal));
    const get = vi.spyOn(api, 'get')
      .mockResolvedValueOnce(response({ meals: [meal], total_count: 1, date_range: { start: '2026-01-01', end: '2026-01-01' } }))
      .mockResolvedValueOnce(response({ user_id: 'u1', goals: {}, last_updated: 'now' }))
      .mockResolvedValueOnce(response({ date: '2026-01-01', calories: {}, protein: {}, sodium: {}, potassium: {}, phosphorus: {}, meals_logged: 1, total_meals: 3 }))
      .mockResolvedValueOnce(response({ week_start: '2026-01-01', week_end: '2026-01-07', daily_summaries: [], average_compliance: 1, streak_days: 1, total_meals_logged: 1 }))
      .mockResolvedValueOnce(response({ current_streak: 1, longest_streak: 2 }));
    const put = vi.spyOn(api, 'put').mockResolvedValue(response({ user_id: 'u1', goals: {}, last_updated: 'now' }));
    const del = vi.spyOn(api, 'delete').mockResolvedValue({} as never);

    await createMeal(meal);
    await getMeals({ start_date: '2026-01-01' });
    await getGoals();
    await getDailyProgress('2026-01-01');
    await getWeeklyProgress('2026-01-01');
    await getStreak();
    await updateGoals({ sodium_mg: 1500 });
    await deleteMeal('meal-1');

    expect(post).toHaveBeenCalledWith('/api/diet-care/meals', meal);
    expect(get).toHaveBeenCalledWith('/api/diet-care/meals', { params: { start_date: '2026-01-01' } });
    expect(put).toHaveBeenCalledWith('/api/diet-care/goals', { sodium_mg: 1500 });
    expect(del).toHaveBeenCalledWith('/api/diet-care/meals/meal-1');
  });
});
