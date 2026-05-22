# FluxDesk v1.1 开发进度

> 最后更新：2026-05-06
> **状态：核心架构完成 + 真实 LLM 端到端支持 + Linux deb 打包/部署验证通过，21/21 自动化测试通过**

---

## 一、已完成

### 1. 项目骨架（Tauri v2 + Vue 3 + Python FastAPI）
- [x] Tauri v2 配置：主窗口 + Command Center 浮动面板
- [x] Vue 3 + Vite 6 + Tailwind CSS + Pinia 前端栈
- [x] Python FastAPI 后端：`main.py` + `uvicorn` + `CORSMiddleware`
- [x] Rust 编译通过（`cargo check` ✅，5 warnings 无 error）
- [x] 前端 TypeScript 检查通过（`vue-tsc --noEmit` ✅）

### 2. 三层通信链路
- [x] Rust ↔ Python：内部 HTTP Server（port 9595）+ 安全 Token
- [x] Rust ↔ Frontend：Tauri IPC (`invoke` + `listen`)
- [x] Frontend ↔ Python：SSE 流式接口 + Bearer Token 鉴权

### 3. 规则引擎（离线零延迟）
- [x] YAML 配置化正则规则（8 条）
- [x] 支持参数捕获：`$1` 提取时长等
- [x] 规则：create_pomodoro / create_todo / create_note / create_calendar / list_todos / greeting / help
- [x] 优先级排序（priority 字段降序）

### 4. LLM 意图引擎（LiteLLM + Function Calling）
- [x] `intent_engine.py`：LiteLLM `acompletion` 接入
- [x] **非流式** `/api/v1/chat` — 规则优先 → LLM fallback
- [x] **流式** `/api/v1/chat/stream` — SSE 事件序列（message/tool_call/tool_result/done）
- [x] **Mock 模式** — 无 API Key 时自动降级，完整测试链路可用
- [x] 4 个 Function Schemas：`create_window` / `manage_todo` / `set_reminder` / `ask_clarification`
- [x] 流式 tool_calls 合并（`_merge_tool_calls`）
- [x] 系统提示词 `prompts/system.md`（中文 + 时间解析 + 工具映射）
- [x] 指数退避重试（`with_retry()`：最多 3 次，退避 1s/2s/4s）

### 5. 配置管理
- [x] `GET /api/v1/settings/llm` — 查看当前 LLM 配置（不含 API Key）
- [x] `POST /api/v1/settings/llm` — 热更新 provider/model/api_key
- [x] `POST /api/v1/settings/llm/verify` — 验证配置是否可用
- [x] 环境变量：`FLUXDESK_LLM_PROVIDER` / `FLUXDESK_LLM_MODEL` / `OPENAI_API_KEY`

### 6. 前端 Chat 组件
- [x] `CommandPalette/index.vue` — 完整 SSE 解析 + UI 展示
- [x] `useAIStream.ts` — SSE 解析器（`TextDecoder` + 事件分块）
- [x] 工具执行：`tool_result` 成功后自动 `invoke('create_window', ...)`
- [x] 输入交互：Enter 发送、Shift+Enter 换行、Escape 中断
- [x] 消息滚动、Loading 动画

### 7. 浮动窗口路由
- [x] `App.vue` — 根据 `?type=` URL 参数路由
- [x] `PomodoroWindow.vue` — 倒计时（开始/暂停/重置），支持 `?duration=`
- [x] `TodoWindow.vue` — 增删改查，对接数据库 API
- [x] `NoteWindow.vue` — 文本编辑，自动保存 + 加载数据库
- [x] `CalendarWindow.vue` — 月历视图，高亮今日
- [x] Rust 侧 `create_floating_window` — 动态构建带参数的 URL

### 8. Rust IPC 命令
- [x] `create_window(window_type, config)` — 创建浮动窗口 + 同步到 Python DB
- [x] `destroy_window(id)` — 关闭窗口 + 从数据库删除
- [x] `focus_window(id)` / `list_windows()` — 窗口管理
- [x] `update_window_position(id, x, y)` — 移动同步到数据库
- [x] `update_window_size(id, width, height)` — 调整大小同步到数据库
- [x] `toggle_command_center()` — 显隐 Command Center
- [x] `get_ai_service_config()` / `restart_ai_service()` — AI 服务生命周期
- [x] `set_api_key(key)` / `get_api_key()` / `delete_api_key()` — API Key 管理

