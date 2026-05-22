# 🚀 FluxDesk v1.1 完整技术架构设计规范（生产就绪版）

> **版本**: v1.1.0-production  
> **状态**: 架构冻结（Architecture Freeze）  
> **目标**: 提供可直接进入开发的工程蓝图，包含配置示例、接口契约与构建脚本。

---

## 一、项目核心概述

### 1.1 项目定位

FluxDesk 是一款 **AI-Native 跨平台桌面工具系统**。它通过自然语言交互（LUI）打破传统 GUI 的层级限制，为用户提供"随叫随到、用完即走"的智能化桌面工作环境。

**核心价值主张：**
- **零干扰**: 全局快捷键唤起，不抢占当前工作流焦点
- **意图驱动**: 自然语言直接转化为结构化操作，消除点击路径
- **本地优先**: 数据默认落盘本地，AI 能力支持离线/云端双模
- **原子化应用**: 每个浮动窗口都是独立生命周期，支持自由组合

### 1.2 核心交互逻辑

| 交互模式 | 触发方式 | 典型场景 |
|---------|---------|---------|
| 全局唤起 | `Ctrl/Cmd + K` | 呼出命令中心，输入自然语言指令 |
| 意图执行 | 回车发送 | "帮我记下明早九点的会议" → 生成置顶浮动笔记 |
| 快捷指令 | `/` 前缀 | `/pomo 25` 直接创建 25 分钟番茄钟 |
| 悬浮操作 | 鼠标悬停 | 窗口边缘显示折叠/置顶/关闭控件 |

### 1.3 非功能性需求（NFR）

| 指标 | 目标值 | 测试方法 |
|------|--------|---------|
| 冷启动时间 | ≤ 800ms（Rust 端） | 从点击图标到命令中心可输入 |
| Python Sidecar 首启 | ≤ 3s（懒加载） | 首次触发 AI 功能到 SSE 连接建立 |
| 窗口创建延迟 | ≤ 150ms | 从指令解析完成到窗口渲染 |
| 内存占用 | 空闲 ≤ 120MB；AI 对话 ≤ 350MB | `top` / 任务管理器 |
| 离线可用性 | 100% 基础功能（非 AI） | 断网环境下测试窗口 CRUD |
| 多显示器支持 | 最多 4 屏，热插拔自动恢复 | 物理拔插显示器验证 |

---

## 二、技术架构与栈

### 2.1 核心技术栈

| 层级 | 技术选型 | 版本约束 | 核心作用 |
|------|---------|---------|---------|
| **系统宿主** | Tauri | ^2.0.0 | 多窗口管理、全局快捷键、系统级 API 安全访问 |
| **视图层** | Vue | ^3.4.0 | UI 渲染，组合式 API 管理复杂窗口状态 |
| **语言** | TypeScript | ^5.4.0 | 全链路类型安全 |
| **样式引擎** | Tailwind CSS | ^3.4.0 | 原子化样式，响应式布局 |
| **组件库** | shadcn-vue | latest | 无样式 headless 组件，保证设计一致性 |
| **状态管理** | Pinia | ^2.1.0 | 窗口内状态缓存（非跨窗口同步） |
| **逻辑大脑** | FastAPI | ^0.110.0 | AI 意图识别、长文本处理、SSE 流式推送 |
| **模型网关** | LiteLLM | ^1.0.0 | 统一 LLM 调用接口，支持云端/本地切换 |
| **ORM/迁移** | SQLAlchemy + Alembic | ^2.0.0 / ^1.13.0 | 数据库模型与版本迁移 |
| **存储层** | SQLite | 3.35+ | 本地轻量级关系数据库 |
| **构建工具** | Vite | ^5.0.0 | 前端构建与 HMR |

### 2.2 逻辑通信架构（Sidecar 模式）

系统采用 **Sidecar 模式**：Tauri (Rust) 作为宿主进程，负责拉起 Python 后端进程。前端 Vue 通过 HTTP/SSE 与 Python 通信处理 AI 逻辑，通过 Tauri Command 与 Rust 通信处理系统级操作。

```
┌─────────────────────────────────────────────────────────────┐
│                      User Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Command     │  │  Floating    │  │  Settings    │      │
│  │  Center      │  │  Window A    │  │  Panel       │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          │ Tauri IPC       │ Tauri IPC       │ Tauri IPC
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   Tauri Host (Rust)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ WindowManager│  │ SidecarMgr   │  │ Security     │      │
│  │ (WindowRegistry│  │ (Python进程) │  │ (Token/Key)  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │ HTTP/SSE        │              │
│         │                 ▼                 │              │
│         │         ┌──────────────┐          │              │
│         └────────►│ Python AI    │◄─────────┘              │
│                   │ Service      │                          │
│                   │ (FastAPI)    │                          │
│                   └──────┬───────┘                          │
│                          │ SQLite                           │
│                          ▼                                  │
│                   ┌──────────────┐                          │
│                   │ Local DB     │                          │
│                   │ (AppData)    │                          │
│                   └──────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、通信架构与协议规范

### 3.1 三条核心通信链路

| 链路 | 协议 | 地址 | 典型场景 |
|------|------|------|---------|
| Vue ↔ Rust | Tauri IPC (`invoke`) | 内部通道 | 创建窗口、设置置顶、读写凭据、获取屏幕信息 |
| Vue ↔ Python | HTTP / SSE | `127.0.0.1:<随机端口>` | 对话消息流、意图解析、笔记/任务 CRUD |
| Rust ↔ Python | HTTP (内部) | `127.0.0.1:9595` | 意图执行快捷通路、健康检查、密钥注入 |

### 3.2 Vue ↔ Python 通信协议

#### 3.2.1 基础配置获取

前端启动时从 Rust 获取 Python 服务配置：

```typescript
// 前端初始化
interface ServiceConfig {
  port: number;           // Python HTTP 服务端口
  apiToken: string;       // JWT-style Bearer Token
  pid: number;            // Python 进程 ID
}

