import { defineStore } from 'pinia';
import type { CardTemplate } from '@/types';

const STORAGE_KEY = 'fluxdesk-card-templates-v2';
const OLD_STORAGE_KEY = 'fluxdesk-templates-v1';

function generateId(): string {
  return `tpl_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

/** Built-in templates metadata — actual components are loaded via defineAsyncComponent */
const BUILT_IN_TEMPLATES: CardTemplate[] = [
  {
    id: 'pomodoro',
    name: '番茄钟',
    icon: '⏱',
    accentColor: 'var(--color-error)',
    defaultWidth: 1,
    defaultHeight: 1,
    vueCode: '',
    configSchema: { duration: { type: 'number', default: 25 } },
    version: '1.0.0',
    isBuiltIn: true,
    description: '专注计时器，默认25分钟',
    createdAt: 0,
    author: 'system',
  },
  {
    id: 'todo',
    name: '待办列表',
    icon: '☐',
    accentColor: 'var(--color-dai)',
    defaultWidth: 1,
    defaultHeight: 2,
    vueCode: '',
    configSchema: { todos: { type: 'array', default: [] } },
    version: '1.0.0',
    isBuiltIn: true,
    description: '任务管理列表',
    createdAt: 0,
    author: 'system',
  },
  {
    id: 'note',
    name: '笔记',
    icon: '✎',
    accentColor: 'var(--color-warning)',
    defaultWidth: 1,
    defaultHeight: 1,
    vueCode: '',
    configSchema: { title: { type: 'string', default: '' }, content: { type: 'string', default: '' } },
    version: '1.0.0',
    isBuiltIn: true,
    description: '快速笔记',
    createdAt: 0,
    author: 'system',
  },
  {
    id: 'calendar',
    name: '日历',
    icon: '📅',
    accentColor: 'var(--color-success)',
    defaultWidth: 2,
    defaultHeight: 1,
    vueCode: '',
    configSchema: {},
    version: '1.0.0',
    isBuiltIn: true,
    description: '月历查看',
    createdAt: 0,
    author: 'system',
  },
  {
    id: 'weather',
    name: '天气',
    icon: '🌤',
    accentColor: 'var(--color-info)',
    defaultWidth: 2,
    defaultHeight: 2,
    vueCode: '',
    configSchema: {},
    version: '1.0.0',
    isBuiltIn: true,
    description: '天气查询，支持城市搜索，5分钟自动刷新',
    createdAt: 0,
    author: 'system',
  },
];

export const useTemplateStore = defineStore('templateStore', {
  state: () => ({
    templates: [] as CardTemplate[],
    _hydrated: false,
  }),

  getters: {
    installedTemplates(state): CardTemplate[] {
      return state.templates;
    },
    builtInTemplates(state): CardTemplate[] {
      return state.templates.filter(t => t.isBuiltIn);
    },
    customTemplates(state): CardTemplate[] {
      return state.templates.filter(t => !t.isBuiltIn);
    },
    getTemplateById: (state) => {
      return (id: string) => state.templates.find(t => t.id === id);
    },
  },

  actions: {
    init() {
      if (this._hydrated) return;

      // Clean up old storage key from previous agent
      try {
        localStorage.removeItem(OLD_STORAGE_KEY);
      } catch { /* ignore */ }

      // Start with built-in templates
      this.templates = [...BUILT_IN_TEMPLATES];

      // Load custom templates from storage
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed)) {
            // Merge: built-ins + custom saved templates
            const custom = parsed.filter((t: CardTemplate) => !t.isBuiltIn);
            this.templates = [...BUILT_IN_TEMPLATES, ...custom];
          }
        }
      } catch { /* ignore */ }

      this._hydrated = true;
    },

    persist() {
      if (!this._hydrated) return;
      try {
        const toSave = this.templates.filter(t => !t.isBuiltIn);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
      } catch { /* storage full */ }
    },

    installTemplate(template: Omit<CardTemplate, 'createdAt'> & { id?: string }): CardTemplate {
      const tmpl: CardTemplate = {
        ...template as CardTemplate,
        id: template.id || generateId(),
        createdAt: Date.now(),
      };
      // Remove any existing template with same id
      const idx = this.templates.findIndex(t => t.id === tmpl.id);
      if (idx !== -1) {
        if (this.templates[idx].isBuiltIn) {
          throw new Error(`Cannot overwrite built-in template: ${tmpl.id}`);
        }
        this.templates.splice(idx, 1);
      }
      this.templates.push(tmpl);
      this.persist();
      return tmpl;
    },

    uninstallTemplate(id: string): boolean {
      const idx = this.templates.findIndex(t => t.id === id);
      if (idx === -1) return false;
      if (this.templates[idx].isBuiltIn) return false;
      this.templates.splice(idx, 1);
      this.persist();
      return true;
    },

    updateTemplate(id: string, partial: Partial<CardTemplate>) {
      const t = this.getTemplateById(id);
      if (!t) return;
      if (t.isBuiltIn) return;
      Object.assign(t, partial);
      this.persist();
    },
  },
});
