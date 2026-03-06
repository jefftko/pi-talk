#!/bin/bash
# Pi-Talk 启动脚本
# 读取 .env 文件（如果存在）
ENV_FILE="$(dirname "$0")/.env"
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

cd "$(dirname "$0")"

# ── OpenClaw Gateway 健康检查 ──────────────────────────────────────────────
OPENCLAW="/home/nanhara/.nvm/versions/node/v22.22.0/bin/openclaw"
GATEWAY_OK=false

echo "[pi-talk] 检查 OpenClaw gateway 状态..."
for i in 1 2 3; do
  if "$OPENCLAW" gateway status 2>/dev/null | grep -q "running\|online"; then
    GATEWAY_OK=true
    break
  fi
  echo "[pi-talk] gateway 未就绪，等待 3 秒... ($i/3)"
  sleep 3
done

if [ "$GATEWAY_OK" = "false" ]; then
  echo "[pi-talk] ⚠️  gateway 未在线，尝试启动..."
  "$OPENCLAW" gateway start &
  sleep 5
  if "$OPENCLAW" gateway status 2>/dev/null | grep -q "running\|online"; then
    echo "[pi-talk] ✅ gateway 启动成功"
  else
    echo "[pi-talk] ❌ gateway 启动失败，Pi 节点将不可用（pi-talk 继续启动）"
  fi
else
  echo "[pi-talk] ✅ gateway 在线"
fi

# ── 启动 Pi-Talk Server ────────────────────────────────────────────────────
fuser -k 3456/tcp 2>/dev/null
sleep 1

exec /home/nanhara/.nvm/versions/node/v22.22.0/bin/node server.js
