<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { invoke } from '@tauri-apps/api/core';
import { useChatStore } from '@/stores/chatStore';
import { useAIStream } from '@/composables/useAIStream';
import { useToolCommands } from '@/composables/useToolCommands';
import { useToolRegistry } from '@/stores/toolRegistry';
import { useTemplateStore } from '@/stores/templateStore';
import GlobalSettings from '@/components/GlobalSettings.vue';
import type { ServiceConfig, ConfirmAction, ChatMessage } from '@/types';

const chatStore = useChatStore();
const { streamChat, abort } = useAIStream();
const { executeCommand, getWorkspaceContext } = useToolCommands();
const registry = useToolRegistry();
const templateStore = useTemplateStore();

const input = ref('');
const inputRef = ref<HTMLTextAreaElement | null>(null);
const messagesRef = ref<HTMLDivElement | null>(null);
const globalSettingsRef = ref<InstanceType<typeof GlobalSettings> | null>(null);
const serviceConfig = ref<ServiceConfig | null>(null);
const currentToolName = ref('');
const currentToolCallId = ref('');
const DEV_MODE_KEY = 'fluxdesk-dev-mode';
const debugLogs = ref<string[]>([]);
const devMode = ref(localStorage.getItem(DEV_MODE_KEY) === '1');

// Pending confirmation for AI destructive actions
const pendingConfirm = ref<ConfirmAction | null>(null);

function addDebug(msg: string) {
  const ts = new Date().toLocaleTimeString();
  debugLogs.value.push(`[${ts}] ${msg}`);
  if (debugLogs.value.length > 15) debugLogs.value.shift();
  console.log('[AgentChat]', msg);
}

function onDevModeChange() {
  devMode.value = localStorage.getItem(DEV_MODE_KEY) === '1';
}

function onOpenSettings() {
  globalSettingsRef.value?.open('agent');
}

onMounted(async () => {
  registry.init();
  templateStore.init();
  chatStore.init();
  window.addEventListener('fluxdesk:devmode', onDevModeChange);
  window.addEventListener('fluxdesk:open-settings', onOpenSettings);

  getServiceConfig().then(cfg => {
    serviceConfig.value = cfg;
  });

  if (!chatStore.hasMessages) {
    setTimeout(() => {
      chatStore.addMessage({
        role: 'assistant',
        content: '你好！我是你的桌面助手。试试对我说：\n\n• "创建一个25分钟的番茄钟"\n• "添加待办：买水果"\n• "打开日历"\n• "创建一个习惯追踪器"',
      });
    }, 400);
  }

  nextTick(() => inputRef.value?.focus());
  document.addEventListener('keydown', onGlobalKeydown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', onGlobalKeydown);
  window.removeEventListener('fluxdesk:devmode', onDevModeChange);
  window.removeEventListener('fluxdesk:open-settings', onOpenSettings);
  if (chatStore.isGenerating) {
    abort();
    chatStore.setGenerating(false);
  }
});

function onGlobalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    inputRef.value?.focus();
  }
}

watch(() => chatStore.isGenerating, (val) => {
  if (!val) nextTick(() => inputRef.value?.focus());
});

watch(
  () => chatStore.messages,
  async () => {
    await nextTick();
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight;
    }
  },
  { deep: true }
);

async function getServiceConfig(): Promise<ServiceConfig | null> {
  for (let i = 0; i < 20; i++) {
    try {
      const cfg = await invoke<ServiceConfig>('get_ai_service_config');
      addDebug(`config OK: port=${cfg.port}`);
      return cfg;
    } catch (e: any) {
      addDebug(`config retry ${i+1}/20: ${e.message || e}`);
      if (i < 19) await new Promise(r => setTimeout(r, 800));
    }
  }
  addDebug('config FAILED after 20 retries');
  return null;
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
  if (e.key === 'Escape' && chatStore.isGenerating) {
    abort();
    chatStore.setGenerating(false);
  }
}