const config = await invoke<ServiceConfig>('get_ai_service_config');
// 后续所有请求自动附加 Header: Authorization: Bearer <apiToken>
```

#### 3.2.2 SSE 流式消息格式

**连接建立：**

```http
GET /api/v1/chat/stream HTTP/1.1
Host: 127.0.0.1:{port}
Authorization: Bearer {token}
Accept: text/event-stream
```

**事件类型定义：**

| 事件名 | 数据格式 | 说明 |
|--------|---------|------|
| `message` | `{"delta": "..."}` | 正常文本流片 |
| `tool_call` | `{"name": "...", "arguments": "{...}"}` | Function Calling 开始 |
| `tool_result` | `{"result": "...", "success": true}` | 工具执行结果 |
| `confirm` | `{"action": "...", "params": {}, "confidence": 0.72}` | 低置信度意图，需用户确认 |
| `error` | `{"code": "...", "message": "..."}` | 服务端错误 |
| `done` | `{}` | 流结束标记 |

**SSE 消息示例：**

```text
event: message
data: {"delta": "好的"}

event: tool_call
data: {"name": "create_window", "arguments": "{\"type\":\"pomodoro\",\"duration\":25}"}

event: tool_result
data: {"result": "window_created", "window_id": "win_abc123", "success": true}

event: done
data: {}
```

#### 3.2.3 REST API 规范

**基础响应包装：**

```json
{
  "code": 200,
  "message": "success",
  "data": { }
}
```

**错误码定义：**

| 错误码 | HTTP Status | 含义 | 前端处理 |
|--------|------------|------|---------|
| `AUTH_INVALID` | 401 | Token 无效或过期 | 请求 Rust 刷新 token，重试一次 |
| `RATE_LIMIT` | 429 | LLM API 限流 | 展示"服务繁忙，请稍后再试" |
| `INTENT_PARSE_FAIL` | 422 | 意图解析失败 | 降级到本地规则引擎，提示用户 |
| `SIDECAR_UNAVAILABLE` | 503 | Python 服务未就绪 | 展示"AI 服务启动中" |
| `VALIDATION_ERROR` | 400 | 请求参数校验失败 | 高亮错误字段 |

### 3.3 Rust ↔ Python 内部通信

Rust 暴露受保护的本地回环端口（`127.0.0.1:9595`），供 Python 直接调用系统命令。

**安全机制：**
- 端口启动时随机生成 `internal_token`，与 `api_token` 隔离
- 仅接受 `127.0.0.1` 来源请求
- 端点白名单制，仅开放以下接口：

| 端点 | 方法 | 功能 | 请求体 |
|------|------|------|--------|
| `/internal/window/create` | POST | 创建窗口 | `{"type": "...", "config": {}}` |
| `/internal/window/destroy` | POST | 销毁窗口 | `{"id": "..."}` |
| `/internal/window/focus` | POST | 聚焦窗口 | `{"id": "..."}` |
| `/internal/health` | GET | 健康检查 | - |
| `/internal/notify` | POST | 系统通知 | `{"title": "...", "body": "..."}` |

**Python 调用示例：**

```python
import os
import httpx

INTERNAL_TOKEN = os.environ["FLUXDESK_INTERNAL_TOKEN"]
RUST_PORT = os.environ.get("FLUXDESK_RUST_PORT", "9595")

async def create_window(window_type: str, config: dict):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"http://127.0.0.1:{RUST_PORT}/internal/window/create",
            headers={"Authorization": f"Bearer {INTERNAL_TOKEN}"},
            json={"type": window_type, "config": config}
        )
        return resp.json()
```

### 3.4 Sidecar 生命周期管理

#### 3.4.1 启动流程

```rust
// Rust 伪代码
fn start_sidecar() -> Result<SidecarHandle, Error> {
    // 1. 生成随机端口与双 Token
    let port = find_free_port();
    let api_token = generate_secure_token(32);
    let internal_token = generate_secure_token(32);

    // 2. 配置环境变量
    let envs = HashMap::from([
        ("FLUXDESK_PORT", port.to_string()),
        ("FLUXDESK_API_TOKEN", api_token.clone()),
        ("FLUXDESK_INTERNAL_TOKEN", internal_token.clone()),
        ("FLUXDESK_RUST_PORT", "9595".to_string()),
        ("FLUXDESK_APP_DIR", app_data_dir()),
    ]);

    // 3. 拉起 Python 可执行文件
    let child = Command::new_sidecar("fluxdesk-ai")
        .envs(envs)
        .spawn()?;

    // 4. 健康检查轮询（最多 10 秒）
    wait_for_healthy(port, Duration::from_secs(10)).await?;

    // 5. 注册到 WindowRegistry，向前端广播配置
    broadcast_service_config(port, api_token);

    Ok(SidecarHandle { child, port, api_token, internal_token })
}
```

#### 3.4.2 懒加载策略

Python 服务**仅在首次触发以下事件时启动**：
- 用户首次在命令中心发送消息
- 用户首次调用需要 AI 解析的快捷指令
- 应用启动时若检测到"开机自启 AI 服务"配置为 true

**Idle 休眠机制：**
- 连续 30 分钟无 AI 交互，Python 进程进入休眠（释放 LLM 模型缓存内存，保留 HTTP 服务）
- 休眠期间内存占用目标 ≤ 80MB
- 下次请求时自动唤醒，唤醒延迟 ≤ 500ms

#### 3.4.3 守护与自愈

| 场景 | 检测方式 | 恢复策略 |
|------|---------|---------|
| Python 进程崩溃 | Rust `try_wait()` 轮询 | 指数退避重启：1s → 2s → 4s → 8s → 16s → 30s（上限） |
| SSE 连接断开 | 前端 `EventSource.onerror` | 前端自动重连，间隔 1s，最多 10 次；超过则提示"AI 服务重连中" |
| 健康检查失败 | Rust 轮询 `/internal/health` | 3 次失败后判定为死亡，触发重启流程 |
| 端口冲突 | 启动时 `bind()` 失败 | 自动递增端口重试，最多 5 次 |

#### 3.4.4 优雅关闭

```rust
fn graceful_shutdown(sidecar: &mut SidecarHandle) {
    // 1. 发送 SIGTERM
    sidecar.child.kill(Signal::Term).ok();

    // 2. 等待持久化完成（最多 5 秒）
    match timeout(Duration::from_secs(5), sidecar.child.wait()) {
        Ok(_) => log::info!("Sidecar exited gracefully"),
        Err(_) => {
            // 3. 超时强制结束
            sidecar.child.kill(Signal::Kill).ok();
            log::warn!("Sidecar force killed");
        }
    }

    // 4. 立即失效所有 token
    revoke_tokens(sidecar.api_token, sidecar.internal_token);
}
```

---

## 四、核心模块深度设计

### 4.1 全局指令中心 (Global Chat)

#### 4.1.1 视觉规范

**设计系统：新禅意极简主义**

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-ink` | `#2C2C2C` | 主文字色 |
| `--color-paper` | `#FAF9F7` | 背景色（素白） |
| `--color-dai` | `#4A5F6F` | 品牌黛色（强调、按钮） |
| `--color-mist` | `rgba(255,255,255,0.72)` | 毛玻璃底色 |
| `--blur-backdrop` | `blur(20px) saturate(180%)` | 背景模糊 |
| `--radius-lg` | `16px` | 大圆角（窗口） |
| `--radius-md` | `12px` | 中圆角（卡片） |
| `--radius-sm` | `8px` | 小圆角（按钮、输入框） |
| `--shadow-float` | `0 8px 32px rgba(0,0,0,0.08)` | 浮动阴影 |
| `--ease-elastic` | `cubic-bezier(0.68, -0.55, 0.265, 1.55)` | 弹性动效 |
| `--ease-smooth` | `cubic-bezier(0.4, 0, 0.2, 1)` | 平滑过渡 |

