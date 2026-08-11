import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { useChatRooms } from '../useChatRooms';

const create = async (result: ReturnType<typeof renderHook<typeof useChatRooms>>['result'], title: string) => {
  let room;
  await act(async () => { room = await result.current.createRoom({ title }); });
  return room!;
};

describe('useChatRooms', () => {
  beforeEach(() => localStorage.clear());

  it('creates and persists a room while selecting it as current', async () => {
    const { result } = renderHook(() => useChatRooms());
    const room = await create(result, 'Test Room');
    expect(result.current.rooms).toHaveLength(1);
    expect(result.current.currentRoomId).toBe(room.id);
    expect(JSON.parse(localStorage.getItem('careguide_chat_rooms')!)[0].title).toBe('Test Room');
  });

  it('updates, pins, archives, and removes a room', async () => {
    const { result } = renderHook(() => useChatRooms());
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
    const { result } = renderHook(() => useChatRooms());
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

  it('loads serialized rooms and supports clearing all state', () => {
    const now = new Date().toISOString();
    localStorage.setItem('careguide_chat_rooms', JSON.stringify([{ id: 'saved', title: 'Saved', agentType: 'auto', messageCount: 0, createdAt: now, updatedAt: now }]));
    const { result } = renderHook(() => useChatRooms());
    expect(result.current.rooms[0].title).toBe('Saved');
    act(() => result.current.clearAllRooms());
    expect(result.current.rooms).toEqual([]);
    expect(result.current.currentRoomId).toBeNull();
  });
});
