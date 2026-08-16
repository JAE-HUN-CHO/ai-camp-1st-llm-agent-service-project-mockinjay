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

export function createChatStreamState(): ChatStreamState {
  return { content: '', terminal: 'open', transportDone: false };
}

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

export function applyChatTransportDone(state: ChatStreamState): ChatStreamState {
  if (state.transportDone) throw new Error('Duplicate [DONE]');
  return { ...state, transportDone: true };
}

export function assertChatStreamSucceeded(state: ChatStreamState): void {
  if (!state.transportDone) throw new Error('Chat stream ended before [DONE]');
  if (state.terminal === 'error') throw new Error(state.error || 'Chat stream failed');
  if (state.terminal === 'cancelled') throw new Error(state.error || 'Chat stream cancelled');
  if (state.terminal !== 'success') {
    throw new Error('[DONE] received before terminal success frame');
  }
}