**布局参数：**
- 命令中心窗口尺寸：宽 680px，高 520px（可拉伸，最小 480×360）
- 输入框高度：56px（单行）/ 自适应（多行，最大 120px）
- 消息气泡最大宽度：85%
- 边距系统：4px 基栅格，主要使用 8/12/16/24/32px

#### 4.1.2 输入增强

| 功能 | 触发 | 行为 |
|------|------|------|
| 换行 | `Shift + Enter` | 输入框内换行，不发送 |
| 快捷指令 | `/` | 弹出指令面板，支持方向键选择、Tab 补全 |
| 历史记录 | `↑` | 浏览历史输入（仅当输入框为空或光标在首行） |
| 取消生成 | `Esc` | AI 生成中按 Esc 中断 SSE 连接 |
| 粘贴图片 | `Ctrl+V` | 支持粘贴剪贴板图片，自动上传并插入 Markdown 图片语法 |

#### 4.1.3 状态反馈

- **AI 思考中**：输入框下边框呈现 1.5px 宽度的脉冲呼吸灯（黛色 → 透明，2s 周期）
- **流式输出**：文字逐字显示，打字机效果，速度 30ms/字（可配置）
- **工具执行**：显示"正在创建番茄钟..."的骨架屏卡片，执行完成后替换为结果卡片

### 4.2 智能浮动窗口系统 (Floating Window)

#### 4.2.1 窗口状态接口

```typescript
interface FloatingWindow {
  id: string;                    // 全局唯一，win_{uuid}
  type: WindowType;              // 'todo' | 'pomodoro' | 'note' | 'calendar' | 'custom'
  position: { x: number; y: number };
  size: { width: number; height: number };
  isAlwaysOnTop: boolean;
  isMinimized: boolean;          // 最小化到系统托盘/边缘
  displayIndex: number;          // 所在显示器索引
  zIndex: number;                // 层级，由 Rust 分配
  opacity: number;               // 0.4 - 1.0，支持半透明
  data: Record<string, any>;     // 应用特定数据
  createdAt: string;
  updatedAt: string;
}

type WindowType = 'todo' | 'pomodoro' | 'note' | 'calendar' | 'custom';
```

#### 4.2.2 多窗口状态同步架构

**Rust 状态中枢（唯一真相源）：**

```rust
// Rust: WindowRegistry 核心结构
use std::collections::HashMap;
use tauri::Window;

struct WindowRegistry {
    windows: HashMap<String, WindowMeta>,
    z_stack: Vec<String>,           // Z-Index 栈，越后越上层
    focus_id: Option<String>,       // 当前焦点窗口
}

struct WindowMeta {
    id: String,
    window: Window,
    position: PhysicalPosition<i32>,
    size: PhysicalSize<u32>,
    display_index: u32,
    always_on_top: bool,
}

impl WindowRegistry {
    // 创建窗口 → 广播 window-created
    // 销毁窗口 → 广播 window-destroyed
    // 焦点变更 → 广播 window-focused，调整 z_stack
    // 位置变更 → 广播 window-moved（拖动结束后触发）
}
```

**前端事件监听：**

```typescript
// Vue composable: useWindowState.ts
import { listen } from '@tauri-apps/api/event';

export function useWindowState() {
  onMounted(() => {
    // 监听 Rust 广播的全局窗口事件
    listen('window-state-changed', (event) => {
      const { action, payload } = event.payload;
      switch (action) {
        case 'created':
        case 'moved':
        case 'resized':
        case 'focused':
        case 'destroyed':
          // 覆盖 Pinia 本地缓存，Rust 为唯一真相源
          windowStore.syncFromRust(payload);
          break;
      }
    });
  });
}
```

#### 4.2.3 Z-Index 与焦点管理

- **层级规则**：命令中心（Chat）始终在最上层（`zIndex = MAX`），浮动窗口按最近聚焦顺序排列
- **焦点切换**：点击窗口标题栏或调用 `invoke('focus_window', { id })`，Rust 将该窗口移至 `z_stack` 末尾并置顶
- **不抢夺输入焦点**：工具类窗口（番茄钟、笔记）设置 `focus: false`，避免打断用户当前在 IDE/编辑器中的输入

#### 4.2.4 边缘吸附与多显示器

**边缘吸附算法：**

```rust
fn snap_to_edge(position: &mut PhysicalPosition<i32>, screen: &Monitor) {
    let threshold = 20; // 像素
    let screen_width = screen.size().width as i32;
    let screen_height = screen.size().height as i32;

    // 左边缘
    if position.x.abs() <= threshold {
        position.x = 0;
    }
    // 右边缘
    else if (screen_width - (position.x + window_width)).abs() <= threshold {
        position.x = screen_width - window_width;
    }
    // 上下边缘同理...
}
```

