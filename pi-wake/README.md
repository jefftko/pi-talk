# pi-wake — 南溪唤醒词检测

用 sherpa-onnx 离线关键词检测实现 "南溪南溪" 唤醒词，运行在 Raspberry Pi 400 上。

## 工作流程

```
麦克风持续监听 → sherpa-onnx 检测 "南溪南溪"
    → 播放 ding 提示音
    → POST /api/trigger-record (触发浏览器录音)
    → 冷却 5s → 继续监听
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `wake.py` | 主程序，sherpa-onnx 关键词监听 |
| `keywords.txt` | 关键词配置（南溪南溪） |
| `install.sh` | Pi 安装脚本（依赖 + 模型下载） |
| `pi-wake.service` | systemd 开机自启服务 |

## 安装

```bash
# 在 Pi 上执行
cd ~/pi-talk/pi-wake
bash install.sh
```

## 手动测试

```bash
python3 ~/pi-talk/pi-wake/wake.py
```

## 服务管理

```bash
sudo systemctl start pi-wake    # 启动
sudo systemctl stop pi-wake     # 停止
sudo systemctl status pi-wake   # 状态
journalctl -u pi-wake -f        # 实时日志
```

## 配置

- **麦克风**: USB PnP Sound Device (card 2)
- **模型**: sherpa-onnx-kws-zipformer-wenetspeech-3.3M
- **采样率**: 16000 Hz
- **冷却时间**: 5 秒（防误触）
- **提示音**: `~/pi-talk/assets/ding.wav`

## 依赖

- Python 3
- sherpa-onnx
- PyAudio
- ALSA / PipeWire（音频播放）
