import { emit, listen, type UnlistenFn } from '@tauri-apps/api/event';

export interface FluxActivity {
  source: string;       // window type: 'todo' | 'note' | 'pomodoro' | 'calendar'
  action: string;       // 'created' | 'updated' | 'completed' | 'deleted' | 'saved'
  label: string;        // human-readable summary, e.g. "待办: 买牛奶"
  detail?: string;      // extra context
  timestamp: string;    // ISO 8601
}

const ACTIVITY_EVENT = 'flux-activity';

export function useActivityBus() {
  function emitActivity(activity: Omit<FluxActivity, 'timestamp'>) {
    emit(ACTIVITY_EVENT, {
      ...activity,
      timestamp: new Date().toISOString(),
    } as FluxActivity).catch(() => {});
  }

  function onActivity(handler: (activity: FluxActivity) => void): Promise<UnlistenFn> {
    return listen<FluxActivity>(ACTIVITY_EVENT, (event) => {
      handler(event.payload);
    });
  }

  return { emitActivity, onActivity };
}
