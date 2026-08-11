/** Diet feature boundary: route-facing page and supported sub-routes. */
export { default as DietCarePage } from './DietCarePage';

export const DIET_ROUTES = [
  '/diet-care',
  '/diet-care/nutri-coach',
  '/diet-care/diet-log',
] as const;

export type DietRoute = (typeof DIET_ROUTES)[number];
