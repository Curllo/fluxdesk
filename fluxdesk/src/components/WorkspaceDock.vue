<script setup lang="ts">
import { ref, computed } from 'vue';
import { useToolRegistry } from '@/stores/toolRegistry';
import { useTemplateStore } from '@/stores/templateStore';
import TemplateManager from './TemplateManager.vue';
import GlobalSettings from './GlobalSettings.vue';

const registry = useToolRegistry();
const templateStore = useTemplateStore();
const addMenuOpen = ref(false);
const templateManagerRef = ref<InstanceType<typeof TemplateManager> | null>(null);
const globalSettingsRef = ref<InstanceType<typeof GlobalSettings> | null>(null);

const toolTypes = computed(() =>
  templateStore.installedTemplates.map(t => ({
    type: t.id,
    label: t.name,
    icon: t.icon,
  }))
);

function onAddTool(type: string) {
  registry.addTool(type);
  addMenuOpen.value = false;
}

function toggleAutoArrange() {
  registry.toggleAutoArrange();
}

function onClearAll() {
  if (confirm('确定要清空当前工作区的所有卡片吗？此操作不可撤销。')) {
    registry.clearAll();
  }
}

function onCreateWorkspace() {
  const name = prompt('工作区名称：');
  if (name && name.trim()) {
    registry.createWorkspace(name.trim());
  }
}

function onDeleteWorkspace(id: string, name: string) {
  if (registry.workspaceCount <= 1) return;
  if (confirm(`确定要删除工作区「${name}」吗？`)) {
    registry.deleteWorkspace(id);
  }
}

function onSwitchWorkspace(id: string) {
  registry.switchWorkspace(id);
}

function onRenameWorkspace(id: string, currentName: string) {
  const name = prompt('新名称：', currentName);
  if (name && name.trim() && name.trim() !== currentName) {
    registry.renameWorkspace(id, name.trim());
  }
}

// Close add menu on outside click
function onAddMenuBlur(e: FocusEvent) {
  // Delay to allow click on menu items
  setTimeout(() => { addMenuOpen.value = false; }, 150);
}
</script>