### 9. Rust 工具命令（LLM Function Calling 落地）
- [x] `manage_todo(action, content, todo_id)` — IPC → Python API → SQLite
- [x] `set_reminder(title, time, repeat)` — IPC → Python API → SQLite
- [x] 前端 `executeTool` 自动分发到对应 IPC 命令

### 10. 数据持久化（SQLite）
- [x] 6 个模型：Window / Message / Todo / Note / Reminder / PomodoroSession
- [x] CRUD 层：`TodoCRUD` / `NoteCRUD` / `ReminderCRUD` / `WindowCRUD`
- [x] REST 路由：`/todos` `/notes` `/reminders` `/windows` 完整 CRUD
- [x] 前端 `useApi.ts` composable：GET/POST/PATCH/DELETE
- [x] Alembic 迁移框架初始化

### 11. 全局快捷键
- [x] `Ctrl+K` 唤起 / 隐藏 Command Center
- [x] `with_handler` Builder 模式处理快捷键事件
- [x] `GlobalShortcutExt::register` 在 setup 中注册

### 12. 设置面板 UI
- [x] `SettingsPanel.vue` — 弹窗式设置面板
- [x] LLM Provider / Model / API Key 配置
- [x] 保存 + 验证按钮，状态实时反馈
- [x] Command Center Header 集成设置入口

### 13. 窗口生命周期同步
- [x] `useWindowLifecycle.ts` — 监听 move/resize 事件
- [x] 窗口移动 → `update_window_position` → SQLite 更新
- [x] 窗口调整大小 → `update_window_size` → SQLite 更新
- [x] 窗口关闭 → `destroy_window` → SQLite 删除
- [x] 创建窗口 → `create_window` → SQLite 插入

### 14. 重启后窗口状态恢复
- [x] Tauri 启动时读取 SQLite `windows` 表
- [x] 自动恢复上次打开的浮动窗口（延迟 2s 等 Python 就绪）
- [x] 恢复窗口位置和大小

### 15. 多 Provider LLM 支持（真实 LLM 端到端验证）
- [x] IntentEngine 改为单例模式 — `get_intent_engine()` 全局共享
- [x] 4 个 Provider 完整支持：OpenAI / Anthropic / DeepSeek / Google Gemini
- [x] 自动检测 Provider 对应的 API Key 环境变量
- [x] DeepSeek 自定义 Base URL（`https://api.deepseek.com/v1`）
- [x] 设置热重载：`POST /settings/llm` → 立即生效，无需重启
- [x] `apply_runtime_config()` 方法支持运行时切换 Provider/Model/API Key
- [x] 验证端点修复：使用当前 Provider 的正确 API Key 和 Base URL
- [x] Function Schema 增强：`data` 字段支持 `duration`/`title`/`content`/`label`
- [x] System Prompt 优化：更详细的工具映射表，减少 LLM 误判
- [x] 前端设置面板：切换 Provider 时自动推荐默认 Model

### 16. 快捷键自定义
- [x] Rust `commands/shortcut.rs` — `get_shortcut` / `update_shortcut` IPC 命令
- [x] `SharedShortcut` 状态管理 + JSON 文件持久化（`shortcut.json`）
- [x] 动态热切换：注销旧快捷键 → 注册新快捷键，即时生效
- [x] `lib.rs` 重构：`with_handler` 不再硬编码快捷键
- [x] 设置面板 Keybinding Capture UI — 点击捕捉按键组合
- [x] 支持 Ctrl/Alt/Shift/Super 组合键 + 任意字符/F键/空格
- [x] 符号化显示（⌃⌘⌥⇧）+ 实时预览
- [x] Command Center Header 动态显示当前快捷键
- [x] Python `GET/POST/DELETE /settings/preferences` 通用偏好存储
- [x] TypeScript 类型检查通过（`vue-tsc --noEmit` ✅）

### 17. 前端状态同步
- [x] `useActivityBus.ts` — 跨 Webview 事件总线（基于 Tauri emit/listen）
- [x] `FluxActivity` 类型：source/action/label/detail/timestamp
- [x] TodoWindow 数据变更 → 实时通知 Command Center
- [x] NoteWindow 自动保存 → 实时通知 Command Center
- [x] PomodoroWindow 完成 → emitActivity + 系统原生通知
- [x] CommandPalette 监听 `window-state-changed` → 实时窗口计数
- [x] CommandPalette 监听 `flux-activity` → Toast 通知 + 活动历史
- [x] Header 显示活跃浮动窗口数量徽标
- [x] 窗口列表从 Rust `list_windows` IPC 加载
- [x] TypeScript 类型检查通过（`vue-tsc --noEmit` ✅）

