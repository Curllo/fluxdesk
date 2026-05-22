import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { ChatMessage, ToolCallInfo, ToolResultInfo } from '@/types';

const STORAGE_KEY = 'fluxdesk-chat-history-v2';
const OLD_STORAGE_KEY = 'fluxdesk-chat-history';

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([]);
  const isGenerating = ref(false);
  const currentStreamId = ref<string | null>(null);
  const _hydrated = ref(false);
  let _saveTimer: ReturnType<typeof setTimeout> | null = null;

  const hasMessages = computed(() => messages.value.length > 0);

  function init() {
    if (_hydrated.value) return;
    try {
      // Try new format first
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          messages.value = parsed;
          _hydrated.value = true;
          return;
        }
      }
      // Migrate from old format
      const oldSaved = localStorage.getItem(OLD_STORAGE_KEY);
      if (oldSaved) {
        const parsed = JSON.parse(oldSaved);
        if (Array.isArray(parsed)) {
          messages.value = parsed.map((m: any) => ({
            ...m,
            toolCalls: undefined,
            toolResults: undefined,
          }));
          persist();
          localStorage.removeItem(OLD_STORAGE_KEY);
        }
      }
    } catch { /* ignore */ }
    _hydrated.value = true;
  }

  function persist() {
    if (!_hydrated.value) return;
    if (_saveTimer) clearTimeout(_saveTimer);
    _saveTimer = setTimeout(() => {
      try {
        const toSave = messages.value.length > 100
          ? messages.value.slice(-100)
          : messages.value;
        localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
      } catch { /* storage full */ }
    }, 500);
  }

  function addMessage(msg: Omit<ChatMessage, 'id' | 'createdAt'>): string {
    const message: ChatMessage = {
      ...msg,
      id: `msg_${crypto.randomUUID()}`,
      createdAt: new Date().toISOString(),
    };
    messages.value.push(message);
    persist();
    return message.id;
  }

  function appendToMessage(id: string, delta: string) {
    const msg = messages.value.find((m) => m.id === id);
    if (msg) {
      msg.content += delta;
    }
  }

  function appendToolCall(id: string, toolCall: ToolCallInfo) {
    const msg = messages.value.find((m) => m.id === id);
    if (msg) {
      if (!msg.toolCalls) msg.toolCalls = [];
      msg.toolCalls.push(toolCall);
    }
  }

  function addToolResult(toolResult: { content: string; toolResults: ToolResultInfo[] }) {
    const message: ChatMessage = {
      role: 'tool',
      content: toolResult.content,
      toolResults: toolResult.toolResults,
      id: `msg_${crypto.randomUUID()}`,
      createdAt: new Date().toISOString(),
    };
    messages.value.push(message);
    persist();
    return message.id;
  }

  function setGenerating(val: boolean) {
    isGenerating.value = val;
    if (!val) {
      currentStreamId.value = null;
      persist();
    }
  }

  function setCurrentStreamId(id: string | null) {
    currentStreamId.value = id;
  }

  function clearMessages() {
    messages.value = [];
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(OLD_STORAGE_KEY);
  }

  return {
    messages,
    isGenerating,
    currentStreamId,
    hasMessages,
    init,
    addMessage,
    appendToMessage,
    appendToolCall,
    addToolResult,
    setGenerating,
    setCurrentStreamId,
    clearMessages,
  };
});
