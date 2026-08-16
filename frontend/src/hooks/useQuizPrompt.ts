/**
 * useQuizPrompt Hook - QUI-007
 * Tracks user messages and shows quiz prompt after 4 messages
 * 사용자 메시지를 추적하고 4개 메시지 후 퀴즈 프롬프트 표시
 */

import { useState } from 'react';

export const useQuizPrompt = (_currentMessageCount: number) => {
  const [userMessageCount, setUserMessageCount] = useState(0);
  const [promptDismissed, setPromptDismissed] = useState(false);
  const showQuizPrompt = userMessageCount >= 4 && !promptDismissed;

  const incrementMessageCount = () => {
    setUserMessageCount((prev) => prev + 1);
  };

  const dismissQuizPrompt = () => {
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
