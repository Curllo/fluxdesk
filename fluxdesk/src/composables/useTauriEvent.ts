import { listen, type UnlistenFn } from '@tauri-apps/api/event';
import { onMounted, onUnmounted } from 'vue';

export function useTauriEvent<T = any>(
  eventName: string,
  handler: (payload: T) => void
) {
  let unlisten: UnlistenFn | null = null;

  onMounted(async () => {
    unlisten = await listen<T>(eventName, (event) => {
      handler(event.payload);
    });
  });

  onUnmounted(() => {
    if (unlisten) {
      unlisten();
      unlisten = null;
    }
  });
}