**多显示器处理：**
- 记录每个窗口的 `display_index`（基于 `tauri::Monitor` 的 `name()` 哈希）
- 显示器拔插时，Rust 监听 `display-changed` 系统事件
- 若窗口所在显示器消失，将其迁移至主显示器，坐标按比例缩放：

```rust
new_x = (old_x / old_screen_width) * new_screen_width;
new_y = (old_y / old_screen_height) * new_screen_height;
```

### 4.3 AI 意图解析引擎

#### 4.3.1 三层解析策略

```
用户输入
    │
    ▼
┌─────────────────┐
│ 第一层：本地规则引擎 │ ◄── 离线可用，0ms 延迟
│ (Keyword + Regex) │
└────────┬────────┘
         │ 未匹配
         ▼
┌─────────────────┐
│ 第二层：本地轻量模型 │ ◄── 可选，Ollama 本地运行
│ (Ollama 7B/14B)  │
└────────┬────────┘
         │ 未启用/失败
         ▼
┌─────────────────┐
│ 第三层：云端 LLM   │ ◄── LiteLLM 网关，Function Calling
│ (GPT-4/Claude 3) │
└────────┬────────┘
         ▼
    结构化 JSON 指令
```

#### 4.3.2 本地规则引擎

**规则定义格式：**

```yaml
# rules/create_window.yaml
rules:
  - name: "create_pomodoro"
    priority: 100
    patterns:
      - regex: '(?:打开|创建|来个|开始).{0,3}(?:番茄钟|番茄|pomodoro)'
      - regex: '(?:pomo|番茄).{0,2}(\d+).{0,2}(?:分钟|min)'
    action:
      type: "create_window"
      params:
        type: "pomodoro"
        duration: "{{ $1 | default: 25 }}"

  - name: "create_todo"
    priority: 90
    patterns:
      - regex: '(?:记下|添加|创建).{0,3}(?:待办|todo|任务)'
    action:
      type: "create_window"
      params:
        type: "todo"
        title: "{{ extract_title(input) }}"
```

**引擎实现要点：**
- 规则按优先级排序，首个匹配即返回
- 支持正则捕获组提取参数
- 内置常用函数：`extract_title()`, `parse_time()`, `default()`
- 规则热更新：支持运行时重新加载 YAML 配置

#### 4.3.3 LLM Function Calling Schema

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "create_window",
        "description": "在桌面上创建一个浮动工具窗口",
        "parameters": {
          "type": "object",
          "properties": {
            "type": {
              "type": "string",
              "enum": ["todo", "pomodoro", "note", "calendar"],
              "description": "窗口类型"
            },
            "position": {
              "type": "object",
              "properties": {
                "x": {"type": "number", "description": "X坐标，不传则自动居中"},
                "y": {"type": "number", "description": "Y坐标，不传则自动居中"}
              }
            },
            "size": {
              "type": "object",
              "properties": {
                "width": {"type": "number", "default": 400},
                "height": {"type": "number", "default": 300}
              }
            },
            "data": {
              "type": "object",
              "description": "窗口初始化数据，如番茄钟时长、笔记内容等"
            }
          },
          "required": ["type"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "manage_todo",
        "description": "管理待办事项",
        "parameters": {
          "type": "object",
          "properties": {
            "action": {
              "type": "string",
              "enum": ["add", "complete", "delete", "list"],
              "description": "操作类型"
            },
            "content": {"type": "string", "description": "待办内容"},
            "todo_id": {"type": "string", "description": "待办ID，complete/delete时需要"}
          },
          "required": ["action"]
        }
      }
    }
  ]
}
```

#### 4.3.4 系统提示词模板（System Prompt）

```markdown
你是 FluxDesk 的智能助手，负责将用户的自然语言指令解析为结构化操作。

## 核心原则
1. 优先使用工具调用（Function Calling），不要仅返回文字描述
2. 如果用户意图不明确，使用 `ask_clarification` 工具询问
3. 涉及删除、覆盖、退出等破坏性操作时，必须请求确认
4. 时间解析：将"明早九点"转换为 ISO 8601 格式（基于当前时间 {{ current_time }}）

## 可用工具
- create_window: 创建浮动窗口
- manage_todo: 管理待办
- set_reminder: 设置提醒
- search_notes: 搜索笔记（RAG）
- ask_clarification: 请求用户澄清

## 响应风格
- 简洁直接，避免冗长解释
- 操作成功后简要确认
- 中文语境优先使用中文回复
```

#### 4.3.5 降级策略

| 场景 | 降级行为 | 用户提示 |
|------|---------|---------|
| LLM API 超时（>10s） | 转本地规则引擎 | "网络较慢，已切换至本地模式" |
| LLM API 返回错误 | 转本地规则引擎 + 记录日志 | "智能服务暂不可用，已为您执行基础指令" |
| 规则引擎未匹配 | 返回澄清卡片 | "您可以尝试说：创建一个25分钟的番茄钟" |
| 置信度 < 0.85 | 推送确认卡片 | "您是要创建番茄钟吗？（是/否）" |
| 完全离线且无本地模型 | 仅支持规则引擎覆盖的指令 | "离线模式：支持基础窗口操作" |

---

## 五、数据层设计

### 5.1 数据库 Schema（SQLite）

```sql
-- 窗口布局持久化
CREATE TABLE windows (
    id TEXT PRIMARY KEY,                    -- win_{uuid}
    type TEXT NOT NULL CHECK(type IN ('todo', 'pomodoro', 'note', 'calendar', 'custom')),
    position_x REAL NOT NULL DEFAULT 100,
    position_y REAL NOT NULL DEFAULT 100,
    width REAL NOT NULL DEFAULT 400,
    height REAL NOT NULL DEFAULT 300,
    always_on_top INTEGER NOT NULL DEFAULT 0,
    is_minimized INTEGER NOT NULL DEFAULT 0,
    display_index INTEGER NOT NULL DEFAULT 0,
    opacity REAL NOT NULL DEFAULT 1.0,
    data_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 对话历史
CREATE TABLE messages (
    id TEXT PRIMARY KEY,                    -- msg_{uuid}
    window_id TEXT NOT NULL,                -- 关联窗口，命令中心为 'global'
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls TEXT,                        -- JSON，Function Calling 记录
    model TEXT,                             -- 使用的模型名称
    tokens_used INTEGER,                    -- token 消耗
    latency_ms INTEGER,                     -- 响应延迟
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (window_id) REFERENCES windows(id) ON DELETE CASCADE
);

-- 应用特定数据（键值存储）
CREATE TABLE app_data (
    id TEXT PRIMARY KEY,
    window_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (window_id) REFERENCES windows(id) ON DELETE CASCADE,
    UNIQUE(window_id, key)
);

-- 待办事项（Todo 应用专用）
CREATE TABLE todos (
    id TEXT PRIMARY KEY,
    window_id TEXT NOT NULL,
    content TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 1 CHECK(priority IN (0,1,2)), -- 0低 1中 2高
    due_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (window_id) REFERENCES windows(id) ON DELETE CASCADE
);

-- 番茄钟记录（Pomodoro 应用专用）
CREATE TABLE pomodoro_sessions (
    id TEXT PRIMARY KEY,
    window_id TEXT NOT NULL,
    duration INTEGER NOT NULL,              -- 计划时长（分钟）
    actual_duration INTEGER,                -- 实际时长
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'interrupted')),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    FOREIGN KEY (window_id) REFERENCES windows(id) ON DELETE CASCADE
);

