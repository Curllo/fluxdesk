<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue';

const props = defineProps<{
  windowId: string;
  data: Record<string, any>;
}>();

import { useToolRegistry } from '@/stores/toolRegistry';
const registry = useToolRegistry();

const duration = ref((props.data.duration ?? 25) * 60);
const remaining = ref(duration.value);
const sessions = ref((props.data.sessions as number) ?? 0);

watch(() => props.data.duration, (val) => {
  if (val) {
    duration.value = val * 60;
    remaining.value = val * 60;
  }
});
watch(() => props.data.sessions, (val) => {
  if (typeof val === 'number') sessions.value = val;
});

const isRunning = ref(false);
const status = ref<'running' | 'paused' | 'completed'>('paused');

const minutes = computed(() =>
  String(Math.floor(remaining.value / 60)).padStart(2, '0')
);
const seconds = computed(() =>
  String(remaining.value % 60).padStart(2, '0')
);

const progress = computed(() =>
  duration.value > 0 ? 1 - remaining.value / duration.value : 0
);

// SVG progress ring
const CIRCLE_R = 54;
const CIRCUMFERENCE = 2 * Math.PI * CIRCLE_R;
const strokeDashoffset = computed(() =>
  CIRCUMFERENCE * (1 - progress.value)
);

let timer: ReturnType<typeof setInterval> | null = null;

function requestNotifyPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

function sendNotification() {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification('番茄钟完成！', {
      body: `${Math.round(duration.value / 60)} 分钟专注已完成`,
      icon: '/vite.svg',
    });
  }
}

function start() {
  if (isRunning.value) return;
  requestNotifyPermission();
  isRunning.value = true;
  status.value = 'running';
  timer = setInterval(() => {
    if (remaining.value > 0) {
      remaining.value--;
    } else {
      complete();
    }
  }, 1000);
}

function pause() {
  if (timer) { clearInterval(timer); timer = null; }
  isRunning.value = false;
  status.value = 'paused';
}

function stop() {
  pause();
  remaining.value = duration.value;
  status.value = 'paused';
}

function addSession() {
  sessions.value++;
  registry.updateTool(props.windowId, {
    config: { ...props.data, sessions: sessions.value },
  });
}

function complete() {
  pause();
  remaining.value = duration.value;
  status.value = 'completed';
  addSession();
  sendNotification();
}

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<template>
  <div class="flex flex-col items-center justify-center h-full gap-4">
    <!-- Circular progress ring -->
    <div class="relative w-[130px] h-[130px] flex items-center justify-center">
      <svg width="130" height="130" viewBox="0 0 130 130" class="absolute">
        <!-- Background circle -->
        <circle
          cx="65" cy="65" :r="CIRCLE_R"
          fill="none" stroke="var(--color-border)" stroke-width="6"
        />
        <!-- Progress circle -->
        <circle
          cx="65" cy="65" :r="CIRCLE_R"
          fill="none"
          :stroke="status === 'completed' ? 'var(--color-success)' : 'var(--color-dai)'"
          stroke-width="6"
          stroke-linecap="round"
          :stroke-dasharray="CIRCUMFERENCE"
          :stroke-dashoffset="strokeDashoffset"
          class="transition-all duration-500 ease-linear"
          transform="rotate(-90 65 65)"
        />
      </svg>
      <div
        class="text-4xl font-mono font-bold tracking-wider z-10"
        :class="
          status === 'completed'
            ? 'text-success'
            : isRunning
              ? 'text-dai'
              : 'text-text-primary'
        "
        data-testid="pomodoro-timer"
      >
        {{ minutes }}:{{ seconds }}
      </div>
    </div>

    <!-- Status -->
    <div class="text-xs text-text-secondary">
      <template v-if="status === 'completed'">✓ 番茄钟完成！休息一下吧</template>
      <template v-else-if="isRunning">专注中...</template>
      <template v-else-if="remaining < duration">已暂停</template>
      <template v-else>专注当下</template>
    </div>

    <!-- Controls -->
    <div class="flex gap-2">
      <button
        v-if="!isRunning"
        class="px-5 py-1.5 text-sm bg-dai text-white rounded-[8px] hover:bg-dai-hover transition-colors"
        @click="start"
      >
        {{ status === 'completed' || remaining < duration ? '继续' : '开始' }}
      </button>
      <button
        v-else
        class="px-5 py-1.5 text-sm bg-warning text-white rounded-[8px] hover:opacity-90 transition-opacity"
        @click="pause"
      >
        暂停
      </button>
      <button
        class="px-5 py-1.5 text-sm bg-bg-secondary text-text-primary rounded-[8px] hover:bg-border transition-colors"
        @click="stop"
      >
        重置
      </button>
    </div>

    <!-- Session counter -->
    <div v-if="sessions > 0" class="flex items-center gap-1 text-[11px] text-text-secondary/60">
      <span v-for="i in sessions" :key="i" class="text-dai">🍅</span>
      <span class="ml-1">{{ sessions }} 个番茄</span>
    </div>
  </div>
</template>
