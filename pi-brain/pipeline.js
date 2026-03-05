#!/usr/bin/env node
/**
 * pi-brain/pipeline.js — Mac mini 全流程处理脚本 v2
 * Pi 通过 SSH 调用：ssh ai-home 'node ~/clawd/pi/pi-talk/pi-brain/pipeline.js'
 * 输入: /tmp/pi-input.wav（Pi 已 SCP 过来）
 * 输出: stdout JSON { transcript, reply }  +  /tmp/pi-output.wav（TTS 音频）
 *
 * v2 改动:
 * - AI: OpenClaw Gateway (Claude Sonnet) → fallback DeepSeek
 * - 注入 MEMORY.md / USER.md / SOUL.md 上下文
 * - 工具支持: 天气 / 时间 / Linear 今日任务
 */

const { execSync, spawnSync } = require('child_process');
const fs   = require('fs');
const path = require('path');

// ─── 配置 ────────────────────────────────────────────────────────────────────
// 从环境变量或 .env 文件读取 key
require('dotenv').config({ path: path.join(__dirname, '../.env') });
const DEEPSEEK_KEY  = process.env.DEEPSEEK_KEY  || '';
const LINEAR_KEY    = process.env.LINEAR_KEY    || '';
const HISTORY_FILE  = '/tmp/pi-conversation.json';
const INPUT_WAV     = '/tmp/pi-input.wav';
const OUTPUT_WAV    = '/tmp/pi-output.wav';
const WHISPER_MODEL = '/Users/zhujianbo/work/projects/ai/EchoNote/models/ggml-large-v3-turbo-q8_0.bin';

// OpenClaw Gateway - 走 main agent（Pi = IO设备，南溪统一处理，有全套工具）
const OPENCLAW_CONFIG = '/Users/zhujianbo/.openclaw/openclaw.json';
const GATEWAY_URL     = 'http://localhost:18789/v1/chat/completions';
const GATEWAY_MODEL   = 'openclaw:main';

// 记忆文件
const MEMORY_MD = '/Users/zhujianbo/clawd/MEMORY.md';
const USER_MD   = '/Users/zhujianbo/clawd/USER.md';
const SOUL_MD   = '/Users/zhujianbo/clawd/SOUL.md';

// ─── 工具函数 ────────────────────────────────────────────────────────────────

function readTail(filePath, lines = 200) {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const all = content.split('\n');
    return all.slice(-lines).join('\n');
  } catch { return ''; }
}

function readFile(filePath) {
  try { return fs.readFileSync(filePath, 'utf-8'); } catch { return ''; }
}

function getGatewayToken() {
  try {
    const cfg = JSON.parse(fs.readFileSync(OPENCLAW_CONFIG, 'utf-8'));
    return cfg?.gateway?.auth?.token || '';
  } catch { return ''; }
}

// ─── 工具识别 ────────────────────────────────────────────────────────────────

function detectIntent(text) {
  const intents = [];
  if (/天气|下雨|温度|多少度|穿什么|外面|气温/.test(text)) intents.push('weather');
  if (/几点|时间|现在|今天几号|日期|星期/.test(text))       intents.push('time');
  if (/任务|todo|今天|待办|工作|Linear/.test(text))         intents.push('linear');
  return intents;
}

async function fetchWeather() {
  try {
    const result = execSync('curl -s "wttr.in/无锡?format=3"', { timeout: 8000, encoding: 'utf-8' });
    return result.trim();
  } catch { return '天气获取失败'; }
}

async function fetchLinearTasks() {
  const query = `{
    issues(filter: {
      team: { key: { eq: "JEF" } },
      state: { type: { in: ["unstarted", "started"] } }
    }, first: 10, orderBy: updatedAt) {
      nodes { title state { name } priority }
    }
  }`;
  try {
    const resp = await fetch('https://api.linear.app/graphql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': LINEAR_KEY },
      body: JSON.stringify({ query }),
      signal: AbortSignal.timeout(8000),
    });
    const data = await resp.json();
    const issues = data?.data?.issues?.nodes || [];
    if (issues.length === 0) return '今日无待办任务';
    return issues.map(i => `- [${i.state.name}] ${i.title}`).join('\n');
  } catch { return 'Linear 任务获取失败'; }
}

// ─── AI 调用 ─────────────────────────────────────────────────────────────────

async function callGateway(messages) {
  const token = getGatewayToken();
  if (!token) throw new Error('no gateway token');
  const resp = await fetch(GATEWAY_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ model: GATEWAY_MODEL, messages, max_tokens: 300 }),
    signal: AbortSignal.timeout(25000),
  });
  const data = await resp.json();
  const content = data.choices?.[0]?.message?.content?.trim();
  if (!content) throw new Error('empty response from gateway');
  return content;
}