-- 用户配置
CREATE TABLE user_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 索引优化
CREATE INDEX idx_messages_window_id ON messages(window_id, created_at);
CREATE INDEX idx_app_data_window_key ON app_data(window_id, key);
CREATE INDEX idx_todos_window_id ON todos(window_id, completed);
```

### 5.2 数据迁移策略

使用 **Alembic** 管理数据库版本：

```python
# alembic/env.py 关键配置
from sqlalchemy import create_engine
from server.models.base import Base

target_metadata = Base.metadata

def run_migrations_offline():
    url = os.environ.get("FLUXDESK_DATABASE_URL", "sqlite:///app.db")
    context.configure(url=url, target_metadata=target_metadata)
    # ...

# 迁移脚本命名规范：{序号}_{描述}.py，如 001_init_schema.py
```

**迁移原则：**
- 应用启动时自动执行 `alembic upgrade head`
- 向后兼容：新版本必须能读取旧版本数据
- 破坏性变更需分两步：先添加新列（兼容读）→ 后续版本移除旧列

### 5.3 备份与恢复

- **自动备份**：每次应用退出时，若数据有变更，自动复制 `app.db` 到 `backups/app.db.{timestamp}`
- **保留策略**：保留最近 10 个备份，自动清理旧备份
- **手动导出**：设置面板提供"导出数据包"（zip 包含 db + 日志 + 配置）
- **导入恢复**：支持选择备份文件恢复，恢复前自动备份当前数据

---

## 六、安全与隐私架构

### 6.1 密钥管理链路

```
用户输入 API Key
    │
    ▼
前端 Vue ──Tauri IPC──► Rust 宿主
                            │
                            ▼
                    ┌───────────────┐
                    │ OS Keychain   │  ← macOS: Keychain
                    │ CredentialMgr │  ← Windows: Credential Manager
                    │ SecretService │  ← Linux: libsecret
                    └───────────────┘
                            │
                            ▼
                    启动时读取，注入环境变量
                            │
                            ▼
                    Python Sidecar 进程
                    （环境变量，进程结束后擦除）
```

**密钥擦除机制：**

```rust
// Rust: 子进程启动后，从当前进程环境变量中移除敏感信息
std::env::remove_var("FLUXDESK_API_TOKEN");
std::env::remove_var("FLUXDESK_INTERNAL_TOKEN");
// Python: 使用后从 os.environ 中删除
```

### 6.2 Token 生命周期管理

| Token 类型 | 生成时机 | 有效期 | 失效时机 |
|-----------|---------|--------|---------|
| `api_token` | Sidecar 启动 | 进程生命周期 | Python 进程退出/崩溃重启 |
| `internal_token` | Sidecar 启动 | 进程生命周期 | Python 进程退出/崩溃重启 |
| `session_token` | 用户登录（未来） | 7 天 | 登出/过期 |

### 6.3 Python 服务沙盒

| 限制项 | 策略 |
|--------|------|
| **文件系统** | 仅允许读写 `AppConfig` 和 `AppData` 目录，通过 Tauri `fs` 权限白名单控制 |
| **网络** | HTTP 服务仅监听 `127.0.0.1`，禁止绑定 `0.0.0.0` |
| **子进程** | Python 禁止 spawn 新子进程（通过 PyInstaller 打包时限制） |
| **内存** | 设置 ulimit（Linux/macOS）或 Job Object（Windows）限制最大内存 1GB |

### 6.4 审计日志

记录所有敏感操作到独立日志表：

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,           -- 'api_key_set', 'window_created', 'data_exported'
    target_type TEXT,               -- 'window', 'setting', 'file'
    target_id TEXT,
    details TEXT,                   -- JSON
    ip TEXT DEFAULT '127.0.0.1',
    user_agent TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

---

## 七、视觉交互与 UI 规范

### 7.1 设计系统（Design Tokens）

**颜色系统：**

| Token | 浅色模式 | 深色模式 | 用途 |
|-------|---------|---------|------|
| `bg-primary` | `#FAF9F7` | `#1A1A1A` | 主背景 |
| `bg-secondary` | `#F2F1EF` | `#242424` | 卡片背景 |
| `bg-glass` | `rgba(255,255,255,0.72)` | `rgba(30,30,30,0.72)` | 毛玻璃 |
| `text-primary` | `#2C2C2C` | `#E8E8E8` | 主文字 |
| `text-secondary` | `#6B6B6B` | `#A0A0A0` | 次要文字 |
| `accent-dai` | `#4A5F6F` | `#6B8FA8` | 品牌色 |
| `accent-dai-hover` | `#3D4F5C` | `#7BA3BE` | 品牌色悬停 |
| `border` | `#E5E5E5` | `#333333` | 边框 |
| `success` | `#4ADE80` | `#4ADE80` | 成功 |
| `warning` | `#FBBF24` | `#FBBF24` | 警告 |
| `error` | `#F87171` | `#F87171` | 错误 |

