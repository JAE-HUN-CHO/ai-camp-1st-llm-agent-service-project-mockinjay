import { secureTokenStorage } from '../../utils/security';

/** Single auth-token lookup seam shared by HTTP adapters. */
export function getAccessToken(): string | null {
  return secureTokenStorage.get();
}
