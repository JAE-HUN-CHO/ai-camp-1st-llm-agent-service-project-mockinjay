import { secureTokenStorage } from '../../utils/security';
import { storage } from '../../utils/storage';

/** Single auth-token lookup seam shared by HTTP adapters. */
export function getAccessToken(): string | null {
  return secureTokenStorage.get() || storage.get<string>('careguide_token');
}
