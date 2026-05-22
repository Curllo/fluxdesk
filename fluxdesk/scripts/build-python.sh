#!/usr/bin/env bash
#
# build-python.sh — 使用 PyInstaller 打包 Python AI Sidecar
#
# 用法:
#   ./scripts/build-python.sh                    # 自动检测目标平台
#   ./scripts/build-python.sh --target x86_64-unknown-linux-gnu
#   ./scripts/build-python.sh --target x86_64-pc-windows-msvc
#   ./scripts/build-python.sh --target aarch64-apple-darwin
#
# 输出:
#   src-tauri/bin/fluxdesk-ai-{target-triple}[.exe]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── 目标检测 ──────────────────────────────────────────────────────────
detect_target() {
    local os arch triple
    os="$(uname -s)"
    arch="$(uname -m)"

    case "$arch" in
        x86_64|amd64) arch="x86_64" ;;
        aarch64|arm64) arch="aarch64" ;;
        *) echo "[ERROR] Unsupported architecture: $arch"; exit 1 ;;
    esac

    case "$os" in
        Linux)  triple="$arch-unknown-linux-gnu" ;;
        Darwin) triple="$arch-apple-darwin" ;;
        MINGW*|MSYS*|CYGWIN*) triple="$arch-pc-windows-msvc" ;;
        *) echo "[ERROR] Unsupported OS: $os"; exit 1 ;;
    esac

    echo "$triple"
}

TARGET="${1:-$(detect_target)}"
echo "[INFO] Target: $TARGET"

# ── 路径 ──────────────────────────────────────────────────────────────
SERVER_DIR="$PROJECT_ROOT/server"
BIN_DIR="$PROJECT_ROOT/src-tauri/bin"
SPEC_FILE="$SERVER_DIR/build.spec"

mkdir -p "$BIN_DIR"

# ── Python 环境检测 ───────────────────────────────────────────────────
# 优先使用项目内虚拟环境，否则回退系统 pip
if [ -f "$SERVER_DIR/.venv/bin/python" ]; then
    PYTHON="$SERVER_DIR/.venv/bin/python"
    PIP="$SERVER_DIR/.venv/bin/pip"
    echo "[INFO] Using venv: $SERVER_DIR/.venv"
elif [ -f "$SERVER_DIR/.venv/Scripts/python.exe" ]; then
    PYTHON="$SERVER_DIR/.venv/Scripts/python.exe"
    PIP="$SERVER_DIR/.venv/Scripts/pip.exe"
    echo "[INFO] Using venv: $SERVER_DIR/.venv"
else
    PYTHON="python3"
    PIP="pip3"
    echo "[INFO] No venv found, using system Python"
fi

# ── 检查 PyInstaller ──────────────────────────────────────────────────
if ! "$PYTHON" -c "import PyInstaller" 2>/dev/null; then
    echo "[INFO] Installing PyInstaller..."
    "$PIP" install pyinstaller
fi

# ── 安装 Python 依赖 ─────────────────────────────────────────────────
echo "[INFO] Installing Python dependencies..."
"$PIP" install -r "$SERVER_DIR/requirements.txt"

# ── 构建 ──────────────────────────────────────────────────────────────
echo "[INFO] Building sidecar binary..."
cd "$SERVER_DIR"
"$PYTHON" -m PyInstaller --clean --distpath "$BIN_DIR/tmp-dist" --workpath "$BIN_DIR/tmp-build" "$SPEC_FILE"

# ── 重命名为 Tauri 标准格式 ─────────────────────────────────────────
SUFFIX=""
case "$TARGET" in
    *windows*) SUFFIX=".exe" ;;
esac

SIDECAR_NAME="fluxdesk-ai-$TARGET$SUFFIX"
mv "$BIN_DIR/tmp-dist/fluxdesk-ai$SUFFIX" "$BIN_DIR/$SIDECAR_NAME"

# ── 清理 ──────────────────────────────────────────────────────────────
rm -rf "$BIN_DIR/tmp-dist" "$BIN_DIR/tmp-build"
rm -rf "$SERVER_DIR/build" "$SERVER_DIR/dist"

echo "[OK] Built: $BIN_DIR/$SIDECAR_NAME"
echo "[INFO] Size: $(ls -lh "$BIN_DIR/$SIDECAR_NAME" | awk '{print $5}')"
