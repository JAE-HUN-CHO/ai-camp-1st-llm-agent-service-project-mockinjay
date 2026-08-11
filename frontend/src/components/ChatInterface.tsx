import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, User, Bot, Loader2, ChevronDown, History, Clock } from 'lucide-react';
import api, { getChatHistory } from '../services/api';
import clsx from 'clsx';
import { useApp } from '../contexts/AppContext';
import { useAuth } from '../contexts/AuthContext';
import { useIdleTimer } from '../hooks/useIdleTimer';
import { env } from '../config/env';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatInterfaceProps {
  agentType?: string; // Optional: to specify a specific agent if needed
}

const ChatInterface: React.FC<ChatInterfaceProps> = () => {
  const { t } = useApp();
  const { user, updateProfile } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<'general' | 'patient' | 'researcher'>(
    user?.profile || 'patient'
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const IDLE_TIMEOUT = 5 * 60 * 1000; // 5 minutes in ms (for screen clear)

  // State for idle/session expiration
  const [isSessionExpired, setIsSessionExpired] = useState(false);
  const [isRestoringHistory, setIsRestoringHistory] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const initSession = async () => {
      try {
        // Chat content and session identifiers stay in memory. Backend history
        // is the source of truth for restoration.
        const userId = user?.id || 'guest_user';
        const response = await api.post('/api/session/create', { user_id: userId });
        const newSessionId = response.data.session_id;
        setSessionId(newSessionId);
        setMessages([]);
      } catch (error) {
        console.error('Failed to initialize session:', error);
      }
    };
    initSession();
  }, [user?.id]);

  // Handle idle timeout - clear messages from screen after 5 minutes of inactivity
  const handleIdle = useCallback(() => {
    if (messages.length > 0) {
      setIsSessionExpired(true);
      setMessages([]); // Clear messages from screen only
      // Note: Messages are still saved in DB (automatically by backend)
      // Backend history remains available for an explicit restore action.
    }
  }, [messages.length]);

  // Handle user becoming active again
  const handleActive = useCallback(() => {
    // User is active - timer will be reset automatically
  }, []);

  // Use idle timer hook
  const { reset: resetIdleTimer } = useIdleTimer({
    timeout: IDLE_TIMEOUT,
    onIdle: handleIdle,
    onActive: handleActive,
    enabled: messages.length > 0 && !isSessionExpired, // Only active when there are messages
  });

  // Restore chat history from DB
  const restoreChatHistory = useCallback(async () => {
    if (!user?.id || !sessionId) {
      console.warn('Cannot restore history: missing user ID or session ID');
      return;
    }

    setIsRestoringHistory(true);
    try {
      const history = await getChatHistory(user.id, sessionId, 50);

      if (history.conversations && history.conversations.length > 0) {
        // Convert DB format to Message format
        const restoredMessages: Message[] = [];

        history.conversations.forEach((conv, index) => {
          // Add user message
          if (conv.user_input) {
            restoredMessages.push({
              id: `restored-user-${index}`,
              role: 'user',
              content: conv.user_input,
              timestamp: new Date(conv.timestamp),
            });
          }
          // Add assistant message
          if (conv.agent_response) {
            restoredMessages.push({
              id: `restored-assistant-${index}`,
              role: 'assistant',
              content: conv.agent_response,
              timestamp: new Date(conv.timestamp),
            });
          }
        });

        setMessages(restoredMessages);
        setIsSessionExpired(false);
        resetIdleTimer(); // Reset idle timer after restoration
      }
    } catch (error) {
      console.error('Failed to restore chat history:', error);
    } finally {
      setIsRestoringHistory(false);
    }
  }, [user?.id, sessionId, resetIdleTimer]);

  // Start new conversation (clear expired state without restoring)
  const startNewConversation = useCallback(() => {
    setIsSessionExpired(false);
    setMessages([]);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Create placeholder for first bot message (loading state)
    let currentBotMessageId = (Date.now() + 1).toString();
    const initialBotMessage: Message = {
      id: currentBotMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, initialBotMessage]);

    try {
      const payload = {
        query: userMessage.content,
        session_id: sessionId,
        agent_type: 'auto',
        user_profile: selectedProfile,
      };

      const response = await fetch(`${env.apiBaseUrl}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: abortControllerRef.current.signal,
      });

      if (!response.body) throw new Error('No response body');

      console.log('🚀 SSE stream started, response status:', response.status);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let buffer = '';
      let messageCount = 0;
      let firstMessageReceived = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        console.log('📥 SSE chunk received, done:', doneReading, 'value length:', value?.length);
        done = doneReading;

        if (value) {
          const chunkValue = decoder.decode(value, { stream: true });
          buffer += chunkValue;
          console.log('📄 Buffer content (first 200 chars):', buffer.substring(0, 200));

          // SSE messages are separated by \n\n, so split properly
          const messages = buffer.split('\n\n');
          console.log('📨 Split messages count:', messages.length);
          buffer = messages.pop() || ''; // Keep incomplete message in buffer

          for (const message of messages) {
            const lines = message.split('\n');
            for (const line of lines) {
              const trimmedLine = line.trim();
              if (trimmedLine.startsWith('data: ')) {
                const dataStr = trimmedLine.slice(6);

                if (dataStr === '[DONE]') {
                  done = true;
                  break;
                }

                try {
                  const data = JSON.parse(dataStr);
                  console.log('🔍 SSE parsed data:', {
                    hasContent: !!data.content,
                    hasAnswer: !!data.answer,
                    hasResponse: !!data.response,
                    status: data.status,
                    agent_type: data.agent_type,
                    answerPreview: data.answer?.substring(0, 100)
                  });

                  let newContent = '';

                  // Check all possible content fields
                  if (data.content) {
                    newContent = data.content;
                  } else if (data.answer) {
                    newContent = data.answer;
                  } else if (data.response) {
                    newContent = data.response;
                  }

                  // Get status from backend (streaming, new_message, complete, etc.)
                  const messageStatus = data.status;
                  console.log('📝 newContent set:', newContent ? newContent.substring(0, 100) : '(empty)', 'status:', messageStatus);

                  if (newContent) {
                    messageCount++;
                    console.log('✅ Processing message #', messageCount, 'firstMessageReceived:', firstMessageReceived, 'status:', messageStatus);

                    if (!firstMessageReceived) {
                      // First message: update the placeholder
                      // 첫 번째 메시지: 플레이스홀더 업데이트
                      firstMessageReceived = true;
                      const capturedContent = newContent;
                      const capturedId = currentBotMessageId;
                      console.log('📤 Updating placeholder message id:', capturedId);
                      setMessages((prev) => {
                        console.log('📤 setMessages called, prev length:', prev.length);
                        return prev.map(msg =>
                          msg.id === capturedId
                            ? { ...msg, content: capturedContent }
                            : msg
                        );
                      });
                    } else if (messageStatus === 'new_message') {
                      // new_message status: append with line break to current bubble
                      // new_message 상태: 현재 버블에 줄바꿈 추가 후 붙이기
                      const capturedContent = newContent;
                      const capturedId = currentBotMessageId;
                      console.log('📤 Appending new_message with line break to:', capturedId);
                      setMessages((prev) =>
                        prev.map(msg =>
                          msg.id === capturedId
                            ? { ...msg, content: msg.content + '\n\n---\n\n' + capturedContent }
                            : msg
                        )
                      );
                    } else {
                      // Other statuses (streaming continuation, etc.): create new bubble
                      // 기타 상태 (스트리밍 연속 등): 새 버블 생성
                      const newMessageId = `${Date.now()}-${messageCount}`;
                      const capturedContent = newContent;
                      console.log('📤 Creating new message bubble id:', newMessageId);
                      setMessages((prev) => [...prev, {
                        id: newMessageId,
                        role: 'assistant' as const,
                        content: capturedContent,
                        timestamp: new Date(),
                      }]);
                      currentBotMessageId = newMessageId;
                    }
                  } else {
                    console.log('⚠️ newContent is empty, skipping message update');
                  }
                } catch (e) {
                  console.error('SSE parse error:', e, 'dataStr:', dataStr?.substring(0, 200));
                }
              }
            }
            if (done) break;
          }
        }
      }

      // Process remaining buffer
      if (buffer.trim()) {
        const lines = buffer.split('\n');
        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith('data: ')) {
            const dataStr = trimmedLine.slice(6);
            if (dataStr !== '[DONE]') {
              try {
                const data = JSON.parse(dataStr);
                const newContent = data.content || data.answer || data.response;
                if (newContent && !firstMessageReceived) {
                  const capturedContent = newContent;
                  const capturedId = currentBotMessageId;
                  firstMessageReceived = true;
                  setMessages((prev) =>
                    prev.map(msg =>
                      msg.id === capturedId
                        ? { ...msg, content: capturedContent }
                        : msg
                    )
                  );
                }
              } catch (e) {
                console.error('SSE buffer parse error:', e);
              }
            }
          }
        }
      }

      // Remove empty placeholder if no messages received
      if (!firstMessageReceived) {
        setMessages((prev) => prev.filter(msg => msg.id !== currentBotMessageId));
      }
    } catch (error: any) {
      // Don't show error if request was aborted (user cancelled)
      if (error.name === 'AbortError') {
        console.log('Request was cancelled');
        // Remove the placeholder message for cancelled request
        setMessages((prev) => prev.filter(msg => msg.id !== currentBotMessageId));
        return;
      }

      console.error('Failed to send message:', error);
      setMessages((prev) =>
        prev.map(msg =>
          msg.id === currentBotMessageId
            ? { ...msg, content: t.common.error }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-colors duration-200">
      {/* Disclaimer Banner */}
      <div className="bg-yellow-50 dark:bg-yellow-900/30 border-b border-yellow-100 dark:border-yellow-800 p-2 text-center text-xs text-yellow-800 dark:text-yellow-200 transition-colors duration-200">
        {t.chat.disclaimer}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-white dark:bg-gray-800 transition-colors duration-200">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 dark:text-gray-400">
            {isSessionExpired ? (
              // Session expired UI - show restore button
              <div className="space-y-4">
                <Clock className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600" />
                <div>
                  <p className="text-lg font-medium text-gray-600 dark:text-gray-300">
                    세션이 만료되었습니다
                  </p>
                  <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                    5분간 활동이 없어 대화가 화면에서 숨겨졌습니다
                  </p>
                </div>
                <div className="flex flex-col sm:flex-row gap-3 mt-4">
                  <button
                    onClick={restoreChatHistory}
                    disabled={isRestoringHistory || !user?.id}
                    className="inline-flex items-center justify-center px-4 py-2 bg-[#00C8B4] text-white rounded-lg hover:bg-[#00b3a1] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isRestoringHistory ? (
                      <>
                        <Loader2 className="animate-spin mr-2 h-4 w-4" />
                        불러오는 중...
                      </>
                    ) : (
                      <>
                        <History className="mr-2 h-4 w-4" />
                        이전 대화 보기
                      </>
                    )}
                  </button>
                  <button
                    onClick={startNewConversation}
                    className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    새 대화 시작
                  </button>
                </div>
                {!user?.id && (
                  <p className="text-xs text-amber-500 mt-2">
                    로그인하면 이전 대화를 복원할 수 있습니다
                  </p>
                )}
              </div>
            ) : (
              // Normal empty state
              <div className="mt-10">
                <Bot className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600 mb-2" />
                <p>{t.chat.welcome}</p>
              </div>
            )}
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={clsx(
              'flex w-full',
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={clsx(
                'flex p-3',
                msg.role === 'user'
                  ? 'chat-bubble-user'
                  : 'chat-bubble-ai'
              )}
            >
              <div className="mr-2 mt-1 flex-shrink-0">
                {msg.role === 'user' ? (
                  <User size={16} />
                ) : (
                  <Bot size={16} />
                )}
              </div>
              <div className="whitespace-pre-wrap">
                {msg.content || (msg.role === 'assistant' && isLoading ? (
                  <span className="flex items-center text-gray-400">
                    <Loader2 className="animate-spin mr-2 h-3 w-3" />
                    {t.chat.thinking}
                  </span>
                ) : msg.content)}
              </div>
            </div>
          </div>
        ))}
{/* Loading indicator is now shown inside the message bubble */}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
        <form onSubmit={handleSend} className="flex flex-col space-y-2">
          {/* Profile Selector */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-gray-500">맞춤 정보:</span>
            <div className="relative flex items-center gap-1 cursor-pointer">
              <span className="text-[11px] text-[#00c8b4] font-medium">
                {selectedProfile === 'general' ? '일반인(간병인)' :
                 selectedProfile === 'patient' ? '환자(신장병 환우)' :
                 '연구원'}
              </span>
              <ChevronDown size={12} color="#00C8B4" />
              <select
                value={selectedProfile}
                onChange={(e) => {
                  const newProfile = e.target.value as 'general' | 'patient' | 'researcher';
                  setSelectedProfile(newProfile);
                  updateProfile(newProfile);
                }}
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              >
                <option value="patient">환자(신장병 환우)</option>
                <option value="general">일반인(간병인)</option>
                <option value="researcher">연구원</option>
              </select>
            </div>
          </div>

          {/* Input Field */}
          <div className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t.chat.placeholder}
              className="input-field flex-1 dark:bg-gray-800 dark:text-gray-100"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="btn-primary inline-flex items-center disabled:opacity-50"
            >
              <Send size={16} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ChatInterface;
