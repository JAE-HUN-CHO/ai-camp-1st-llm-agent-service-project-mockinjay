import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import api from '../../services/api';
import { secureTokenStorage } from '../../utils/security';

// Mock the API module
vi.mock('../../services/api', () => ({
  default: {
    post: vi.fn(),
    defaults: {
      headers: {
        common: {},
      },
    },
  },
}));

describe('AuthContext', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    secureTokenStorage.clear();
    delete api.defaults.headers.common.Authorization;
    // Clear all mocks
    vi.clearAllMocks();
  });

  it('initializes with no user and no token', () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('deletes legacy credentials instead of restoring them', () => {
    localStorage.setItem('careguide_user', '{"email":"pii-canary@example.com"}');
    localStorage.setItem('careguide_token', 'token-canary');
    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(localStorage.getItem('careguide_user')).toBeNull();
    expect(localStorage.getItem('careguide_token')).toBeNull();
  });

  it('logs in successfully and keeps credentials out of localStorage', async () => {
    const mockResponse = {
      data: {
        access_token: 'new-token-123',
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
        },
      },
    };

    vi.mocked(api.post).mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await act(async () => {
      await result.current.login('testuser', 'password123');
    });

    expect(result.current.token).toBe('new-token-123');
    expect(result.current.user).toEqual(mockResponse.data.user);
    expect(result.current.isAuthenticated).toBe(true);
    expect(localStorage.getItem('careguide_token')).toBeNull();
    expect(localStorage.getItem('careguide_user')).toBeNull();
  });

  it('handles login failure', async () => {
    const mockError = {
      response: {
        data: {
          detail: 'Invalid credentials',
        },
      },
    };

    vi.mocked(api.post).mockRejectedValueOnce(mockError);

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await expect(
      act(async () => {
        await result.current.login('testuser', 'wrongpassword');
      })
    ).rejects.toThrow('Invalid credentials');

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('logs out and clears credentials', () => {
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
    };
    const mockToken = 'test-token-123';

    localStorage.setItem('careguide_user', JSON.stringify(mockUser));
    localStorage.setItem('careguide_token', mockToken);

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    act(() => {
      result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(localStorage.getItem('careguide_token')).toBeNull();
    expect(localStorage.getItem('careguide_user')).toBeNull();
  });

  it('throws error when useAuth is used outside AuthProvider', () => {
    expect(() => {
      renderHook(() => useAuth());
    }).toThrow('useAuth must be used within an AuthProvider');
  });
});
