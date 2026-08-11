/** Community feature boundary for posts, comments, likes, and uploads. */
export { default as CommunityPage } from './CommunityPage';

export const COMMUNITY_ROUTES = ['/community', '/community/detail/:id'] as const;

export type CommunityRoute = (typeof COMMUNITY_ROUTES)[number];
