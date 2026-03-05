#!/bin/bash
# Pi-Face 安装脚本 — 在 Raspberry Pi 上执行
set -e

echo "🦊 安装 Pi-Face 人脸识别依赖..."

# 方式1: 系统包（推荐，Pi 上更稳定）
echo "📦 安装 OpenCV 系统包..."
sudo apt-get update -qq
sudo apt-get install -y python3-opencv

# 检查 opencv-contrib（LBPH 在 contrib 中）
python3 -c "import cv2; cv2.face.LBPHFaceRecognizer_create()" 2>/dev/null && {
    echo "✅ OpenCV + contrib 可用"
} || {
    echo "⚠️ 系统包缺少 contrib，尝试 pip 安装..."
    pip3 install opencv-contrib-python-headless --break-system-packages || \
    pip3 install opencv-contrib-python-headless
}

# 下载 Haar cascade（如果不存在）
CASCADE="/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml"
LOCAL_CASCADE="$(dirname $0)/haarcascade_frontalface_default.xml"
if [ ! -f "$CASCADE" ] && [ ! -f "$LOCAL_CASCADE" ]; then
    echo "📥 下载 Haar cascade..."
    wget -q -O "$LOCAL_CASCADE" \
        https://github.com/opencv/opencv/raw/master/data/haarcascades/haarcascade_frontalface_default.xml
fi

echo "✅ Pi-Face 安装完成！"
echo ""
echo "下一步："
echo "  1. 在 samples/{Jeff,dongqin,hanqing}/ 放入人脸照片"
echo "  2. 运行 python3 train.py 训练模型"
echo "  3. 运行 python3 face_recognition_service.py 启动服务"
