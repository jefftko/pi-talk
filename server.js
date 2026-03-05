/**
 * Pi-Talk server.js — v5 极简版
 * Pi 只负责：录音 → 发 Mac mini → 显示文字 → 播放音频
 * 所有处理（Whisper + AI + TTS）全在 Mac mini 的 pipeline.js 完成
 */

const express  = require('express');
const multer   = require('multer');
const { execSync, exec, spawnSync } = require('child_process');
const fs   = require('fs');
const path = require('path');
const https = require('https');
const WebSocket = require('ws');

const app  = express();
const PORT = 3456;
const UPLOAD_DIR = '/tmp/pi-talk';
const CERT_DIR   = path.join(__dirname, 'certs');

if (!fs.existsSync(UPLOAD_DIR)) fs.mkdirSync(UPLOAD_DIR, { recursive: true });
if (!fs.existsSync(CERT_DIR))   fs.mkdirSync(CERT_DIR,   { recursive: true });

// ── TLS ──────────────────────────────────────────────────────────────────────
const keyPath  = path.join(CERT_DIR, 'server.key');
const certPath = path.join(CERT_DIR, 'server.cert');
if (!fs.existsSync(keyPath)) {
  try {
    execSync(`openssl req -x509 -newkey rsa:2048 -keyout ${keyPath} -out ${certPath} -days 3650 -nodes -subj "/CN=pi-talk" -addext "subjectAltName=IP:127.0.0.1,IP:192.168.6.187,DNS:localhost"`, { stdio: 'pipe' });
  } catch {
    execSync(`openssl req -x509 -newkey rsa:2048 -keyout ${keyPath} -out ${certPath} -days 3650 -nodes -subj "/CN=pi-talk"`, { stdio: 'pipe' });
  }
}

const httpsServer = https.createServer({ key: fs.readFileSync(keyPath), cert: fs.readFileSync(certPath) }, app);
const wss    = new WebSocket.Server({ server: httpsServer });
const upload = multer({ dest: UPLOAD_DIR });

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// ── WebSocket ─────────────────────────────────────────────────────────────────
const clients = new Set();
wss.on('connection', ws => {
  clients.add(ws);
  ws.on('close', () => clients.delete(ws));
});
function broadcast(obj) {
  const msg = JSON.stringify(obj);
  clients.forEach(ws => { if (ws.readyState === WebSocket.OPEN) ws.send(msg); });
}

// ── 互斥锁 ───────────────────────────────────────────────────────────────────
let processing = false;

