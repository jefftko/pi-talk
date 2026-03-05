#!/usr/bin/env python3
"""
南溪人脸识别服务 — OpenCV LBPH
从摄像头抓帧，识别 Jeff / 冬芹 / 汉青，POST 到 server.js
"""

import cv2
import os
import sys
import time
import json
import ssl
import urllib.request
import urllib.error
import signal

# ── 配置 ──────────────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.yml")
CASCADE_PATH = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml"
# Fallback cascade path
CASCADE_FALLBACK = os.path.join(os.path.dirname(__file__), "haarcascade_frontalface_default.xml")

CAMERA_DEVICE = 0  # /dev/video0
DETECT_INTERVAL = 3  # 每3秒识别一次
SERVER_URL = "https://localhost:3456/api/face-detect"

# 标签映射
LABEL_MAP = {
    0: "Jeff",
    1: "冬芹",
    2: "汉青",
}

CONFIDENCE_THRESHOLD = 80  # LBPH 距离阈值（越小越相似，低于此值认为识别成功）


# ── SSL 上下文（自签名证书） ──────────────────────────────────────────────────
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def report_face(name, confidence):
    """POST 识别结果到 server.js"""
    data = json.dumps({"name": name, "confidence": round(confidence)}).encode("utf-8")
    req = urllib.request.Request(
        SERVER_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=5, context=ssl_ctx)
        return json.loads(resp.read())
    except Exception as e:
        print(f"⚠️ 上报失败: {e}")
        return None


def main():
    print("🦊 南溪人脸识别服务启动")

    # 加载人脸检测器
    cascade_path = CASCADE_PATH if os.path.exists(CASCADE_PATH) else CASCADE_FALLBACK
    if not os.path.exists(cascade_path):
        print(f"❌ 找不到 Haar cascade: {cascade_path}")
        print("   请下载: https://github.com/opencv/opencv/raw/master/data/haarcascades/haarcascade_frontalface_default.xml")
        sys.exit(1)

    face_cascade = cv2.CascadeClassifier(cascade_path)
    print(f"✅ Haar cascade 加载: {cascade_path}")

    # 加载 LBPH 识别模型
    if not os.path.exists(MODEL_PATH):
        print(f"⚠️ 模型文件不存在: {MODEL_PATH}")
        print("   请先运行 train.py 训练模型")
        print("   当前仅做人脸检测（不识别身份）")
        recognizer = None
    else:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(MODEL_PATH)
        print(f"✅ LBPH 模型加载: {MODEL_PATH}")

    # 打开摄像头
    cap = cv2.VideoCapture(CAMERA_DEVICE)
    if not cap.isOpened():
        print(f"❌ 无法打开摄像头 /dev/video{CAMERA_DEVICE}")
        sys.exit(1)
    print(f"✅ 摄像头已打开: /dev/video{CAMERA_DEVICE}")

    # 设置较低分辨率加速
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

    # 优雅退出
    running = True

    def handle_signal(sig, frame):
        nonlocal running
        print("\n🛑 收到退出信号")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"🔍 每 {DETECT_INTERVAL}s 识别一次，Ctrl+C 退出")
    print("─" * 40)

    last_name = None

    try:
        while running:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ 摄像头读取失败，重试...")
                time.sleep(1)
                continue

            # 转灰度
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 检测人脸
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(60, 60),
            )

            if len(faces) > 0:
                # 取最大的人脸
                largest = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = largest

                face_roi = gray[y : y + h, x : x + w]
                face_resized = cv2.resize(face_roi, (200, 200))

                if recognizer is not None:
                    label, distance = recognizer.predict(face_resized)
                    # LBPH distance: 越小越相似
                    confidence = max(0, 100 - distance)  # 转换为 0-100 置信度

                    if distance < CONFIDENCE_THRESHOLD:
                        name = LABEL_MAP.get(label, "未知")
                    else:
                        name = "未知"
                        confidence = 0
                else:
                    name = "检测到人脸"
                    confidence = 0

                if name != last_name or name != "未知":
                    print(f"👤 {name} (置信度: {confidence:.0f}%)")
                    report_face(name, confidence)
                    last_name = name
            else:
                if last_name is not None:
                    last_name = None

            time.sleep(DETECT_INTERVAL)

    finally:
        cap.release()
        print("📷 摄像头已关闭")


if __name__ == "__main__":
    main()
