<script setup lang="ts">
import { useGlobalSettingsStore } from '@/stores/globalSettingsStore';
import { invoke } from '@tauri-apps/api/core';

const store = useGlobalSettingsStore();
const general = store.state.general;

async function toggleAutoLaunch() {
  general.autoLaunch = !general.autoLaunch;
  await store.syncAutoLaunch();
}

async function toggleMinimizeToTray() {
  general.minimizeToTray = !general.minimizeToTray;
}

async function setCloseBehavior(behavior: 'minimize' | 'quit') {
  general.closeBehavior = behavior;
}

async function toggleAutoCheckUpdate() {
  general.autoCheckUpdate = !general.autoCheckUpdate;
}

async function checkUpdateNow() {
  try {
    const version = await invoke<string | null>('check_for_update');
    if (version) {
      alert(`发现新版本: ${version}`);
    } else {
      alert('当前已是最新版本');
    }
  } catch {
    alert('检查更新失败');
  }
}
</script>

<template>
  <div class="space-y-5">
    <div class="text-xs font-medium text-text-secondary uppercase tracking-wide">通用</div>

    <!-- 语言 -->
    <div>
      <label class="block text-xs text-text-secondary mb-1.5">界面语言</label>
      <select
        v-model="general.language"
        class="w-full px-3 py-2 text-sm bg-bg-secondary rounded-[8px] outline-none border border-border/40 focus:border-dai/50 focus:bg-bg-primary text-text-primary transition-all"
      >
        <option value="zh-CN">简体中文</option>
        <option value="en">English</option>
        <option value="ja">日本語</option>
      </select>
    </div>

    <!-- 开机自启动 -->
    <div class="flex items-center justify-between text-sm">
      <div>
        <div class="text-text-primary">开机自启动</div>
        <div class="text-[11px] text-text-secondary/60 mt-0.5">登录时自动启动 FluxDesk</div>
      </div>
        <button
          class="relative w-9 h-5 rounded-full transition-colors duration-200 flex-shrink-0"
          :class="general.autoLaunch ? 'bg-dai' : 'bg-border'"
          @click="toggleAutoLaunch"
        >
          <span
            class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all duration-200"
            :style="{ transform: general.autoLaunch ? 'translateX(16px)' : 'translateX(0)' }"
          />
        </button>
    </div>

    <!-- 最小化到托盘 -->
    <div class="flex items-center justify-between text-sm">
      <div>
        <div class="text-text-primary">最小化到托盘</div>
        <div class="text-[11px] text-text-secondary/60 mt-0.5">关闭窗口时最小化到系统托盘</div>
      </div>
        <button
          class="relative w-9 h-5 rounded-full transition-colors duration-200 flex-shrink-0"
          :class="general.minimizeToTray ? 'bg-dai' : 'bg-border'"
          @click="toggleMinimizeToTray"
        >
          <span
            class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all duration-200"
            :style="{ transform: general.minimizeToTray ? 'translateX(16px)' : 'translateX(0)' }"
          />
        </button>
    </div>

    <!-- 关闭窗口行为 -->
    <div>
      <label class="block text-xs text-text-secondary mb-2">关闭窗口行为</label>
      <div class="flex gap-2">
        <button
          class="flex-1 px-3 py-2 text-sm rounded-[8px] border transition-all"
          :class="general.closeBehavior === 'minimize' ? 'border-dai bg-dai/10 text-dai' : 'border-border/40 text-text-secondary hover:text-text-primary hover:border-border'"
          @click="setCloseBehavior('minimize')"
        >
          最小化
        </button>
        <button
          class="flex-1 px-3 py-2 text-sm rounded-[8px] border transition-all"
          :class="general.closeBehavior === 'quit' ? 'border-dai bg-dai/10 text-dai' : 'border-border/40 text-text-secondary hover:text-text-primary hover:border-border'"
          @click="setCloseBehavior('quit')"
        >
          退出
        </button>
      </div>
    </div>

    <!-- 自动检查更新 -->
    <div class="flex items-center justify-between text-sm">
      <div>
        <div class="text-text-primary">自动检查更新</div>
        <div class="text-[11px] text-text-secondary/60 mt-0.5">启动时自动检查新版本</div>
      </div>
      <button
        class="relative w-9 h-5 rounded-full transition-colors duration-200 flex-shrink-0"
        :class="general.autoCheckUpdate ? 'bg-dai' : 'bg-border'"
        @click="toggleAutoCheckUpdate"
      >
        <span
          class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all duration-200"
          :style="{ transform: general.autoCheckUpdate ? 'translateX(16px)' : 'translateX(0)' }"
        />
      </button>
    </div>

    <!-- 手动检查更新 -->
    <div class="pt-2">
      <button
        class="w-full px-3 py-2 text-sm bg-bg-secondary hover:bg-border text-text-secondary hover:text-text-primary rounded-[8px] transition-all"
        @click="checkUpdateNow"
      >
        立即检查更新
      </button>
    </div>
  </div>
</template>
