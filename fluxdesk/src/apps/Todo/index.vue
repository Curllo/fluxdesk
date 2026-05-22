<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useToolRegistry } from '@/stores/toolRegistry';

const props = defineProps<{
  windowId: string;
  data: Record<string, any>;
}>();

const registry = useToolRegistry();

interface TodoItem {
  id: string;
  content: string;
  completed: boolean;
  priority: 0 | 1 | 2;
}

const todos = ref<TodoItem[]>([]);
const newTodo = ref('');

// ── Load initial data from props (once) ──
onMounted(() => {
  if (Array.isArray(props.data.todos)) {
    todos.value = props.data.todos;
  }
});

// ── Persist on change (debounced) ──
let saveTimer: ReturnType<typeof setTimeout> | null = null;
function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    registry.updateToolConfig(props.windowId, { todos: todos.value });
  }, 300);
}
watch(todos, () => scheduleSave(), { deep: true });
onUnmounted(() => {
  if (saveTimer) clearTimeout(saveTimer);
});

// ── Computed ──
const totalTodos = computed(() => todos.value.length);
const completedTodos = computed(() => todos.value.filter(t => t.completed).length);
const progress = computed(() => totalTodos.value > 0 ? completedTodos.value / totalTodos.value : 0);

const sortedTodos = computed(() => {
  return [...todos.value].sort((a, b) => {
    if (a.completed !== b.completed) return a.completed ? 1 : -1;
    return b.priority - a.priority;
  });
});

// ── Actions ──
function addTodo() {
  const text = newTodo.value.trim();
  if (!text) return;
  todos.value.push({
    id: `todo_${crypto.randomUUID()}`,
    content: text,
    completed: false,
    priority: 1,
  });
  newTodo.value = '';
}

function toggleTodo(id: string) {
  const todo = todos.value.find(t => t.id === id);
  if (todo) todo.completed = !todo.completed;
}

function removeTodo(id: string) {
  todos.value = todos.value.filter(t => t.id !== id);
}

function setPriority(id: string, priority: 0 | 1 | 2) {
  const todo = todos.value.find(t => t.id === id);
  if (todo) todo.priority = priority;
}

const priorityColors: Record<number, string> = {
  0: 'bg-success/20 text-success',
  1: 'bg-warning/20 text-warning',
  2: 'bg-error/20 text-error',
};

const priorityLabels: Record<number, string> = {
  0: '低',
  1: '中',
  2: '高',
};
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Progress bar -->
    <div v-if="totalTodos > 0" class="mb-3">
      <div class="h-1.5 w-full bg-bg-secondary rounded-full overflow-hidden">
        <div
          class="h-full bg-dai rounded-full transition-all duration-500 ease-smooth"
          :style="{ width: `${progress * 100}%` }"
        />
      </div>
      <div class="flex justify-between mt-1 text-[10px] text-text-secondary/60">
        <span>{{ completedTodos }}/{{ totalTodos }} 已完成</span>
        <span>{{ Math.round(progress * 100) }}%</span>
      </div>
    </div>

    <!-- Input -->
    <div class="flex gap-2 mb-3">
      <input
        v-model="newTodo"
        class="flex-1 px-3 py-1.5 text-sm bg-bg-secondary rounded-[8px] outline-none border border-transparent focus:border-dai text-text-primary placeholder:text-text-secondary/40"
        placeholder="添加待办..."
        @keydown.enter.prevent="addTodo"
      />
      <button
        class="px-3 py-1.5 text-sm bg-dai text-white rounded-[8px] hover:bg-dai-hover transition-colors flex-shrink-0"
        @click="addTodo"
      >
        添加
      </button>
    </div>

    <!-- List -->
    <div class="flex-1 overflow-y-auto space-y-1">
      <div
        v-for="todo in sortedTodos"
        :key="todo.id"
        class="flex items-center gap-2 px-2.5 py-2 rounded-[8px] hover:bg-bg-secondary/80 group transition-colors"
      >
        <input
          type="checkbox"
          :checked="todo.completed"
          class="w-3.5 h-3.5 accent-dai cursor-pointer flex-shrink-0"
          @change="toggleTodo(todo.id)"
        />
        <span
          class="flex-1 text-sm min-w-0 truncate"
          :class="todo.completed ? 'line-through text-text-secondary/50' : 'text-text-primary'"
        >
          {{ todo.content }}
        </span>
        <span
          class="px-1.5 py-0.5 text-[10px] rounded cursor-pointer flex-shrink-0 hidden group-hover:inline-flex"
          :class="priorityColors[todo.priority]"
          @click="setPriority(todo.id, ((todo.priority + 1) % 3) as 0 | 1 | 2)"
        >
          {{ priorityLabels[todo.priority] }}
        </span>
        <button
          class="hidden group-hover:inline text-error/60 hover:text-error text-xs px-1 transition-all flex-shrink-0"
          @click="removeTodo(todo.id)"
        >
          ✕
        </button>
      </div>

      <!-- Empty state -->
      <div
        v-if="totalTodos === 0"
        class="flex flex-col items-center justify-center h-full text-text-secondary/40 text-xs gap-1"
      >
        <span>没有待办事项</span>
        <span>在上方输入并点击添加</span>
      </div>
    </div>

    <!-- Footer -->
    <div v-if="totalTodos > 0" class="mt-2 pt-2 border-t border-border text-[10px] text-text-secondary/40 flex justify-between">
      <span>{{ totalTodos }} 项</span>
      <span>点击标签切换优先级</span>
    </div>
  </div>
</template>
