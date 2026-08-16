import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useChatRooms } from '../useChatRooms';
import { getChatRooms } from '../../services/api';

vi.mock('../../services/api', () => ({
  createRoomWithSession: vi.fn(async (_userId, agentType, _profile, title) => ({
    id: `room-${title}`,
    title,
    agent_type: agentType,
    message_count: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  })),
  getChatRooms: vi.fn(async () => []),
}));

const create = async (result: ReturnType<typeof renderHook<typeof useChatRooms>>['result'], title: string) => {
  let room;
  await act(async () => { await Promise.resolve(); });
  await act(async () => { room = await result.current.createRoom({ title }, 'user-1'); });
  return room!;
};

describe('useChatRooms', () => {
  beforeEach(() => localStorage.clear());

  it('creates an authenticated in-memory room while selecting it as current', async () => {
    const { result } = renderHook(() => useChatRooms('user-1'));
    const room = await create(result, 'Test Room');
    expect(result.current.rooms).toHaveLength(1);
    expect(result.current.currentRoomId).toBe(room.id);
    expect(localStorage.getItem('careguide_chat_rooms')).toBeNull();
  });

  it('updates, pins, archives, and removes a room', async () => {
    const { result } = renderHook(() => useChatRooms('user-1'));
    const room = await create(result, 'Original');
    act(() => result.current.updateRoom(room.id, { title: 'Updated' }));
    act(() => result.current.togglePinRoom(room.id));
    act(() => result.current.toggleArchiveRoom(room.id));
    expect(result.current.rooms[0]).toMatchObject({ title: 'Updated', isPinned: true, isArchived: true });
    act(() => result.current.deleteRoom(room.id));
    expect(result.current.rooms).toEqual([]);
    expect(result.current.currentRoomId).toBeNull();
  });

  it('updates message metadata and filters active rooms', async () => {
    const { result } = renderHook(() => useChatRooms('user-1'));
    const first = await create(result, 'Medical');
    const second = await create(result, 'Nutrition');
    const timestamp = new Date('2026-01-01T00:00:00Z');
    act(() => result.current.updateRoomLastMessage(first.id, 'A message', timestamp));
    act(() => result.current.incrementMessageCount(first.id));
    act(() => result.current.toggleArchiveRoom(second.id));
    expect(result.current.rooms.find((room) => room.id === first.id)).toMatchObject({ lastMessage: 'A message', messageCount: 1 });
    expect(result.current.activeRooms).toHaveLength(1);
    expect(result.current.filterRooms({ searchQuery: 'message' })).toHaveLength(1);
  });

  it('does not restore serialized rooms and supports clearing all state', async () => {
    localStorage.setItem('careguide_chat_rooms', '[{"title":"health-canary"}]');
    const { result } = renderHook(() => useChatRooms('user-1'));
    await act(async () => { await Promise.resolve(); });
    expect(result.current.rooms).toEqual([]);
    act(() => result.current.clearAllRooms());
    expect(result.current.rooms).toEqual([]);
    expect(result.current.currentRoomId).toBeNull();
  });

  it('hydrates authenticated rooms from the server after remount', async () => {
    vi.mocked(getChatRooms).mockResolvedValueOnce([{
      id: 'persisted-room',
      title: 'Persisted',
      agent_type: 'research_paper',
      message_count: 2,
      created_at: '2026-08-15T00:00:00Z',
      updated_at: '2026-08-15T01:00:00Z',
    }]);

    const { result } = renderHook(() => useChatRooms('user-1', 'patient'));
    await act(async () => { await Promise.resolve(); });

    expect(getChatRooms).toHaveBeenCalledWith('user-1');
    expect(result.current.isHydrated).toBe(true);
    expect(result.current.rooms[0]).toMatchObject({
      id: 'persisted-room',
      title: 'Persisted',
      messageCount: 2,
    });
    expect(result.current.currentRoomId).toBe('persisted-room');
  });
});