**字体规范：**
- 主字体：`Inter`, `PingFang SC`, `Microsoft YaHei`, sans-serif
- 等宽字体：`JetBrains Mono`, `Fira Code`（代码块）
- 层级：
  - H1: 24px / 32px line-height / 600 weight
  - H2: 18px / 24px / 600
  - Body: 14px / 20px / 400
  - Caption: 12px / 16px / 400
  - Mono: 13px / 20px / 400

### 7.2 动效规范

| 场景 | 时长 | 缓动 | 说明 |
|------|------|------|------|
| 窗口弹出 | 300ms | `cubic-bezier(0.68, -0.55, 0.265, 1.55)` | 弹性缩放 0.95 → 1.0 |
| 窗口关闭 | 200ms | `ease-in` | 缩放 1.0 → 0.95，透明度 1 → 0 |
| 消息进入 | 250ms | `ease-out` | 位移 + 淡入 |
| 骨架屏脉冲 | 1500ms | `ease-in-out` | 无限循环 |
| 悬停反馈 | 150ms | `ease` | 背景色/阴影变化 |
| 页面切换 | 200ms | `ease-in-out` | 淡入淡出 |

### 7.3 暗黑模式实现

```typescript
// Vue 组合式函数
export function useTheme() {
  const isDark = ref(false);

  const init = () => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    isDark.value = media.matches;
    media.addEventListener('change', (e) => isDark.value = e.matches);
  };

  const toggle = () => {
    isDark.value = !isDark.value;
    document.documentElement.classList.toggle('dark', isDark.value);
  };

  return { isDark, init, toggle };
}
```

```css
/* Tailwind 配置 */
@custom-variant dark (&:where(.dark, .dark *));
/* 或使用 media 策略：darkMode: 'media' */
```

---

## 八、工程化与目录规范

### 8.1 完整目录结构

```text
fluxdesk/
├── .github/
│   └── workflows/
│       ├── ci.yml              # PR 检查
│       └── release.yml         # 自动构建发布
├── scripts/
│   ├── setup.sh                # 开发环境一键初始化
│   ├── build-python.sh         # PyInstaller/Nuitka 打包脚本
│   ├── build-release.sh        # 全量构建（前端+Rust+Python）
│   └── check-env.py            # 环境检查（Node/Rust/Python 版本）
├── src/                        # Vue 3 前端
│   ├── apps/                   # 浮动应用组件
│   │   ├── Todo/
│   │   │   ├── index.vue
│   │   │   ├── TodoItem.vue
│   │   │   └── useTodo.ts      # 应用级 composable
│   │   ├── Pomodoro/
│   │   ├── Note/
│   │   └── Calendar/
│   ├── components/             # 通用 UI 组件
│   │   ├── ui/                 # shadcn-vue 组件
│   │   ├── CommandPalette/     # 命令中心
│   │   ├── FloatingWindow/     # 窗口容器
│   │   └── ConfirmCard/        # 确认卡片
│   ├── composables/            # 通用组合函数
│   │   ├── useTauriEvent.ts
│   │   ├── useWindowState.ts
│   │   ├── useAIStream.ts      # SSE 流式处理
│   │   └── useTheme.ts
│   ├── stores/                 # Pinia
│   │   ├── windowStore.ts      # 本地窗口缓存
│   │   ├── chatStore.ts        # 对话历史
│   │   └── settingStore.ts
│   ├── router/
│   │   └── index.ts            # 窗口类型路由映射
│   ├── styles/
│   │   ├── globals.css
│   │   └── theme.css           # CSS Variables
│   ├── types/
│   │   └── index.ts            # 全局类型定义
│   └── main.ts
├── src-tauri/                  # Rust 宿主
│   ├── src/
│   │   ├── main.rs
│   │   ├── lib.rs
│   │   ├── commands/           # Tauri Commands
│   │   │   ├── window.rs
│   │   │   ├── system.rs
│   │   │   └── security.rs
│   │   ├── window_manager/     # 窗口注册表与 Z-Index
│   │   │   ├── registry.rs
│   │   │   ├── z_stack.rs
│   │   │   └── monitor.rs
│   │   ├── sidecar/            # Python 进程管理
│   │   │   ├── manager.rs
│   │   │   ├── health.rs
│   │   │   └── token.rs
│   │   ├── security/           # 密钥与鉴权
│   │   │   ├── keychain.rs
│   │   │   ├── token.rs
│   │   │   └── sandbox.rs
│   │   └── api/                # 内部 HTTP 服务（供 Python 调用）
│   │       ├── server.rs
│   │       └── handlers.rs
│   ├── capabilities/           # Tauri 权限配置
│   │   └── default.json
│   ├── icons/
│   ├── build.rs
│   ├── Cargo.toml
│   └── tauri.conf.json
├── server/                     # Python AI 后端
│   ├── main.py                 # FastAPI 入口
│   ├── core/
│   │   ├── intent_engine.py    # 意图解析引擎主入口
│   │   ├── rule_engine.py      # 本地规则引擎
│   │   ├── llm_adapter.py      # LiteLLM 适配
│   │   ├── prompt_manager.py   # 提示词模板管理
│   │   └── function_schemas.py # Function Calling Schema
│   ├── routers/
│   │   ├── chat.py
│   │   ├── windows.py
│   │   ├── history.py
│   │   └── health.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py          # Pydantic 请求/响应模型
│   │   └── database.py         # SQLAlchemy 模型
│   ├── database/
│   │   ├── connection.py
│   │   └── migrations/         # Alembic 迁移脚本
│   ├── services/
│   │   ├── window_service.py
│   │   ├── chat_service.py
│   │   └── todo_service.py
│   ├── utils/
│   │   ├── security.py         # Token 验证
│   │   ├── config.py           # 配置管理
│   │   └── logger.py           # 日志配置
│   ├── rules/                  # 本地规则 YAML
│   │   ├── create_window.yaml
│   │   ├── manage_todo.yaml
│   │   └── system.yaml
│   ├── prompts/                # 提示词模板
│   │   └── system.md
│   └── tests/
│       ├── test_intent.py
│       └── test_rules.py
├── tests/
│   ├── e2e/                    # Playwright 测试
│   │   └── window.spec.ts
│   └── integration/            # 集成测试
└── docs/                       # 补充文档
    ├── api.md
    └── deployment.md
```

