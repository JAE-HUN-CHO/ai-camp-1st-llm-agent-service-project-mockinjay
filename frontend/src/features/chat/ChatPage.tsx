/**
 * ChatPageEnhanced - Enhanced Chat Page with Sidebar and Controls
 * 사이드바와 컨트롤이 있는 향상된 채팅 페이지
 *
 * Features:
 * - Chat rooms sidebar / 채팅 방 사이드바
 * - Stop streaming button / 스트리밍 중지 버튼
 * - Reset session controls / 세션 초기화 컨트롤
 * - Agent type tabs / 에이전트 타입 탭
 * - Proper stream cancellation with AbortController / AbortController로 스트림 취소
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { ROUTES } from '../../types/careguide-ia';
import { useApp } from '../../contexts/AppContext';
import { useAuth } from '../../contexts/AuthContext';

// Components
import { ChatSidebar } from '../../components/chat/ChatSidebar';
import { ChatHeader } from '../../components/chat/ChatHeader';
import { ChatMessages } from '../../components/chat/ChatMessages';
import { ChatInput } from '../../components/chat/ChatInput';
import { QuizPromptBanner } from '../../components/chat/QuizPromptBanner';

// Hooks
import { useChatRooms } from '../../hooks/useChatRooms';

// Types
import type { ChatMessage } from '../../types/chat';
import type { IntentCategory } from '../../types/intent';
import { routeQueryStream, type AgentType, type StreamCallOptions } from '../../services/intentRouter';
import { getChatHistoryBySession, getUserProfile } from '../../services/api';
import { createSession, analyzeNutrition } from '../../services/dietCareApi';
import {
  getPublishedUserProfile,
  isUserProfile,
  type UserProfile,
} from '../../utils/profileSync';

/**
 * Location state interface for navigation
 * 네비게이션을 위한 Location state 인터페이스
 */
interface LocationState {
  fromMain?: boolean;
  initialMessage?: string;
  selectedImage?: File | null;
  selectedCategory?: string;
}

