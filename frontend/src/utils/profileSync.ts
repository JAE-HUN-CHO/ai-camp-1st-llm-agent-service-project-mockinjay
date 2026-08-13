export type UserProfile = 'general' | 'patient' | 'researcher';

export const USER_PROFILE_STORAGE_KEY = 'careguide_user_profile';

export const publishUserProfile = (profile: UserProfile) => {
  localStorage.setItem(USER_PROFILE_STORAGE_KEY, profile);
  window.dispatchEvent(new CustomEvent('careguide:profile-changed', { detail: profile }));
};

export const isUserProfile = (value: string | null): value is UserProfile =>
  value === 'general' || value === 'patient' || value === 'researcher';
