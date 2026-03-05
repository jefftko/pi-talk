# Pi-Talk 🦊

南溪语音交互系统 — 运行在办公室 Raspberry Pi 400 上。

## 架构

```
Pi（录音/显示/播放）
  → SSH → Mac mini pi-brain/pipeline.js
    → Whisper STT（本地）
    → OpenClaw Gateway → claude:pi-talk agent（Sonnet）
    → Qwen3-TTS（声音克隆）
  → Pi 播放音频 + 显示文字
```

## 文件结构

```
server.js          Pi 端 HTTPS 服务器（v5 极简版）
public/
  index.html       前端界面（南溪狐狸形象）
pi-brain/
  pipeline.js      Mac mini 全流程处理脚本
  server.js        旧版辅助服务（已废弃）
voices/            参考音频样本
start.sh           Pi 启动脚本
```

## 部署

### Pi 端
```bash
# 从 Mac mini 部署 server.js
scp ~/work/projects/tools/pi-talk/server.js nanhara@192.168.6.187:~/pi-talk/server.js

# 重启 Pi server（通过 OpenClaw RaspberryPi node）
# invokeCommand: system.run
# command: lsof -ti:3456 | xargs -r kill -9; sleep 1; cd ~/pi-talk && nohup node server.js > /tmp/pi-talk.log 2>&1 &
```

### Mac mini 端
```bash
# pipeline.js 直接在本机运行，Pi 通过 SSH 调用
# SSH key 已配置：Pi → Mac mini (ai-home)
```

## 配置

- Pi IP: `192.168.6.187`，端口 `3456`（HTTPS）
- Mac mini pipeline: `~/work/projects/tools/pi-talk/pi-brain/pipeline.js`
- OpenClaw agent: `openclaw:pi-talk`（gateway port 18789）
- 语音克隆: 林志玲音色（`ref_audio_linzhiling.wav`）

## 待开发

- [ ] `pi-wake/` — 唤醒词"南溪南溪"（sherpa-onnx）
- [ ] `pi-face/` — 人脸识别（LBPH，Jeff/冬芹/汉青）
- [ ] systemd 服务（开机自启）
