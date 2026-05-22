<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useTemplateStore } from '@/stores/templateStore';
import type { CardTemplate } from '@/types';

const templateStore = useTemplateStore();
const open = ref(false);
const activeTab = ref<'installed' | 'code'>('installed');
const selectedTemplate = ref<CardTemplate | null>(null);
const codeInput = ref('');
const codeError = ref('');

const customTemplates = computed(() => templateStore.customTemplates);
const hasCustomTemplates = computed(() => customTemplates.value.length > 0);

function openPanel() {
  templateStore.init();
  open.value = true;
  activeTab.value = 'installed';
  selectedTemplate.value = null;
  codeInput.value = '';
  codeError.value = '';
}

function closePanel() {
  open.value = false;
  selectedTemplate.value = null;
}

function viewTemplate(tpl: CardTemplate) {
  selectedTemplate.value = tpl;
}

function backToList() {
  selectedTemplate.value = null;
}

function deleteTemplate(id: string) {
  const tpl = templateStore.getTemplateById(id);
  if (!tpl) return;
  if (confirm(`确定要卸载模板「${tpl.name}」吗？此操作不可撤销。`)) {
    templateStore.uninstallTemplate(id);
    if (selectedTemplate.value?.id === id) {
      selectedTemplate.value = null;
    }
  }
}

function installFromCode() {
  codeError.value = '';
  const code = codeInput.value.trim();
  if (!code) {
    codeError.value = '请输入 Vue 组件代码';
    return;
  }

  try {
    // Extract template id from code if it defines one
    const idMatch = code.match(/id:\s*['"]([^'"]+)['"]/);
    const nameMatch = code.match(/name:\s*['"]([^'"]+)['"]/);
    const iconMatch = code.match(/icon:\s*['"]([^'"]+)['"]/);

    const id = idMatch?.[1] || `custom_${Date.now()}`;
    const name = nameMatch?.[1] || '自定义卡片';
    const icon = iconMatch?.[1] || '▪';

    templateStore.installTemplate({
      id,
      name,
      icon,
      accentColor: 'var(--color-dai)',
      defaultWidth: 1,
      defaultHeight: 1,
      vueCode: code,
      configSchema: {},
      version: '1.0.0',
      isBuiltIn: false,
      description: '手动安装的自定义模板',
      author: 'user',
    });

    codeInput.value = '';
    activeTab.value = 'installed';
  } catch (e: any) {
    codeError.value = e.message || '安装失败';
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && open.value) closePanel();
}

onMounted(() => document.addEventListener('keydown', onKeydown));
onUnmounted(() => document.removeEventListener('keydown', onKeydown));

defineExpose({ openPanel, closePanel });
</script>

