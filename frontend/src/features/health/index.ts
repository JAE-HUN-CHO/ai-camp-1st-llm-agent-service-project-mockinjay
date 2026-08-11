/** Health feature boundary for records and health-related route ownership. */
export { default as HealthRecordsPage } from './HealthRecordsPage';

export const HEALTH_ROUTES = ['/mypage/test-results', '/mypage/test-results/add'] as const;

export type HealthRoute = (typeof HEALTH_ROUTES)[number];
