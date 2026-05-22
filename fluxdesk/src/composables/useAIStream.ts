import { ref } from 'vue';
import type { SSEEvent } from '@/types';

export function useAIStream() {
  const abortController = ref<AbortController | null>(null);

  async function* streamChat(
    endpoint: string,
    token: string,
    body: Record<string, any>
  ): AsyncGenerator<SSEEvent, void, unknown> {
    abortController.value?.abort();
    abortController.value = new AbortController();

    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
      signal: abortController.value.signal,
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.message || `HTTP ${resp.status}`);
    }

    const reader = resp.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          const event = parseSSEBlock(block);
          if (event) yield event;
        }
      }

      if (buffer.trim()) {
        const event = parseSSEBlock(buffer);
        if (event) yield event;
      }
    } finally {
      reader.releaseLock();
    }
  }

  function abort() {
    abortController.value?.abort();
    abortController.value = null;
  }

  return { streamChat, abort };
}

function parseSSEBlock(block: string): SSEEvent | null {
  const lines = block.trim().split('\n');
  let event = '';
  let data = '';

  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      const chunk = line.slice(5).trim();
      data = data ? data + '\n' + chunk : chunk;
    }
  }

  if (!event || !data) return null;

  try {
    return { event: event as SSEEvent['event'], data: JSON.parse(data) };
  } catch {
    return { event: event as SSEEvent['event'], data: { raw: data } };
  }
}
