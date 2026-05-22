<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

const sidebarOpen = ref(true);

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value;
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
    e.preventDefault();
    toggleSidebar();
  }
}

onMounted(() => document.addEventListener('keydown', onKeydown));
onUnmounted(() => document.removeEventListener('keydown', onKeydown));
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden bg-bg-primary relative">
    <!-- Workspace -->
    <div class="flex-1 min-w-0">
      <slot name="workspace" />
    </div>

    <!-- Agent Sidebar -->
    <Transition name="sidebar-slide">
      <aside
        v-if="sidebarOpen"
        class="flex-shrink-0 w-[360px] border-l border-border/60 overflow-visible bg-bg-primary shadow-[-8px_0_32px_rgba(0,0,0,0.06)] relative"
      >
        <!-- Sidebar toggle button (inside sidebar, left edge) -->
        <button
          class="absolute top-1/2 -translate-y-1/2 -left-[10px] flex-shrink-0 w-5 h-9
                 flex items-center justify-center
                 bg-gradient-to-l from-bg-secondary/90 to-bg-secondary/70
                 hover:from-bg-secondary hover:to-bg-secondary
                 backdrop-blur-sm
                 rounded-r-[6px] text-text-secondary/50 hover:text-text-primary
                 transition-all duration-200 cursor-pointer border-0 outline-none
                 shadow-sm hover:shadow-md z-20"
          title="收起侧边栏 (⌘B)"
          @click="toggleSidebar"
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="rotate-180 transition-transform duration-300"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <slot name="sidebar" />
      </aside>
    </Transition>

    <!-- Toggle button (when sidebar closed) -->
    <button
      v-if="!sidebarOpen"
      class="absolute top-1/2 -translate-y-1/2 right-1 flex-shrink-0 w-5 h-9
             flex items-center justify-center
             bg-gradient-to-r from-bg-secondary/90 to-bg-secondary/70
             hover:from-bg-secondary hover:to-bg-secondary
             backdrop-blur-sm
             rounded-l-[6px] text-text-secondary/50 hover:text-text-primary
             transition-all duration-200 cursor-pointer border-0 outline-none
             shadow-sm hover:shadow-md z-20"
      title="展开侧边栏 (⌘B)"
      @click="toggleSidebar"
    >
      <svg
        width="10"
        height="10"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="transition-transform duration-300"
      >
        <polyline points="15 18 9 12 15 6" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.sidebar-slide-enter-active,
.sidebar-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  width: 0 !important;
  min-width: 0 !important;
  opacity: 0;
  border-left-width: 0;
  overflow: hidden;
}
</style>
