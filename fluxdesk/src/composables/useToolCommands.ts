import { invoke } from '@tauri-apps/api/core';
import { useToolRegistry } from '@/stores/toolRegistry';
import { useTemplateStore } from '@/stores/templateStore';

export interface CommandResult {
  success: boolean;
  message: string;
  error?: string;
}

export function useToolCommands() {
  const registry = useToolRegistry();
  const templateStore = useTemplateStore();

  function normalizeParams(action: string, params: Record<string, any>): { action: string; params: Record<string, any> } {
    let normalizedAction = action;
    if (action === 'create_window') normalizedAction = 'create_tool';

    if (params.tool_type === undefined && params.type !== undefined) {
      params.tool_type = params.type;
    }

    if (params.config === undefined) {
      const configKeys = ['duration', 'content', 'title', 'label'];
      const config: Record<string, any> = {};
      for (const key of configKeys) {
        if (params[key] !== undefined) config[key] = params[key];
      }
      if (Object.keys(config).length > 0) params.config = config;
    }

    return { action: normalizedAction, params };
  }

  async function executeCommand(rawAction: string, rawParams: Record<string, any>): Promise<CommandResult> {
    try {
      const { action, params } = normalizeParams(rawAction, rawParams);

      switch (action) {
        // ── Workspace tool commands ──────────────────────
        case 'create_tool': {
          const type = params.tool_type || params.type;
          if (!type) return { success: false, message: '缺少工具类型', error: 'tool_type is required' };
          const tool = registry.addTool(type, params.config || {});
          return { success: true, message: `已创建 ${tool.type} 工具「${tool.title}」` };
        }

        case 'update_tool': {
          const id = params.tool_id || params.id;
          if (!id) return { success: false, message: '缺少工具 ID', error: 'tool_id is required' };
          const tool = registry.getToolById(id);
          if (!tool) return { success: false, message: `工具 ${id} 不存在`, error: 'tool not found' };
          registry.updateTool(id, {
            config: { ...tool.config, ...(params.config || {}) },
            ...(params.title ? { title: params.title } : {}),
          });
          return { success: true, message: `已更新工具「${tool.title}」` };
        }

        case 'delete_tool': {
          const id = params.tool_id || params.id;
          if (!id) return { success: false, message: '缺少工具 ID', error: 'tool_id is required' };
          const tool = registry.getToolById(id);
          if (!tool) return { success: false, message: `工具 ${id} 不存在`, error: 'tool not found' };
          registry.removeTool(id);
          return { success: true, message: `已删除工具「${tool.title}」` };
        }

        case 'move_tool': {
          const id = params.tool_id || params.id;
          if (!id) return { success: false, message: '缺少工具 ID', error: 'tool_id is required' };
          const tool = registry.getToolById(id);
          if (!tool) return { success: false, message: `工具 ${id} 不存在`, error: 'tool not found' };
          registry.moveTool(id, params.column || 1, params.row || 1);
          if (params.width !== undefined) registry.resizeTool(id, params.width, params.height || 1);
          else if (params.height !== undefined) registry.resizeTool(id, tool.gridWidth, params.height);
          return { success: true, message: `已移动工具「${tool.title}」` };
        }

        // ── Template commands ──
        case 'install_template': {
          if (!params.template_id) return { success: false, message: '缺少模板 ID', error: 'template_id is required' };
          if (!params.name) return { success: false, message: '缺少模板名称', error: 'name is required' };
          if (!params.vue_code) return { success: false, message: '缺少 Vue 组件代码', error: 'vue_code is required. Please describe what the card should look like.' };
          const tpl = templateStore.installTemplate({
            id: params.template_id,
            name: params.name,
            icon: params.icon || '▪',
            accentColor: params.accent_color || 'var(--color-dai)',
            defaultWidth: params.default_width || 1,
            defaultHeight: params.default_height || 1,
            vueCode: params.vue_code,
            configSchema: params.config_schema || {},
            version: params.version || '1.0.0',
            isBuiltIn: false,
            description: params.description || '',
            author: 'ai',
          });
          // Fill initial_config defaults from config_schema if not provided
          if (!params.initial_config && params.config_schema) {
            const defaults: Record<string, any> = {};
            for (const [key, schema] of Object.entries(params.config_schema)) {
              if (typeof schema === 'object' && schema !== null && 'default' in schema) {
                defaults[key] = schema.default;
              }
            }
            params.initial_config = Object.keys(defaults).length > 0 ? defaults : {};
          }
          const tool = registry.addTool(tpl.id, params.initial_config || {});
          return { success: true, message: `已安装模板「${tpl.name}」并创建卡片「${tool.title}」` };
        }

        case 'uninstall_template': {
          const success = templateStore.uninstallTemplate(params.template_id);
          return success
            ? { success: true, message: `已卸载模板「${params.template_id}」` }
            : { success: false, message: '模板不存在或是内置模板', error: 'template not found or built-in' };
        }

        case 'list_templates': {
          const list = templateStore.installedTemplates.map(t => `- ${t.icon} ${t.name} (${t.id})`);
          return { success: true, message: `已安装模板(${list.length}个)：\n${list.join('\n')}` };
        }

        // ── Legacy Tauri commands ──
        case 'manage_todo': {
          await invoke('manage_todo', {
            action: params.action,
            content: params.content,
            todo_id: params.todo_id,
          });
          return { success: true, message: '待办已处理' };
        }

        case 'set_reminder': {
          await invoke('set_reminder', {
            title: params.title,
            time: params.time,
            repeat: params.repeat || 'once',
          });
          return { success: true, message: '提醒已设置' };
        }

        default:
          return { success: false, message: `未知操作: ${action}`, error: `unknown action: ${action}` };
      }
    } catch (e: any) {
      return { success: false, message: `执行失败: ${e.message}`, error: e.message };
    }
  }

  function getWorkspaceContext(): string {
    const tools = registry.tools;
    const tpls = templateStore.installedTemplates;

    let context = '';
    if (tools.length === 0) {
      context += '当前工作区是空的，没有任何工具。\n';
    } else {
      const lines = tools.map(t =>
        `- ${t.title} (${t.type}, id: ${t.id}, 位置: 第${t.gridRow}行第${t.gridColumn}列, 大小: ${t.gridWidth}x${t.gridHeight})`
      );
      context += `当前工作区有以下工具：\n${lines.join('\n')}\n`;
    }

    context += `\n已安装的卡片模板(${tpls.length}个)：\n`;
    for (const t of tpls) {
      context += `- ${t.icon} ${t.name} (${t.id})${t.isBuiltIn ? ' [内置]' : ''}\n`;
    }

    context += `\n你可以使用以下命令操作工具：\n1. create_tool — 创建新工具 (参数: tool_type, config)\n2. update_tool — 修改工具配置 (参数: tool_id, config, title)\n3. delete_tool — 删除工具 (参数: tool_id)\n4. move_tool — 移动工具位置或大小 (参数: tool_id, column, row, width, height)`;
    context += `\n5. install_template — 安装新卡片模板 (参数: template_id, name, vue_code, icon, accent_color, default_width, default_height)\n6. uninstall_template — 卸载模板 (参数: template_id)\n7. list_templates — 列出已安装模板`;
    return context;
  }

  return { executeCommand, getWorkspaceContext };
}
