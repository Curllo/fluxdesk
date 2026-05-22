import { defineStore } from 'pinia';
import { reactive, watch } from 'vue';
import { useTheme } from '@/composables/useTheme';
import { invoke } from '@tauri-apps/api/core';

export interface GeneralSettings {
  language: 'zh-CN' | 'en' | 'ja';
  autoLaunch: boolean;
  minimizeToTray: boolean;
  closeBehavior: 'minimize' | 'quit';
  autoCheckUpdate: boolean;
}

export interface AppearanceSettings {
  theme: 'light' | 'dark' | 'system';
  accentColor: 'indigo' | 'rose' | 'amber' | 'emerald';
  fontSize: 'small' | 'medium' | 'large';
  animations: boolean;
  glassmorphism: boolean;
}

export interface WorkspaceSettings {
  defaultColumns: number;
  defaultAutoArrange: boolean;
  cardGap: 'compact' | 'comfortable' | 'spacious';
  defaultCardHeight: number;
}

export interface ShortcutSettings {
  commandCenter: string;
  toggleSidebar: string;
}

export interface DebugSettings {
  logLevel: 'verbose' | 'debug' | 'info' | 'warn' | 'error';
  showFps: boolean;
}

export interface GlobalSettingsState {
  general: GeneralSettings;
  appearance: AppearanceSettings;
  workspace: WorkspaceSettings;
  shortcuts: ShortcutSettings;
  debug: DebugSettings;
}

const STORAGE_KEY = 'fluxdesk-global-settings-v1';

const DEFAULTS: GlobalSettingsState = {
  general: {
    language: 'zh-CN',
    autoLaunch: false,
    minimizeToTray: true,
    closeBehavior: 'minimize',
    autoCheckUpdate: true,
  },
  appearance: {
    theme: 'system',
    accentColor: 'indigo',
    fontSize: 'medium',
    animations: true,
    glassmorphism: true,
  },
  workspace: {
    defaultColumns: 4,
    defaultAutoArrange: true,
    cardGap: 'comfortable',
    defaultCardHeight: 240,
  },
  shortcuts: {
    commandCenter: 'Ctrl+K',
    toggleSidebar: 'Ctrl+B',
  },
  debug: {
    logLevel: 'info',
    showFps: false,
  },
};

export const useGlobalSettingsStore = defineStore('globalSettings', () => {
  const state = reactive<GlobalSettingsState>({ ...DEFAULTS });

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<GlobalSettingsState>;
        Object.assign(state, DEFAULTS, parsed);
      }
    } catch {
      // ignore parse errors, use defaults
    }
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // ignore storage errors
    }
  }

  async function syncToRust() {
    try {
      await invoke('set_general_settings', {
        settings: {
          language: state.general.language,
          auto_launch: state.general.autoLaunch,
          minimize_to_tray: state.general.minimizeToTray,
          close_behavior: state.general.closeBehavior,
          auto_check_update: state.general.autoCheckUpdate,
        },
      });
    } catch {
      // ignore
    }
  }

  async function syncAutoLaunch() {
    try {
      await invoke('set_auto_launch', { enabled: state.general.autoLaunch });
    } catch {
      // ignore
    }
  }

  async function loadFromRust() {
    try {
      const rustSettings = await invoke<{
        language: string;
        auto_launch: boolean;
        minimize_to_tray: boolean;
        close_behavior: string;
        auto_check_update: boolean;
      }>('get_general_settings');
      if (rustSettings) {
        state.general.language = rustSettings.language as any;
        state.general.autoLaunch = rustSettings.auto_launch;
        state.general.minimizeToTray = rustSettings.minimize_to_tray;
        state.general.closeBehavior = rustSettings.close_behavior as any;
        state.general.autoCheckUpdate = rustSettings.auto_check_update;
      }
    } catch {
      // ignore
    }
    try {
      const enabled = await invoke<boolean>('is_auto_launch_enabled');
      state.general.autoLaunch = enabled;
    } catch {
      // ignore
    }
  }

  async function init() {
    load();
    await loadFromRust();
    applyAppearance();
  }

  function applyAppearance() {
    const { applyAppearanceSettings } = useTheme();
    applyAppearanceSettings(state.appearance);
  }

  // Auto-persist on any change
  watch(
    () => state,
    () => {
      persist();
      syncToRust();
    },
    { deep: true, immediate: false }
  );

  return {
    state,
    init,
    load,
    persist,
    applyAppearance,
    syncAutoLaunch,
    loadFromRust,
  };
});
