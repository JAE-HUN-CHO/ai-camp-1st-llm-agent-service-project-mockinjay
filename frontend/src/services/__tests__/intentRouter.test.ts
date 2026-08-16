import { afterEach, describe, expect, it, vi } from 'vitest';
import { callBackendAgentStream } from '../intentRouter';

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
    vi.stubGlobal('fetch', vi.fn(async () => streamResponse([
      'data: {"status":"stream',
      'ing","content":"hello ","agent_type":"research_paper"}\n\n',
      'data:{"status":"complete","content":"hello world","is_emergency":true}\n\n',
      'data:[DONE]\n\n',
    ])));
    const onChunk = vi.fn();

    const result = await callBackendAgentStream(
      'question',
      'research_paper',
      onChunk,
    );

    expect(result.isEmergency).toBe(true);
    expect(result.agents).toContain('research_paper');
    expect(onChunk).toHaveBeenLastCalledWith('hello world', true);
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
});
