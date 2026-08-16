/**
 * useChatRooms Hook
 * 채팅 방 관리 훅
 *
 * Manages in-memory chat room metadata and CRUD operations.
 */

import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import type { ChatRoom, CreateRoomOptions, RoomFilterOptions } from '../types/chat';
import type { AgentType } from '../services/intentRouter';
import { createRoomWithSession, getChatRooms, type ChatRoomData } from '../services/api';

/**
 * Generate a title based on agent type
 * 에이전트 타입 기반으로 제목 생성
 */
function generateRoomTitle(agentType: AgentType | 'auto'): string {
  const titles: Record<AgentType | 'auto', string> = {
    auto: 'Auto 대화',
    medical_welfare: '의료 복지 상담',
    nutrition: '식이 영양 상담',
    research_paper: '연구 논문 검색',
    router: 'AI 상담',
  };
  return titles[agentType] || 'AI 대화';
}

function mapApiRoom(room: ChatRoomData): ChatRoom {
  const createdAt = new Date(room.created_at);
  const updatedAt = new Date(room.updated_at || room.last_activity || room.created_at);
  return {
    id: room.id || room.room_id || '',
    title: room.title || room.room_name || 'AI 대화',
    agentType: (room.agent_type as AgentType) || 'auto',
    lastMessage: room.last_message,
    lastMessageTime: room.last_message_time ? new Date(room.last_message_time) : undefined,
    messageCount: room.message_count || 0,
    createdAt,
    updatedAt,
    isPinned: room.is_pinned || false,
    isArchived: room.is_archived || false,
    parlantSessionId: room.parlant_session_id,
    parlantCustomerId: room.parlant_customer_id,
  };
}