<template>
  <div class="dock-wrapper">
    <div class="dock-bar">
      <!-- Left: Function area -->
      <div class="flex items-center gap-1 flex-shrink-0">
        <!-- Auto-arrange toggle -->
        <div class="dock-btn-wrap">
          <span class="dock-label">{{ registry.isAutoArrange ? '自动排列：开' : '自动排列：关（长按拖动）' }}</span>
          <button
            class="dock-btn"
            :class="registry.isAutoArrange ? 'dock-btn-active' : ''"
            @click="toggleAutoArrange"
          >
            <!-- Auto-arrange ON: grid icon -->
            <svg v-if="registry.isAutoArrange" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
            <!-- Auto-arrange OFF: move icon -->
            <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="5 9 2 12 5 15" />
              <polyline points="9 5 12 2 15 5" />
              <polyline points="15 19 12 22 9 19" />
              <polyline points="19 9 22 12 19 15" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <line x1="12" y1="2" x2="12" y2="22" />
            </svg>
          </button>
        </div>

        <!-- Add dropdown -->
        <div class="dock-btn-wrap">
          <span class="dock-label">添加卡片</span>
          <div class="relative">
            <button
              class="dock-btn dock-btn-add"
              @click="addMenuOpen = !addMenuOpen"
              @blur="onAddMenuBlur"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>
            <div
              v-if="addMenuOpen"
              class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-36 bg-bg-primary/95 backdrop-blur-xl border border-border/60 rounded-xl shadow-[0_16px_48px_rgba(0,0,0,0.22)] py-1.5 z-50"
            >
              <button
                v-for="tt in toolTypes"
                :key="tt.type"
                class="w-full flex items-center gap-2.5 px-3.5 py-2 text-sm text-text-primary/80 hover:bg-bg-secondary/60 transition-colors text-left"
                @mousedown.prevent="onAddTool(tt.type)"
              >
                <span class="text-base w-5 text-center">{{ tt.icon }}</span>
                <span>{{ tt.label }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Clear all -->
        <div class="dock-btn-wrap">
          <span class="dock-label">清空工作区</span>
          <button class="dock-btn" @click="onClearAll">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6l-2 14H7L5 6" />
              <path d="M10 11v6" />
              <path d="M14 11v6" />
            </svg>
          </button>
        </div>

        <!-- Templates -->
        <div class="dock-btn-wrap">
          <span class="dock-label">模板管理</span>
          <button class="dock-btn" @click="templateManagerRef?.openPanel()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="12" y1="18" x2="12" y2="12"/>
              <line x1="9" y1="15" x2="15" y2="15"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Divider -->
      <div class="w-px h-6 bg-border/30 mx-1.5 flex-shrink-0" />

      <!-- Right: Workspace management -->
      <div class="flex items-center gap-1 flex-shrink-0">
        <button
          v-for="ws in registry.workspaces"
          :key="ws.id"
          class="ws-tab"
          :class="ws.id === registry.activeWorkspaceId ? 'ws-tab-active' : ''"
          @click="onSwitchWorkspace(ws.id)"
          @dblclick="onRenameWorkspace(ws.id, ws.name)"
        >
          <svg v-if="ws.isDefault" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-40 flex-shrink-0">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <span class="text-xs font-medium truncate max-w-[100px]">{{ ws.name }}</span>
        </button>

        <div class="dock-btn-wrap">
          <span class="dock-label">新建工作区</span>
          <button
            class="dock-btn-icon"
            @click="onCreateWorkspace"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
        </div>

        <div class="dock-btn-wrap">
          <span class="dock-label">{{ registry.activeWorkspace?.isDefault ? '默认工作区不可删除' : registry.workspaceCount <= 1 ? '至少保留一个工作区' : '删除工作区' }}</span>
          <button
            class="dock-btn-icon dock-btn-delete"
            :class="registry.workspaceCount <= 1 || registry.activeWorkspace?.isDefault ? 'opacity-25 pointer-events-none' : ''"
            @click="onDeleteWorkspace(registry.activeWorkspaceId, registry.activeWorkspace?.name || '')"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Divider -->
      <div class="w-px h-6 bg-border/30 mx-1.5 flex-shrink-0" />

      <!-- Settings button -->
      <div class="dock-btn-wrap">
        <span class="dock-label">全局设置</span>
        <button
          class="dock-btn-icon"
          @click="globalSettingsRef?.open()"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
          </svg>
        </button>
      </div>
    </div>
    <TemplateManager ref="templateManagerRef" />
    <GlobalSettings ref="globalSettingsRef" />
  </div>
</template>

<style scoped>
.dock-wrapper {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  padding: 0 16px 10px;
  flex-shrink: 0;
}

.dock-bar {
  height: 46px;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 6px;
  background: var(--color-bg-secondary, rgba(245, 245, 247, 0.72));
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.18));
  border-radius: 18px;
  box-shadow:
    0 2px 12px rgba(0, 0, 0, 0.08),
    0 0.5px 0 0 rgba(255, 255, 255, 0.3) inset;
  flex-shrink: 0;
}

.dock-btn-wrap {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.dock-label {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  padding: 4px 10px;
  border-radius: 6px;
  background: var(--color-bg-primary, rgba(255, 255, 255, 0.92));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: var(--color-text-primary);
  font-size: 11px;
  font-weight: 500;
  line-height: 1.3;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.18s ease;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.15));
}

.dock-btn-wrap:hover .dock-label {
  opacity: 1;
}

.dock-btn {
  height: 34px;
  width: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border-radius: 12px;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.25, 0.1, 0.25, 1);
  white-space: nowrap;
}

.dock-btn:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-primary, rgba(255, 255, 255, 0.6));
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.dock-btn-active {
  color: #fff;
  background: var(--color-dai, #6366f1);
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.3);
}
.dock-btn-active:hover {
  color: #fff;
  background: var(--color-dai, #6366f1);
}

.dock-btn-add {
  color: var(--color-dai);
  width: 36px;
  height: 36px;
  border-radius: 14px;
}

.dock-btn-add:hover {
  color: #fff;
  background: var(--color-dai, #6366f1);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.dock-btn-icon {
  height: 30px;
  width: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.dock-btn-icon:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-primary, rgba(255, 255, 255, 0.5));
}

.dock-btn-delete:hover {
  color: var(--color-error, #ef4444);
  background: rgba(239, 68, 68, 0.08);
}

.ws-tab {
  height: 32px;
  display: inline-flex;
  align-items: center;
  padding: 0 12px;
  border-radius: 10px;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.ws-tab:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-primary, rgba(255, 255, 255, 0.5));
}

.ws-tab-active {
  color: var(--color-text-primary);
  background: var(--color-bg-primary, rgba(255, 255, 255, 0.7));
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
</style>
