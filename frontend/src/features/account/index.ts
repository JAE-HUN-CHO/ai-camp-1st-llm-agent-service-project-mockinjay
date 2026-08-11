/** Account feature boundary for profile, bookmarks, notifications, and points. */
export { default as MyPage } from './MyPage';
export { default as ProfileInfoPage } from './ProfileInfoPage';
export { default as ChangePasswordPage } from './ChangePasswordPage';
export { default as NotificationSettingsPage } from './NotificationSettingsPage';
export { default as NotificationPage } from './NotificationPage';
export { default as BookmarkPage } from './BookmarkPage';
export const ACCOUNT_ROUTES = ['/mypage', '/mypage/profile', '/notifications'] as const;

export type AccountRoute = (typeof ACCOUNT_ROUTES)[number];
