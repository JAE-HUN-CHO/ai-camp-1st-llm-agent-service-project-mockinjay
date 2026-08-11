/** Research feature boundary for trends, papers, news, and clinical trials. */
export { default as TrendsPage } from './TrendsPage';
export { default as NewsDetailPage } from './NewsDetailPage';

export const RESEARCH_ROUTES = ['/trends', '/news/detail/:id'] as const;

export type ResearchRoute = (typeof RESEARCH_ROUTES)[number];