### 8.2 Tauri 配置关键项

```json
// src-tauri/tauri.conf.json
{
  "productName": "FluxDesk",
  "version": "1.1.0",
  "identifier": "com.fluxdesk.app",
  "build": {
    "frontendDist": "../dist",
    "devUrl": "http://localhost:5173"
  },
  "app": {
    "windows": [
      {
        "label": "command-center",
        "title": "FluxDesk",
        "width": 680,
        "height": 520,
        "decorations": false,
        "transparent": true,
        "alwaysOnTop": true,
        "visible": false,
        "center": true
      }
    ],
    "security": {
      "csp": "default-src 'self'; connect-src 'self' http://localhost:*; img-src 'self' data: blob:",
      "dangerousDisableAssetCspModification": false
    }
  },
  "bundle": {
    "active": true,
    "targets": ["dmg", "msi", "appimage", "deb"],
    "externalBin": ["bin/fluxdesk-ai"],
    "icon": ["icons/32x32.png", "icons/128x128.png", "icons/icon.icns", "icons/icon.ico"]
  }
}
```

### 8.3 Python 打包配置

```python
# server/build.spec (PyInstaller)
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('rules', 'rules'), ('prompts', 'prompts')],
    hiddenimports=['litellm', 'sqlalchemy', 'alembic'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='fluxdesk-ai',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

---

## 九、性能与监控

### 9.1 性能基线

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 安装包体积 | ≤ 80MB（含 Python） | `ls -lh` |
| 冷启动时间 | ≤ 800ms | 手动计时，从点击到可交互 |
| 内存占用（空闲） | ≤ 120MB | 系统监控 |
| 内存占用（AI 对话） | ≤ 350MB | 长对话后观测 |
| 窗口创建延迟 | ≤ 150ms | 从指令到窗口可见 |
| SSE 首字延迟 | ≤ 800ms | 从发送到首字返回 |
| 数据库查询 | ≤ 50ms（单表） | SQLite EXPLAIN |

### 9.2 监控埋点

**Rust 侧指标：**
- `fluxdesk_window_created_total`：窗口创建总数
- `fluxdesk_sidecar_restart_total`：Sidecar 重启次数
- `fluxdesk_memory_usage_mb`：内存占用
- `fluxdesk_ipc_call_duration_ms`：IPC 调用耗时

**Python 侧指标：**
- `fluxdesk_llm_request_duration_ms`：LLM 请求耗时
- `fluxdesk_intent_parse_duration_ms`：意图解析耗时
- `fluxdesk_sse_connections_active`：活跃 SSE 连接数

**前端指标：**
- 首屏渲染时间（FCP）
- 窗口交互响应时间
- 错误上报（通过 IPC 推送至 Rust 日志）

### 9.3 日志规范

**统一日志格式：**

```text
2024-05-04T14:32:10.123Z [INFO] [rust::window_manager] Window created: win_abc123, type=todo
2024-05-04T14:32:10.456Z [INFO] [python::intent_engine] Parsed intent: create_window, confidence=0.94
2024-05-04T14:32:10.789Z [DEBUG] [vue::CommandPalette] Message rendered, delta=12ms
```

**日志级别：**
- `ERROR`：异常、崩溃、安全事件
- `WARN`：降级、超时、异常状态
- `INFO`：关键生命周期事件
- `DEBUG`：开发调试（生产环境关闭）

**日志轮转：**
- 单文件最大 10MB，保留 5 个历史文件
- 路径：`AppData/logs/fluxdesk.log`

---

## 十、测试策略

### 10.1 分层测试矩阵

| 层级 | 类型 | 工具 | 覆盖内容 | CI 要求 |
|------|------|------|---------|---------|
| Rust | 单元测试 | `cargo test` | 窗口注册表、Token 生成、边界吸附 | 100% 通过 |
| Rust | 集成测试 | `cargo test --test '*'` | Sidecar 生命周期、IPC 命令 | 100% 通过 |
| Python | 单元测试 | `pytest` | 意图解析、规则匹配、Schema 校验 | 覆盖率 ≥ 80% |
| Python | 集成测试 | `pytest` | 数据库 CRUD、SSE 流格式 | 覆盖率 ≥ 70% |
| Vue | 组件测试 | `Vitest` + `@vue/test-utils` | 浮动组件、命令中心输入 | 覆盖率 ≥ 60% |
| E2E | 端到端 | `Playwright` | 完整链路：唤起→输入→窗口创建→置顶 | 关键路径 100% |

### 10.2 关键测试用例

**E2E 示例：创建番茄钟**

```typescript
// tests/e2e/pomodoro.spec.ts
import { test, expect } from '@playwright/test';

test('create pomodoro via command center', async ({ page }) => {
  // 1. 唤起命令中心
  await page.keyboard.press('Control+K');
  await expect(page.locator('[data-testid="command-center"]')).toBeVisible();

  // 2. 输入指令
  await page.fill('[data-testid="chat-input"]', '创建一个25分钟的番茄钟');
  await page.keyboard.press('Enter');

  // 3. 验证窗口创建
  const window = page.locator('[data-testid="floating-window"][data-type="pomodoro"]');
  await expect(window).toBeVisible({ timeout: 2000 });

  // 4. 验证数据
  await expect(window.locator('text=25:00')).toBeVisible();

  // 5. 验证置顶
  const isAlwaysOnTop = await page.evaluate(() => 
    window.__TAURI__.invoke('is_window_always_on_top', { id: '...' })
  );
  expect(isAlwaysOnTop).toBe(true);
});
```

---

## 十一、开发环境搭建

### 11.1 依赖清单

| 工具 | 版本 | 用途 |
|------|------|------|
| Node.js | ≥ 18 | 前端构建 |
| Rust | ≥ 1.75 | Tauri 宿主 |
| Python | ≥ 3.10 | AI 后端 |
| Tauri CLI | latest | `cargo install tauri-cli` |

### 11.2 一键初始化

```bash
# 克隆仓库
git clone https://github.com/yourname/fluxdesk.git
cd fluxdesk

