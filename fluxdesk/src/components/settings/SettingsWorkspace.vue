<script setup lang="ts">
import { useGlobalSettingsStore } from '@/stores/globalSettingsStore';

const store = useGlobalSettingsStore();
const workspace = store.state.workspace;
</script>

<template>
  <div class="space-y-5">
    <div class="text-xs font-medium text-text-secondary uppercase tracking-wide">工作区</div>

    <!-- 默认网格列数 -->
    <div>
      <label class="block text-xs text-text-secondary mb-2">默认网格列数：{{ workspace.defaultColumns }}</label>
      <div class="flex items-center gap-3">
        <span class="text-xs text-text-secondary/60">2</span>
        <input
          type="range"
          min="2"
          max="6"
          step="1"
          v-model.number="workspace.defaultColumns"
          class="flex-1 h-1.5 bg-bg-secondary rounded-full appearance-none cursor-pointer accent-dai"
        />
        <span class="text-xs text-text-secondary/60">6</span>
      </div>
    </div>

    <!-- 默认自动排列 -->
    <div class="flex items-center justify-between text-sm">
      <div>
        <div class="text-text-primary">默认自动排列</div>
        <div class="text-[11px] text-text-secondary/60 mt-0.5">新工作区默认启用自动排列</div>
      </div>
      <button
        class="relative w-9 h-5 rounded-full transition-colors duration-200 flex-shrink-0"
        :class="workspace.defaultAutoArrange ? 'bg-dai' : 'bg-border'"
        @click="workspace.defaultAutoArrange = !workspace.defaultAutoArrange"
      >
        <span
          class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all duration-200"
          :style="{ transform: workspace.defaultAutoArrange ? 'translateX(16px)' : 'translateX(0)' }"
        />
      </button>
    </div>

    <!-- 卡片间距 -->
    <div>
      <label class="block text-xs text-text-secondary mb-2">卡片间距</label>
      <div class="flex gap-2">
        <button
          v-for="opt in ([{ key: 'compact', label: '紧凑' }, { key: 'comfortable', label: '舒适' }, { key: 'spacious', label: '宽松' }] as const)"
          :key="opt.key"
          class="flex-1 px-3 py-2 text-sm rounded-[8px] border transition-all"
          :class="workspace.cardGap === opt.key ? 'border-dai bg-dai/10 text-dai' : 'border-border/40 text-text-secondary hover:text-text-primary hover:border-border'"
          @click="workspace.cardGap = opt.key"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <!-- 默认卡片高度 -->
    <div>
      <label class="block text-xs text-text-secondary mb-2">默认卡片高度</label>
      <div class="flex gap-2">
        <button
          v-for="opt in ([{ value: 180, label: '180px' }, { value: 220, label: '220px' }, { value: 260, label: '260px' }] as const)"
          :key="opt.value"
          class="flex-1 px-3 py-2 text-sm rounded-[8px] border transition-all"
          :class="workspace.defaultCardHeight === opt.value ? 'border-dai bg-dai/10 text-dai' : 'border-border/40 text-text-secondary hover:text-text-primary hover:border-border'"
          @click="workspace.defaultCardHeight = opt.value"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>
  </div>
</template>
