import { defineStore } from 'pinia';
import { ref } from 'vue';

export interface AppSettings {
  theme: 'light' | 'dark' | 'system';
  shortcut: string;
  autoStartAi: boolean;
  typingSpeed: number;
  llmProvider: string;
  llmModel: string;
  apiKey?: string;
  tokenLimit: number;
}

const DEFAULT_SETTINGS: AppSettings = {
  theme: 'system',
  shortcut: 'CommandOrControl+K',
  autoStartAi: false,
  typingSpeed: 30,
  llmProvider: 'openai',
  llmModel: 'gpt-4o-mini',
  tokenLimit: 100000,
};

export const useSettingStore = defineStore('setting', () => {
  const settings = ref<AppSettings>({ ...DEFAULT_SETTINGS });

  function updateSetting<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    settings.value[key] = value;
  }

  function updateSettings(partial: Partial<AppSettings>) {
    settings.value = { ...settings.value, ...partial };
  }

  function resetSettings() {
    settings.value = { ...DEFAULT_SETTINGS };
  }

  return {
    settings,
    updateSetting,
    updateSettings,
    resetSettings,
  };
});
