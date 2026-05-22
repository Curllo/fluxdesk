<script setup lang="ts">
import { onMounted, onErrorCaptured, ref } from 'vue';
import { listen } from '@tauri-apps/api/event';
import AppShell from '@/components/AppShell.vue';
import ToolWorkspace from '@/components/ToolWorkspace.vue';
import AgentChat from '@/components/AgentChat.vue';
import { useTheme } from '@/composables/useTheme';
import { refreshConfig } from '@/composables/useApi';

const { init } = useTheme();
const fatalError = ref('');

onMounted(() => {
  init();
  // Auto-refresh API config when sidecar restarts
  listen('ai-service-ready', async () => {
    await refreshConfig();
  }).catch(() => {});
});

onErrorCaptured((err: Error) => {
  console.error('[FluxDesk] Unhandled error:', err);
  fatalError.value = err.message || '未知错误';
  return false; // prevent propagation
});

function reloadApp() {
  window.location.reload();
}
</script>

<template>
  <div v-if="fatalError" class="h-screen w-screen flex flex-col items-center justify-center bg-bg-primary text-text-primary p-8">
    <div class="w-16 h-16 mb-6 rounded-2xl bg-error/10 flex items-center justify-center">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-error/60">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
    </div>
    <p class="text-lg font-semibold mb-2">应用发生错误</p>
    <p class="text-sm text-text-secondary/60 mb-6 max-w-md text-center">{{ fatalError }}</p>
    <button class="px-5 py-2 rounded-xl bg-dai text-white text-sm font-medium hover:bg-dai-hover transition-colors" @click="reloadApp">
      重新加载
    </button>
  </div>
  <AppShell v-else>
    <template #workspace>
      <ToolWorkspace />
    </template>
    <template #sidebar>
      <AgentChat />
    </template>
  </AppShell>
</template>