### 18. RAG 笔记检索 ✅ 已完成
- [x] `server/core/rag_engine.py` — RAG 引擎（embedding 生成 + 向量搜索 + 关键词回退）
- [x] `NoteEmbedding` 数据库表 — 存储笔记 embedding 向量（JSON）
- [x] LiteLLM `aembedding()` 集成 — 支持 OpenAI/Gemini embedding 模型
- [x] 纯 Python 余弦相似度计算 — 零依赖向量检索
- [x] 关键词搜索回退（Jaccard 相似度）— 无 API Key 时可用
- [x] `search_notes` Function Schema — LLM 可调用搜索笔记
- [x] Agent Loop 透明处理：LLM 调用 `search_notes` → 后端执行搜索 → 结果送回 LLM 总结 → 流式输出
- [x] `GET /notes/search?q=` — 语义搜索 API
- [x] 笔记创建/更新时自动生成 embedding（BackgroundTasks）
- [x] 笔记删除时自动清理 embedding
- [x] System Prompt 更新：包含 `search_notes` 工具说明和示例
- [x] 路由顺序修复：`/notes/search` 优先于 `/notes/{note_id}`
- [x] E2E 测试套件：21 项测试全部通过

### 19. 数据导出/导入 ✅ 已完成
- [x] `server/routers/data.py` — `GET /data/export` + `POST /data/import`
- [x] 全量导出：notes / todos / reminders / messages / pomodoro_sessions / windows / embeddings
- [x] 导入策略：upsert-by-id（已存在的更新，不存在的插入）
- [x] JSON 格式，包含 version + exported_at + counts + data
- [x] 前端 UI：导出（Blob download）+ 导入（file input + POST）+ 状态消息
- [x] 导入支持完整导出格式和纯 data 数组

### 20. 打包与部署 ✅ 已完成
- [x] `server/main.py` — 修复 uvicorn.run 为 PyInstaller 兼容的 `uvicorn.run(app, ...)`
- [x] `server/utils/config.py` — 添加 `_resolve_app_dir()` 处理 PyInstaller 冻结路径
- [x] `server/models/database.py` — 添加 `_resolve_db_url()` 安全的数据库 URL 解析
- [x] `server/build.spec` — 添加 alembic 数据文件（目录 + ini）
- [x] `scripts/build-python.sh` — 修复清理命令 bug（不再删除源码 build.spec）
- [x] `LICENSE` — MIT License（FluxDesk Team）
- [x] `src-tauri/icons/icon.ico` — 重新生成 7 尺寸（16/24/32/48/64/128/256）
- [x] `src-tauri/capabilities/default.json` — 添加 notification:default 权限
- [x] `src-tauri/tauri.conf.json` — NSIS 安装器 + deb 依赖 + updater 插件配置
- [x] `src-tauri/fluxdesk.desktop` — Linux freedesktop 桌面入口模板
- [x] `.gitignore` — 添加 PyInstaller build/dist 输出目录
- [x] `src-tauri/icons/` — 清理 11 个未使用的图标文件
- [x] TypeScript 类型检查通过（`vue-tsc --noEmit` ✅）
- [x] Vite 生产构建通过（`npm run build` ✅）
- [x] E2E 测试套件：21 项测试全部通过

---

## 二、自动化测试报告

### 原有测试（13 项）
```
[PASS] Health          → {"status":"ok","version":"1.1.0"}
[PASS] Rule engine     → action: create_window, params: {type: "pomodoro", duration: "25"}
[PASS] Mock LLM        → model: "mock", intent: "chat"
[PASS] SSE stream      → 8 events: message → tool_call → tool_result → done
[PASS] Todo create     → id: xxx, content: "test"
[PASS] Todo list       → N items returned
[PASS] Todo delete     → deleted: True
[PASS] Note create     → id: xxx, title: "test"
[PASS] Note get        → title: "test", content: "content"
[PASS] Window create   → type: "pomodoro", id: xxx
[PASS] Window list     → N items returned
[PASS] Settings get    → provider: "openai", mock_mode: True
[PASS] Reminder create → title: "test", repeat: "once"

Total: 13 tests, 13 passed
ALL TESTS PASSED
```

