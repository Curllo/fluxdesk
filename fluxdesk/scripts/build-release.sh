#!/usr/bin/env bash
#
# build-release.sh — 全量构建 FluxDesk 发布包
#
# 流程:
#   1. 前端构建 (npm run build)
#   2. Python Sidecar 打包 (PyInstaller)
#   3. Tauri 构建 (cargo tauri build)
#   4. 签名 (可选)
#
# 用法:
#   ./scripts/build-release.sh                    # 完整构建
#   ./scripts/build-release.sh --skip-python      # 跳过 Python 打包(使用已有二进制)
#   ./scripts/build-release.sh --target all        # 全平台构建
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║        FluxDesk v$(node -e "console.log(require('$PROJECT_ROOT/package.json').version)")  Release Build        ║"
echo "╚═══════════════════════════════════════════════════════════╝"

# ── Step 1: 前端构建 ─────────────────────────────────────────────
echo ""
echo "▸ Step 1/4: Building frontend..."
cd "$PROJECT_ROOT"
npm install
npm run build
echo "  [OK] Frontend built → dist/"

# ── Step 2: Python Sidecar 打包 ──────────────────────────────────
echo ""
echo "▸ Step 2/4: Building Python sidecar..."
if [[ "$*" != *"--skip-python"* ]]; then
    bash "$SCRIPT_DIR/build-python.sh"
else
    echo "  [SKIP] --skip-python flag detected"
fi

# ── Step 3: Tauri 构建 ───────────────────────────────────────────
echo ""
echo "▸ Step 3/4: Building Tauri app..."
cd "$PROJECT_ROOT/src-tauri"

case "$(uname -s)" in
    Darwin)
        cargo tauri build --bundles dmg
        ;;
    Linux)
        cargo tauri build --bundles appimage,deb
        ;;
    MINGW*|MSYS*|CYGWIN*)
        cargo tauri build --bundles msi,nsis
        ;;
esac

# ── Step 4: 签名 (仅 macOS) ──────────────────────────────────────
echo ""
echo "▸ Step 4/4: Code signing..."
if [[ "$(uname -s)" == "Darwin" && -n "${APPLE_SIGNING_IDENTITY:-}" ]]; then
    find "$PROJECT_ROOT/src-tauri/target/release/bundle" -name "*.dmg" -o -name "*.app" | while read -r artifact; do
        codesign --deep --force --verify --verbose --sign "$APPLE_SIGNING_IDENTITY" "$artifact"
        echo "  [OK] Signed: $artifact"
    done
else
    echo "  [SKIP] No signing identity configured"
fi

# ── 完成 ─────────────────────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           Build complete!                                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Output artifacts:"
ls -lh "$PROJECT_ROOT/src-tauri/target/release/bundle/"* 2>/dev/null || echo "(check target/release/bundle/)"
