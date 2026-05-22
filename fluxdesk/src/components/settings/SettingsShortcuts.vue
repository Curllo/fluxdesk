<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { invoke } from '@tauri-apps/api/core';

const currentShortcut = ref('Ctrl+K');
const capturing = ref(false);
const capturedKeys = ref<string[]>([]);
const shortcutSaved = ref(false);

function shortcutDisplay(key: string) {
  return key
    .replace(/Ctrl/g, '⌃')
    .replace(/Cmd/g, '⌘')
    .replace(/Alt/g, '⌥')
    .replace(/Shift/g, '⇧')
    .replace(/Super/g, '⌘')
    .replace(/Meta/g, '◆')
    .replace(/\+/g, ' + ');
}

function formatShortcut(modifiers: string[], key: string): string {
  const order = ['Ctrl', 'Cmd', 'Super', 'Alt', 'Shift'];
  const sorted = modifiers.filter(m => order.includes(m)).sort(
    (a, b) => order.indexOf(a) - order.indexOf(b)
  );
  return [...sorted, key].join('+');
}

function startCapture() {
  capturing.value = true;
  capturedKeys.value = [];
  shortcutSaved.value = false;
}

async function saveShortcut() {
  if (capturedKeys.value.length === 0) return;
  const key = capturedKeys.value.join('+');
  try {
    const result = await invoke<string>('update_shortcut', { newKey: key });
    currentShortcut.value = result;
    shortcutSaved.value = true;
  } catch (e: any) {
    // Keep the old shortcut on error
  }
  capturing.value = false;
  capturedKeys.value = [];
}

function cancelCapture() {
  capturing.value = false;
  capturedKeys.value = [];
}

function handleKeyDown(e: KeyboardEvent) {
  if (!capturing.value) return;
  e.preventDefault();
  e.stopPropagation();

  const modifiers: string[] = [];
  if (e.ctrlKey) modifiers.push('Ctrl');
  if (e.metaKey) modifiers.push('Super');
  if (e.altKey) modifiers.push('Alt');
  if (e.shiftKey) modifiers.push('Shift');

  const modifierKeys = ['Control', 'Meta', 'Alt', 'Shift', 'Super'];
  if (modifierKeys.includes(e.key)) return;

  let key = e.key;
  if (key === ' ') key = 'Space';
  if (key.length === 1) key = key.toUpperCase();

  capturedKeys.value = [...modifiers, key];
}

onMounted(async () => {
  try {
    currentShortcut.value = await invoke<string>('get_shortcut');
  } catch {
    // keep default
  }
  window.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
});
</script>

<template>
  <div class="space-y-4">
    <div class="text-xs font-medium text-text-secondary uppercase tracking-wide">快捷键</div>

    <div class="flex items-center justify-between text-sm">
      <span class="text-text-primary">唤起 Command Center</span>
      <button
        v-if="!capturing"
        class="px-3 py-1.5 text-xs bg-bg-secondary hover:bg-bg-secondary/70 rounded-[6px] text-text-primary transition-colors border border-transparent hover:border-border font-mono"
        @click="startCapture"
      >
        {{ shortcutDisplay(currentShortcut) }}
      </button>
      <button
        v-else
        class="px-3 py-1.5 text-xs bg-dai/10 border border-dai text-dai rounded-[6px] font-mono animate-pulse"
      >
        {{ capturedKeys.length > 0 ? shortcutDisplay(capturedKeys.join('+')) : '按下快捷键...' }}
      </button>
    </div>

    <div v-if="capturing" class="flex gap-2">
      <button
        class="flex-1 px-3 py-1.5 text-xs bg-dai text-white rounded-[6px] hover:bg-dai-hover transition-colors disabled:opacity-50"
        :disabled="capturedKeys.length === 0"
        @click="saveShortcut"
      >
        确认
      </button>
      <button
        class="flex-1 px-3 py-1.5 text-xs bg-bg-secondary text-text-secondary rounded-[6px] hover:text-text-primary transition-colors"
        @click="cancelCapture"
      >
        取消
      </button>
    </div>

    <div v-if="shortcutSaved" class="text-xs text-green-600">
      快捷键已更新，立即生效
    </div>
  </div>
</template>