async function callDeepSeek(messages) {
  const resp = await fetch('https://api.deepseek.com/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${DEEPSEEK_KEY}` },
    body: JSON.stringify({ model: 'deepseek-chat', messages, max_tokens: 250 }),
    signal: AbortSignal.timeout(25000),
  });
  const data = await resp.json();
  return data.choices?.[0]?.message?.content?.trim() || '';
}

// ─── 主流程 ──────────────────────────────────────────────────────────────────

async function main() {
  // 1. Whisper STT
  let transcript = '';
  try {
    transcript = execSync(
      `/opt/homebrew/bin/whisper-cli -m ${WHISPER_MODEL} -l zh -f ${INPUT_WAV} --no-timestamps 2>/dev/null`,
      { timeout: 60000, encoding: 'utf-8' }
    ).trim();
  } catch (e) {
    process.stdout.write(JSON.stringify({ error: 'whisper failed: ' + e.message }));
    process.exit(1);
  }

  if (!transcript || transcript.length < 2) {
    process.stdout.write(JSON.stringify({ transcript: '', reply: '' }));
    process.exit(0);
  }

  // 2. 构建 system prompt（Pi = IO设备，走 main agent，无需手动注入记忆）
  // main agent 自带完整工具集（Linear、天气、执行任务等）
  const now = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
  const systemPrompt = `【Pi语音输入】这条消息来自办公室树莓派语音助手，不是 Telegram。
当前时间：${now}
办公室成员：Jeff（老板）、冬芹（女同事）、汉青（男同事）

回复要求（TTS朗读，严格遵守）：
1. 动作/神态用（）：（歪头看了看你）— 会显示在屏幕，不朗读
2. 说话内容用""：简洁口语，2-4句，温暖俏皮 — 会朗读
3. 数据/代码用【】— 只显示不朗读
不要用 markdown，不要回复 Telegram。`;

  // 5. 构建消息（main agent 自维护 session 历史，这里只传当前轮）
  const messages = [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: transcript },
  ];

  // 6. AI 调用: Gateway (Sonnet) → fallback DeepSeek
  let reply = '（挠挠头）没想好，再问我一次吧～';
  let usedModel = 'none';

  try {
    reply = await callGateway(messages);
    usedModel = 'gateway';
  } catch (e1) {
    process.stderr.write(`Gateway failed (${e1.message}), falling back to DeepSeek\n`);
    try {
      reply = await callDeepSeek(messages);
      usedModel = 'deepseek';
    } catch (e2) {
      process.stderr.write(`DeepSeek also failed: ${e2.message}\n`);
    }
  }

  // 7. 先输出文字
  process.stdout.write(JSON.stringify({ transcript, reply, model: usedModel }) + '\n');

  // 9. TTS (Qwen3-TTS MLX, 声音克隆)
  const spokenParts = [];
  const qr = /["""]([^"""]+)["""]/g; let m;
  while ((m = qr.exec(reply)) !== null) spokenParts.push(m[1]);
  const ttsText = (spokenParts.length > 0
    ? spokenParts.join('，')
    : reply.replace(/（[^）]*）/g, '').replace(/【[^】]*】/g, ''))
    .replace(/["""]/g, '').replace(/\n/g, ' ').trim().substring(0, 400);

  if (ttsText) {
    const prefix = '/tmp/pi-tts-out';
    const pyCode = [
      `from mlx_audio.tts.utils import load_model`,
      `from mlx_audio.tts.generate import generate_audio`,
      `model = load_model('mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit')`,
      `generate_audio(model=model, text=${JSON.stringify(ttsText)},`,
      `  ref_audio='/Volumes/Jeff2TEXTEND1/video/nanhara/assets/voice/ref_audio_linzhiling.wav',`,
      `  ref_text='这个附家是一个非常传统的可能大家看到以前那个叫哆啦咩看小贝比很多人都会讲说是女婆婆和婆婆相处非常自在思路也很清晰了我一位母亲',`,
      `  file_prefix='${prefix}', lang='zh')`,
    ].join('\n');

    try {
      fs.writeFileSync('/tmp/pi-tts.py', pyCode);
      execSync(`/Users/zhujianbo/miniforge3/envs/zimage/bin/python3 /tmp/pi-tts.py`, { timeout: 120000 });
      if (fs.existsSync(prefix + '_000.wav')) {
        fs.copyFileSync(prefix + '_000.wav', OUTPUT_WAV);
      }
    } catch (e) {
      process.stderr.write('TTS failed: ' + e.message + '\n');
    }
  }
}

main().catch(e => {
  process.stdout.write(JSON.stringify({ error: e.message }));
  process.exit(1);
});
