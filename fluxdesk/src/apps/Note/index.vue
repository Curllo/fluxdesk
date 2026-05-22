<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useToolRegistry } from '@/stores/toolRegistry';

const props = defineProps<{
  windowId: string;
  data: Record<string, any>;
}>();

const registry = useToolRegistry();

const content = ref('');
const title = ref('未命名笔记');

// ── Load initial data from props (once) ──
onMounted(() => {
  if (typeof props.data.content === 'string') content.value = props.data.content;
  if (typeof props.data.title === 'string') title.value = props.data.title;
});

const wordCount = computed(() => {
  const text = content.value.trim();
  return text ? text.length : 0;
});

// ── Persist on change (debounced) ──
let saveTimer: ReturnType<typeof setTimeout> | null = null;
function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    registry.updateToolConfig(props.windowId, {
      content: content.value,
      title: title.value,
    });
  }, 300);
}
watch(content, () => scheduleSave());
watch(title, () => scheduleSave());
onUnmounted(() => {
  if (saveTimer) clearTimeout(saveTimer);
});
</script>

<template>
  <div class="flex flex-col h-full">
    <input
      v-model="title"
      class="w-full min-w-0 px-1 py-1 mb-2 text-base font-semibold bg-transparent outline-none text-text-primary border-b border-transparent focus:border-dai transition-colors"
      placeholder="笔记标题..."
    />
    <textarea
      v-model="content"
      class="flex-1 w-full px-1 py-1 text-sm bg-transparent outline-none resize-none text-text-primary leading-relaxed placeholder:text-text-secondary/30"
      placeholder="在此输入笔记内容..."
      @keydown.enter.stop
    />
    <div class="text-[10px] text-text-secondary/40 pt-1 border-t border-border mt-1">
      {{ wordCount }} 字
    </div>
  </div>
</template>
