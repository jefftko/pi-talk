#!/bin/bash
# 启动 TTS HTTP Server（持久化，模型只加载一次）
source ~/miniforge3/etc/profile.d/conda.sh
conda activate zimage
python ~/work/projects/tools/pi-talk/pi-brain/tts_server.py