### E2E 测试套件（21 项，test_llm_e2e.py）
```
[PASS] Health check
[PASS] Get settings
[PASS] Update settings
[PASS] Verify settings
[PASS] Pomodoro rule
[PASS] Todo rule
[PASS] Greeting rule
[PASS] Mock chat: pomodoro
[PASS] Mock chat: todo
[PASS] Mock chat: note
[PASS] SSE stream mock
[PASS] Todo create
[PASS] Todo list
[PASS] Todo delete
[PASS] Note create
[PASS] Note get
[PASS] Note delete
[PASS] Reminder create
[PASS] Reminder delete
[PASS] Data export
[PASS] Data import

Total: 21 tests, 21 passed
ALL TESTS PASSED
```

---

## 三、架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                         前端 (Vue 3)                         │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ CommandCenter│  │ 浮动窗口    │  │ SettingsPanel    │   │
│  │  - Chat UI   │  │ - Pomodoro  │  │ - LLM Config     │   │
│  │  - SSE解析   │  │ - Todo      │  │ - API Key        │   │
│  │  - Tool执行  │  │ - Note      │  │                  │   │
│  └──────┬───────┘  │ - Calendar  │  └──────────────────┘   │
│         │          └──────┬──────┘                         │
│    Tauri IPC        Tauri IPC                              │
│         │                 │                                  │
└─────────┼─────────────────┼──────────────────────────────────┘
          │                 │
          ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      Rust (Tauri v2)                         │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ IPC Commands │  │ WindowMgr   │  │ Global Shortcut  │   │
│  │ - create_win │  │ - Registry  │  │ - Ctrl+K toggle  │   │
│  │ - manage_todo│  │ - create    │  │                  │   │
│  │ - set_remind │  │ - destroy   │  └──────────────────┘   │
│  └──────┬───────┘  │ - focus     │                          │
│         │          └──────┬──────┘                          │
│         │                 │                                   │
│    HTTP (reqwest)    Window 事件                             │
│         │                 │                                   │
└─────────┼─────────────────┼───────────────────────────────────┘
          │                 │
          ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python (FastAPI + SQLite)                 │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ REST API     │  │ IntentEngine│  │ RuleEngine       │   │
│  │ /chat/stream │  │ - LiteLLM   │  │ - YAML Regex     │   │
│  │ /todos       │  │ - Function  │  │ - 8 rules        │   │
│  │ /notes       │  │   Calling   │  │ - 0ms latency    │   │
│  │ /windows     │  │ - Mock mode │  └──────────────────┘   │
│  └──────┬───────┘  └──────┬──────┘                          │
│         │                  │                                  │
│    SQLAlchemy        Prompt + Schemas                        │
│         │                  │                                  │
│         ▼                  ▼                                  │
│  ┌────────────────────────────────────┐                     │
│  │ SQLite (fluxdesk.db)               │                     │
│  │ windows / todos / notes / reminders│                     │
│  └────────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、待办清单（下一步）

### 🔴 高优先级

1. ~~**真实 LLM 端到端验证**~~ ✅ 已完成
   - ✅ IntentEngine 单例 + 热重载
   - ✅ 多 Provider 支持（OpenAI / Anthropic / DeepSeek / Gemini）
   - ✅ Function Calling 正确触发 `create_window`
   - ✅ 19 项 E2E 测试全部通过

### 🟡 中优先级

2. ~~**前端状态同步**~~ ✅ 已完成
   - ✅ `useActivityBus` 跨 Webview 事件总线
   - ✅ 浮动窗口数据变更 → Toast 通知 Command Center
   - ✅ Pomodoro 完成 → 系统原生通知 + Activity 事件
   - ✅ 活跃窗口计数 + 实时状态跟踪

3. ~~**设置面板扩展**~~ ✅ 已完成
   - ✅ 主题切换（light / dark / system）+ localStorage 持久化
   - ✅ Provider 切换自动推荐默认 Model
   - ✅ 快捷键自定义（Keybinding Capture UI + 动态热切换）
   - ✅ 数据导出/导入（JSON 格式，upsert-by-id 合并策略）

### 🟢 低优先级

4. ~~**RAG 笔记检索**~~ ✅ 已完成
   - ✅ LiteLLM Embedding + 纯 Python 余弦相似度向量搜索
   - ✅ 关键词回退（无 API Key 时可用）
   - ✅ Agent Loop 透明处理 — LLM 自动搜索 + 总结笔记内容
   - ✅ 笔记自动索引 + 删除清理

