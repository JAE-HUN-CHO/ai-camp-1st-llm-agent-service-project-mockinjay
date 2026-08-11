import { describe, expect, it } from 'vitest';
import { ROUTES } from '../../types/careguide-ia';

describe('canonical route parity contract', () => {
  it('keeps feature and legacy-compatible route constants available', () => {
    expect(ROUTES.CHAT_MEDICAL_WELFARE).toBe('/chat/medical-welfare');
    expect(ROUTES.CHAT_NUTRITION).toBe('/chat/nutrition');
    expect(ROUTES.NUTRI_COACH).toBe('/nutri-coach');
    expect(ROUTES.DIET_LOG).toBe('/diet-log');
    expect(ROUTES.MY_PAGE_HEALTH_RECORDS).toBe('/mypage/test-results');
    expect(ROUTES.COMMUNITY_DETAIL).toBe('/community/:postId');
    expect(ROUTES.TRENDS).toBe('/trends');
    expect(ROUTES.MY_PAGE).toBe('/mypage');
    expect(ROUTES.NOTIFICATION).toBe('/notification');
    expect(ROUTES.TERMS_CONDITIONS).toBe('/terms-conditions');
  });
});
