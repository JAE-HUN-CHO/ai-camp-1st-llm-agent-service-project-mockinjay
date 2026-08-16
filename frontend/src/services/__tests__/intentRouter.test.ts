import { afterEach, describe, expect, it, vi } from 'vitest';
import { callBackendAgentStream, routeQueryStream } from '../intentRouter';
import contractFixture from '../__fixtures__/chat-v1-contract.json';
import {
  applyChatStreamFrame,
  applyChatTransportDone,
  assertChatStreamSucceeded,
  createChatStreamState,
  type ChatStreamFrame,
} from '../chatStreamContract';

function streamResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  return new Response(new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  }), { status: 200 });
}

describe('callBackendAgentStream', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('buffers split SSE JSON and preserves emergency terminal metadata', async () => {
    const fetchMock = vi.fn(async () => streamResponse([
      'data: {"status":"stream',
      'ing","content":"hello ","agent_type":"research_paper"}\n\n',
      'data:{"status":"complete","content":"hello world","is_emergency":true}\n\n',
      'data:[DONE]\n\n',
    ]));
    vi.stubGlobal('fetch', fetchMock);
    const onChunk = vi.fn();

    const result = await callBackendAgentStream(
      'question',
      'research_paper',
      onChunk,
      undefined,
      { clientMessageId: 'fixture-client-message-id' },
    );

    expect(result.isEmergency).toBe(true);
    expect(result.agents).toContain('research_paper');
    expect(onChunk).toHaveBeenLastCalledWith('hello world', true);
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(JSON.parse(String(request.body))).toMatchObject({
      client_message_id: 'fixture-client-message-id',
    });
  });

  it('propagates a complete SSE error frame', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => streamResponse([
      'data:{"status":"error","error":"local failure"}\n\n',
    ])));
    const onError = vi.fn();

    await expect(callBackendAgentStream(
      'question',
      'research_paper',
      vi.fn(),
      onError,
    )).rejects.toThrow('local failure');
    expect(onError).toHaveBeenCalledTimes(1);
  });

  it('rejects EOF without the [DONE] transport terminal', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => streamResponse([
      'data: {"status":"streaming","content":"partial"}\n\n',
    ])));
    const onChunk = vi.fn();
    const onError = vi.fn();

    await expect(callBackendAgentStream(
      'question',
      'research_paper',
      onChunk,
      onError,
    )).rejects.toThrow('before [DONE]');
    expect(onChunk).not.toHaveBeenCalledWith('partial', true);
    expect(onError).toHaveBeenCalledTimes(1);
  });

  it('does not promote error followed by [DONE] to success', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => streamResponse([
      'data: {"status":"streaming","content":"partial"}\n\n',
      'data: {"status":"error","error":"local failure"}\n\n',
      'data: [DONE]\n\n',
    ])));
    const onChunk = vi.fn();

    await expect(callBackendAgentStream(
      'question',
      'research_paper',
      onChunk,
    )).rejects.toThrow('local failure');
    expect(onChunk).not.toHaveBeenCalledWith(expect.anything(), true);
  });

  it('does not convert a terminal backend error into a successful fallback response', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => streamResponse([
      'data: {"status":"error","error":"local failure"}\n\n',
      'data: [DONE]\n\n',
    ])));

    await expect(routeQueryStream('question', vi.fn())).rejects.toThrow('local failure');
  });
});

describe('frozen chat v1 fixture', () => {
  it.each(contractFixture.scenarios)(
    '$name preserves terminal and content semantics',
    (scenario) => {
      let state = createChatStreamState();
      let failure: Error | undefined;
      try {
        for (const frame of scenario.frames) {
          state = frame === '[DONE]'
            ? applyChatTransportDone(state)
            : applyChatStreamFrame(state, frame as ChatStreamFrame);
        }
        assertChatStreamSucceeded(state);
      } catch (error) {
        failure = error as Error;
      }

      expect(state.content).toBe(scenario.expected_content);
      if (scenario.expected_outcome === 'success') {
        expect(failure).toBeUndefined();
        expect(state.terminal).toBe('success');
      } else {
        expect(failure).toBeInstanceOf(Error);
        if (scenario.expected_outcome === 'error') expect(state.terminal).toBe('error');
        if (scenario.expected_outcome === 'cancelled') expect(state.terminal).toBe('cancelled');
      }
    },
  );
});
