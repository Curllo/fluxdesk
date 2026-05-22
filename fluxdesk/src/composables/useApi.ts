import { invoke } from '@tauri-apps/api/core';
import type { ServiceConfig } from '@/types';

let _config: ServiceConfig | null = null;
let _configPromise: Promise<ServiceConfig | null> | null = null;

async function getConfig(): Promise<ServiceConfig | null> {
  if (_config) return _config;
  if (_configPromise) return _configPromise;

  _configPromise = (async () => {
    for (let i = 0; i < 3; i++) {
      try {
        _config = await invoke<ServiceConfig>('get_ai_service_config');
        return _config;
      } catch {
        if (i < 2) await new Promise(r => setTimeout(r, 800));
      }
    }
    // After 3 failed attempts, clear the promise so next call can retry
    _configPromise = null;
    return null;
  })();

  return _configPromise;
}

/** Force refresh cached service config (e.g. after sidecar restart). */
export function clearApiConfig() {
  _config = null;
  _configPromise = null;
}

/** Re-fetch service config, clearing cache first. */
async function refreshConfigOnce(): Promise<ServiceConfig | null> {
  _config = null;
  _configPromise = null;
  return getConfig();
}

function getHeaders(token: string) {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

async function fetchWithRetry(path: string, options?: RequestInit, retries = 2): Promise<any> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    const config = await getConfig();
    if (!config) {
      if (attempt < retries) {
        await new Promise(r => setTimeout(r, 800));
        continue;
      }
      throw new Error('AI service not available');
    }

    const url = `http://127.0.0.1:${config.port}${path}`;
    try {
      const hasBody = options?.body != null;
      const resp = await fetch(url, {
        ...options,
        headers: {
          Authorization: `Bearer ${config.apiToken}`,
          ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
          ...options?.headers,
        },
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${text}`);
      }
      return resp.json();
    } catch (e: any) {
      // Only retry on network-level errors (connection refused, DNS failure, etc.).
      // HTTP 4xx/5xx are application-level errors — retrying with the same config
      // won't fix them, so propagate immediately.
      const isNetworkError = e instanceof TypeError || e.message?.includes('Failed to fetch');
      if (isNetworkError && attempt < retries) {
        console.warn(`[api] Network error (attempt ${attempt + 1}), refreshing config...`, e.message);
        await refreshConfigOnce();
        continue;
      }
      throw e;
    }
  }
}

export async function apiGet(path: string) {
  return fetchWithRetry(path);
}

export async function apiPost(path: string, body: Record<string, any>) {
  return fetchWithRetry(path, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function apiPatch(path: string, body: Record<string, any>) {
  const config = await getConfig();
  if (!config) throw new Error('AI service not available');
  const resp = await fetch(`http://127.0.0.1:${config.port}${path}`, {
    method: 'PATCH',
    headers: getHeaders(config.apiToken),
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

export async function apiDelete(path: string) {
  const config = await getConfig();
  if (!config) throw new Error('AI service not available');
  const resp = await fetch(`http://127.0.0.1:${config.port}${path}`, {
    method: 'DELETE',
    headers: getHeaders(config.apiToken),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

/** Re-fetch service config from Rust (use after restart). */
export async function refreshConfig(): Promise<ServiceConfig | null> {
  _config = null;
  _configPromise = null;
  return getConfig();
}