// ── POST /api/audio ───────────────────────────────────────────────────────────
app.post('/api/audio', upload.single('audio'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No audio' });
  if (processing) {
    fs.unlinkSync(req.file.path);
    return res.status(429).json({ error: 'Busy' });
  }
  processing = true;
  broadcast({ type: 'state', state: 'thinking' });

  try {
    // 1. 转 WAV
    const wavPath = req.file.path + '.wav';
    execSync(`ffmpeg -y -i ${req.file.path} -ar 16000 -ac 1 ${wavPath} 2>/dev/null`);
    fs.unlinkSync(req.file.path);

    // 2. SCP 到 Mac mini
    execSync(`scp -o ConnectTimeout=5 ${wavPath} ai-home:/tmp/pi-input.wav 2>/dev/null`);
    fs.unlinkSync(wavPath);

    // 3. Mac mini 全流程处理（Whisper + AI + TTS）
    //    pipeline.js 先输出 JSON，再生成 TTS
    const result = spawnSync(
      'ssh', ['-o', 'ConnectTimeout=10', 'ai-home',
        'node /Users/zhujianbo/clawd/pi/pi-talk/pi-brain/pipeline.js'],
      { timeout: 150000, encoding: 'utf-8' }
    );

    if (result.error) throw result.error;

    // pipeline.js 输出 JSON（第一行）
    const jsonLine = (result.stdout || '').split('\n').find(l => l.trim().startsWith('{'));
    if (!jsonLine) throw new Error('pipeline: no JSON output\n' + (result.stderr || ''));

    const data = JSON.parse(jsonLine);
    const { transcript, reply } = data;

    if (!transcript) {
      broadcast({ type: 'state', state: 'idle' });
      processing = false;
      return res.json({ transcript: '', reply: '' });
    }

    // 4. 立即返回文字（TTS 也已完成，因为 pipeline 是同步的）
    broadcast({ type: 'state', state: 'speaking' });
    res.json({ transcript, reply });

    // 5. 拉取音频并播放
    const audioOut = path.join(UPLOAD_DIR, `reply-${Date.now()}.wav`);
    const scp = spawnSync('scp', ['-o', 'ConnectTimeout=5', 'ai-home:/tmp/pi-output.wav', audioOut],
      { timeout: 15000 });

    if (!scp.error && fs.existsSync(audioOut) && fs.statSync(audioOut).size > 1000) {
      exec(`XDG_RUNTIME_DIR=/run/user/1000 pw-play ${audioOut}`, { timeout: 60000 }, () => {
        broadcast({ type: 'state', state: 'idle' });
        try { fs.unlinkSync(audioOut); } catch {}
        processing = false;
      });
    } else {
      broadcast({ type: 'state', state: 'idle' });
      processing = false;
    }

  } catch (err) {
    console.error('Error:', err.message);
    broadcast({ type: 'state', state: 'idle' });
    processing = false;
    if (!res.headersSent) res.status(500).json({ error: err.message });
  }
});

// ── GET /api/history ──────────────────────────────────────────────────────────
app.get('/api/history', (req, res) => {
  try {
    const h = JSON.parse(require('fs').readFileSync('/tmp/pi-conversation-cache.json', 'utf-8'));
    res.json(h);
  } catch { res.json([]); }
});

// ── POST /api/trigger-record (唤醒词触发录音) ─────────────────────────────────
app.post('/api/trigger-record', (req, res) => {
  if (processing) return res.status(429).json({ ok: false, error: 'Busy' });

  console.log('🔔 唤醒词触发录音');

  // 通知浏览器开始录音（3秒自动停止）
  broadcast({ type: 'cmd', cmd: 'trigger-record', duration: 3000 });
  res.json({ ok: true });
});

// ── POST /api/remote-cmd ──────────────────────────────────────────────────────
app.post('/api/remote-cmd', (req, res) => {
  const { cmd, payload } = req.body || {};
  switch (cmd) {
    case 'vad-on':  broadcast({ type: 'cmd', cmd: 'vad-on' });  break;
    case 'vad-off': broadcast({ type: 'cmd', cmd: 'vad-off' }); break;
    case 'sleep':   broadcast({ type: 'cmd', cmd: 'sleep' });   break;
    case 'wake':    broadcast({ type: 'cmd', cmd: 'wake' });    break;
    default: return res.status(400).json({ error: 'Unknown cmd' });
  }
  res.json({ ok: true });
});

// ── POST /api/push-voice ──────────────────────────────────────────────────────
app.post('/api/push-voice', upload.single('audio'), (req, res) => {
  const file = req.file?.path;
  if (!file) return res.status(400).json({ error: 'No audio' });
  broadcast({ type: 'state', state: 'speaking' });
  exec(`XDG_RUNTIME_DIR=/run/user/1000 pw-play ${file}`, { timeout: 60000 }, () => {
    broadcast({ type: 'state', state: 'idle' });
    try { fs.unlinkSync(file); } catch {}
  });
  res.json({ ok: true });
});

// ── 启动 ──────────────────────────────────────────────────────────────────────
httpsServer.listen(PORT, '0.0.0.0', () => {
  console.log(`🦊 Pi-Talk v5 → https://0.0.0.0:${PORT}  (Mac mini 全处理)`);
});
