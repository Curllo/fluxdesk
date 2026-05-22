<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  title?: string;
  message: string;
  action?: string;
  params?: Record<string, any>;
}>();

const emit = defineEmits<{
  confirm: [params?: Record<string, any>];
  cancel: [];
}>();
</script>

<template>
  <div class="flex flex-col gap-3 p-4 bg-bg-secondary rounded-[12px] border border-border">
    <div class="flex items-start gap-3">
      <div class="w-8 h-8 flex items-center justify-center rounded-full bg-warning/20 text-warning shrink-0">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <div>
        <p class="text-sm font-medium text-text-primary">
          {{ title || '请确认' }}
        </p>
        <p class="text-xs text-text-secondary mt-1">{{ message }}</p>
      </div>
    </div>
    <div class="flex justify-end gap-2">
      <button
        class="px-3 py-1.5 text-xs bg-bg-primary text-text-secondary rounded-[8px] hover:bg-border transition-colors border border-border"
        @click="emit('cancel')"
      >
        取消
      </button>
      <button
        class="px-3 py-1.5 text-xs bg-dai text-white rounded-[8px] hover:bg-dai-hover transition-colors"
        @click="emit('confirm', props.params)"
      >
        确认
      </button>
    </div>
  </div>
</template>
