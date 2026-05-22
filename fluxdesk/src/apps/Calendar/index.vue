<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  windowId: string;
  data: Record<string, any>;
}>();

const currentDate = ref(new Date());

const year = computed(() => currentDate.value.getFullYear());
const month = computed(() => currentDate.value.getMonth());

const monthNames = [
  '一月','二月','三月','四月','五月','六月',
  '七月','八月','九月','十月','十一月','十二月',
];

const weekDays = ['日','一','二','三','四','五','六'];

const calendarDays = computed(() => {
  const firstDay = new Date(year.value, month.value, 1);
  const lastDay = new Date(year.value, month.value + 1, 0);
  const startOffset = firstDay.getDay();
  const daysInMonth = lastDay.getDate();

  const days: { day: number; isCurrentMonth: boolean }[] = [];
  for (let i = 0; i < startOffset; i++) {
    days.push({ day: 0, isCurrentMonth: false });
  }
  for (let i = 1; i <= daysInMonth; i++) {
    days.push({ day: i, isCurrentMonth: true });
  }
  return days;
});

const today = new Date().getDate();
const isTodayMonth =
  new Date().getFullYear() === year.value &&
  new Date().getMonth() === month.value;

function prevMonth() {
  currentDate.value = new Date(year.value, month.value - 1, 1);
}
function nextMonth() {
  currentDate.value = new Date(year.value, month.value + 1, 1);
}
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="flex items-center justify-between mb-3">
      <button
        class="px-2 py-1 text-xs bg-bg-secondary rounded hover:bg-border transition-colors text-text-primary"
        @click="prevMonth"
      >
        ◀
      </button>
      <span class="text-sm font-semibold text-text-primary">
        {{ year }}年 {{ monthNames[month] }}
      </span>
      <button
        class="px-2 py-1 text-xs bg-bg-secondary rounded hover:bg-border transition-colors text-text-primary"
        @click="nextMonth"
      >
        ▶
      </button>
    </div>

    <div class="grid grid-cols-7 gap-1 mb-1">
      <div
        v-for="d in weekDays"
        :key="d"
        class="text-center text-[10px] text-text-secondary py-1"
      >
        {{ d }}
      </div>
    </div>

    <div class="grid grid-cols-7 gap-1 flex-1">
      <div
        v-for="(cell, idx) in calendarDays"
        :key="idx"
        class="flex items-center justify-center text-xs rounded-[6px]"
        :class="{
          'text-text-secondary': !cell.isCurrentMonth,
          'text-text-primary hover:bg-bg-secondary cursor-pointer': cell.isCurrentMonth,
          'bg-dai text-white hover:bg-dai-hover':
            cell.isCurrentMonth && cell.day === today && isTodayMonth,
        }"
      >
        {{ cell.day || '' }}
      </div>
    </div>
  </div>
</template>
