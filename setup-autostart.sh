#!/bin/bash
# Pi-Talk 自启动配置脚本
# 在 Pi 上运行一次即可，配置完成后每次重启自动上线
# 用法：bash setup-autostart.sh
#
# 前置条件：
#   - Node.js / npm 已安装（推荐 nvm）
#   - openclaw 已安装并配置完成（openclaw gateway 能正常启动）
#   - pm2 已安装：npm install -g pm2

set -e

PI_TALK_DIR="$(cd "$(dirname "$0")" && pwd)"
NODE_BIN="/home/nanhara/.nvm/versions/node/v22.22.0/bin"
PM2="$NODE_BIN/pm2"
OPENCLAW="$NODE_BIN/openclaw"

echo "=== Pi-Talk 自启动配置 ==="
echo "目录: $PI_TALK_DIR"
echo ""

# ── 1. 检查依赖 ─────────────────────────────────────────────────────────────
echo "[1/5] 检查依赖..."

if [ ! -f "$PM2" ]; then
  echo "  ⚠️  pm2 未找到，正在安装..."
  "$NODE_BIN/npm" install -g pm2
  echo "  ✅ pm2 安装完成"
else
  echo "  ✅ pm2 已安装: $($PM2 --version)"
fi

if [ ! -f "$OPENCLAW" ]; then
  echo "  ❌ openclaw 未找到: $OPENCLAW"
  echo "     请先安装 openclaw 并完成配置"
  exit 1
fi
echo "  ✅ openclaw 已找到"

# ── 2. 停止旧进程 ────────────────────────────────────────────────────────────
echo ""
echo "[2/5] 清理旧进程..."
$PM2 delete openclaw-gateway 2>/dev/null && echo "  已清理旧 openclaw-gateway" || echo "  无旧进程"
$PM2 delete pi-talk 2>/dev/null && echo "  已清理旧 pi-talk" || echo "  无旧进程"
fuser -k 3456/tcp 2>/dev/null || true

# ── 3. 注册 OpenClaw Gateway 到 pm2 ─────────────────────────────────────────
echo ""
echo "[3/5] 注册 openclaw-gateway..."
$PM2 start "$OPENCLAW" \
  --name "openclaw-gateway" \
  --interpreter none \
  -- gateway start \
  --restart-delay 5000

sleep 3

# 验证 gateway 在线
if $PM2 list | grep -q "openclaw-gateway.*online"; then
  echo "  ✅ openclaw-gateway 在线"
else
  echo "  ⚠️  gateway 未能启动，检查 openclaw 配置后重试"
  $PM2 logs openclaw-gateway --lines 20 --nostream
fi

# ── 4. 注册 Pi-Talk Server 到 pm2 ────────────────────────────────────────────
echo ""
echo "[4/5] 注册 pi-talk..."
$PM2 start "$NODE_BIN/node" \
  --name "pi-talk" \
  --cwd "$PI_TALK_DIR" \
  --restart-delay 3000 \
  -- server.js

sleep 2
echo "  ✅ pi-talk 注册完成"

# ── 5. 保存 pm2 配置 + 设置开机自启 ─────────────────────────────────────────
echo ""
echo "[5/5] 保存配置并设置开机自启..."
$PM2 save
echo ""
echo "======================================"
echo "  ⚡ 即将生成开机自启命令"
echo "  复制下面的 sudo 命令并执行："
echo "======================================"
$PM2 startup | grep "sudo"
echo "======================================"
echo ""
echo "✅ 配置完成！执行上面的 sudo 命令后，Pi 重启将自动启动："
echo "   - openclaw-gateway（OpenClaw 节点）"
echo "   - pi-talk（Pi-Talk Server，port 3456）"
echo ""
echo "验证命令：pm2 status"
