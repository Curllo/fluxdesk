<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { apiGet, apiPost } from '@/composables/useApi';

interface LLMConfig {
  provider: string;
  api_base: string;
  model: string;
  mock_mode: boolean;
}

const API_FORMATS = [
  { value: 'openai', label: 'OpenAI', base: 'https://api.openai.com/v1' },
  { value: 'anthropic', label: 'Anthropic', base: 'https://api.anthropic.com' },
  { value: 'deepseek', label: 'DeepSeek', base: 'https://api.deepseek.com' },
  { value: 'gemini', label: 'Google Gemini', base: 'https://generativelanguage.googleapis.com' },
  { value: 'ollama', label: 'Ollama', base: 'http://localhost:11434/v1' },
  { value: 'custom', label: '自定义', base: '' },
];

const emit = defineEmits<{
  'config-saved': [];
}>();

const config = ref<LLMConfig>({ provider: 'openai', api_base: 'https://api.openai.com/v1', model: 'gpt-4o-mini', mock_mode: true });
const apiKey = ref('');
const verifying = ref(false);
const verifyResult = ref('');
const saveSuccess = ref(false);
const saving = ref(false);
const scanning = ref(false);
const scanResult = ref<string[]>([]);
const customModel = ref('');
const DEV_MODE_KEY = 'fluxdesk-dev-mode';
const devMode = ref(localStorage.getItem(DEV_MODE_KEY) === '1');

function toggleDevMode() {
  devMode.value = !devMode.value;
  localStorage.setItem(DEV_MODE_KEY, devMode.value ? '1' : '0');
  window.dispatchEvent(new CustomEvent('fluxdesk:devmode'));
  if (!devMode.value) {
    debugInfo.value = '';
    debugLogs.value = [];
  }
}

// ── Debug state ────────────────────────────────────────────────────────
const debugInfo = ref('');
const debugLogs = ref<string[]>([]);

function addDebugLog(msg: string) {
  const ts = new Date().toLocaleTimeString();
  debugLogs.value.push(`[${ts}] ${msg}`);
  if (debugLogs.value.length > 20) debugLogs.value.shift();
}

async function checkSidecarConnection() {
  addDebugLog('Checking sidecar connection...');
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    const cfg = await invoke<{port: number, apiToken: string}>('get_ai_service_config');
    debugInfo.value = `Connected: port=${cfg.port}`;
    addDebugLog(`Sidecar OK: port=${cfg.port}`);

    const res = await apiGet('/api/v1/settings/llm');
    addDebugLog(`GET settings: ${JSON.stringify(res.data)}`);
  } catch (e: any) {
    debugInfo.value = `Error: ${e.message}`;
    addDebugLog(`Error: ${e.message}`);
  }
}

onMounted(async () => {
  for (let i = 0; i < 30; i++) {
    try {
      const res = await apiGet('/api/v1/settings/llm');
      if (res.data) {
        config.value = res.data;
        if (res.data.model) customModel.value = res.data.model;
        addDebugLog(`Loaded config: mock_mode=${res.data.mock_mode} model=${res.data.model}`);
        break;
      }
    } catch (e: any) {
      addDebugLog(`Load config retry ${i+1}/30: ${e.message || e}`);
      if (i < 29) await new Promise(r => setTimeout(r, 1000));
    }
  }
});

function onFormatChange(format: string) {
  const found = API_FORMATS.find(f => f.value === format);
  if (found && found.base) {
    config.value.api_base = found.base;
  }
  config.value.model = '';
  customModel.value = '';
  scanResult.value = [];
}

async function scanModels() {
  scanning.value = true;
  scanResult.value = [];
  addDebugLog(`scan: provider=${config.value.provider} api_base=${config.value.api_base} hasKey=${!!apiKey.value}`);
  try {
    const res = await apiPost('/api/v1/settings/llm/scan', {
      provider: config.value.provider,
      api_base: config.value.api_base,
      api_key: apiKey.value || undefined,
    });
    addDebugLog(`scan response: ${JSON.stringify(res)}`);
    if (Array.isArray(res.data)) {
      scanResult.value = res.data;
      if (res.data.length > 0 && !config.value.model) {
        config.value.model = res.data[0];
      }
    }
  } catch (e: any) {
    addDebugLog(`scan ERROR: ${e.message}`);
    verifyResult.value = '扫描失败: ' + e.message;
  } finally {
    scanning.value = false;
  }
}

