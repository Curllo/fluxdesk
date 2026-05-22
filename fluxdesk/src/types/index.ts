export type WindowType = string;
export type ToolType = string;

export interface ToolInstance {
  id: string;
  type: ToolType;
  title: string;
  gridColumn: number;
  gridRow: number;
  gridWidth: number;
  gridHeight: number;
  config: Record<string, any>;
}

export interface WorkspaceData {
  id: string;
  name: string;
  tools: ToolInstance[];
  createdAt: number;
  isDefault?: boolean;
}

export interface ServiceConfig {
  port: number;
  apiToken: string;
  pid: number;
}

export interface ToolCallInfo {
  id: string;
  name: string;
  arguments: string;
}

export interface ToolResultInfo {
  name: string;
  toolCallId: string;
  success: boolean;
  result: string;
  error?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: ToolCallInfo[];
  toolResults?: ToolResultInfo[];
  model?: string;
  tokensUsed?: number;
  latencyMs?: number;
  createdAt: string;
}

export interface SSEEvent {
  event: 'message' | 'tool_call' | 'tool_result' | 'confirm' | 'error' | 'done';
  data: Record<string, any>;
}

export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface CardTemplate {
  id: string;
  name: string;
  icon: string;
  accentColor: string;
  defaultWidth: number;
  defaultHeight: number;
  vueCode: string;
  configSchema: Record<string, any>;
  version: string;
  isBuiltIn: boolean;
  description?: string;
  createdAt: number;
  author?: string;
}

export interface ConfirmAction {
  id: string;
  action: 'install_template' | 'uninstall_template' | 'delete_tool';
  title: string;
  message: string;
  params: Record<string, any>;
  toolCallId: string;
  createdAt: number;
}
