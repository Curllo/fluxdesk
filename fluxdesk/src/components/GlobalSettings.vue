<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useGlobalSettingsStore } from '@/stores/globalSettingsStore';
import SettingsGeneral from './settings/SettingsGeneral.vue';
import SettingsAgent from './settings/SettingsAgent.vue';
import SettingsAppearance from './settings/SettingsAppearance.vue';
import SettingsWorkspace from './settings/SettingsWorkspace.vue';
import SettingsShortcuts from './settings/SettingsShortcuts.vue';
import SettingsData from './settings/SettingsData.vue';
import SettingsAbout from './settings/SettingsAbout.vue';
import SettingsDebug from './settings/SettingsDebug.vue';

const store = useGlobalSettingsStore();

const visible = ref(false);
const activeSection = ref('general');
const devMode = ref(localStorage.getItem('fluxdesk-dev-mode') === '1');

const SECTIONS = [
  { id: 'general', label: '通用', icon: 'gear' },
  { id: 'agent', label: 'Agent', icon: 'cpu' },
  { id: 'appearance', label: '外观', icon: 'palette' },
  { id: 'workspace', label: '工作区', icon: 'grid' },
  { id: 'shortcuts', label: '快捷键', icon: 'keyboard' },
  { id: 'data', label: '数据管理', icon: 'database' },
  { id: 'about', label: '关于', icon: 'info' },
];

const sectionLabels: Record<string, string> = {
  general: '通用',
  agent: 'AI 服务',
  appearance: '外观',
  workspace: '工作区',
  shortcuts: '快捷键',
  data: '数据管理',
  about: '关于',
  debug: '调试',
};

const currentSectionLabel = computed(() => sectionLabels[activeSection.value] || activeSection.value);

function open(section?: string) {
  store.init();
  visible.value = true;
  if (section) activeSection.value = section;
}

function close() {
  visible.value = false;
}

function onOverlayClick(e: MouseEvent) {
  if ((e.target as HTMLElement)?.classList.contains('modal-overlay')) {
    close();
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && visible.value) {
    close();
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown);
  window.addEventListener('fluxdesk:devmode', () => {
    devMode.value = localStorage.getItem('fluxdesk-dev-mode') === '1';
  });
});

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown);
});

defineExpose({ open });
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="visible"
        class="modal-overlay fixed inset-0 z-[9999] flex items-center justify-center bg-black/30 backdrop-blur-sm"
        @click="onOverlayClick"
      >
        <div class="w-[720px] h-[580px] flex bg-bg-primary rounded-[16px] shadow-[0_32px_64px_rgba(0,0,0,0.24)] border border-border/40 overflow-hidden">
          <!-- Sidebar -->
          <div class="w-[170px] flex-shrink-0 bg-bg-secondary/30 border-r border-border/30 p-2 flex flex-col">
            <nav class="space-y-0.5 flex-1">
              <button
                v-for="section in SECTIONS"
                :key="section.id"
                class="w-full flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-all"
                :class="activeSection === section.id ? 'bg-dai/10 text-dai font-medium' : 'text-text-secondary hover:bg-bg-secondary hover:text-text-primary'"
                @click="activeSection = section.id"
              >
                <!-- gear -->
                <svg v-if="section.icon === 'gear'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                </svg>
                <!-- cpu -->
                <svg v-else-if="section.icon === 'cpu'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>
                </svg>
                <!-- palette -->
                <svg v-else-if="section.icon === 'palette'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.93 0 1.5-.67 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-1 0-.83.67-1.5 1.5-1.5H16c3.31 0 6-2.69 6-6 0-5.5-4.5-10-10-10z"/>
                </svg>
                <!-- grid -->
                <svg v-else-if="section.icon === 'grid'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
                </svg>
                <!-- keyboard -->
                <svg v-else-if="section.icon === 'keyboard'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M6 16h.01M10 16h.01M14 16h.01M18 16h.01"/>
                </svg>
                <!-- database -->
                <svg v-else-if="section.icon === 'database'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                </svg>
                <!-- info -->
                <svg v-else-if="section.icon === 'info'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
                {{ section.label }}
              </button>
            </nav>

            <!-- Debug section (devMode only) -->
            <button
              v-if="devMode"
              class="w-full flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-all mt-1"
              :class="activeSection === 'debug' ? 'bg-dai/10 text-dai font-medium' : 'text-text-secondary hover:bg-bg-secondary hover:text-text-primary'"
              @click="activeSection = 'debug'"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 4V1M8 5l-2-2m10 2l2-2M12 20v3m-4-1l-2 2m10-2l2 2"/>
                <rect x="4" y="8" width="16" height="8" rx="2"/>
                <path d="M8 12h.01M16 12h.01"/>
              </svg>
              调试
              <span class="w-1.5 h-1.5 rounded-full bg-dai ml-auto" />
            </button>
          </div>

          <!-- Content -->
          <div class="flex-1 flex flex-col min-w-0">
            <!-- Header -->
            <div class="flex items-center justify-between px-6 py-4 border-b border-border/30 flex-shrink-0">
              <h2 class="text-base font-semibold text-text-primary">{{ currentSectionLabel }}</h2>
              <button
                class="w-7 h-7 flex items-center justify-center rounded-md hover:bg-bg-secondary text-text-secondary/60 hover:text-text-primary transition-all"
                @click="close"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>

            <!-- Content area -->
            <div class="flex-1 overflow-y-auto px-6 py-5">
              <SettingsGeneral v-if="activeSection === 'general'" />
              <SettingsAgent v-else-if="activeSection === 'agent'" />
              <SettingsAppearance v-else-if="activeSection === 'appearance'" />
              <SettingsWorkspace v-else-if="activeSection === 'workspace'" />
              <SettingsShortcuts v-else-if="activeSection === 'shortcuts'" />
              <SettingsData v-else-if="activeSection === 'data'" />
              <SettingsAbout v-else-if="activeSection === 'about'" />
              <SettingsDebug v-else-if="activeSection === 'debug'" />
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active {
  transition: opacity 0.2s ease;
}
.modal-enter-active > div {
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s ease;
}
.modal-leave-active {
  transition: opacity 0.15s ease;
}
.modal-leave-active > div {
  transition: transform 0.15s ease, opacity 0.15s ease;
}
.modal-enter-from {
  opacity: 0;
}
.modal-enter-from > div {
  opacity: 0;
  transform: scale(0.95) translateY(8px);
}
.modal-leave-to {
  opacity: 0;
}
.modal-leave-to > div {
  opacity: 0;
  transform: scale(0.97) translateY(-4px);
}
</style>