<template>
  <Teleport to="body">
    <Transition name="tpl-fade">
      <div
        v-if="open"
        class="fixed inset-0 z-[100] flex items-center justify-center"
        @click.self="closePanel"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" />

        <!-- Panel -->
        <div
          class="relative w-[640px] max-h-[85vh] bg-bg-primary/95 backdrop-blur-xl rounded-2xl border border-border/60
                 shadow-[0_32px_64px_rgba(0,0,0,0.24)] flex flex-col overflow-hidden"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-5 py-4 border-b border-border/40">
            <h2 class="text-base font-semibold text-text-primary tracking-wide">卡片模板管理</h2>
            <button
              class="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-bg-secondary text-text-secondary/40 hover:text-text-primary transition-all"
              @click="closePanel"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <!-- Tabs -->
          <div class="flex items-center gap-0 px-5 border-b border-border/20">
            <button
              class="px-4 py-2.5 text-sm font-medium border-b-2 transition-all"
              :class="activeTab === 'installed' ? 'border-dai text-dai' : 'border-transparent text-text-secondary/60 hover:text-text-primary'"
              @click="activeTab = 'installed'; selectedTemplate = null"
            >已安装</button>
            <button
              class="px-4 py-2.5 text-sm font-medium border-b-2 transition-all"
              :class="activeTab === 'code' ? 'border-dai text-dai' : 'border-transparent text-text-secondary/60 hover:text-text-primary'"
              @click="activeTab = 'code'; selectedTemplate = null"
            >从代码安装</button>
          </div>

          <!-- Content: Installed -->
          <div v-if="activeTab === 'installed'" class="flex-1 overflow-y-auto px-5 py-4">
            <!-- Template detail view -->
            <div v-if="selectedTemplate" class="space-y-4">
              <button
                class="text-xs text-text-secondary/60 hover:text-text-primary flex items-center gap-1 transition-colors"
                @click="backToList"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
                返回列表
              </button>

              <div class="flex items-center gap-3">
                <span class="w-10 h-10 flex items-center justify-center text-xl rounded-xl bg-bg-secondary border border-border/30">
                  {{ selectedTemplate.icon }}
                </span>
                <div>
                  <p class="text-sm font-semibold text-text-primary">{{ selectedTemplate.name }}</p>
                  <p class="text-xs text-text-secondary/50">{{ selectedTemplate.id }} · {{ selectedTemplate.isBuiltIn ? '内置' : '自定义' }}</p>
                </div>
              </div>

              <div v-if="selectedTemplate.description" class="text-sm text-text-secondary/70 bg-bg-secondary/40 rounded-lg p-3">
                {{ selectedTemplate.description }}
              </div>

              <div class="space-y-2">
                <p class="text-xs font-medium text-text-secondary/50 uppercase tracking-wider">Vue 代码</p>
                <pre class="text-[11px] font-mono bg-bg-secondary/60 rounded-lg p-3 overflow-x-auto max-h-[300px] text-text-secondary/80">{{ selectedTemplate.vueCode || '(内置模板，代码内嵌在应用中)' }}</pre>
              </div>

              <div v-if="!selectedTemplate.isBuiltIn" class="flex justify-end pt-2">
                <button
                  class="px-4 py-2 text-xs font-medium rounded-lg bg-error/10 text-error hover:bg-error/20 transition-colors"
                  @click="deleteTemplate(selectedTemplate.id)"
                >卸载模板</button>
              </div>
            </div>

            <!-- Template list -->
            <div v-else class="space-y-2.5">
              <!-- Built-in section -->
              <p class="text-xs font-medium text-text-secondary/40 uppercase tracking-wider px-1">内置模板</p>
              <div
                v-for="tpl in templateStore.builtInTemplates"
                :key="tpl.id"
                class="group flex items-center gap-3 p-3 rounded-xl bg-bg-secondary/40 hover:bg-bg-secondary/80 border border-border/20 hover:border-border/40 transition-all cursor-pointer"
                @click="viewTemplate(tpl)"
              >
                <span class="w-9 h-9 flex items-center justify-center text-lg rounded-lg bg-bg-primary border border-border/30 flex-shrink-0">
                  {{ tpl.icon }}
                </span>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-text-primary truncate">{{ tpl.name }}</p>
                  <p class="text-xs text-text-secondary/50 truncate mt-0.5">{{ tpl.description }}</p>
                </div>
                <span class="text-[10px] text-text-secondary/30 px-2 py-0.5 rounded bg-bg-primary/60 flex-shrink-0">内置</span>
              </div>

              <!-- Custom section -->
              <template v-if="hasCustomTemplates">
                <p class="text-xs font-medium text-text-secondary/40 uppercase tracking-wider px-1 mt-4">自定义模板</p>
                <div
                  v-for="tpl in customTemplates"
                  :key="tpl.id"
                  class="group flex items-center gap-3 p-3 rounded-xl bg-bg-secondary/40 hover:bg-bg-secondary/80 border border-border/20 hover:border-border/40 transition-all cursor-pointer"
                  @click="viewTemplate(tpl)"
                >
                  <span class="w-9 h-9 flex items-center justify-center text-lg rounded-lg bg-bg-primary border border-border/30 flex-shrink-0">
                    {{ tpl.icon }}
                  </span>
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-text-primary truncate">{{ tpl.name }}</p>
                    <p class="text-xs text-text-secondary/50 truncate mt-0.5">{{ tpl.description || '自定义卡片模板' }}</p>
                  </div>
                  <button
                    class="w-7 h-7 flex items-center justify-center rounded-lg text-text-secondary/30 hover:text-error hover:bg-error/10 transition-all opacity-0 group-hover:opacity-100"
                    @click.stop="deleteTemplate(tpl.id)"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                    </svg>
                  </button>
                </div>
              </template>

              <div v-if="!hasCustomTemplates" class="flex flex-col items-center justify-center py-8 text-text-secondary/40">
                <p class="text-sm">还没有自定义模板</p>
                <p class="text-xs mt-1">通过 AI 助手创建，或在「从代码安装」标签页手动添加</p>
              </div>
            </div>
          </div>

          <!-- Content: Code install -->
          <div v-else class="flex-1 overflow-y-auto px-5 py-4 space-y-3">
            <p class="text-sm text-text-secondary/70">
              粘贴 Vue 3 组件代码以安装新卡片模板。代码需要包含 <code>__fluxdesk</code> 全局对象的使用。
            </p>
            <textarea
              v-model="codeInput"
              class="w-full h-[300px] px-3 py-2.5 text-xs font-mono bg-bg-secondary rounded-xl outline-none border border-border/40 focus:border-dai/50 resize-none text-text-primary placeholder:text-text-secondary/30"
              placeholder="const Component = {\n  setup() {\n    const { windowId, data, updateConfig } = __fluxdesk;\n    ...\n  },\n  template: `...`\n};\ncreateApp(Component).mount('#app');"
            />
            <p v-if="codeError" class="text-xs text-error">{{ codeError }}</p>
            <button
              class="w-full py-2.5 text-sm font-medium rounded-xl bg-dai text-white hover:bg-dai-hover active:scale-[0.98] transition-all"
              @click="installFromCode"
            >安装模板</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.tpl-fade-enter-active,
.tpl-fade-leave-active {
  transition: opacity 0.2s ease;
}
.tpl-fade-enter-from,
.tpl-fade-leave-to {
  opacity: 0;
}
</style>