export function useChatRooms(authenticatedUserId?: string, authenticatedProfile = 'general') {
  const [rooms, setRooms] = useState<ChatRoom[]>([]);
  const [currentRoomId, setCurrentRoomId] = useState<string | null>(null);
  const [hydratedUserId, setHydratedUserId] = useState<string | null>(null);
  const [hydrationError, setHydrationError] = useState<string | null>(null);
  const [hydrationAttempt, setHydrationAttempt] = useState(0);
  const isHydrated = Boolean(authenticatedUserId && hydratedUserId === authenticatedUserId);
  const activeUserIdRef = useRef(authenticatedUserId);
  const activeProfileRef = useRef(authenticatedProfile);
  const hydratedUserIdRef = useRef(hydratedUserId);
  activeUserIdRef.current = authenticatedUserId;
  activeProfileRef.current = authenticatedProfile;
  hydratedUserIdRef.current = hydratedUserId;

  useEffect(() => {
    let cancelled = false;
    if (!authenticatedUserId) {
      queueMicrotask(() => {
        if (cancelled) return;
        setRooms([]);
        setCurrentRoomId(null);
        setHydratedUserId(null);
        hydratedUserIdRef.current = null;
        setHydrationError(null);
      });
      return () => { cancelled = true; };
    }

    void getChatRooms(authenticatedUserId)
      .then((serverRooms) => {
        if (cancelled || activeUserIdRef.current !== authenticatedUserId) return;
        const restored = serverRooms.map(mapApiRoom).filter((room) => room.id);
        setRooms(restored);
        setCurrentRoomId(restored[0]?.id || null);
        hydratedUserIdRef.current = authenticatedUserId;
        setHydratedUserId(authenticatedUserId);
        setHydrationError(null);
      })
      .catch(() => {
        if (cancelled || activeUserIdRef.current !== authenticatedUserId) return;
        setHydrationError('채팅방을 불러오지 못했습니다. 다시 시도해주세요.');
      });
    return () => { cancelled = true; };
  }, [authenticatedUserId, hydrationAttempt]);

  /**
   * Create a new chat room with Parlant session (async)
   * Parlant 세션과 함께 새 채팅 방 생성 (비동기)
   *
   * @param options - Room creation options
   * @param userId - User ID for backend session creation
   * @param profile - User profile for Parlant customer tags
   */
  const createRoom = useCallback(
    async (
      options: CreateRoomOptions = {},
      userId: string | undefined = authenticatedUserId,
      profile: string = authenticatedProfile
    ): Promise<ChatRoom> => {
      const now = new Date();
      const agentType = options.agentType || 'auto';
      const title = options.title || generateRoomTitle(agentType);

      if (
        userId
        && userId === activeUserIdRef.current
        && hydratedUserIdRef.current === userId
        && profile === activeProfileRef.current
      ) {
        try {
          // Call backend API to create room with Parlant session
          // 백엔드 API를 호출하여 Parlant 세션과 함께 방 생성
          const roomData = await createRoomWithSession(
            userId,
            agentType,
            profile,
            title
          );

          if (
            activeUserIdRef.current !== userId
            || hydratedUserIdRef.current !== userId
            || activeProfileRef.current !== profile
          ) {
            throw new Error('사용자 또는 프로필이 변경되어 방 생성을 취소했습니다.');
          }

          const newRoom: ChatRoom = {
            id: roomData.id || roomData.room_id || `room_${Date.now()}`,
            title: roomData.title || roomData.room_name || title,
            agentType: (roomData.agent_type as AgentType) || agentType,
            messageCount: roomData.message_count || 0,
            createdAt: roomData.created_at ? new Date(roomData.created_at) : now,
            updatedAt: roomData.updated_at ? new Date(roomData.updated_at) : now,
            isPinned: false,
            isArchived: false,
            parlantSessionId: roomData.parlant_session_id,
            parlantCustomerId: roomData.parlant_customer_id,
          };

          setRooms((prev) => [newRoom, ...prev]);
          setCurrentRoomId(newRoom.id);

          return newRoom;
        } catch (_error) {
          throw new Error('채팅방을 안전하게 생성하지 못했습니다. 다시 시도해주세요.');
        }
      }
      throw new Error('채팅방 초기화가 완료된 뒤 다시 시도해주세요.');
    },
    [authenticatedProfile, authenticatedUserId]
  );

  /**
   * Delete a chat room
   * 채팅 방 삭제
   */
  const deleteRoom = useCallback((roomId: string) => {
    setRooms((prev) => prev.filter((room) => room.id !== roomId));

    // If deleting current room, switch to another room or null
    // 현재 방을 삭제하는 경우, 다른 방으로 전환하거나 null로 설정
    if (currentRoomId === roomId) {
      const remainingRooms = rooms.filter((room) => room.id !== roomId);
      setCurrentRoomId(remainingRooms.length > 0 ? remainingRooms[0].id : null);
    }
  }, [currentRoomId, rooms]);

  /**
   * Update a chat room
   * 채팅 방 업데이트
   */
  const updateRoom = useCallback((roomId: string, updates: Partial<ChatRoom>) => {
    setRooms((prev) =>
      prev.map((room) =>
        room.id === roomId
          ? { ...room, ...updates, updatedAt: new Date() }
          : room
      )
    );
  }, []);

  /**
   * Pin/unpin a room
   * 방 고정/고정 해제
   */
  const togglePinRoom = useCallback((roomId: string) => {
    setRooms((prev) =>
      prev.map((room) =>
        room.id === roomId
          ? { ...room, isPinned: !room.isPinned, updatedAt: new Date() }
          : room
      )
    );
  }, []);

  /**
   * Archive/unarchive a room
   * 방 보관/보관 해제
   */
  const toggleArchiveRoom = useCallback((roomId: string) => {
    setRooms((prev) =>
      prev.map((room) =>
        room.id === roomId
          ? { ...room, isArchived: !room.isArchived, updatedAt: new Date() }
          : room
      )
    );
  }, []);

  /**
   * Update room with last message info
   * 마지막 메시지 정보로 방 업데이트
   */
  const updateRoomLastMessage = useCallback((
    roomId: string,
    message: string,
    timestamp: Date
  ) => {
    setRooms((prev) =>
      prev.map((room) =>
        room.id === roomId
          ? {
              ...room,
              lastMessage: message.substring(0, 100), // Truncate to 100 chars
              lastMessageTime: timestamp,
              updatedAt: timestamp,
            }
          : room
      )
    );
  }, []);

  /**
   * Increment message count for a room
   * 방의 메시지 카운트 증가
   */
  const incrementMessageCount = useCallback((roomId: string) => {
    setRooms((prev) =>
      prev.map((room) =>
        room.id === roomId
          ? { ...room, messageCount: room.messageCount + 1 }
          : room
      )
    );
  }, []);

  /**
   * Clear all rooms
   * 모든 방 삭제
   */
  const clearAllRooms = useCallback(() => {
    setRooms([]);
    setCurrentRoomId(null);
  }, []);

  /**
   * Get current room
   * 현재 방 가져오기
   */
  const currentRoom = useMemo(() => {
    if (!isHydrated) return null;
    return rooms.find((room) => room.id === currentRoomId) || null;
  }, [isHydrated, rooms, currentRoomId]);

  /**
   * Filter rooms based on criteria
   * 기준에 따라 방 필터링
   */
  const filterRooms = useCallback((options: RoomFilterOptions = {}): ChatRoom[] => {
    if (!isHydrated) return [];
    return rooms.filter((room) => {
      // Filter by agent type
      // 에이전트 타입으로 필터링
      if (options.agentType && options.agentType !== 'all' && room.agentType !== options.agentType) {
        return false;
      }

      // Filter by pinned status
      // 고정 상태로 필터링
      if (options.isPinned !== undefined && room.isPinned !== options.isPinned) {
        return false;
      }

      // Filter by archived status
      // 보관 상태로 필터링
      if (options.isArchived !== undefined && room.isArchived !== options.isArchived) {
        return false;
      }

      // Filter by search query
      // 검색어로 필터링
      if (options.searchQuery) {
        const query = options.searchQuery.toLowerCase();
        const titleMatch = room.title.toLowerCase().includes(query);
        const messageMatch = room.lastMessage?.toLowerCase().includes(query);
        return titleMatch || messageMatch;
      }

      return true;
    });
  }, [isHydrated, rooms]);

  /**
   * Sort rooms (pinned first, then by last activity)
   * 방 정렬 (고정된 방 먼저, 그 다음 최근 활동순)
   */
  const sortedRooms = useMemo(() => {
    if (!isHydrated) return [];
    return [...rooms].sort((a, b) => {
      // Pinned rooms come first
      // 고정된 방이 먼저
      if (a.isPinned && !b.isPinned) return -1;
      if (!a.isPinned && b.isPinned) return 1;

      // Then sort by last activity (most recent first)
      // 그 다음 최근 활동순 (최신이 먼저)
      const aTime = a.lastMessageTime || a.updatedAt;
      const bTime = b.lastMessageTime || b.updatedAt;
      return bTime.getTime() - aTime.getTime();
    });
  }, [isHydrated, rooms]);

  /**
   * Get rooms excluding archived ones
   * 보관된 방을 제외한 방 목록
   */
  const activeRooms = useMemo(() => {
    return sortedRooms.filter((room) => !room.isArchived);
  }, [sortedRooms]);

  const retryHydration = useCallback(() => {
    setHydrationError(null);
    setHydrationAttempt((attempt) => attempt + 1);
  }, []);

  return {
    // State
    rooms: sortedRooms,
    activeRooms,
    currentRoom,
    currentRoomId: isHydrated ? currentRoomId : null,
    isHydrated,
    hydrationError,

    // Actions
    createRoom,
    deleteRoom,
    updateRoom,
    togglePinRoom,
    toggleArchiveRoom,
    updateRoomLastMessage,
    incrementMessageCount,
    clearAllRooms,
    setCurrentRoomId,
    filterRooms,
    retryHydration,
  };
}