function confirmPendingAction(confirm: boolean) {
  if (!pendingConfirm.value) return;
  const action = pendingConfirm.value;
  pendingConfirm.value = null;

  if (confirm) {
    executeCommand(action.action, action.params).then(result => {
      addDebug(`${action.action} confirmed: ${result.message}`);
      // Add tool result to history so AI knows what happened
      chatStore.addToolResult({
        content: result.success ? result.message : `Error: ${result.error || result.message}`,
        toolResults: [{
          name: action.action,
          toolCallId: action.toolCallId,
          success: result.success,
          result: result.message,
          error: result.error,
        }],
      });
    });
  } else {
    addDebug(`${action.action} cancelled by user`);
    chatStore.addToolResult({
      content: `用户取消了 ${action.action} 操作`,
      toolResults: [{
        name: action.action,
        toolCallId: action.toolCallId,
        success: false,
        result: 'cancelled by user',
        error: 'user cancelled',
      }],
    });
  }
}

function tryFixTruncatedJSON(raw: string): Record<string, any> | null {
  let fixed = raw.trim().replace(/[\x00-\x1F]/g, '');
  const dqCount = (fixed.match(/(?<!\\)"/g) || []).length;
  if (dqCount % 2 !== 0) fixed += '"';
  const opens = (fixed.match(/[{[]/g) || []).length;
  const closes = (fixed.match(/[}\]]/g) || []).length;
  fixed += '}'.repeat(Math.max(0, opens - closes));
  try { return JSON.parse(fixed); } catch { return null; }
}

function buildHistoryForAI(): Array<{role: string; content: string; tool_call_id?: string; tool_calls?: any[]}> {
  const history: Array<{role: string; content: string; tool_call_id?: string; tool_calls?: any[]}> = [];
  for (const msg of chatStore.messages) {
    if (msg.role === 'assistant' && msg.toolCalls && msg.toolCalls.length > 0) {
      history.push({
        role: 'assistant',
        content: msg.content,
        tool_calls: msg.toolCalls.map((tc, idx) => ({
          id: tc.id || `call_${idx}`,
          type: 'function',
          function: { name: tc.name, arguments: tc.arguments },
        })),
      });
    } else if (msg.role === 'tool') {
      history.push({
        role: 'tool',
        content: msg.content,
        tool_call_id: msg.toolResults?.[0]?.toolCallId || 'tool',
      });
    } else if (msg.role === 'user' || msg.role === 'assistant') {
      history.push({ role: msg.role, content: msg.content });
    }
  }
  // Keep last 20 messages to stay within token limits
  return history.slice(-20);
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text || chatStore.isGenerating) return;

  if (pendingConfirm.value) {
    confirmPendingAction(false);
  }

  chatStore.addMessage({ role: 'user', content: text });
  input.value = '';
  chatStore.setGenerating(true);

  const streamId = chatStore.addMessage({ role: 'assistant', content: '' });
  chatStore.setCurrentStreamId(streamId);

  if (!serviceConfig.value) {
    addDebug('Getting service config...');
    serviceConfig.value = await getServiceConfig();
  }

  if (!serviceConfig.value) {
    chatStore.appendToMessage(streamId, 'AI 服务未启动，请检查设置。');
    chatStore.setGenerating(false);
    return;
  }

  const config = serviceConfig.value;
  const context = getWorkspaceContext();
  const history = buildHistoryForAI();
  addDebug(`Streaming to port ${config.port}, history=${history.length} msgs`);

  try {
    const gen = streamChat(
      `http://127.0.0.1:${config.port}/api/v1/chat/stream`,
      config.apiToken,
      { message: `[工作区上下文]\n${context}\n\n---\n用户: ${text}`, history }
    );

    for await (const event of gen) {
      switch (event.event) {
        case 'message':
          chatStore.appendToMessage(streamId, event.data.delta || '');
          break;

        case 'tool_call': {
          const toolName = event.data.name || '';
          const rawArgs = event.data.arguments || '{}';
          const toolCallId = crypto.randomUUID();
          currentToolName.value = toolName;
          currentToolCallId.value = toolCallId;

          // Save tool call to the assistant message
          chatStore.appendToolCall(streamId, {
            id: toolCallId,
            name: toolName,
            arguments: rawArgs,
          });

          if (toolName === 'install_template') {
            let params: Record<string, any> | null = null;
            let parseError: string = '';
            try {
              params = JSON.parse(rawArgs);
            } catch (e: any) {
              parseError = e.message;
              // Attempt truncation fix
              params = tryFixTruncatedJSON(rawArgs);
              if (!params) {
                const hint = rawArgs.length > 200 ? '（AI 输出过长被截断，已通知 AI 重试）' : '';
                chatStore.appendToMessage(streamId,
                  `\n⚠️ 模板安装参数解析失败: ${parseError}${hint}\n` +
                  `原始参数: ${rawArgs.slice(0, 300)}${rawArgs.length > 300 ? '...' : ''}\n`
                );
                // Tell AI about the failure so it can retry with simpler output
                chatStore.addToolResult({
                  content: `install_template JSON parse error: ${parseError}. The vue_code was likely too long and got truncated. Please regenerate with shorter code (under 5000 chars).`,
                  toolResults: [{ name: toolName, toolCallId, success: false, result: 'parse_error', error: parseError }],
                });
              }
            }
            if (params) {
              // Check if essential fields are missing after truncation fix
              if (!params.vue_code) {
                const hint = parseError 
                  ? '（JSON 被截断，缺少 vue_code。代码片段太长，请精简到 4000 字符以内，且 config_schema 用扁平格式如 {"key": value}）' 
                  : '';
                chatStore.appendToMessage(streamId,
                  `\n⚠️ 模板安装参数不完整${hint}\n` +
                  `原始参数: ${rawArgs.slice(0, 300)}${rawArgs.length > 300 ? '...' : ''}\n`
                );
                chatStore.addToolResult({
                  content: `install_template error: vue_code field missing due to truncation. Reduce vue_code length under 4000 chars, use flat config_schema format like {"habits": []} not {"type":"object","properties":...}.`,
                  toolResults: [{ name: toolName, toolCallId, success: false, result: 'parse_error', error: 'vue_code truncated' }],
                });
              } else {
                if (parseError) {
                  addDebug(`install_template: auto-fixed truncated JSON (${parseError})`);
                }
                pendingConfirm.value = {
                  id: crypto.randomUUID(),
                  action: 'install_template',
                  title: '安装新卡片模板',
                  message: `AI 想要安装「${params.name || '新模板'}」卡片模板${parseError ? '（已自动修复截断）' : ''}`,
                  params,
                  toolCallId,
                  createdAt: Date.now(),
                };
                chatStore.appendToMessage(streamId, `\n[等待确认: 安装「${params.name || '新模板'}」模板]\n`);
              }
            }
          } else if (toolName === 'delete_tool') {
            let delParams: Record<string, any> | null = null;
            try {
              delParams = JSON.parse(rawArgs);
            } catch (e: any) {
              delParams = tryFixTruncatedJSON(rawArgs);
            }
            if (delParams) {
              const tool = registry.getToolById(delParams.tool_id);
              pendingConfirm.value = {
                id: crypto.randomUUID(),
                action: 'delete_tool',
                title: '删除工具卡片',
                message: `AI 想要删除「${tool?.title || delParams.tool_id || '未知工具'}」`,
                params: delParams,
                toolCallId,
                createdAt: Date.now(),
              };
              chatStore.appendToMessage(streamId, `\n[等待确认: 删除「${tool?.title || delParams.tool_id || '未知工具'}」]\n`);
            } else {
              chatStore.appendToMessage(streamId,
                `\n⚠️ 删除参数解析失败\n` +
                `原始参数: ${rawArgs.slice(0, 300)}${rawArgs.length > 300 ? '...' : ''}\n` +
                `建议: 请明确指定要删除的工具名称。\n`
              );
              chatStore.addToolResult({
                content: `delete_tool JSON parse error`,
                toolResults: [{ name: toolName, toolCallId, success: false, result: 'parse_error', error: 'json parse failed' }],
              });
            }
          } else {
            chatStore.appendToMessage(streamId, `\n[正在执行: ${toolName}]\n`);
          }
          break;
        }

        case 'tool_result': {
          const toolName = event.data.name || currentToolName.value;
          const toolCallId = currentToolCallId.value || toolName;
          if ((toolName === 'install_template' || toolName === 'delete_tool') && pendingConfirm.value) {
            chatStore.appendToMessage(streamId, `✓ 操作已准备好，请在上方确认\n`);
          } else if (event.data.success) {
            try {
              const result = await executeCommand(toolName, event.data.params || {});
              if (result.success) {
                chatStore.appendToMessage(streamId, `✓ ${result.message}\n`);
              } else {
                chatStore.appendToMessage(streamId,
                  `✗ ${result.message}\n` +
                  (result.error ? `原因: ${result.error}\n` : '') +
                  `建议: 请检查参数是否正确，或尝试用不同方式描述需求。\n`
                );
              }
              // Record tool result in history
              chatStore.addToolResult({
                content: result.success ? result.message : `Error: ${result.error || result.message}`,
                toolResults: [{
                  name: toolName,
                  toolCallId,
                  success: result.success,
                  result: result.message,
                  error: result.error,
                }],
              });
            } catch (e: any) {
              chatStore.appendToMessage(streamId,
                `✗ 执行失败: ${e.message}\n建议: 请稍后重试或换个说法。\n`
              );
              chatStore.addToolResult({
                content: `Error: ${e.message}`,
                toolResults: [{ name: toolName, toolCallId, success: false, result: e.message, error: e.message }],
              });
            }
          } else {
            const errMsg = event.data.message || event.data.error || '未知错误';
            chatStore.appendToMessage(streamId,
              `✗ 失败: ${errMsg}\n建议: 请检查 AI 设置中的模型是否支持工具调用，或简化请求后重试。\n`
            );
            chatStore.addToolResult({
              content: `Error: ${errMsg}`,
              toolResults: [{ name: toolName, toolCallId, success: false, result: errMsg, error: errMsg }],
            });
          }
          break;
        }

        case 'error':
          chatStore.appendToMessage(streamId, `\n[错误: ${event.data.message}]\n建议: 请检查网络连接和 AI 服务配置。`);
          break;

        case 'done':
          break;
      }
    }
    addDebug('Stream completed');
  } catch (err: any) {
    if (err.name !== 'AbortError') {
      addDebug(`Stream ERROR: ${err.message}`);
      chatStore.appendToMessage(streamId, `\n[连接错误: ${err.message}]\n建议: 请检查 AI 服务是否正常运行。`);
    }
  } finally {
    chatStore.setGenerating(false);
  }
}
</script>

<template>
  <div class="flex flex-col h-full bg-gradient-to-b from-bg-primary to-bg-secondary/5">
    <!-- Sidebar header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-border/60 bg-gradient-to-r from-bg-primary to-bg-secondary/10">
      <div class="flex items-center gap-2.5">
        <span class="w-2 h-2 rounded-full shadow-sm bg-dai/60 shadow-dai/10" />
        <span class="text-sm font-semibold text-text-primary tracking-wide">AI 助手</span>
      </div>
      <div class="flex items-center gap-1">
        <button
          class="w-7 h-7 flex items-center justify-center text-text-secondary/40 hover:text-text-primary rounded-lg hover:bg-bg-secondary/80 transition-all"
          title="清除上下文"
          @click="chatStore.clearMessages()"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
            <path d="M10 11v6"/>
            <path d="M14 11v6"/>
            <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
          </svg>
        </button>
        <button
          class="w-7 h-7 flex items-center justify-center text-text-secondary/40 hover:text-text-primary rounded-lg hover:bg-bg-secondary/80 transition-all"
          title="设置"
          @click="globalSettingsRef?.open('agent')"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09A1.65 1.65 0 0 0 19.4 15a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Messages -->
    <div
      ref="messagesRef"
      class="flex-1 overflow-y-auto px-3 py-4 space-y-3"
    >
      <div
        v-for="msg in chatStore.messages"
        :key="msg.id"
        class="flex"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="max-w-[88%] px-3.5 py-2.5 text-sm leading-6 shadow-sm"
          :class="
            msg.role === 'user'
              ? 'bg-dai text-white rounded-[14px] rounded-br-[4px] shadow-dai/10'
              : 'bg-bg-secondary text-text-primary rounded-[14px] rounded-bl-[4px]'
          "
        >
          <pre class="whitespace-pre-wrap font-sans text-[13px] leading-[1.65]">{{ msg.content }}</pre>
        </div>
      </div>

      <!-- Pending confirmation card -->
      <div v-if="pendingConfirm" class="flex justify-start">
        <div class="max-w-[88%] px-3.5 py-3 bg-bg-secondary rounded-[14px] rounded-bl-[4px] border border-dai/20">
          <p class="text-sm font-medium text-text-primary mb-1">{{ pendingConfirm.title }}</p>
          <p class="text-xs text-text-secondary mb-3">{{ pendingConfirm.message }}</p>
          <div class="flex gap-2">
            <button
              class="px-3 py-1.5 text-xs bg-dai text-white rounded-[8px] hover:bg-dai-hover transition-colors"
              @click="confirmPendingAction(true)"
            >{{ pendingConfirm.action === 'delete_tool' ? '删除' : '安装' }}</button>
            <button
              class="px-3 py-1.5 text-xs bg-bg-primary text-text-secondary rounded-[8px] hover:bg-border transition-colors border border-border"
              @click="confirmPendingAction(false)"
            >取消</button>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-if="!chatStore.hasMessages && !pendingConfirm"
        class="flex flex-col items-center justify-center h-full text-text-secondary px-4"
      >
        <div
          class="w-12 h-12 mb-4 rounded-xl bg-gradient-to-br from-dai/10 to-dai/5
                 flex items-center justify-center border border-border/40"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-dai/50">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <p class="text-sm font-medium mb-2 text-text-primary/60">AI 助手</p>
        <p class="text-xs text-center leading-5 text-text-secondary/50">
          试试说：<br>
          "创建一个25分钟的番茄钟"<br>
          "添加待办：买水果"<br>
          "创建一个习惯追踪器"
        </p>
      </div>
    </div>

    <!-- Input -->
    <div class="px-3 py-3 border-t border-border/60 bg-gradient-to-t from-bg-primary to-transparent">
      <div class="relative">
        <textarea
          ref="inputRef"
          v-model="input"
          rows="1"
          class="w-full min-h-[44px] max-h-[100px] px-3.5 py-2.5 pr-12 text-sm text-text-primary bg-bg-secondary rounded-[12px] resize-none outline-none border border-border/40 focus:border-dai/50 focus:bg-bg-primary transition-all duration-200"
          placeholder="输入指令..."
          @keydown="handleKeydown"
        />
        <div class="absolute right-2 top-1/2 -translate-y-1/2">
          <div
            v-if="chatStore.isGenerating"
            class="w-7 h-7 flex items-center justify-center"
          >
            <div class="w-4 h-4 border-[2.5px] border-dai/30 border-t-dai rounded-full animate-spin" />
          </div>
          <button
            v-else
            class="w-7 h-7 flex items-center justify-center bg-dai text-white rounded-[8px] hover:bg-dai-hover active:scale-95 transition-all shadow-sm shadow-dai/10"
            @click="sendMessage"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Debug panel (developer mode only) -->
    <div v-if="devMode && debugLogs.length > 0" class="px-3 pb-2">
      <details class="text-[10px] font-mono">
        <summary class="text-text-secondary/50 cursor-pointer hover:text-text-secondary select-none">调试日志 ({{ debugLogs.length }})</summary>
        <div class="mt-1 bg-bg-secondary rounded-[6px] p-2 max-h-[80px] overflow-y-auto space-y-0.5">
          <div v-for="(log, i) in debugLogs" :key="i" class="text-text-secondary/60">{{ log }}</div>
        </div>
      </details>
    </div>

    <GlobalSettings ref="globalSettingsRef" />
  </div>
</template>
