#!/usr/bin/env python3
"""
TTS HTTP Server — 持久化 Qwen3-TTS，避免每次重新加载模型
端口: 18790
"""

import os
import json
import shutil
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

REF_AUDIO = '/Volumes/Jeff2TEXTEND1/video/nanhara/assets/voice/ref_audio_linzhiling.wav'
REF_TEXT  = '这个附家是一个非常传统的可能大家看到以前那个叫哆啦咩看小贝比很多人都会讲说是女婆婆和婆婆相处非常自在思路也很清晰了我一位母亲'
MODEL_ID  = 'mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit'
PORT      = 18790

# 全局模型（只加载一次）
model = None
model_lock = threading.Lock()

def load():
    global model
    print(f'[tts_server] 加载模型 {MODEL_ID} ...')
    from mlx_audio.tts.utils import load_model
    model = load_model(MODEL_ID)
    print('[tts_server] 模型加载完成，ready.')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默日志

    def do_GET(self):
        if self.path == '/health':
            self._json(200, {'ok': True, 'model': MODEL_ID})
        else:
            self._json(404, {'ok': False, 'error': 'not found'})

    def do_POST(self):
        if self.path != '/tts':
            self._json(404, {'ok': False, 'error': 'not found'})
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except Exception:
            self._json(400, {'ok': False, 'error': 'invalid json'})
            return

        text   = data.get('text', '').strip()
        output = data.get('output', '/tmp/pi-output.wav')

        if not text:
            self._json(400, {'ok': False, 'error': 'text required'})
            return

        try:
            with model_lock:
                from mlx_audio.tts.generate import generate_audio
                prefix = '/tmp/pi-tts-server-out'
                generate_audio(
                    model=model,
                    text=text,
                    ref_audio=REF_AUDIO,
                    ref_text=REF_TEXT,
                    file_prefix=prefix,
                    lang='zh'
                )
                gen_file = prefix + '_000.wav'
                if os.path.exists(gen_file):
                    shutil.copy(gen_file, output)
                    self._json(200, {'ok': True, 'path': output})
                else:
                    self._json(500, {'ok': False, 'error': 'output file not found'})
        except Exception as e:
            self._json(500, {'ok': False, 'error': str(e)})

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

if __name__ == '__main__':
    load()
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    print(f'[tts_server] 监听 http://127.0.0.1:{PORT}')
    server.serve_forever()
