export type UserProfile = 'general' | 'patient' | 'researcher';

let currentProfile: UserProfile | null = null;

export const publishUserProfile = (profile: UserProfile) => {
  currentProfile = profile;
  window.dispatchEvent(new CustomEvent('careguide:profile-changed', { detail: profile }));
};

export const getPublishedUserProfile = (): UserProfile | null => currentProfile;

export const isUserProfile = (value: string | null): value is UserProfile =>
  value === 'general' || value === 'patient' || value === 'researcher';
