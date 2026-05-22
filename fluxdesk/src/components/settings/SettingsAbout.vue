<script setup lang="ts">
import { ref } from 'vue';

const checking = ref(false);
const updateMsg = ref('');

async function checkUpdate() {
  checking.value = true;
  updateMsg.value = '';
  // Simulated update check — replace with real Tauri updater API when configured
  await new Promise(r => setTimeout(r, 1000));
  updateMsg.value = '当前已是最新版本 v1.1.0';
  checking.value = false;
}
</script>

<template>
  <div class="flex flex-col items-center justify-center py-8 space-y-4">
    <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-dai/20 to-dai/5 flex items-center justify-center border border-border/40 shadow-sm">
      <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-dai">
        <rect x="3" y="3" width="18" height="18" rx="4" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="9" y1="21" x2="9" y2="9" />
      </svg>
    </div>
    <div class="text-center">
      <h3 class="text-lg font-semibold text-text-primary">FluxDesk</h3>
      <p class="text-sm text-text-secondary">v1.1.0</p>
    </div>

    <div class="flex flex-col items-center gap-3 pt-2">
      <button
        class="px-4 py-2 text-sm bg-dai text-white rounded-[8px] hover:bg-dai-hover transition-colors disabled:opacity-50"
        :disabled="checking"
        @click="checkUpdate"
      >
        {{ checking ? '检查中...' : '检查更新' }}
      </button>
      <div v-if="updateMsg" class="text-xs text-green-600">{{ updateMsg }}</div>
    </div>

    <div class="flex flex-col items-center gap-2 text-sm pt-2">
      <a
        href="https://github.com/user/fluxdesk"
        target="_blank"
        rel="noopener noreferrer"
        class="text-text-secondary hover:text-dai transition-colors flex items-center gap-1.5"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
        </svg>
        GitHub
      </a>
      <a
        href="#"
        class="text-text-secondary hover:text-dai transition-colors text-xs"
      >
        MIT License
      </a>
    </div>
  </div>
</template>