# 运行初始化脚本
./scripts/setup.sh

# 脚本内容：
# 1. 安装 Node 依赖 (npm install)
# 2. 安装 Python 依赖 (cd server && pip install -r requirements.txt)
# 3. 检查 Rust 工具链
# 4. 初始化 SQLite 数据库
# 5. 生成开发环境配置 (.env.local)
```

### 11.3 开发启动

```bash
# 终端 1：启动前端（带 HMR）
npm run dev

# 终端 2：启动 Python 后端（独立模式，调试用）
cd server
uvicorn main:app --reload --port 8000

# 终端 3：启动 Tauri（开发模式）
cargo tauri dev
```

---

## 十二、构建与发布

### 12.1 构建流程

```bash
# 全量构建（CI/CD 执行）
./scripts/build-release.sh

# 流程：
# 1. 前端构建：npm run build → dist/
# 2. Python 打包：PyInstaller → src-tauri/bin/fluxdesk-ai-{target}
# 3. Rust 构建：cargo tauri build → release/
# 4. 签名（macOS: codesign, Windows: signtool）
# 5. 生成更新包（.zip / .msi / .dmg / .AppImage）
```

### 12.2 自动更新

使用 **Tauri Updater**：

```json
// tauri.conf.json
{
  "plugins": {
    "updater": {
      "active": true,
      "endpoints": ["https://fluxdesk.app/api/v1/update/{{target}}/{{current_version}}"],
      "dialog": true,
      "pubkey": "dW50cnVzdGVkIGNvbW1lbnQ6IG1pbml..."
    }
  }
}
```

### 12.3 发布检查清单

- [ ] 版本号同步（`package.json`, `Cargo.toml`, `tauri.conf.json`, `server/__init__.py`）
- [ ] 更新日志（`CHANGELOG.md`）
- [ ] 数据库迁移脚本测试
- [ ] 全平台构建通过
- [ ] 签名验证
- [ ] 病毒扫描（Windows Defender / VirusTotal）
- [ ] 更新端点可用性检查

---

## 十三、路线图 (Roadmap)

### Phase 1：底座打磨（Q2 2026）

**目标**：可稳定运行的 MVP，支持基础窗口管理与 AI 对话

| 任务 | 优先级 | 验收标准 |
|------|--------|---------|
| Tauri 2 + Vue 3 基础框架 | P0 | 命令中心窗口正常唤起/隐藏 |
| Rust WindowRegistry | P0 | 支持创建/销毁/焦点切换，Z-Index 正确 |
| 全局快捷键 Ctrl+K | P0 | 任意场景唤起，不冲突 |
| Python Sidecar 集成 | P0 | 懒加载启动，崩溃自动重启 |
| SSE 流式对话 | P0 | 逐字输出，支持中断 |
| 基础浮动窗口（Todo/Note） | P0 | 创建、编辑、持久化 |
| 安全密钥链路 | P0 | API Key 存 Keychain，Token 鉴权 |
| 本地规则引擎 | P1 | 支持 10+ 高频指令离线解析 |

### Phase 2：智能化增强（Q3 2026）

| 任务 | 说明 |
|------|------|
| Ollama 本地模型支持 | 完全离线模式，隐私优先 |
| RAG 本地知识库 | 基于历史笔记的问答 |
| 多模型对比 | 同时展示 GPT-4 / Claude / 本地模型回答 |
| 意图置信度与确认 | 低置信度自动弹出确认卡片 |
| 番茄钟与日历联动 | 自动识别"会议"类待办并同步到日历窗口 |

### Phase 3：生态与同步（Q4 2026）

| 任务 | 说明 |
|------|------|
| WebDAV 同步 | 支持坚果云、iCloud 等第三方同步 |
| 插件系统预览 | JSON 配置简单应用，JS 插件沙箱 |
| 使用统计仪表板 | 本地计算番茄钟统计、AI 使用时长 |
| 社区插件市场 | 插件分发与安装（需安全审核） |

---

## 十四、风险应对

| 风险 | 影响 | 概率 | 应对策略 |
|------|------|------|---------|
| **Python 内存泄漏** | 高 | 中 | Idle 休眠释放缓存；设置内存上限，超限时自动重启 |
| **全局快捷键冲突** | 中 | 高 | 启动时检测冲突，设置面板支持自定义；提供备选方案（如双击 Alt） |
| **WebView 兼容性** | 中 | 中 | 测试覆盖 WebKit2GTK（Linux）、WebKit（macOS）、Edge WebView2（Windows） |
| **多窗口状态不一致** | 高 | 中 | Rust 作为唯一真相源；前端收到事件后强制覆盖本地状态 |
| **LLM API 成本失控** | 中 | 低 | 本地规则引擎优先；设置月度 Token 上限；默认使用本地模型 |
| **数据库损坏** | 高 | 低 | 自动备份机制；启动时校验 SQLite 完整性；损坏时自动恢复最近备份 |
| **跨平台打包差异** | 中 | 中 | CI 矩阵构建（macOS/Windows/Ubuntu）；统一 PyInstaller 配置 |

---

## 附录

### A. 术语表

| 术语 | 说明 |
|------|------|
| Sidecar | 与主进程伴生的辅助进程，此处指 Python AI 服务 |
| LUI | Language User Interface，自然语言用户界面 |
| SSOT | Single Source of Truth，唯一真相源 |
| SSE | Server-Sent Events，服务器推送事件 |
| RAG | Retrieval-Augmented Generation，检索增强生成 |

### B. 参考资源

- Tauri 2 文档：https://v2.tauri.app/
- LiteLLM 文档：https://docs.litellm.ai/
- shadcn-vue：https://www.shadcn-vue.com/
- PyInstaller：https://pyinstaller.org/

---

> **文档维护**：本规范采用"架构冻结"机制。Phase 1 开发期间，架构变更需经过 RFC 流程（提交 Issue → 讨论 → 批准）。Phase 1 结束后进入迭代优化期。
