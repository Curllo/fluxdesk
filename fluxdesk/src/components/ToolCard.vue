<script setup lang="ts">
import { computed, defineAsyncComponent, shallowRef, onMounted, onUnmounted } from 'vue';
import type { ToolInstance } from '@/types';
import { useToolRegistry } from '@/stores/toolRegistry';
import { useTemplateStore } from '@/stores/templateStore';
import DynamicCardRenderer from './DynamicCardRenderer.vue';

const props = defineProps<{
  instance: ToolInstance;
}>();

const emit = defineEmits<{
  close: [id: string];
  resize: [id: string, gw: number, gh: number];
  'drag-start': [id: string];
  'drag-move': [id: string, x: number, y: number];
  'drag-end': [id: string, x: number, y: number];
}>();

const registry = useToolRegistry();
const templateStore = useTemplateStore();
const appComponent = shallowRef<any>(null);

const template = computed(() => templateStore.getTemplateById(props.instance.type));

const typeIcons = computed(() => {
  const map: Record<string, string> = {};
  for (const t of templateStore.installedTemplates) {
    map[t.id] = t.icon;
  }
  return map;
});

const accentColor = computed(() => {
  return template.value?.accentColor || 'var(--color-dai)';
});

const isBuiltIn = computed(() => template.value?.isBuiltIn ?? true);

onMounted(() => {
  if (isBuiltIn.value) {
    const map: Record<string, any> = {
      todo: defineAsyncComponent(() => import('@/apps/Todo/index.vue')),
      pomodoro: defineAsyncComponent(() => import('@/apps/Pomodoro/index.vue')),
      note: defineAsyncComponent(() => import('@/apps/Note/index.vue')),
      calendar: defineAsyncComponent(() => import('@/apps/Calendar/index.vue')),
      weather: defineAsyncComponent(() => import('@/apps/Weather/index.vue')),
    };
    appComponent.value = map[props.instance.type] || null;
  }
});

function onDynamicUpdate(config: Record<string, any>) {
  if (JSON.stringify(props.instance.config) !== JSON.stringify(config)) {
    registry.updateToolConfig(props.instance.id, config);
  }
}

// ── Cleanup ──
let dragController: AbortController | null = null;
let resizeController: AbortController | null = null;

onUnmounted(() => {
  dragController?.abort();
  resizeController?.abort();
  if (longPressTimer) clearTimeout(longPressTimer);
});

// ── Long-press drag ──
let longPressTimer: ReturnType<typeof setTimeout> | null = null;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;

function onTitlePointerDown(e: PointerEvent) {
  e.preventDefault();
  if (registry.isAutoArrange) return;
  if ((e.target as HTMLElement).closest('button')) return;

  const card = (e.currentTarget as HTMLElement).closest('.card-wrapper') as HTMLElement;
  if (!card) return;

  dragStartX = e.clientX;
  dragStartY = e.clientY;

  dragController = new AbortController();
  const { signal } = dragController;

  longPressTimer = setTimeout(() => {
    isDragging = true;
    card.setPointerCapture(e.pointerId);
    emit('drag-start', props.instance.id);
    card.addEventListener('pointermove', onDragMove, { signal });
    card.addEventListener('pointerup', onDragEnd, { signal });
    card.addEventListener('pointercancel', onDragEnd, { signal });
  }, 80);

  card.addEventListener('pointermove', onEarlyMove, { signal });
  card.addEventListener('pointerup', onEarlyUp, { signal });
  card.addEventListener('pointercancel', onEarlyUp, { signal });
}

function onEarlyMove(e: PointerEvent) {
  if (isDragging) return;
  if (Math.abs(e.clientX - dragStartX) > 5 || Math.abs(e.clientY - dragStartY) > 5) {
    cleanupDrag();
  }
}

function onEarlyUp() {
  if (!isDragging) cleanupDrag();
}

function onDragMove(e: PointerEvent) {
  emit('drag-move', props.instance.id, e.clientX, e.clientY);
}

function onDragEnd(e: PointerEvent) {
  cleanupDrag();
  emit('drag-end', props.instance.id, e.clientX, e.clientY);
}

function cleanupDrag() {
  if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
  isDragging = false;
  dragController?.abort();
  dragController = null;
}

