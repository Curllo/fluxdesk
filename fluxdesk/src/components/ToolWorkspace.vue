<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useToolRegistry } from '@/stores/toolRegistry';
import { useGlobalSettingsStore } from '@/stores/globalSettingsStore';
import ToolCard from '@/components/ToolCard.vue';
import WorkspaceDock from '@/components/WorkspaceDock.vue';

const registry = useToolRegistry();
const settingsStore = useGlobalSettingsStore();
const workspaceSettings = computed(() => settingsStore.state.workspace);

const PADDING = 16;

const CELL_H = computed(() => workspaceSettings.value.defaultCardHeight);
const GAP = computed(() => {
  const map: Record<string, number> = { compact: 8, comfortable: 12, spacious: 20 };
  return map[workspaceSettings.value.cardGap] ?? 12;
});
const COLUMNS = computed(() => workspaceSettings.value.defaultColumns);

const dragHighlightCol = ref(0);
const dragHighlightRow = ref(0);
const dragHighlightW = ref(1);
const dragHighlightH = ref(1);
const draggingId = ref<string | null>(null);
const gridRef = ref<HTMLElement | null>(null);

onMounted(() => registry.init());

function closeTool(id: string) {
  registry.removeTool(id);
}

// ToolCard emits grid spans directly — just forward
function resizeTool(id: string, gw: number, gh: number) {
  registry.resizeTool(id, gw, gh);
}

// ── Long-press drag ──
function onDragStart(id: string) {
  draggingId.value = id;
  const tool = registry.getToolById(id);
  if (tool) {
    dragHighlightW.value = tool.gridWidth;
    dragHighlightH.value = tool.gridHeight;
  }
}

function onDragMove(_id: string, clientX: number, clientY: number) {
  if (!gridRef.value) return;
  const rect = gridRef.value.getBoundingClientRect();
  const colWidth = (rect.width - PADDING * 2) / COLUMNS.value;
  const col = Math.max(1, Math.min(COLUMNS.value, Math.floor((clientX - rect.left - PADDING) / colWidth) + 1));
  const row = Math.max(1, Math.floor((clientY - rect.top - PADDING) / (CELL_H.value + GAP.value)) + 1);
  dragHighlightCol.value = col;
  dragHighlightRow.value = row;
}

function onDragEnd(id: string, clientX: number, clientY: number) {
  if (!gridRef.value) return;
  const rect = gridRef.value.getBoundingClientRect();
  const colWidth = (rect.width - PADDING * 2) / COLUMNS.value;
  const col = Math.max(1, Math.min(COLUMNS.value, Math.floor((clientX - rect.left - PADDING) / colWidth) + 1));
  const row = Math.max(1, Math.floor((clientY - rect.top - PADDING) / (CELL_H.value + GAP.value)) + 1);

  const toolA = registry.getToolById(id);
  if (!toolA) { cleanupDragHighlight(); return; }

  const clampedCol = Math.max(1, Math.min(COLUMNS.value - toolA.gridWidth + 1, col));

  // Swap if target cell is occupied by a same-size card
  const toolB = registry.tools.find(t =>
    t.id !== id &&
    t.gridColumn === clampedCol &&
    t.gridRow === row &&
    t.gridWidth === toolA.gridWidth &&
    t.gridHeight === toolA.gridHeight
  );

  if (toolB) {
    const tmpCol = toolB.gridColumn;
    const tmpRow = toolB.gridRow;
    registry.moveTool(id, tmpCol, tmpRow);       // A → B's old pos
    registry.moveTool(toolB.id, toolA.gridColumn, toolA.gridRow); // B → A's old pos
  } else {
    registry.moveTool(id, clampedCol, row);
  }

  cleanupDragHighlight();
}

function cleanupDragHighlight() {
  dragHighlightCol.value = 0;
  dragHighlightRow.value = 0;
  dragHighlightW.value = 1;
  dragHighlightH.value = 1;
  draggingId.value = null;
}

</script>

<template>
  <div class="h-full w-full flex flex-col">
    <!-- Grid workspace -->
    <div ref="gridRef" class="flex-1 overflow-auto">
      <div
        v-if="registry.tools.length > 0"
        class="grid p-4"
        :style="{
          gridTemplateColumns: `repeat(${COLUMNS}, 1fr)`,
          gridAutoRows: `${CELL_H}px`,
          gridAutoFlow: 'row dense',
          gap: `${GAP}px`,
        }"
      >
        <div
          v-for="tool in registry.tools"
          :key="tool.id"
          :style="{
            gridColumn: `${tool.gridColumn} / span ${tool.gridWidth}`,
            gridRow: `${tool.gridRow} / span ${tool.gridHeight}`,
          }"
          class="relative transition-all duration-200"
        >
          <ToolCard
            :instance="tool"
            @close="closeTool"
            @resize="resizeTool"
            @drag-start="onDragStart"
            @drag-move="onDragMove"
            @drag-end="onDragEnd"
          />
        </div>

        <!-- Drag highlight -->
        <div
          v-if="dragHighlightCol > 0 && dragHighlightRow > 0"
          class="rounded-2xl border-2 border-dai/40 bg-dai/[0.06] pointer-events-none transition-all duration-150 z-10"
          :style="{
            gridColumn: `${dragHighlightCol} / span ${dragHighlightW}`,
            gridRow: `${dragHighlightRow} / span ${dragHighlightH}`,
          }"
        />
      </div>

      <!-- Empty -->
      <div
        v-else
        class="h-full flex flex-col items-center justify-center text-text-secondary px-8
               bg-gradient-to-b from-transparent via-bg-secondary/[0.04] to-bg-secondary/[0.08]"
      >
        <p class="text-base font-medium mb-3 text-text-primary/70">工作区是空的</p>
        <p class="text-sm text-text-secondary/50 text-center">对右侧 AI 助手说「创建一个番茄钟」</p>
      </div>
    </div>

    <!-- Dock -->
    <WorkspaceDock />
  </div>
</template>