const ChatPageEnhanced: React.FC = () => {
  const { t } = useApp();
  const { user } = useAuth();
  const location = useLocation();
  const [chatProfile, setChatProfile] = useState<UserProfile>(user?.profile || 'general');
  const [profileHydratedUserId, setProfileHydratedUserId] = useState<string | null>(null);
  const [defaultRoomCreationKey, setDefaultRoomCreationKey] = useState<string | null>(null);
  const profileRevision = useRef(0);
  const defaultRoomCreationRef = useRef<string | null>(null);
  const defaultRoomAttemptedKeyRef = useRef<string | null>(null);

  // Sidebar state
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Chat rooms hook
  const {
    activeRooms,
    currentRoomId,
    createRoom,
    deleteRoom,
    updateRoom,
    togglePinRoom,
    toggleArchiveRoom,
    updateRoomLastMessage,
    incrementMessageCount,
    clearAllRooms,
    setCurrentRoomId,
    rooms,
    isHydrated,
    hydrationError,
    retryHydration,
  } = useChatRooms(user?.id, chatProfile);

  // Stream state
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const abortControllerRef = useRef<AbortController | null>(null);
  const activeUserIdRef = useRef(user?.id);
  activeUserIdRef.current = user?.id;

  // Messages state (keyed by room ID)
  // Chat content is restored from backend history; never persist health data in
  // browser storage.
  const [messagesByRoom, setMessagesByRoom] = useState<Record<string, ChatMessage[]>>({});

  // Input state
  const [input, setInput] = useState('');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  // Session state
  const [isSessionExpired, setIsSessionExpired] = useState(false);
  const [isRestoringHistory, setIsRestoringHistory] = useState(false);

  // Refs
  const initialMessageProcessed = useRef(false);
  const initialMessageSendRef = useRef<((message: string) => Promise<void>) | null>(null);

  // Page visibility animation
  const [pageVisible, setPageVisible] = useState(false);

  useEffect(() => {
    profileRevision.current += 1;
    setChatProfile(user?.profile || 'general');
  }, [user?.profile]);

  useEffect(() => {
    let cancelled = false;
    const activeUserId = user?.id;
    const applyProfile = (value: string | null) => {
      if (!cancelled && isUserProfile(value)) {
        profileRevision.current += 1;
        setChatProfile(value);
      }
    };

    const loadProfile = async () => {
      if (!activeUserId) return;
      const requestRevision = profileRevision.current;
      try {
        const profile = await getUserProfile();
        if (profileRevision.current !== requestRevision) return;
        if (profile?.profile) {
          applyProfile(profile.profile);
        } else {
          applyProfile(getPublishedUserProfile());
        }
      } catch {
        applyProfile(getPublishedUserProfile());
      } finally {
        if (!cancelled) setProfileHydratedUserId(activeUserId);
      }
    };

    const handleProfileChanged = (event: Event) => {
      applyProfile((event as CustomEvent<string>).detail);
    };

    void loadProfile();
    window.addEventListener('careguide:profile-changed', handleProfileChanged);
    return () => {
      cancelled = true;
      window.removeEventListener('careguide:profile-changed', handleProfileChanged);
    };
  }, [user?.id]);

  const isRoomCreationReady = Boolean(
    user?.id && isHydrated && profileHydratedUserId === user.id
  );

  // Current agent type based on route
  const isMedicalWelfare = location.pathname === ROUTES.CHAT_MEDICAL_WELFARE;
  const isNutrition = location.pathname === ROUTES.CHAT_NUTRITION;
  const isResearch = location.pathname === ROUTES.CHAT_RESEARCH;

  /**
   * Get current agent type based on route
   * 경로 기반으로 현재 에이전트 타입 가져오기
   */
  const getCurrentAgentType = useCallback((): AgentType | 'auto' => {
    if (isMedicalWelfare) return 'medical_welfare';
    if (isNutrition) return 'nutrition';
    if (isResearch) return 'research_paper';
    return 'auto';
  }, [isMedicalWelfare, isNutrition, isResearch]);

  /**
   * Get messages for current room
   * 현재 방의 메시지 가져오기
   */
  const currentMessages = currentRoomId ? messagesByRoom[currentRoomId] || [] : [];

  /**
   * Calculate user message count for quiz prompt
   * 퀴즈 프롬프트를 위한 사용자 메시지 수 계산
   */
  const userMessageCount = currentMessages.filter(msg => msg.role === 'user').length;

  // Page enter animation
  useEffect(() => {
    const timer = setTimeout(() => setPageVisible(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // Create default room if none exists
  useEffect(() => {
    const initializeDefaultRoom = async () => {
      if (!user?.id || !isRoomCreationReady) return;
      if (rooms.length === 0) {
        const capturedUserId = user.id;
        const creationKey = `${capturedUserId}:${chatProfile}:${getCurrentAgentType()}`;
        if (
          defaultRoomCreationRef.current
          || defaultRoomAttemptedKeyRef.current === creationKey
        ) return;
        defaultRoomCreationRef.current = creationKey;
        defaultRoomAttemptedKeyRef.current = creationKey;
        setDefaultRoomCreationKey(creationKey);
        try {
          await createRoom(
            { agentType: getCurrentAgentType() },
            capturedUserId,
            chatProfile,
          );
        } catch {
          // The hook rejects stale user/profile results and hydration failures.
        } finally {
          if (defaultRoomCreationRef.current === creationKey) {
            defaultRoomCreationRef.current = null;
          }
          setDefaultRoomCreationKey((current) => current === creationKey ? null : current);
        }
      } else if (!currentRoomId && rooms.length > 0) {
        setCurrentRoomId(rooms[0].id);
      }
    };
    void initializeDefaultRoom();
  }, [rooms, currentRoomId, createRoom, defaultRoomCreationKey, getCurrentAgentType, setCurrentRoomId, user?.id, chatProfile, isRoomCreationReady]);

  // Cleanup on unmount, route change, or authenticated actor transition.
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = null;
      setIsStreaming(false);
      setStreamingContent('');
    };
  }, [location.pathname, user?.id]);

  /**
   * Toggle sidebar
   * 사이드바 토글
   */
  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen((prev) => !prev);
  }, []);

  /**
   * Close sidebar
   * 사이드바 닫기
   */
  const closeSidebar = useCallback(() => {
    setIsSidebarOpen(false);
  }, []);

  /**
   * Handle room selection
   * 방 선택 처리
   */
  const handleSelectRoom = useCallback(
    (roomId: string) => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      setIsStreaming(false);
      setStreamingContent('');
      setCurrentRoomId(roomId);
      setIsSessionExpired(false);
    },
    [setCurrentRoomId]
  );

  /**
   * Handle create new room
   * 새 방 생성 처리
   */
  const handleCreateRoom = useCallback(async () => {
    if (!isRoomCreationReady || !user?.id) return;
    await createRoom(
      { agentType: getCurrentAgentType() },
      user.id,
      chatProfile
    );
  }, [createRoom, getCurrentAgentType, user?.id, chatProfile, isRoomCreationReady]);

  /**
   * Handle delete room
   * 방 삭제 처리
   */
  const handleDeleteRoom = useCallback(
    (roomId: string) => {
      // Also delete messages for this room
      setMessagesByRoom((prev) => {
        const newMessages = { ...prev };
        delete newMessages[roomId];
        return newMessages;
      });
      deleteRoom(roomId);
    },
    [deleteRoom]
  );

  /**
   * Handle stop streaming
   * 스트리밍 중지 처리
   */
  const handleStopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
      setStreamingContent('');
    }
  }, []);

  /**
   * Handle reset current session
   * 현재 세션 초기화 처리
   */
  const handleResetSession = useCallback(() => {
    if (currentRoomId) {
      setMessagesByRoom((prev) => ({
        ...prev,
        [currentRoomId]: [],
      }));
      updateRoom(currentRoomId, {
        messageCount: 0,
        lastMessage: undefined,
        lastMessageTime: undefined,
      });
    }
    handleStopStream();
    setIsSessionExpired(false);
  }, [currentRoomId, updateRoom, handleStopStream]);

  /**
   * Handle reset all sessions
   * 모든 세션 초기화 처리
   */
  const handleResetAllSessions = useCallback(async () => {
    if (!isRoomCreationReady || !user?.id) return;
    setMessagesByRoom({});
    clearAllRooms();
    handleStopStream();
    setIsSessionExpired(false);
    // Create a new default room
    await createRoom({ agentType: getCurrentAgentType() }, user.id, chatProfile);
  }, [clearAllRooms, handleStopStream, createRoom, getCurrentAgentType, user?.id, chatProfile, isRoomCreationReady]);

  /**
   * Handle restore history
   * 히스토리 복원 처리
   */
  const handleRestoreHistory = useCallback(async () => {
    if (!currentRoomId) return;

    setIsRestoringHistory(true);
    try {
      // Fetch chat history from backend using session/room ID
      const historyResponse = await getChatHistoryBySession(currentRoomId, 100);

      if (historyResponse.conversations && historyResponse.conversations.length > 0) {
        // Convert backend conversation format to ChatMessage format
        // Backend returns user_input and agent_response, so we need to expand each conversation
        const restoredMessages: ChatMessage[] = [];
        historyResponse.conversations.forEach((conv, index) => {
          // Add user message
          restoredMessages.push({
            id: `restored_${currentRoomId}_${index}_user_${Date.now()}`,
            role: 'user',
            content: conv.user_input,
            timestamp: conv.timestamp ? new Date(conv.timestamp) : new Date(),
            intents: [],
            agents: [],
            confidence: undefined,
            isDirectResponse: false,
            isEmergency: false,
          });
          // Add assistant response
          restoredMessages.push({
            id: `restored_${currentRoomId}_${index}_assistant_${Date.now()}`,
            role: 'assistant',
            content: conv.agent_response,
            timestamp: conv.timestamp ? new Date(conv.timestamp) : new Date(),
            intents: [],
            agents: [],
            confidence: undefined,
            isDirectResponse: false,
            isEmergency: false,
            roomId: currentRoomId,
          });
        });

        // Update messages for current room
        setMessagesByRoom((prev) => ({
          ...prev,
          [currentRoomId]: restoredMessages,
        }));
      }

      setIsSessionExpired(false);
    } catch (_error) {
      // Preserve current messages; the existing retry state remains visible.
      void _error;
    } finally {
      setIsRestoringHistory(false);
    }
  }, [currentRoomId]);

  /**
   * Handle start new conversation
   * 새 대화 시작 처리
   */
  const handleStartNewConversation = useCallback(() => {
    setIsSessionExpired(false);
    handleCreateRoom();
  }, [handleCreateRoom]);

  /**
   * Handle image select
   * 이미지 선택 처리
   */
  const handleImageSelect = useCallback((file: File) => {
    setSelectedImage(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  }, []);

  /**
   * Handle image remove
   * 이미지 제거 처리
   */
  const handleImageRemove = useCallback(() => {
    setSelectedImage(null);
    setImagePreview(null);
  }, []);

  /**
   * Handle send message with custom message
   * 커스텀 메시지로 전송 처리
   */
  const handleSendWithMessage = useCallback(async (customMessage?: string) => {
    const messageToSend = customMessage || input;
    if (!messageToSend.trim() && !selectedImage) return;
    const initiatingUserId = user?.id;
    if (!initiatingUserId || !isRoomCreationReady) return;

    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new AbortController for this request
    const requestController = new AbortController();
    abortControllerRef.current = requestController;
    const requestIsActive = () => (
      activeUserIdRef.current === initiatingUserId
      && abortControllerRef.current === requestController
      && !requestController.signal.aborted
    );

    // Get or create room ID (must await if creating new room)
    // 방 ID 가져오기 또는 생성 (새 방 생성 시 await 필요)
    let roomId = currentRoomId;
    if (!roomId) {
      let createdRoomId: string;
      try {
        const newRoom = await createRoom(
          { agentType: getCurrentAgentType() },
          initiatingUserId,
          chatProfile
        );
        createdRoomId = newRoom.id;
      } catch {
        if (abortControllerRef.current === requestController) {
          abortControllerRef.current = null;
        }
        return;
      }
      if (!requestIsActive()) return;
      roomId = createdRoomId;
    }

    if (!requestIsActive()) return;

    const messageContent = selectedImage
      ? `${messageToSend || '음식 이미지 분석'} [이미지 첨부]`
      : messageToSend;

    // Create user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: messageContent,
      timestamp: new Date(),
      roomId,
    };

    // Add user message to room
    setMessagesByRoom((prev) => ({
      ...prev,
      [roomId]: [...(prev[roomId] || []), userMessage],
    }));

    // Update room last message
    updateRoomLastMessage(roomId, messageContent, new Date());
    incrementMessageCount(roomId);

    // Clear input
    const currentImage = selectedImage;
    setInput('');
    setSelectedImage(null);
    setImagePreview(null);
    setIsStreaming(true);
    setStreamingContent('');

    const assistantMessageId = (Date.now() + 1).toString();

    try {
      // Handle nutrition image upload (non-streaming)
      if (isNutrition && currentImage) {
        // Create a valid session first
        const sessionResponse = await createSession(initiatingUserId);

        // Call nutrition analysis API with proper session
        const nutritionResponse = await analyzeNutrition({
          session_id: sessionResponse.session_id,
          image: currentImage,
          text: messageToSend || '음식 이미지 분석',
        });
        if (!requestIsActive()) return;

        // Format the analysis result for display
        const analysis = nutritionResponse.analysis;
        const foodsText = analysis.foods
          .map(f => `- ${f.name}: ${f.calories}kcal, 단백질 ${f.protein_g}g, 나트륨 ${f.sodium_mg}mg`)
          .join('\n');

        const assistantContent = `## 영양 분석 결과\n\n**식품 목록:**\n${foodsText}\n\n**총 영양소:**\n- 칼로리: ${analysis.total_calories}kcal\n- 단백질: ${analysis.total_protein_g}g\n- 나트륨: ${analysis.total_sodium_mg}mg\n- 칼륨: ${analysis.total_potassium_mg}mg\n- 인: ${analysis.total_phosphorus_mg}mg\n\n**권장사항:**\n${analysis.recommendations.map(r => `- ${r}`).join('\n')}${analysis.warnings.length > 0 ? `\n\n**주의사항:**\n${analysis.warnings.map(w => `⚠️ ${w}`).join('\n')}` : ''}`;

        const assistantMessage: ChatMessage = {
          id: assistantMessageId,
          role: 'assistant',
          content: assistantContent,
          timestamp: new Date(),
          intents: ['nutrition' as IntentCategory],
          agents: ['nutrition' as AgentType],
          confidence: 0.95,
          roomId,
        };

        setMessagesByRoom((prev) => ({
          ...prev,
          [roomId]: [...(prev[roomId] || []), assistantMessage],
        }));
        updateRoomLastMessage(roomId, assistantContent, new Date());
        incrementMessageCount(roomId);
      } else {
        // Stream text response with room-based session separation
        // 방 기반 세션 분리로 스트리밍 응답
        const streamOptions: StreamCallOptions = {
          sessionId: roomId,  // Use roomId as sessionId for Parlant session separation
          roomId: roomId,
          userId: initiatingUserId,
          userProfile: chatProfile,
        };

        const response = await routeQueryStream(
          messageToSend,
          // onChunk callback
          (content, _isComplete) => {
            if (requestIsActive()) setStreamingContent(content);
          },
          // onError callback
          (_error) => undefined,
          // Options with sessionId = roomId for proper room separation
          streamOptions,
          requestController.signal,
        );
        if (!requestIsActive()) return;

        // Add final assistant message
        const assistantMessage: ChatMessage = {
          id: assistantMessageId,
          role: 'assistant',
          content: response.content,
          timestamp: new Date(),
          intents: response.intents,
          agents: response.agents,
          confidence: response.confidence,
          isDirectResponse: response.isDirectResponse,
          isEmergency: response.isEmergency,
          roomId,
        };

        setMessagesByRoom((prev) => ({
          ...prev,
          [roomId]: [...(prev[roomId] || []), assistantMessage],
        }));
        updateRoomLastMessage(roomId, response.content, new Date());
        incrementMessageCount(roomId);
      }
    } catch (error) {
      if (!requestIsActive()) return;
      // Don't show error for user-cancelled requests
      if ((error as Error).name === 'AbortError') {
        return;
      }

      const errorMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: '죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.',
        timestamp: new Date(),
        roomId,
        fallbackType: 'RESPONSE_GENERATION_FAILED',
      };

      setMessagesByRoom((prev) => ({
        ...prev,
        [roomId]: [...(prev[roomId] || []), errorMessage],
      }));
    } finally {
      if (
        activeUserIdRef.current === initiatingUserId
        && abortControllerRef.current === requestController
      ) {
        setIsStreaming(false);
        setStreamingContent('');
        abortControllerRef.current = null;
      }
    }
  }, [
    input,
    selectedImage,
    currentRoomId,
    isNutrition,
    chatProfile,
    createRoom,
    getCurrentAgentType,
    updateRoomLastMessage,
    incrementMessageCount,
    user?.id,
    isRoomCreationReady,
  ]);
  initialMessageSendRef.current = handleSendWithMessage;

  /**
   * Handle send message (delegates to handleSendWithMessage)
   * 메시지 전송 처리 (handleSendWithMessage에 위임)
   */
  const handleSend = useCallback(async () => {
    await handleSendWithMessage();
  }, [handleSendWithMessage]);

  // Consume MainPage's initial message only after actor/profile/room hydration.
  useEffect(() => {
    const state = location.state as LocationState | null;
    if (
      !isRoomCreationReady
      || !currentRoomId
      || !state?.initialMessage
      || initialMessageProcessed.current
    ) return;

    const initialMessage = state.initialMessage;
    setInput(initialMessage);
    const timer = setTimeout(() => {
      const sendInitialMessage = initialMessageSendRef.current;
      if (!sendInitialMessage) return;
      initialMessageProcessed.current = true;
      void sendInitialMessage(initialMessage);
    }, 500);

    return () => clearTimeout(timer);
  }, [currentRoomId, isRoomCreationReady, location.state]);

  /**
   * Handle suggestion click
   * 제안 클릭 처리
   */
  const handleSuggestionClick = useCallback((suggestion: string) => {
    // Directly call handleSendWithMessage with the suggestion
    handleSendWithMessage(suggestion);
  }, [handleSendWithMessage]);

  return (
    <div
      className={`flex flex-col lg:flex-row h-full transition-all duration-500 bg-surface-alt lg:rounded-2xl lg:overflow-hidden lg:shadow-soft ${
        pageVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-95'
      }`}
      role="main"
      aria-label="AI 채팅"
    >
      {/* Screen reader announcement for streaming */}
      {isStreaming && (
        <div className="sr-only" role="status" aria-live="polite">
          AI가 응답을 생성하고 있습니다...
        </div>
      )}

      {/* Sidebar */}
      <ChatSidebar
        rooms={activeRooms}
        currentRoomId={currentRoomId}
        onSelectRoom={handleSelectRoom}
        onCreateRoom={handleCreateRoom}
        onDeleteRoom={handleDeleteRoom}
        onTogglePin={togglePinRoom}
        onToggleArchive={toggleArchiveRoom}
        isOpen={isSidebarOpen}
        onClose={closeSidebar}
        isCreateDisabled={!isRoomCreationReady}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-white/50 backdrop-blur-sm">
        {/* Header */}
        <ChatHeader
          currentPath={location.pathname}
          isStreaming={isStreaming}
          onToggleSidebar={toggleSidebar}
          onStopStream={handleStopStream}
          onResetSession={handleResetSession}
          onResetAllSessions={handleResetAllSessions}
          hasMessages={currentMessages.length > 0}
        />

        {/* Messages */}
        {hydrationError && (
          <div
            className="mx-4 mt-3 flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            role="alert"
          >
            <span>{hydrationError}</span>
            <button
              type="button"
              className="shrink-0 rounded-lg bg-white px-3 py-1.5 font-medium text-red-700 shadow-sm hover:bg-red-100"
              onClick={retryHydration}
            >
              다시 시도
            </button>
          </div>
        )}
        <ChatMessages
          messages={currentMessages}
          isStreaming={isStreaming}
          streamingContent={streamingContent}
          isSessionExpired={isSessionExpired}
          isRestoringHistory={isRestoringHistory}
          onRestoreHistory={handleRestoreHistory}
          onStartNewConversation={handleStartNewConversation}
          agentType={getCurrentAgentType() === 'research_paper' ? 'research' : getCurrentAgentType() as 'auto' | 'medical_welfare' | 'nutrition'}
          onSuggestionClick={handleSuggestionClick}
        />

        {/* Quiz Prompt Banner - Shows after 4 user messages */}
        <QuizPromptBanner userMessageCount={userMessageCount} />

        {/* Input */}
        <ChatInput
          input={input}
          onInputChange={setInput}
          onSend={handleSend}
          isDisabled={isStreaming || !isRoomCreationReady}
          placeholder={isNutrition ? '메시지 입력...' : t.chat.placeholder}
          showImageUpload={isNutrition}
          selectedImage={selectedImage}
          imagePreview={imagePreview}
          onImageSelect={handleImageSelect}
          onImageRemove={handleImageRemove}
        />
      </div>
    </div>
  );
};

export default ChatPageEnhanced;
