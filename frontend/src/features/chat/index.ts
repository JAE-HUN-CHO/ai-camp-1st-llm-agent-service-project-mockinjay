/** Chat feature boundary: route-facing page and feature-owned route metadata. */
export { default as ChatPage } from './ChatPage';

export const CHAT_ROUTES = [
  '/chat',
  '/chat/medical-welfare',
  '/chat/nutrition',
  '/chat/research',
] as const;

export type ChatRoute = (typeof CHAT_ROUTES)[number];
