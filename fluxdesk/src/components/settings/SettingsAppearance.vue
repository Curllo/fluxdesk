<script setup lang="ts">
import { useGlobalSettingsStore } from '@/stores/globalSettingsStore';

const store = useGlobalSettingsStore();
const appearance = store.state.appearance;

const ACCENT_COLORS: { key: string; color: string }[] = [
  { key: 'indigo', color: '#6366f1' },
  { key: 'rose', color: '#f43f5e' },
  { key: 'amber', color: '#f59e0b' },
  { key: 'emerald', color: '#10b981' },
];

function onThemeChange(theme: 'light' | 'dark' | 'system') {
  appearance.theme = theme;
  store.applyAppearance();
}

function onAccentChange(key: string) {
  appearance.accentColor = key as any;
  store.applyAppearance();
}

function onFontSizeChange(key: string) {
  appearance.fontSize = key as any;
  store.applyAppearance();
}

function onAnimationsChange() {
  appearance.animations = !appearance.animations;
  store.applyAppearance();
}

function onGlassmorphismChange() {
  appearance.glassmorphism = !appearance.glassmorphism;
  store.applyAppearance();
}
</script>

<template>
  <div class="space-y-5">
    <div class="text-xs font-medium text-text-secondary uppercase tracking-wide">外观</div>

    <!-- 主题模式 -->
    <div>
      <label class="block text-xs text-text-secondary mb-2">主题模式</label>
      <div class="flex gap-2">
        <button
          v-for="mode in ([{ key: 'light', label: '浅色' }, { key: 'dark', label: '深色' }, { key: 'system', label: '跟随系统' }] as const)"
          :key="mode.key"
          class="flex-1 px-3 py-2 text-sm rounded-[8px] border transition-all"
          :class="appearance.theme === mode.key ? 'border-dai bg-dai/10 text-dai' : 'border-border/40 text-text-secondary hover:text-text-primary hover:border-border'"
          @click="onThemeChange(mode.key)"
        >
          {{ mode.label }}
        </button>
      </div>
    </div>

    <!-- 强调色 -->
    <div>
      <label class="block text-xs text-text-secondary mb-2">强调色</label>
      <div class="flex gap-3">
        <button
          v-for="accent in ACCENT_COLORS"
          :key="accent.key"
          class="w-8 h-8 rounded-full transition-all duration-200"
          :class="appearance.accentColor === accent.key ? 'ring-2 ring-offset-2 ring-offset-bg-primary' : 'ring-0'"
          :style="{ backgroundColor: accent.color, '--tw-ring-color': accent.color }"
          @click="onAccentChange(accent.key)"
        />
      </div>
    </div>

    <!-- 字体大小 -->
    <div>
      <label class="block text-xs text-text-secondary mb-2">字体大小</label>
      <div class="flex gap-2">
        <button
          v-for="opt in ([{ key: 'small', label: '小' }, { key: 'medium', label: '中' }, { key: 'large', label: '大' }] as const)"
          :key="opt.key"
          class="flex-1 px-3 py-2 text-sm rounded-[8px] border transition-all"
          :class="appearance.fontSize === opt.key ? 'border-dai bg-dai/10 text-dai' : 'border-border/40 text-text-secondary hover:text-text-primary hover:border-border'"
          @click="onFontSizeChange(opt.key)"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <!-- 界面动画 -->
    <div class="flex items-center justify-between text-sm">
      <div>
        <div class="text-text-primary">界面动画</div>
        <div class="text-[11px] text-text-secondary/60 mt-0.5">启用界面过渡动画效果</div>
      </div>
      <button
        class="relative w-9 h-5 rounded-full transition-colors duration-200 flex-shrink-0"
        :class="appearance.animations ? 'bg-dai' : 'bg-border'"
        @click="onAnimationsChange()"
      >
        <span
          class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all duration-200"
          :style="{ transform: appearance.animations ? 'translateX(16px)' : 'translateX(0)' }"
        />
      </button>
    </div>

    <!-- 毛玻璃效果 -->
    <div class="flex items-center justify-between text-sm">
      <div>
        <div class="text-text-primary">毛玻璃效果</div>
        <div class="text-[11px] text-text-secondary/60 mt-0.5">启用毛玻璃背景效果</div>
      </div>
      <button
        class="relative w-9 h-5 rounded-full transition-colors duration-200 flex-shrink-0"
        :class="appearance.glassmorphism ? 'bg-dai' : 'bg-border'"
        @click="onGlassmorphismChange()"
      >
        <span
          class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all duration-200"
          :style="{ transform: appearance.glassmorphism ? 'translateX(16px)' : 'translateX(0)' }"
        />
      </button>
    </div>
  </div>
</template>
