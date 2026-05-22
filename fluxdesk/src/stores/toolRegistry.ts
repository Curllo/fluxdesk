import { defineStore } from 'pinia';
import type { ToolInstance, ToolType, WorkspaceData } from '@/types';
import { useTemplateStore } from './templateStore';
import { useGlobalSettingsStore } from './globalSettingsStore';

function getGridCols(): number {
  try {
    return useGlobalSettingsStore().state.workspace.defaultColumns;
  } catch {
    return 4;
  }
}

const STORAGE_KEY = 'fluxdesk-workspaces-v2';
const OLD_STORAGE_KEY = 'fluxdesk-tool-layout';

let nextId = 1;

function generateId(): string {
  return `t${nextId++}`;
}

function refreshNextId(tools: ToolInstance[]) {
  let max = 0;
  for (const t of tools) {
    const match = t.id.match(/^t(\d+)$/);
    if (match) {
      const n = parseInt(match[1], 10);
      if (n >= max) max = n;
    }
  }
  nextId = max + 1;
}

function generateWsId(): string {
  return `ws_${Date.now()}`;
}

function cellKey(row: number, col: number): string {
  return `${row},${col}`;
}

/**
 * Build an occupancy map of all tools except the one with excludeId.
 * Returns a Set of "row,col" strings for occupied cells.
 */
function buildOccupancy(tools: ToolInstance[], excludeId?: string): Set<string> {
  const occupied = new Set<string>();
  for (const t of tools) {
    if (t.id === excludeId) continue;
    for (let r = t.gridRow; r < t.gridRow + t.gridHeight; r++) {
      for (let c = t.gridColumn; c < t.gridColumn + t.gridWidth; c++) {
        occupied.add(cellKey(r, c));
      }
    }
  }
  return occupied;
}