// ── Resize (bottom-right) ──
let resizeCellW = 0, resizeCellH = 0;
let resizeStartGW = 0, resizeStartGH = 0;
let resizeStartX = 0, resizeStartY = 0;

function onResizeStart(e: PointerEvent) {
  e.preventDefault();
  e.stopPropagation();

  const card = (e.currentTarget as HTMLElement).closest('.card-wrapper') as HTMLElement;
  if (!card) return;

  const rect = card.getBoundingClientRect();
  resizeCellW = rect.width / props.instance.gridWidth;
  resizeCellH = rect.height / props.instance.gridHeight;
  resizeStartGW = props.instance.gridWidth;
  resizeStartGH = props.instance.gridHeight;
  resizeStartX = e.clientX;
  resizeStartY = e.clientY;

  resizeController = new AbortController();
  const { signal } = resizeController;

  card.setPointerCapture(e.pointerId);
  card.addEventListener('pointermove', onResizeMove, { signal });
  card.addEventListener('pointerup', onResizeEnd, { signal });
  card.addEventListener('pointercancel', onResizeEnd, { signal });
}

function onResizeMove(e: PointerEvent) {
  const dx = e.clientX - resizeStartX;
  const dy = e.clientY - resizeStartY;
  const dgw = Math.round(dx / resizeCellW);
  const dgh = Math.round(dy / resizeCellH);
  emit('resize', props.instance.id,
    Math.max(1, resizeStartGW + dgw),
    Math.max(1, resizeStartGH + dgh));
}

function onResizeEnd() {
  resizeController?.abort();
  resizeController = null;
}
</script>

<template>
  <div class="card-wrapper h-full">
    <div
      class="group relative flex flex-col h-full bg-bg-primary rounded-2xl overflow-hidden border border-border/60
             transition-shadow duration-300 ease-smooth"
      :class="isDragging
        ? 'shadow-[0_16px_48px_rgba(0,0,0,0.18)] scale-105 z-50 border-dai/40'
        : 'hover:shadow-[0_8px_30px_rgba(0,0,0,0.10)] hover:border-border/40'"
      :style="{ '--card-accent': accentColor }"
    >
      <div class="h-[3px] w-full flex-shrink-0 opacity-60" :style="{ background: accentColor }" />

      <!-- Title bar -->
      <div
        class="flex items-center justify-between px-3 py-1.5 select-none
               bg-gradient-to-r from-bg-primary to-bg-secondary/20
               border-b border-border/40"
        :class="registry.isAutoArrange ? 'cursor-default' : 'cursor-grab'"
        @pointerdown="onTitlePointerDown"
      >
        <span class="text-[11px] font-semibold text-text-secondary/70 truncate flex items-center gap-1.5 tracking-wide uppercase pointer-events-none">
          <span class="opacity-60 flex-shrink-0">{{ typeIcons[instance.type] || '▪' }}</span>
          {{ instance.title }}
        </span>
        <button
          class="w-5 h-5 flex items-center justify-center rounded-md hover:bg-error/10 text-text-secondary/40 hover:text-error transition-all flex-shrink-0"
          @click="emit('close', instance.id)"
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <!-- Content: built-in -->
      <div v-if="isBuiltIn" class="flex-1 overflow-auto p-3 min-h-0">
        <component v-if="appComponent" :is="appComponent" :window-id="instance.id" :data="instance.config" />
      </div>

      <!-- Content: dynamic -->
      <div v-else class="flex-1 overflow-auto p-3 min-h-0">
        <DynamicCardRenderer
          :vue-code="template?.vueCode || ''"
          :window-id="instance.id"
          :data="instance.config"
          @update-config="onDynamicUpdate"
        />
      </div>

      <!-- Resize handle -->
      <div
        class="absolute bottom-0 right-0 w-6 h-6 opacity-0 group-hover:opacity-100
               transition-all duration-200 cursor-se-resize flex items-end justify-end"
        @pointerdown="onResizeStart"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" class="text-border/50 mb-[3px] mr-[3px]">
          <line x1="8" y1="12" x2="12" y2="8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="4" y1="12" x2="12" y2="4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="0" y1="12" x2="12" y2="0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
    </div>
  </div>
</template>
