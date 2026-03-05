#!/bin/bash
# Pi-Talk 启动脚本
# 读取 .env 文件（如果存在）
ENV_FILE="$(dirname "$0")/.env"
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

cd "$(dirname "$0")"
fuser -k 3456/tcp 2>/dev/null
sleep 1

exec /home/nanhara/.nvm/versions/node/v22.22.0/bin/node server.js