export const useToolRegistry = defineStore('toolRegistry', {
  state: () => ({
    workspaces: [] as WorkspaceData[],
    activeWorkspaceId: '' as string,
    autoArrangeEnabled: true,
    _hydrated: false,
  }),

  getters: {
    tools(state): ToolInstance[] {
      const active = state.workspaces.find(w => w.id === state.activeWorkspaceId);
      return active?.tools ?? [];
    },

    activeWorkspace(state): WorkspaceData | undefined {
      return state.workspaces.find(w => w.id === state.activeWorkspaceId);
    },

    workspaceCount(state): number {
      return state.workspaces.length;
    },

    isAutoArrange(state): boolean {
      return state.autoArrangeEnabled;
    },

    getToolById: (state) => {
      return (id: string) => {
        const active = state.workspaces.find(w => w.id === state.activeWorkspaceId);
        return active?.tools.find(t => t.id === id);
      };
    },
  },

  actions: {
    init() {
      if (this._hydrated) return;

      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed.workspaces && Array.isArray(parsed.workspaces)) {
            this.workspaces = parsed.workspaces;
            this.activeWorkspaceId = parsed.activeWorkspaceId || this.workspaces[0]?.id || '';
            if (typeof parsed.autoArrangeEnabled === 'boolean') {
              this.autoArrangeEnabled = parsed.autoArrangeEnabled;
            } else {
              // First launch: use global settings default
              try {
                this.autoArrangeEnabled = useGlobalSettingsStore().state.workspace.defaultAutoArrange;
              } catch { /* ignore */ }
            }
          }
        }
      } catch { /* ignore */ }

      // Allow persist() calls from this point forward
      this._hydrated = true;

      // Fix nextId to avoid collisions with restored tools
      refreshNextId(this.tools);

      // Migration from old format
      if (this.workspaces.length === 0) {
        try {
          const old = localStorage.getItem(OLD_STORAGE_KEY);
          if (old) {
            const parsed = JSON.parse(old);
            if (Array.isArray(parsed) && parsed.length > 0) {
              this.workspaces.push({
                id: generateWsId(),
                name: 'Default',
                tools: parsed,
                createdAt: Date.now(),
                isDefault: true,
              });
              this.activeWorkspaceId = this.workspaces[0].id;
              this.persist();
              localStorage.removeItem(OLD_STORAGE_KEY);
            }
          }
        } catch { /* ignore */ }
      }

      // First launch: create default workspace with demo tools
      if (this.workspaces.length === 0 && !localStorage.getItem('fluxdesk-has-launched')) {
        const wsId = generateWsId();
        this.workspaces.push({
          id: wsId,
          name: 'Default',
          tools: [],
          createdAt: Date.now(),
          isDefault: true,
        });
        this.activeWorkspaceId = wsId;
        this.addTool('pomodoro', { duration: 25 });
        this.addTool('todo');
        localStorage.setItem('fluxdesk-has-launched', '1');
        this.persist();
      }

      // Safety net: always ensure a default workspace exists
      if (this.workspaces.length === 0) {
        const wsId = generateWsId();
        this.workspaces.push({
          id: wsId,
          name: 'Default',
          tools: [],
          createdAt: Date.now(),
          isDefault: true,
        });
        this.activeWorkspaceId = wsId;
        this.persist();
      }
      // If there are workspaces but none marked default, mark the first one
      if (!this.workspaces.some(w => w.isDefault)) {
        this.workspaces[0].isDefault = true;
      }
      // If active is invalid, switch to default
      if (!this.workspaces.some(w => w.id === this.activeWorkspaceId)) {
        this.activeWorkspaceId = this.workspaces.find(w => w.isDefault)?.id || this.workspaces[0].id;
      }
    },

    persist() {
      if (!this._hydrated) return;
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
          workspaces: this.workspaces,
          activeWorkspaceId: this.activeWorkspaceId,
          autoArrangeEnabled: this.autoArrangeEnabled,
        }));
      } catch { /* storage full */ }
    },

    // ── Tool CRUD (on active workspace) ──────────────────────────────────

    addTool(type: ToolType, config: Record<string, any> = {}): ToolInstance {
      const tools = this.tools;
      const occupied = buildOccupancy(tools);

      const templateStore = useTemplateStore();
      const tmpl = templateStore.getTemplateById(type);
      const w = tmpl?.defaultWidth ?? 1;
      const h = tmpl?.defaultHeight ?? 1;

      const cols = getGridCols();

      // Find first free cell
      let col = 1, row = 1, found = false;
      for (let r = 1; r <= 20 && !found; r++) {
        for (let c = 1; c <= cols && !found; c++) {
          if (c + w - 1 > cols) continue; // won't fit in remaining columns
          let fits = true;
          for (let dr = 0; dr < h && fits; dr++) {
            for (let dc = 0; dc < w && fits; dc++) {
              if (occupied.has(cellKey(r + dr, c + dc))) fits = false;
            }
          }
          if (fits) { row = r; col = c; found = true; }
        }
      }

      const tool: ToolInstance = {
        id: generateId(),
        type,
        title: config.title || type.charAt(0).toUpperCase() + type.slice(1),
        gridColumn: col,
        gridRow: row,
        gridWidth: Math.min(w, cols - col + 1),
        gridHeight: h,
        config,
      };

      tools.push(tool);
      if (this.autoArrangeEnabled) this.autoArrange();
      this.persist();
      return tool;
    },

    removeTool(id: string) {
      const tools = this.tools;
      const idx = tools.findIndex(t => t.id === id);
      if (idx !== -1) {
        tools.splice(idx, 1);
        this.persist();
      }
    },

    updateTool(id: string, partial: Partial<ToolInstance>) {
      const tool = this.getToolById(id);
      if (tool) {
        Object.assign(tool, partial);
        this.persist();
      }
    },

    /** Update only the config field of a tool. Safer than updateTool with whole-object replace. */
    updateToolConfig(id: string, config: Record<string, any>) {
      const tool = this.getToolById(id);
      if (!tool) return;
      if (JSON.stringify(tool.config) === JSON.stringify(config)) return;
      // Merge instead of replace to preserve any non-config properties
      Object.assign(tool.config, config);
      // Remove keys not in the new config
      for (const key of Object.keys(tool.config)) {
        if (!(key in config)) {
          delete tool.config[key];
        }
      }
      this.persist();
    },

    moveTool(id: string, gridColumn: number, gridRow: number) {
      const tool = this.getToolById(id);
      if (!tool) return;

      const cols = getGridCols();

      // Clamp to grid bounds
      const col = Math.max(1, Math.min(gridColumn, cols - tool.gridWidth + 1));
      const row = Math.max(1, gridRow);

      // Check target cells don't overlap other tools
      const occupied = buildOccupancy(this.tools, id);
      for (let r = row; r < row + tool.gridHeight; r++) {
        for (let c = col; c < col + tool.gridWidth; c++) {
          if (occupied.has(cellKey(r, c))) return;
        }
      }

      tool.gridColumn = col;
      tool.gridRow = row;
      this.persist();
    },

    /**
     * Resize a tool, clamped to avoid overlapping other tools.
     */
    resizeTool(id: string, gridWidth: number, gridHeight: number) {
      const tool = this.getToolById(id);
      if (!tool) return;

      const cols = getGridCols();
      const occupied = buildOccupancy(this.tools, id);

      // Clamp the requested values to grid bounds first
      const reqW = Math.max(1, Math.min(gridWidth, cols - tool.gridColumn + 1));
      const reqH = Math.max(1, gridHeight);

      // maxWidth: scan rightward using the REQUESTED new height
      let maxW = 1;
      for (let w = 1; w <= cols - tool.gridColumn + 1; w++) {
        let blocked = false;
        for (let r = tool.gridRow; r < tool.gridRow + reqH; r++) {
          for (let c = tool.gridColumn; c < tool.gridColumn + w; c++) {
            if (occupied.has(cellKey(r, c))) { blocked = true; break; }
          }
          if (blocked) break;
        }
        if (!blocked) maxW = w;
        else break;
      }

      // maxHeight: scan downward using the REQUESTED new width
      let maxH = 1;
      for (let h = 1; h <= 10; h++) {
        let blocked = false;
        for (let r = tool.gridRow; r < tool.gridRow + h; r++) {
          for (let c = tool.gridColumn; c < tool.gridColumn + reqW; c++) {
            if (occupied.has(cellKey(r, c))) { blocked = true; break; }
          }
          if (blocked) break;
        }
        if (!blocked) maxH = h;
        else break;
      }

      tool.gridWidth = Math.max(1, Math.min(reqW, maxW));
      tool.gridHeight = Math.max(1, Math.min(reqH, maxH));
      this.persist();
    },

    // ── Auto-arrange toggle ──

    toggleAutoArrange() {
      this.autoArrangeEnabled = !this.autoArrangeEnabled;
      if (this.autoArrangeEnabled) {
        this.autoArrange();
      }
      this.persist();
    },

    /**
     * Compact all tools in the active workspace (first-fit, top-left fill).
     */
    autoArrange() {
      const tools = this.tools;
      if (tools.length === 0) return;

      const cols = getGridCols();

      // Sort by current position
      const sorted = [...tools].sort((a, b) => a.gridRow - b.gridRow || a.gridColumn - b.gridColumn);
      const occupied = new Set<string>();

      for (const t of sorted) {
        let placed = false;
        for (let r = 1; r <= 20 && !placed; r++) {
          for (let c = 1; c <= cols && !placed; c++) {
            if (c + t.gridWidth - 1 > cols) continue;
            let fits = true;
            for (let dr = 0; dr < t.gridHeight && fits; dr++) {
              for (let dc = 0; dc < t.gridWidth && fits; dc++) {
                if (occupied.has(cellKey(r + dr, c + dc))) fits = false;
              }
            }
            if (fits) {
              t.gridRow = r;
              t.gridColumn = c;
              for (let dr = 0; dr < t.gridHeight; dr++) {
                for (let dc = 0; dc < t.gridWidth; dc++) {
                  occupied.add(cellKey(r + dr, c + dc));
                }
              }
              placed = true;
            }
          }
        }
      }

      this.persist();
    },

    clearAll() {
      const active = this.activeWorkspace;
      if (active) {
        active.tools = [];
        this.persist();
      }
    },

    // ── Workspace management ─────────────────────────────────────────────

    createWorkspace(name: string) {
      const ws: WorkspaceData = {
        id: generateWsId(),
        name: name || 'Untitled',
        tools: [],
        createdAt: Date.now(),
      };
      this.workspaces.push(ws);
      this.activeWorkspaceId = ws.id;
      this.persist();
    },

    deleteWorkspace(id: string) {
      if (this.workspaces.length <= 1) return;
      const ws = this.workspaces.find(w => w.id === id);
      if (ws?.isDefault) return;
      const idx = this.workspaces.findIndex(w => w.id === id);
      if (idx !== -1) {
        this.workspaces.splice(idx, 1);
        if (this.activeWorkspaceId === id) {
          this.activeWorkspaceId = this.workspaces.find(w => w.isDefault)?.id || this.workspaces[0]?.id || '';
        }
        this.persist();
      }
    },

    switchWorkspace(id: string) {
      if (this.workspaces.some(w => w.id === id)) {
        this.activeWorkspaceId = id;
        this.persist();
      }
    },

    renameWorkspace(id: string, name: string) {
      const ws = this.workspaces.find(w => w.id === id);
      if (ws) {
        ws.name = name;
        this.persist();
      }
    },
  },
});
