/**
 * useChatSession Hook
 * 채팅 세션 관리 훅
 *
 * Manages chat session lifecycle, expiration, and backend history restoration.
 * 채팅 세션 라이프사이클과 백엔드 히스토리 복원을 관리합니다.
 */

import { useState, useEffect, useCallback } from 'react';
import api, { getChatHistory } from '../services/api';
import type { ChatMessage } from '../types/chat';
import { useAuth } from '../contexts/AuthContext';

export function useChatSession(roomId: string | null) {
  const { user } = useAuth();

  // Session state
  // 세션 상태
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSessionExpired, setIsSessionExpired] = useState(false);
  const [isRestoringHistory, setIsRestoringHistory] = useState(false);

  // Messages state per room
  // 방별 메시지 상태
  // Chat content stays in memory and is restored from backend history.
  const [messages, setMessages] = useState<Record<string, ChatMessage[]>>({});

  /**
   * Initialize or restore session
   * 세션 초기화 또는 복원
   */
  const initializeSession = useCallback(async () => {
    try {
      const response = await api.post('/api/session/create', {
        user_id: user?.id || 'guest_user',
        room_id: roomId || undefined,
      });
      // Backend returns SuccessResponse format: { message, data: { session_id, ... } }
      const newSessionId = response.data.data?.session_id || response.data.session_id;
      setSessionId(newSessionId);
    } catch (error) {
      console.error('Failed to initialize session:', error);
    }
  }, [roomId, user?.id]);

  // Initialize session on mount
  // 마운트 시 세션 초기화
  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  /**
   * Get messages for current room
   * 현재 방의 메시지 가져오기
   */
  const roomMessages = roomId ? messages[roomId] || [] : [];

  /**
   * Add a message to the current room
   * 현재 방에 메시지 추가
   */
  const addMessage = useCallback(
    (message: ChatMessage) => {
      if (!roomId) return;

      setMessages((prev) => ({
        ...prev,
        [roomId]: [...(prev[roomId] || []), message],
      }));

    },
    [roomId]
  );

  /**
   * Update a specific message
   * 특정 메시지 업데이트
   */
  const updateMessage = useCallback(
    (messageId: string, content: string) => {
      if (!roomId) return;

      setMessages((prev) => ({
        ...prev,
        [roomId]: (prev[roomId] || []).map((msg) =>
          msg.id === messageId ? { ...msg, content } : msg
        ),
      }));
    },
    [roomId]
  );

  /**
   * Clear messages for current room
   * 현재 방의 메시지 삭제
   */
  const clearMessages = useCallback(() => {
    if (!roomId) return;

    setMessages((prev) => ({
      ...prev,
      [roomId]: [],
    }));
  }, [roomId]);

  /**
   * Clear all messages for all rooms
   * 모든 방의 모든 메시지 삭제
   */
  const clearAllMessages = useCallback(() => {
    setMessages({});
  }, []);

  /**
   * Restore chat history from backend
   * 백엔드에서 채팅 히스토리 복원
   */
  const restoreChatHistory = useCallback(
    async (limit: number = 50) => {
      if (!user?.id || !sessionId || !roomId) {
        console.warn('Cannot restore history: missing user ID, session ID, or room ID');
        return;
      }

      setIsRestoringHistory(true);
      try {
        const history = await getChatHistory(user.id, sessionId, limit);

        if (history.conversations && history.conversations.length > 0) {
          // Convert DB format to Message format
          // DB 포맷을 메시지 포맷으로 변환
          const restoredMessages: ChatMessage[] = [];

          history.conversations.forEach((conv, index) => {
            // Add user message
            // 사용자 메시지 추가
            if (conv.user_input) {
              restoredMessages.push({
                id: `restored-user-${index}`,
                role: 'user',
                content: conv.user_input,
                timestamp: new Date(conv.timestamp),
                sessionId: conv.session_id,
                roomId,
              });
            }
            // Add assistant message
            // 어시스턴트 메시지 추가
            if (conv.agent_response) {
              restoredMessages.push({
                id: `restored-assistant-${index}`,
                role: 'assistant',
                content: conv.agent_response,
                timestamp: new Date(conv.timestamp),
                sessionId: conv.session_id,
                roomId,
              });
            }
          });

          setMessages((prev) => ({
            ...prev,
            [roomId]: restoredMessages,
          }));

          setIsSessionExpired(false);
        }
      } catch (error) {
        console.error('Failed to restore chat history:', error);
      } finally {
        setIsRestoringHistory(false);
      }
    },
    [user?.id, sessionId, roomId]
  );

  /**
   * Mark session as expired
   * 세션을 만료된 것으로 표시
   */
  const expireSession = useCallback(() => {
    setIsSessionExpired(true);
  }, []);

  /**
   * Create a new session
   * 새 세션 생성
   */
  const createNewSession = useCallback(async () => {
    try {
      const response = await api.post('/api/session/create', {
        user_id: user?.id || 'guest_user',
        room_id: roomId || undefined,
      });
      // Backend returns SuccessResponse format: { message, data: { session_id, ... } }
      const newSessionId = response.data.data?.session_id || response.data.session_id;
      setSessionId(newSessionId);

      setIsSessionExpired(false);
      return newSessionId;
    } catch (error) {
      console.error('Failed to create new session:', error);
      return null;
    }
  }, [user?.id, roomId]);

  return {
    // State
    sessionId,
    isSessionExpired,
    isRestoringHistory,
    messages: roomMessages,

    // Actions
    addMessage,
    updateMessage,
    clearMessages,
    clearAllMessages,
    restoreChatHistory,
    expireSession,
    createNewSession,
    initializeSession,
  };
}
