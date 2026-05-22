<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';

const props = defineProps<{
  vueCode: string;
  windowId: string;
  data: Record<string, any>;
}>();

const emit = defineEmits<{
  'update-config': [config: Record<string, any>];
}>();

const mountRef = ref<HTMLDivElement | null>(null);
const mountId = `flux-card-${props.windowId}`;
let vueApp: any = null;
let vueLoading = false;
let vueLoaded = false;
let vueLoadQueue: (() => void)[] = [];
let isRendering = false;
let lastSnapshot = '';

function ensureVueLoaded(): Promise<void> {
  if (vueLoaded) return Promise.resolve();
  if (vueLoading) {
    return new Promise((resolve) => { vueLoadQueue.push(resolve); });
  }
  vueLoading = true;
  return new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://registry.npmmirror.com/vue/3.5.13/files/dist/vue.global.js';
    script.onload = () => {
      vueLoaded = true;
      vueLoading = false;
      resolve();
      vueLoadQueue.forEach(fn => fn());
      vueLoadQueue = [];
    };
    script.onerror = () => {
      vueLoading = false;
      resolve();
    };
    document.head.appendChild(script);
  });
}

function sanitizeCode(code: string): string {
  let cleaned = code.trim();
  
  // Replace const/let Component with var Component
  cleaned = cleaned.replace(/\b(const|let)\s+Component\b/g, 'var Component');
  
  // Remove everything after the last mount() call
  const lastMount = cleaned.lastIndexOf('mount(');
  if (lastMount !== -1) {
    const semi = cleaned.indexOf(';', lastMount);
    if (semi !== -1) {
      cleaned = cleaned.substring(0, semi + 1);
    }
  }
  
  // If multiple "var Component = {" exist, keep only the last one
  const pattern = /var\s+Component\s*=\s*\{/g;
  const matches: number[] = [];
  let m: RegExpExecArray | null;
  while ((m = pattern.exec(cleaned)) !== null) {
    matches.push(m.index);
  }
  if (matches.length > 1) {
    const lastComp = matches[matches.length - 1];
    const lastBrace = cleaned.lastIndexOf('};');
    if (lastBrace !== -1 && lastBrace > lastComp) {
      cleaned = cleaned.substring(lastComp, lastBrace + 2) + `\ncreateApp(Component).mount("#${mountId}");`;
    }
  }
  
  // If no mount call, append one
  if (!cleaned.includes('mount(')) {
    cleaned += `\ncreateApp(Component).mount("#${mountId}");`;
  }
  
  // Replace #app references with our mount id
  cleaned = cleaned.replace(/mount\s*\(\s*['"]#app['"]\s*\)/g, `mount("#${mountId}")`);
  cleaned = cleaned.replace(/getElementById\s*\(\s*['"]app['"]\s*\)/g, `getElementById("${mountId}")`);
  cleaned = cleaned.replace(/querySelector\s*\(\s*['"]#app['"]\s*\)/g, `querySelector("#${mountId}")`);
  
  return cleaned;
}

function renderCard() {
  const snapshot = props.vueCode + '::' + JSON.stringify(props.data);
  if (snapshot === lastSnapshot) return;
  if (isRendering) return;

  lastSnapshot = snapshot;
  isRendering = true;

  if (!mountRef.value) { isRendering = false; return; }

  // Destroy previous app
  if (vueApp) {
    try { vueApp.unmount(); } catch {}
    vueApp = null;
  }

  const vueCode = props.vueCode || '';
  if (!vueCode) { isRendering = false; return; }

  const container = mountRef.value;
  container.innerHTML = '<div style="padding:20px;text-align:center;font-size:12px;color:var(--color-text-secondary);opacity:0.5;">卡片加载中...</div>';
  
  ensureVueLoaded().then(() => {
    if (!mountRef.value) return;
    
    const V = (window as any).Vue;
    if (!V) {
      container.innerHTML = '<div style="padding:12px;color:#ef4444;font-size:11px;white-space:pre-wrap;">Vue library failed to load.</div>';
      return;
    }
    
    let code: string;
    try {
      code = sanitizeCode(vueCode);
    } catch (e: any) {
      container.innerHTML = `<div style="padding:12px;color:#ef4444;font-size:11px;white-space:pre-wrap;">Sanitize error: ${e.message}</div>`;
      return;
    }
    
    // Replace __fluxdesk references with a unique window property
    // so AI code's setup() closure can access it via global scope
    const fluxGlobalKey = `__fluxdesk_${mountId}`;
    code = code.replace(/__fluxdesk/g, `window['${fluxGlobalKey}']`);
    
    const { createApp, reactive, ref: vRef, computed, watch: vWatch, onMounted: vOnMounted, onUnmounted: vOnUnmounted, h } = V;
    (window as any)[fluxGlobalKey] = {
      windowId: props.windowId,
      data: reactive(JSON.parse(JSON.stringify(props.data))),
      updateConfig(cfg: Record<string, any>) {
        emit('update-config', cfg);
      }
    };
    
    try {
      eval(code);
    } catch (e: any) {
      container.innerHTML = `<div style="padding:12px;color:#ef4444;font-size:11px;white-space:pre-wrap;">ERROR: ${e.message}</div>`;
      delete (window as any)[fluxGlobalKey];
      return;
    }
    
    delete (window as any)[fluxGlobalKey];
    
    // Check if mount happened
    const appEl = container.querySelector(`#${mountId}`);
    if (appEl && appEl.children.length === 0 && appEl.innerHTML.trim() === '') {
      container.innerHTML = `<div style="padding:12px;color:#f59e0b;font-size:11px;white-space:pre-wrap;">Code executed but component did not mount.<br>Make sure the code ends with createApp(...).mount("#app")</div>`;
    }
  }).catch(() => {}).finally(() => {
    isRendering = false;
  });
}

onMounted(() => {
  renderCard();
});

watch(() => [props.vueCode, JSON.stringify(props.data)], () => {
  renderCard();
});

onUnmounted(() => {
  if (vueApp) {
    try { vueApp.unmount(); } catch {}
    vueApp = null;
  }
});
</script>

<template>
  <div ref="mountRef" :id="mountId" class="w-full h-full overflow-auto min-h-0" />
</template>