import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBookmarks } from '../useBookmarks';
import {
  createBookmark,
  deleteBookmark,
  deleteBookmarkByPaperId,
  getBookmarks,
  updateBookmark,
} from '../../services/bookmarkApi';

vi.mock('../../services/bookmarkApi', () => ({
  createBookmark: vi.fn(),
  deleteBookmark: vi.fn(),
  deleteBookmarkByPaperId: vi.fn(),
  getBookmarks: vi.fn(),
  updateBookmark: vi.fn(),
}));

const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
};

describe('useBookmarks user isolation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(createBookmark).mockResolvedValue({} as never);
    vi.mocked(deleteBookmark).mockResolvedValue(undefined);
    vi.mocked(deleteBookmarkByPaperId).mockResolvedValue(undefined);
    vi.mocked(updateBookmark).mockResolvedValue({} as never);
  });

  it('keeps the newest account data when requests resolve out of order', async () => {
    const first = deferred<never[]>();
    const second = deferred<never[]>();
    vi.mocked(getBookmarks).mockImplementation((userId) => userId === 'user-a' ? first.promise : second.promise);

    const { result, rerender } = renderHook(({ userId }) => useBookmarks(userId), {
      initialProps: { userId: 'user-a' as string | undefined },
    });
    rerender({ userId: 'user-b' });

    await act(async () => { second.resolve([{ id: 'b' }] as never[]); await second.promise; });
    await waitFor(() => expect(result.current.bookmarks).toEqual([{ id: 'b' }]));
    await act(async () => { first.resolve([{ id: 'a' }] as never[]); await first.promise; });

    expect(result.current.bookmarks).toEqual([{ id: 'b' }]);
  });

  it('clears state and ignores a response completed after logout', async () => {
    const pending = deferred<never[]>();
    vi.mocked(getBookmarks).mockReturnValue(pending.promise);
    const { result, rerender } = renderHook(({ userId }) => useBookmarks(userId), {
      initialProps: { userId: 'user-a' as string | undefined },
    });

    rerender({ userId: undefined });
    await act(async () => { pending.resolve([{ id: 'a' }] as never[]); await pending.promise; });

    expect(result.current.bookmarks).toEqual([]);
    expect(result.current.error).toBeNull();
    expect(result.current.actionError).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('clears a prior mutation error when the account changes', async () => {
    vi.mocked(getBookmarks).mockResolvedValue([]);
    vi.mocked(deleteBookmark).mockRejectedValue(new Error('delete failed'));
    const { result, rerender } = renderHook(({ userId }) => useBookmarks(userId), {
      initialProps: { userId: 'user-a' as string | undefined },
    });
    await waitFor(() => expect(vi.mocked(getBookmarks)).toHaveBeenCalled());
    await act(async () => { await expect(result.current.removeBookmark('bookmark')).rejects.toThrow('delete failed'); });
    expect(result.current.actionError).toBe('delete failed');

    rerender({ userId: 'user-b' });
    expect(result.current.actionError).toBeNull();
  });
});
