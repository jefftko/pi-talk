# Pi-Talk Code Review 风格指南

## 项目背景
Pi-Talk 是一个树莓派 AI 语音助手，Mac mini 作为主脑（Whisper + Claude + TTS），Pi 作为 IO 设备。

## Review 重点

### 安全
- `pipeline.js` 涉及身份验证（人脸识别 + 每日暗语），修改时严格检查
- 不允许绕过 `FACE_STATE_FILE` 或 `AUTH_PASSPHRASE` 验证

### 性能
- TTS 调用优先走 HTTP Server（port 18790），fallback 才 spawn Python
- 避免同步阻塞主流程（execSync 只用在必要地方）
- Quick Reply 匹配必须在 TTS 之前执行

### 代码质量
- Node.js 异步用 async/await，不用 callback
- Python 文件用 conda `zimage` 环境
- 错误要有 fallback，不能让整个 pipeline 崩掉

### 不需要 review 的内容
- `.env` 文件（不会进 repo）
- `assets/quick-replies/*.wav`（二进制音频文件）
- `node_modules/`
