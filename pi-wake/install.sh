#!/bin/bash
# ══════════════════════════════════════════════════════
# 南溪唤醒词 — Pi 安装脚本
# 在 Raspberry Pi 上执行: bash install.sh
# ══════════════════════════════════════════════════════
set -e

echo "🦊 南溪唤醒词安装开始..."
echo ""

# 1. 安装 Python 依赖
echo "📦 安装 Python 包..."
pip3 install --user sherpa-onnx pyaudio requests

# 2. 下载 sherpa-onnx 中文 KWS 模型
MODEL_DIR="$HOME/sherpa-models"
MODEL_TAR="sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01"
MODEL_URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/${MODEL_TAR}.tar.bz2"

if [ -f "$MODEL_DIR/encoder.onnx" ]; then
    echo "✅ 模型已存在，跳过下载"
else
    echo "📥 下载中文 KWS 模型..."
    mkdir -p "$MODEL_DIR"
    cd "$MODEL_DIR"
    wget -q --show-progress "$MODEL_URL"
    echo "📦 解压模型..."
    tar xf "${MODEL_TAR}.tar.bz2"
    cp "${MODEL_TAR}"/* "$MODEL_DIR/"
    rm -rf "${MODEL_TAR}" "${MODEL_TAR}.tar.bz2"
    echo "✅ 模型下载完成"
fi

# 3. 确保提示音存在
ASSETS_DIR="$HOME/pi-talk/assets"
DING_WAV="$ASSETS_DIR/ding.wav"
if [ ! -f "$DING_WAV" ]; then
    echo "🔔 生成默认提示音..."
    mkdir -p "$ASSETS_DIR"
    # 用 sox 生成一个简单的 ding 音效（如果有 sox）
    if command -v sox &> /dev/null; then
        sox -n "$DING_WAV" synth 0.3 sine 880 fade l 0 0.3 0.1 vol 0.5
    else
        echo "⚠️ sox 未安装，请手动放置 ding.wav 到 $DING_WAV"
        echo "   安装 sox: sudo apt install sox"
    fi
fi

# 4. 安装 systemd 服务（可选）
echo ""
read -p "是否安装 systemd 服务（开机自启）? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    UNIT_SRC="$HOME/pi-talk/pi-wake/pi-wake.service"
    UNIT_DST="/etc/systemd/system/pi-wake.service"
    if [ -f "$UNIT_SRC" ]; then
        sudo cp "$UNIT_SRC" "$UNIT_DST"
        sudo systemctl daemon-reload
        sudo systemctl enable pi-wake
        sudo systemctl start pi-wake
        echo "✅ systemd 服务已安装并启动"
    else
        echo "❌ 找不到 $UNIT_SRC"
    fi
fi

echo ""
echo "══════════════════════════════════════════"
echo "✅ 安装完成！"
echo ""
echo "手动测试: python3 ~/pi-talk/pi-wake/wake.py"
echo "查看服务: sudo systemctl status pi-wake"
echo "查看日志: journalctl -u pi-wake -f"
echo "══════════════════════════════════════════"
