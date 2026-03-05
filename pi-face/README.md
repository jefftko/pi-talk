# Pi-Face 🦊

人脸识别服务 — 运行在 Raspberry Pi 上，识别 Jeff / 冬芹 / 汉青。

## 架构

```
USB 摄像头 (/dev/video0)
  → OpenCV 人脸检测 (Haar cascade)
  → LBPH 人脸识别
  → POST https://localhost:3456/api/face-detect
  → server.js WebSocket 广播给前端
```

## 安装

```bash
# 在 Pi 上执行
bash install.sh
```

## 训练模型

1. 在 `samples/` 目录放入人脸照片：
   ```
   samples/
     Jeff/       ← Jeff 的正面照（10-20张）
     dongqin/    ← 冬芹的正面照
     hanqing/    ← 汉青的正面照
   ```
2. 运行训练：
   ```bash
   python3 train.py
   ```
3. 生成 `model.yml`

## 运行

```bash
python3 face_recognition_service.py
```

## 状态

- [x] 代码框架
- [ ] 待训练（需要人在场采集样本照片）
- [ ] 集成到 systemd 服务
