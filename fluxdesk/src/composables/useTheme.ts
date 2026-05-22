import { ref, watch } from 'vue';
import type { AppearanceSettings } from '@/stores/globalSettingsStore';

type ThemeMode = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'fluxdesk-theme';

const themeMode = ref<ThemeMode>('system');
const isDark = ref(false);

const ACCENT_MAP: Record<string, { dai: string; hover: string; light: string }> = {
  indigo: { dai: '#6366f1', hover: '#5558e0', light: 'rgba(99,102,241,0.15)' },
  rose:   { dai: '#f43f5e', hover: '#e11d48', light: 'rgba(244,63,94,0.15)' },
  amber:  { dai: '#f59e0b', hover: '#d97706', light: 'rgba(245,158,11,0.15)' },
  emerald:{ dai: '#10b981', hover: '#059669', light: 'rgba(16,185,129,0.15)' },
};

function getSystemDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function applyTheme() {
  const dark = themeMode.value === 'system' ? getSystemDark() : themeMode.value === 'dark';
  isDark.value = dark;
  document.documentElement.classList.toggle('dark', dark);
}

function applyAccentColor(colorKey: string) {
  const colors = ACCENT_MAP[colorKey] || ACCENT_MAP.indigo;
  const root = document.documentElement;
  root.style.setProperty('--color-dai', colors.dai);
  root.style.setProperty('--color-dai-hover', colors.hover);

  // Update selection color
  const lightSel = colors.light;
  const darkSel = colors.dai + '59'; // 35% opacity in hex

  // Update selection styles dynamically
  let style = document.getElementById('fluxdesk-accent-style');
  if (!style) {
    style = document.createElement('style');
    style.id = 'fluxdesk-accent-style';
    document.head.appendChild(style);
  }
  style.textContent = `
    ::selection { background: ${lightSel}; }
    .dark ::selection { background: ${darkSel}; }
    :focus-visible { outline-color: ${colors.dai}; }
  `;
}

function applyFontSize(size: string) {
  const sizes: Record<string, string> = {
    small: '14px',
    medium: '16px',
    large: '18px',
  };
  document.documentElement.style.fontSize = sizes[size] || sizes.medium;
}

function applyAnimations(enabled: boolean) {
  document.documentElement.classList.toggle('no-animations', !enabled);
}

function applyGlassmorphism(enabled: boolean) {
  document.documentElement.classList.toggle('no-glassmorphism', !enabled);
}

export function applyAppearanceSettings(settings: AppearanceSettings) {
  setTheme(settings.theme);
  applyAccentColor(settings.accentColor);
  applyFontSize(settings.fontSize);
  applyAnimations(settings.animations);
  applyGlassmorphism(settings.glassmorphism);
}

function init() {
  const saved = localStorage.getItem(STORAGE_KEY) as ThemeMode | null;
  if (saved && ['light', 'dark', 'system'].includes(saved)) {
    themeMode.value = saved;
  }
  applyTheme();

  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (themeMode.value === 'system') {
      applyTheme();
    }
  });
}

function setTheme(mode: ThemeMode) {
  themeMode.value = mode;
  localStorage.setItem(STORAGE_KEY, mode);
  applyTheme();
}

watch(themeMode, applyTheme);

export function useTheme() {
  return { themeMode, isDark, init, setTheme, applyAppearanceSettings };
}
