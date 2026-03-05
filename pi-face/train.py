#!/usr/bin/env python3
"""
LBPH 人脸识别模型训练
从 samples/{name}/ 目录读取人脸图片，训练模型保存为 model.yml
"""

import cv2
import os
import sys
import numpy as np

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")
MODEL_OUTPUT = os.path.join(os.path.dirname(__file__), "model.yml")
CASCADE_PATH = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml"
CASCADE_FALLBACK = os.path.join(os.path.dirname(__file__), "haarcascade_frontalface_default.xml")

# 标签映射（与 face_recognition_service.py 一致）
NAME_TO_LABEL = {
    "Jeff": 0,
    "dongqin": 1,
    "hanqing": 2,
}

FACE_SIZE = (200, 200)


def main():
    print("🦊 LBPH 人脸模型训练")
    print(f"   样本目录: {SAMPLES_DIR}")
    print(f"   输出模型: {MODEL_OUTPUT}")
    print()

    # 加载 Haar cascade
    cascade_path = CASCADE_PATH if os.path.exists(CASCADE_PATH) else CASCADE_FALLBACK
    if not os.path.exists(cascade_path):
        print(f"❌ 找不到 Haar cascade: {cascade_path}")
        sys.exit(1)
    face_cascade = cv2.CascadeClassifier(cascade_path)

    faces = []
    labels = []

    for name, label in NAME_TO_LABEL.items():
        person_dir = os.path.join(SAMPLES_DIR, name)
        if not os.path.isdir(person_dir):
            print(f"⚠️ 目录不存在: {person_dir}，跳过")
            continue

        images = [
            f
            for f in os.listdir(person_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))
        ]

        if not images:
            print(f"⚠️ {name}: 无样本图片，跳过")
            continue

        count = 0
        for img_name in images:
            img_path = os.path.join(person_dir, img_name)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"  ⚠️ 无法读取: {img_path}")
                continue

            # 检测人脸
            detected = face_cascade.detectMultiScale(
                img, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            if len(detected) == 0:
                # 如果检测不到人脸，把整张图作为人脸（可能已裁剪过）
                face_resized = cv2.resize(img, FACE_SIZE)
                faces.append(face_resized)
                labels.append(label)
                count += 1
            else:
                for x, y, w, h in detected:
                    face_roi = img[y : y + h, x : x + w]
                    face_resized = cv2.resize(face_roi, FACE_SIZE)
                    faces.append(face_resized)
                    labels.append(label)
                    count += 1

        print(f"✅ {name}: {count} 个人脸样本")

    if not faces:
        print("\n❌ 没有可用的训练样本！")
        print("   请在以下目录放入人脸照片：")
        for name in NAME_TO_LABEL:
            print(f"   - {SAMPLES_DIR}/{name}/")
        sys.exit(1)

    # 训练 LBPH 模型
    print(f"\n🔧 训练 LBPH 模型（{len(faces)} 个样本）...")
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    recognizer.write(MODEL_OUTPUT)
    print(f"✅ 模型已保存: {MODEL_OUTPUT}")


if __name__ == "__main__":
    main()
