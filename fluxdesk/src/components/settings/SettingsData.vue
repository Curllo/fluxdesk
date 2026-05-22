<script setup lang="ts">
import { ref } from 'vue';
import { apiGet, apiPost } from '@/composables/useApi';
import { useToolRegistry } from '@/stores/toolRegistry';
import { useChatStore } from '@/stores/chatStore';

const fileInput = ref<HTMLInputElement | null>(null);
const registry = useToolRegistry();
const chatStore = useChatStore();
const exporting = ref(false);
const importing = ref(false);
const dataMsg = ref('');

async function exportData() {
  exporting.value = true;
  dataMsg.value = '';
  try {
    const res = await apiGet('/api/v1/data/export');
    const json = JSON.stringify(res.data || res, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fluxdesk-export-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    dataMsg.value = '导出成功';
  } catch (e: any) {
    dataMsg.value = '导出失败: ' + (e.message || e);
  } finally {
    exporting.value = false;
  }
}

function triggerImport() {
  fileInput.value?.click();
}

async function importData() {
  const file = fileInput.value?.files?.[0];
  if (!file) return;

  importing.value = true;
  dataMsg.value = '';
  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    const data = parsed.data || parsed;

    const res = await apiPost('/api/v1/data/import', { data });
    const stats = res.data?.stats || {};
    const parts = Object.entries(stats)
      .filter(([, v]) => (v as number) > 0)
      .map(([k, v]) => `${k}: ${v}`);
    dataMsg.value = `导入成功 (${parts.join(', ')})`;
  } catch (e: any) {
    dataMsg.value = '导入失败: ' + (e.message || e);
    console.error(e);
  } finally {
    importing.value = false;
    if (fileInput.value) fileInput.value.value = '';
  }
}

function clearWorkspace() {
  if (confirm('确定要清除所有工作区数据吗？此操作不可撤销。')) {
    registry.clearAll();
    dataMsg.value = '工作区数据已清除';
  }
}

function clearChatHistory() {
  if (confirm('确定要清除所有聊天记录吗？此操作不可撤销。')) {
    chatStore.clearMessages();
    dataMsg.value = '聊天记录已清除';
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="text-xs font-medium text-text-secondary uppercase tracking-wide">数据管理</div>

    <div class="flex gap-2">
      <button
        class="flex-1 px-4 py-2 text-sm bg-bg-secondary text-text-primary rounded-[8px] hover:bg-bg-secondary/80 transition-colors disabled:opacity-50"
        :disabled="exporting"
        @click="exportData"
      >
        {{ exporting ? '导出中...' : '导出数据' }}
      </button>
      <button
        class="flex-1 px-4 py-2 text-sm bg-bg-secondary text-text-primary rounded-[8px] hover:bg-bg-secondary/80 transition-colors disabled:opacity-50"
        :disabled="importing"
        @click="triggerImport"
      >
        {{ importing ? '导入中...' : '导入数据' }}
      </button>
    </div>

    <input
      ref="fileInput"
      type="file"
      accept=".json"
      class="hidden"
      @change="importData"
    />

    <div v-if="dataMsg" class="text-xs py-2 px-3 rounded-[6px]" :class="dataMsg.includes('成功') || dataMsg.includes('已') ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-500'">
      {{ dataMsg }}
    </div>

    <div class="pt-4 border-t border-border space-y-2">
      <button
        class="w-full px-4 py-2 text-sm bg-bg-secondary text-text-primary rounded-[8px] hover:bg-red-500/10 hover:text-error transition-colors"
        @click="clearWorkspace"
      >
        清除工作区数据
      </button>
      <button
        class="w-full px-4 py-2 text-sm bg-bg-secondary text-text-primary rounded-[8px] hover:bg-red-500/10 hover:text-error transition-colors"
        @click="clearChatHistory"
      >
        清除聊天记录
      </button>
    </div>
  </div>
</template>
