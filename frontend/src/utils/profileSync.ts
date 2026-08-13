export type UserProfile = 'general' | 'patient' | 'researcher';

export const USER_PROFILE_STORAGE_KEY = 'careguide_user_profile';

export const isUserProfile = (value: string | null): value is UserProfile =>
  value === 'general' || value === 'patient' || value === 'researcher';

