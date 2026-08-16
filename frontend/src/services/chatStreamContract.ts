export type ChatStreamStatus =
  | 'streaming'
  | 'processing'
  | 'partial'
  | 'synthesizing'
  | 'complete'
  | 'new_message'
  | 'success'
  | 'error'
  | 'cancelled';

export interface ChatStreamFrame {
  status?: ChatStreamStatus;
  content?: string;
  answer?: string;
  response?: string;
  error?: string;
  message?: string;
  [key: string]: unknown;
}

export type ChatTerminal = 'open' | 'success' | 'error' | 'cancelled';

export interface ChatStreamState {
  content: string;
  terminal: ChatTerminal;
  transportDone: boolean;
  error?: string;
}

/**
 * 채팅 스트림의 초기 상태를 생성합니다.
 *
 * @returns 빈 콘텐츠, 열린 터미널 상태 및 완료되지 않은 전송 상태를 가진 채팅 스트림 상태
 */
export function createChatStreamState(): ChatStreamState {
  return { content: '', terminal: 'open', transportDone: false };
}

/**
 * 채팅 스트림 프레임을 상태에 반영합니다.
 *
 * 스트리밍 콘텐츠를 누적하고, 메시지·부분 응답을 갱신하며, 성공·오류·취소 상태를 처리합니다.
 * 전송 완료 또는 터미널 상태 이후에 수신된 프레임은 오류로 처리합니다.
 *
 * @param state - 현재 채팅 스트림 상태
 * @param frame - 반영할 채팅 스트림 프레임
 * @returns 프레임이 반영된 새로운 채팅 스트림 상태
 */
export function applyChatStreamFrame(
  state: ChatStreamState,
  frame: ChatStreamFrame,
): ChatStreamState {
  if (state.transportDone) throw new Error('SSE frame received after [DONE]');
  if (state.terminal !== 'open') {
    throw new Error(`SSE frame received after terminal ${state.terminal}`);
  }

  const content = frame.content || frame.answer || frame.response || '';
  if (frame.error && frame.status !== 'cancelled') {
    return { ...state, terminal: 'error', error: frame.error };
  }
  switch (frame.status) {
    case 'processing':
    case 'synthesizing':
      return state;
    case 'streaming':
      return { ...state, content: state.content + content };
    case 'new_message':
      return {
        ...state,
        content: state.content ? `${state.content}\n\n${content}` : content,
      };
    case 'partial':
      return { ...state, content: content || state.content };
    case 'complete':
    case 'success':
      return {
        ...state,
        content: content || state.content,
        terminal: 'success',
      };
    case 'error':
      return {
        ...state,
        terminal: 'error',
        error: frame.error || 'Chat stream failed',
      };
    case 'cancelled':
      return {
        ...state,
        terminal: 'cancelled',
        error: frame.message || 'Chat stream cancelled',
      };
    default:
      return content ? { ...state, content } : state;
  }
}

/**
 * 채팅 스트림의 전송 완료 상태를 기록합니다.
 *
 * @param state - 갱신할 채팅 스트림 상태
 * @returns 전송 완료로 표시된 채팅 스트림 상태
 * @throws 이미 전송 완료로 표시된 경우 오류를 발생시킵니다.
 */
export function applyChatTransportDone(state: ChatStreamState): ChatStreamState {
  if (state.transportDone) throw new Error('Duplicate [DONE]');
  return { ...state, transportDone: true };
}

/**
 * 채팅 스트림이 정상적으로 성공했는지 검증한다.
 *
 * @param state - 검증할 채팅 스트림 상태
 * @throws 스트림이 `[DONE]` 없이 종료되었거나 오류·취소 상태이거나 성공 프레임으로 종료되지 않은 경우
 */
export function assertChatStreamSucceeded(state: ChatStreamState): void {
  if (!state.transportDone) throw new Error('Chat stream ended before [DONE]');
  if (state.terminal === 'error') throw new Error(state.error || 'Chat stream failed');
  if (state.terminal === 'cancelled') throw new Error(state.error || 'Chat stream cancelled');
  if (state.terminal !== 'success') {
    throw new Error('[DONE] received before terminal success frame');
  }
}
