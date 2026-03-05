# Pi-Talk 🦊

南溪（Nanhara）语音交互系统 — 运行在办公室 Raspberry Pi 400 上的 AI 语音助手。

## 架构

```
Pi（录音 / 显示 / 播放）
  → SSH → Mac mini（pi-brain/pipeline.js）
    → Whisper STT（本地离线）
    → AI（OpenClaw Gateway → Claude Sonnet）
    → Qwen3-TTS 声音克隆
  ← Pi 播放音频 + 显示文字
```

## 文件结构

```
server.js            Pi 端 HTTPS 服务器（含 WebSocket 广播 + face-detect API）
public/
  index.html         前端界面（南溪狐狸形象）
pi-brain/
  pipeline.js        Mac mini 全流程处理脚本（Whisper → AI → TTS）
pi-wake/             唤醒词检测（sherpa-onnx）
pi-face/             人脸识别（OpenCV LBPH）
pi-talk.service      systemd 服务文件
voices/              参考音频样本（gitignored）
start.sh             Pi 启动脚本
```

## 环境变量

复制 `.env.example` 为 `.env` 并填入：

```bash
DEEPSEEK_KEY=your-deepseek-key
LINEAR_KEY=your-linear-api-key
```

`pi-brain/` 目录同样需要 `.env`，参考 `pi-brain/.env.example`（如有）。

## 部署

### 前置条件

- Raspberry Pi 400（或其他 ARM Pi），安装 Node.js 18+
- Mac mini（或任意主机）运行 `pi-brain/pipeline.js`
- Pi → Mac mini SSH 免密登录（`~/.ssh/config` 中配置 `Host ai-home`）
- Mac mini 安装：`whisper-cli`、`ffmpeg`、Python 环境（含 mlx-audio）

### Pi 端

```bash
# 克隆项目
git clone https://github.com/jefftko/pi-talk.git ~/pi-talk
cd ~/pi-talk

npm install

# 生成自签名证书（首次运行自动生成）
node server.js
```

### Mac mini 端

```bash
cd pi-brain
npm install
# pipeline.js 由 Pi 通过 SSH 远程调用，无需手动启动
```

## 模块状态

- [x] `pi-wake/` — 唤醒词检测（sherpa-onnx，关键词"南溪南溪"，代码+依赖已部署）
- [x] `pi-face/` — 人脸识别框架（OpenCV LBPH，代码已写，待采集样本训练）
- [x] systemd 服务（pi-talk.service 已启用运行，pi-wake.service 等模型下载完启用）

### 待完成

- [ ] sherpa-onnx KWS 模型下载（Pi 后台下载中，约 45MB）
- [ ] pi-face 人脸样本采集 + 训练（需人在场）
- [ ] pi-wake 首次实际唤醒测试（需麦克风+模型就绪）

## License

MIT