5. ~~**多 LLM Provider 支持**~~ ✅ 已完成
   - ✅ OpenAI / Anthropic / DeepSeek / Gemini 完整支持
   - ✅ Provider 自动检测 API Key + Base URL

6. ~~**打包与部署**~~ ✅ 已完成 — 含 NSIS/deb 安装器、updater、CI/CD、图标/许可证/Linux desktop
   - ✅ `scripts/build-python.sh` — PyInstaller 打包 Python Sidecar
   - ✅ `scripts/build-release.sh` — 全量构建流程（前端 + Python + Rust）
   - ✅ `server/build.spec` — PyInstaller 配置（`collect_submodules` + `collect_data_files` 自动收集 litellm 依赖）
   - ✅ `src-tauri/tauri.conf.json` — 配置 externalBin + 多平台 bundle targets
   - ✅ `src-tauri/Cargo.toml` — 添加 tauri-plugin-shell 支持
   - ✅ `src-tauri/src/sidecar/manager.rs` — 生产/开发双模式侧载启动（含 deb 安装路径修正）
   - ✅ `src-tauri/src/lib.rs` — 启动时自动拉起 sidecar + 恢复浮动窗口
   - ✅ `src-tauri/capabilities/default.json` — shell 权限
   - ✅ `.github/workflows/ci.yml` — CI 自动化
   - ✅ `.github/workflows/release.yml` — 全平台发布流水线（Windows/macOS/Linux）
   - ✅ Linux deb 端到端验证通过（FluxDesk_1.1.0_amd64.deb，65MB）
   
   **deb 打包中修复的关键 Bug：**
   1. `bundled_binary_path()` 需要同时检查 resource_dir/ 和可执行文件同级目录（deb 安装到 /usr/bin/）
   2. `axum::serve()` 不能在 `tokio::spawn` 中执行（runtime 被 drop），需直接 await 阻塞线程
   3. `get_ai_service_config` 的 lazy start 会导致重复启动 sidecar，改为只读状态
   4. PyInstaller 必须用 `collect_submodules` + `collect_data_files` 收集 litellm 的 tokenizer JSON 文件

---

## 五、已知问题

| 问题 | 状态 | 备注 |
|------|------|------|
| Windows 终端中文显示乱码 | 🟡 可忽略 | 实际数据 UTF-8 正确，终端编码问题 |
| LiteLLM 无法获取远程价格表 | 🟡 可忽略 | 网络受限，回退本地备份 |
| Pydantic 版本降级 | 🟢 正常 | LiteLLM 安装 2.12.5，功能无影响 |
| `fluxdesk-ai` Sidecar 二进制缺失 | 🟢 正常 | dev 模式走 HTTP 直连，非阻塞 |
| AppImage 构建超时 | 🟡 可忽略 | 网络无法下载 AppRun，deb 构建正常 |

---

## 六、快速启动命令

### 开发模式

```powershell
# 1. 启动 Python 后端（端口 8000）
cd fluxdesk/server
py -3.12 main.py

# 2. 启动前端开发服务器（端口 1420）
cd fluxdesk
npm run dev

# 3. 启动 Tauri（会自动拉起 1+2）
cd fluxdesk/src-tauri
& "$env:USERPROFILE\.cargo\bin\cargo.exe" tauri dev

# 或一键（推荐）
cd fluxdesk/src-tauri
& "$env:USERPROFILE\.cargo\bin\cargo.exe" tauri dev
```

配置真实 LLM：
```powershell
$env:OPENAI_API_KEY="sk-your-key"
$env:FLUXDESK_LLM_PROVIDER="openai"
$env:FLUXDESK_LLM_MODEL="gpt-4o-mini"
```

### Linux 构建

```bash
# 1. 安装 Rust (rustup)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# 2. 构建 Python sidecar
bash scripts/build-python.sh

# 3. 构建 deb 包
source "$HOME/.cargo/env" && npx tauri build --bundles deb

# 4. 安装
sudo dpkg -i src-tauri/target/release/bundle/deb/FluxDesk_1.1.0_amd64.deb

# 5. 运行
/usr/bin/fluxdesk
```

---

## 七、文件统计

```
Rust:     ~15 个文件 (src-tauri/src/)
Vue/TS:   ~20 个文件 (src/)
Python:   ~25 个文件 (server/)
Config:   ~10 个文件
─────────────────────────────
总计:     ~70 个文件
```