async function saveConfig() {
  saving.value = true;
  verifyResult.value = '';
  saveSuccess.value = false;
  addDebugLog(`save: model=${config.value.model || customModel.value}`);
  try {
    const res = await apiPost('/api/v1/settings/llm', {
      provider: config.value.provider,
      api_base: config.value.api_base,
      model: config.value.model || customModel.value,
      api_key: apiKey.value || undefined,
    });
    addDebugLog(`save response: ${JSON.stringify(res)}`);
    if (res.data) {
      config.value = res.data;
      saveSuccess.value = true;
      if (res.data.model) customModel.value = res.data.model;
      emit('config-saved');
    }
  } catch (e: any) {
    addDebugLog(`save ERROR: ${e.message}`);
    verifyResult.value = '保存失败: ' + e.message;
  } finally {
    saving.value = false;
  }
}

async function verifyConfig() {
  verifying.value = true;
  verifyResult.value = '';
  addDebugLog(`verify: model=${config.value.model || customModel.value} hasKey=${!!apiKey.value}`);
  try {
    const res = await apiPost('/api/v1/settings/llm/verify', {
      api_base: config.value.api_base,
      model: config.value.model || customModel.value,
      api_key: apiKey.value || undefined,
    });
    addDebugLog(`verify response: ${JSON.stringify(res)}`);
    if (res.data?.ok) {
      verifyResult.value = `验证成功！模型: ${res.data.model}`;
    } else {
      verifyResult.value = '验证失败: ' + (res.message || '未知错误');
    }
  } catch (e: any) {
    addDebugLog(`verify ERROR: ${e.message}`);
    verifyResult.value = '验证失败: ' + e.message;
  } finally {
    verifying.value = false;
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="text-xs font-medium text-text-secondary uppercase tracking-wide">AI 服务</div>

    <!-- API 格式 -->
    <div>
      <label class="block text-xs text-text-secondary mb-1.5">接口格式</label>
      <select
        v-model="config.provider"
        class="w-full px-3 py-2 text-sm bg-bg-secondary rounded-[8px] outline-none border border-border/40 focus:border-dai/50 focus:bg-bg-primary text-text-primary transition-all"
        @change="onFormatChange(config.provider)"
      >
        <option v-for="fmt in API_FORMATS" :key="fmt.value" :value="fmt.value">{{ fmt.label }}</option>
      </select>
    </div>

    <!-- API 地址 -->
    <div>
      <label class="block text-xs text-text-secondary mb-1.5">API 端点地址</label>
      <input
        v-model="config.api_base"
        class="w-full px-3 py-2 text-sm bg-bg-secondary rounded-[8px] outline-none border border-border/40 focus:border-dai/50 focus:bg-bg-primary text-text-primary transition-all font-mono text-[12px]"
        placeholder="https://api.openai.com/v1"
      />
    </div>

    <!-- API Key -->
    <div>
      <label class="block text-xs text-text-secondary mb-1.5">API Key</label>
      <input
        v-model="apiKey"
        type="password"
        class="w-full px-3 py-2 text-sm bg-bg-secondary rounded-[8px] outline-none border border-border/40 focus:border-dai/50 focus:bg-bg-primary text-text-primary transition-all"
        placeholder="sk-..."
      />
      <div class="mt-1.5 text-[11px]">
        <span v-if="!config.mock_mode" class="text-green-600">已配置 API Key — 留空则保留现有 Key</span>
        <span v-else class="text-text-secondary/60">未配置</span>
      </div>
    </div>

    <!-- Model: scan or custom -->
    <div>
      <label class="block text-xs text-text-secondary mb-1.5">模型</label>
      <div class="flex gap-2">
        <div class="flex-1 relative">
          <input
            v-if="scanResult.length === 0"
            v-model="customModel"
            class="w-full px-3 py-2 text-sm bg-bg-secondary rounded-[8px] outline-none border border-border/40 focus:border-dai/50 focus:bg-bg-primary text-text-primary transition-all"
            placeholder="gpt-4o-mini"
          />
          <select
            v-else
            v-model="config.model"
            class="w-full px-3 py-2 text-sm bg-bg-secondary rounded-[8px] outline-none border border-border/40 focus:border-dai/50 focus:bg-bg-primary text-text-primary transition-all"
          >
            <option value="" disabled>选择模型...</option>
            <option v-for="m in scanResult" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
        <button
          class="px-3 py-2 text-xs bg-bg-secondary hover:bg-border text-text-secondary hover:text-text-primary rounded-[8px] transition-all flex-shrink-0 disabled:opacity-40"
          :disabled="scanning"
          @click="scanModels"
          title="扫描可用模型"
        >
          <svg v-if="scanning" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="animate-spin"><circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="32" stroke-linecap="round"/></svg>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </button>
      </div>
      <div v-if="scanResult.length > 0" class="mt-1 text-[11px] text-dai/70">
        扫描到 {{ scanResult.length }} 个模型
      </div>
    </div>

    <!-- Result messages -->
    <div
      v-if="saveSuccess"
      class="text-xs py-2 px-3 rounded-[6px] bg-green-500/10 text-green-600 flex items-center gap-1.5"
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
      保存成功 — 下次启动自动加载
    </div>
    <div
      v-if="verifyResult"
      class="text-xs py-2 px-3 rounded-[6px]"
      :class="verifyResult.includes('成功') ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-500'"
    >
      {{ verifyResult }}
    </div>

    <!-- Buttons -->
    <div class="flex gap-2 pt-1">
      <button
        class="flex-1 px-4 py-2 text-sm bg-dai text-white rounded-[8px] hover:bg-dai-hover transition-colors disabled:opacity-50"
        :disabled="saving"
        @click="saveConfig"
      >
        {{ saving ? '保存中...' : '保存' }}
      </button>
      <button
        class="px-4 py-2 text-sm bg-bg-secondary text-text-primary rounded-[8px] hover:bg-bg-secondary/80 transition-colors disabled:opacity-40 flex items-center gap-1.5"
        :disabled="verifying || !apiKey && !config.model"
        @click="verifyConfig"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
        {{ verifying ? '测试中...' : '测试' }}
      </button>
    </div>

    <!-- Developer Mode toggle -->
    <div class="pt-4 border-t border-border">
      <div class="flex items-center justify-between text-sm">
        <span class="text-text-primary">开发者模式</span>
        <button
          class="relative w-9 h-5 rounded-full transition-colors duration-200"
          :class="devMode ? 'bg-dai' : 'bg-border'"
          @click="toggleDevMode"
        >
          <span
            class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all duration-200"
            :style="{ transform: devMode ? 'translateX(16px)' : 'translateX(0)' }"
          />
        </button>
      </div>
    </div>

    <!-- Debug Section (developer mode only) -->
    <div v-if="devMode" class="pt-4 border-t border-border space-y-3">
      <div class="text-xs font-medium text-text-secondary uppercase tracking-wide flex items-center justify-between">
        调试
        <button
          class="px-2 py-1 text-[10px] bg-bg-secondary hover:bg-border rounded text-text-secondary hover:text-text-primary transition-colors"
          @click="checkSidecarConnection"
        >
          检测连接
        </button>
      </div>
      <div v-if="debugInfo" class="text-xs py-2 px-3 rounded-[6px] font-mono"
        :class="debugInfo.startsWith('Connected') ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-500'">
        {{ debugInfo }}
      </div>
      <div v-if="debugLogs.length > 0" class="text-[11px] font-mono bg-bg-secondary rounded-[6px] p-2 max-h-[120px] overflow-y-auto space-y-0.5">
        <div v-for="(log, i) in debugLogs" :key="i" class="text-text-secondary/80">{{ log }}</div>
      </div>
    </div>
  </div>
</template>
