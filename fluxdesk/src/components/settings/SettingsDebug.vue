<script setup lang="ts">
import { ref } from 'vue';
import { useGlobalSettingsStore } from '@/stores/globalSettingsStore';

const store = useGlobalSettingsStore();
const debug = store.state.debug;

const LOG_LEVELS = [
  { value: 'verbose', label: 'Verbose' },
  { value: 'debug', label: 'Debug' },
  { value: 'info', label: 'Info' },
  { value: 'warn', label: 'Warn' },
  { value: 'error', label: 'Error' },
];

const actionMsg = ref('');

async function restartSidecar() {
  actionMsg.value = '';
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('restart_ai_service');
    actionMsg.value = 'Sidecar 已重启';
  } catch (e: any) {
    actionMsg.value = '重启失败: ' + (e.message || e);
  }
}

function clearCache() {
  actionMsg.value = '';
  try {
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('fluxdesk-')) {
        keysToRemove.push(key);
      }
    }
    for (const key of keysToRemove) {
      localStorage.removeItem(key);
    }
    actionMsg.value = `已清除 ${keysToRemove.length} 项本地缓存`;
  } catch (e: any) {
    actionMsg.value = '清除失败: ' + (e.message || e);
  }
}
</script>

<template>
  <div class="space-y-5">
    <div class="text-xs font-medium text-text-secondary uppercase tracking-wide">调试</div>

    <!-- 日志级别 -->
    <div>
      <label class="block text-xs text-text-secondary mb-1.5">日志级别</label>
      <select
        v-model="debug.logLevel"
        class="w-full px-3 py-2 text-sm bg-bg-secondary rounded-[8px] outline-none border border-border/40 focus:border-dai/50 focus:bg-bg-primary text-text-primary transition-all"
      >
        <option v-for="lvl in LOG_LEVELS" :key="lvl.value" :value="lvl.value">{{ lvl.label }}</option>
      </select>
    </div>

    <!-- 显示 FPS -->
    <div class="flex items-center justify-between text-sm">
      <div>
        <div class="text-text-primary">显示 FPS 计数器</div>
        <div class="text-[11px] text-text-secondary/60 mt-0.5">在界面角落显示帧率</div>
      </div>
      <button
        class="relative w-9 h-5 rounded-full transition-colors duration-200 flex-shrink-0"
        :class="debug.showFps ? 'bg-dai' : 'bg-border'"
        @click="debug.showFps = !debug.showFps"
      >
        <span
          class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all duration-200"
          :style="{ transform: debug.showFps ? 'translateX(16px)' : 'translateX(0)' }"
        />
      </button>
    </div>

    <!-- Actions -->
    <div class="space-y-2 pt-2">
      <button
        class="w-full px-4 py-2 text-sm bg-bg-secondary text-text-primary rounded-[8px] hover:bg-bg-secondary/80 transition-colors"
        @click="restartSidecar"
      >
        重启 AI Sidecar
      </button>
      <button
        class="w-full px-4 py-2 text-sm bg-bg-secondary text-text-primary rounded-[8px] hover:bg-red-500/10 hover:text-error transition-colors"
        @click="clearCache"
      >
        清除本地缓存
      </button>
    </div>

    <div v-if="actionMsg" class="text-xs py-2 px-3 rounded-[6px]" :class="actionMsg.includes('失败') ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-600'">
      {{ actionMsg }}
    </div>
  </div>
</template>
