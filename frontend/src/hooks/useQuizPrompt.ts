/**
 * useQuizPrompt Hook - QUI-007
 * Tracks user messages and shows quiz prompt after 4 messages
 * 사용자 메시지를 추적하고 4개 메시지 후 퀴즈 프롬프트 표시
 */

import { useState, useEffect } from 'react';

export const useQuizPrompt = (_currentMessageCount: number) => {
  const [showQuizPrompt, setShowQuizPrompt] = useState(false);
  const [userMessageCount, setUserMessageCount] = useState(0);
  const [promptDismissed, setPromptDismissed] = useState(false);

  useEffect(() => {
    if (userMessageCount >= 4 && !promptDismissed && !showQuizPrompt) {
      setShowQuizPrompt(true);
    }
  }, [promptDismissed, userMessageCount, showQuizPrompt]);

  const incrementMessageCount = () => {
    setUserMessageCount((prev) => prev + 1);
  };

  const dismissQuizPrompt = () => {
    setShowQuizPrompt(false);
    setPromptDismissed(true);
  };

  const resetMessageCount = () => {
    setUserMessageCount(0);
    setPromptDismissed(false);
  };

  return {
    showQuizPrompt,
    userMessageCount,
    incrementMessageCount,
    dismissQuizPrompt,
    resetMessageCount,
  };
};
