import { afterEach, describe, expect, it, vi } from 'vitest';

import api, { getHealthProfile, updateHealthProfile } from '../api';


const frozenProfile = {
  userId: 'synthetic-owner',
  conditions: ['synthetic-condition'],
  healthConditions: ['synthetic-condition'],
  allergies: ['synthetic-allergy'],
  dietaryRestrictions: ['synthetic-restriction'],
  age: 44,
  gender: 'other',
  updatedAt: '2026-08-16T00:00:00+00:00',
};


describe('Health Profile frozen v1 client contract', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('reads the canonical MyPage path without reshaping the payload', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: frozenProfile });

    await expect(getHealthProfile()).resolves.toEqual(frozenProfile);
    expect(get).toHaveBeenCalledWith('/api/mypage/health-profile');
  });

  it('writes the canonical MyPage path and preserves request field names', async () => {
    const update = {
      conditions: ['synthetic-condition'],
      dietaryRestrictions: ['synthetic-restriction'],
      age: 44,
      gender: 'other',
    };
    const put = vi.spyOn(api, 'put').mockResolvedValue({ data: frozenProfile });

    await expect(updateHealthProfile(update)).resolves.toEqual(frozenProfile);
    expect(put).toHaveBeenCalledWith('/api/mypage/health-profile', update);
  });

  it('returns null when the read fails', async () => {
    vi.spyOn(api, 'get').mockRejectedValue(new Error('synthetic-network-error'));
    vi.spyOn(console, 'error').mockImplementation(() => undefined);

    await expect(getHealthProfile()).resolves.toBeNull();
  });

  it('rethrows when the write fails', async () => {
    vi.spyOn(api, 'put').mockRejectedValue(new Error('synthetic-network-error'));
    vi.spyOn(console, 'error').mockImplementation(() => undefined);

    await expect(updateHealthProfile({ age: 44 })).rejects.toThrow(
      'synthetic-network-error',
    );
  });
});
