# FluxDesk

AI-Native 跨平台桌面工具系统。通过自然语言交互打破传统 GUI 的层级限制，为用户提供"随叫随到、用完即走"的智能化桌面工作环境。

## 核心特性

- **零干扰**: 全局快捷键 `Ctrl/Cmd + K` 唤起，不抢占当前工作流焦点
- **意图驱动**: 自然语言直接转化为结构化操作
- **本地优先**: 数据默认落盘本地，AI 能力支持离线/云端双模
- **原子化应用**: 每个浮动窗口都是独立生命周期，支持自由组合

## 技术栈

| 层级 | 技术 |
|------|------|
| 系统宿主 | Tauri 2 (Rust) |
| 视图层 | Vue 3 + TypeScript |
| 样式 | Tailwind CSS |
| 状态管理 | Pinia |
| AI 后端 | Python FastAPI |
| 数据库 | SQLite |

## 开发环境

### 依赖

- Node.js >= 18
- Rust >= 1.75
- Python >= 3.10

### 启动开发服务器

```bash
# 终端 1: 前端
npm install
npm run dev

# 终端 2: Python AI 后端
cd server
py -m pip install -r requirements.txt
py main.py

# 终端 3: Tauri (需 Rust)
cd src-tauri
cargo tauri dev
```

## Phase 1 功能

- [x] Tauri 2 + Vue 3 基础框架
- [x] 命令中心窗口（全局唤起/隐藏）
- [x] Rust WindowRegistry
- [x] Python Sidecar 集成（懒加载）
- [x] SSE 流式对话
- [x] 基础浮动窗口（Todo / Pomodoro / Note / Calendar）
- [x] 本地规则引擎（10+ 高频指令离线解析）
- [x] 安全 Token 鉴权链路

## 项目结构

```
fluxdesk/
├── src/                    # Vue 3 前端
│   ├── apps/               # 浮动应用
│   ├── components/         # 通用组件
│   ├── composables/        # 组合函数
│   ├── stores/             # Pinia 状态
│   └── styles/             # 全局样式
├── src-tauri/              # Rust 宿主
│   └── src/
│       ├── commands/       # Tauri Commands
│       ├── window_manager/ # 窗口注册表
│       ├── sidecar/        # Python 进程管理
│       └── api/            # 内部 HTTP 服务
└── server/                 # Python AI 后端
    ├── core/               # 意图引擎 / 规则引擎
    ├── routers/            # FastAPI 路由
    ├── models/             # 数据模型
    └── rules/              # 本地规则 YAML
```

## License

MIT
