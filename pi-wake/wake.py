#!/usr/bin/env python3
"""
南溪唤醒词检测 — sherpa-onnx keyword spotting
检测到 "南溪南溪" 后播放提示音并触发 Pi-Talk 录音
"""

import sys
import time
import signal
import subprocess
import urllib.request
import urllib.error
import ssl
import json

try:
    import sherpa_onnx
except ImportError:
    print("❌ sherpa-onnx 未安装，请执行: pip3 install sherpa-onnx")
    sys.exit(1)

# ── 配置 ──────────────────────────────────────────────────────────────────────
MODEL_DIR = "/home/nanhara/sherpa-models"
KEYWORDS_FILE = "/home/nanhara/pi-talk/pi-wake/keywords.txt"
DING_WAV = "/home/nanhara/pi-talk/assets/ding.wav"
TRIGGER_URL = "https://localhost:3456/api/trigger-record"

SAMPLE_RATE = 16000
SAMPLES_PER_READ = 1600  # 100ms chunks
COOLDOWN_SECS = 5  # 检测到唤醒词后冷却时间

# 麦克风设备 — card 2 (USB PnP Sound Device)
MIC_DEVICE = "plughw:2,0"

# ── 初始化 sherpa-onnx ────────────────────────────────────────────────────────
def create_keyword_spotter():
    config = sherpa_onnx.KeywordSpotterConfig(
        feat_config=sherpa_onnx.FeatureExtractorConfig(
            sample_rate=SAMPLE_RATE,
            feature_dim=80,
        ),
        model_config=sherpa_onnx.OnlineTransducerModelConfig(
            encoder=f"{MODEL_DIR}/encoder.onnx",
            decoder=f"{MODEL_DIR}/decoder.onnx",
            joiner=f"{MODEL_DIR}/joiner.onnx",
            tokens=f"{MODEL_DIR}/tokens.txt",
        ),
        keywords_file=KEYWORDS_FILE,
        keywords_score=1.5,
        keywords_threshold=0.25,
        num_trailing_blanks=1,
    )
    return sherpa_onnx.KeywordSpotter(config)


# ── 播放提示音 ────────────────────────────────────────────────────────────────
def play_ding():
    """播放 ding 提示音（非阻塞）"""
    try:
        # 优先 pw-play (PipeWire)，fallback aplay (ALSA)
        subprocess.Popen(
            ["pw-play", DING_WAV],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        try:
            subprocess.Popen(
                ["aplay", DING_WAV],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            print("⚠️ 无法播放提示音：pw-play 和 aplay 都不可用")


# ── 触发录音 ──────────────────────────────────────────────────────────────────
def trigger_record():
    """POST 到 server.js 触发录音"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # 自签名证书

    req = urllib.request.Request(
        TRIGGER_URL,
        data=json.dumps({"source": "wake"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=5, context=ctx)
        body = json.loads(resp.read())
        if body.get("ok"):
            print("✅ 录音已触发")
        else:
            print(f"⚠️ 触发响应异常: {body}")
    except urllib.error.URLError as e:
        print(f"❌ 触发录音失败: {e}")
    except Exception as e:
        print(f"❌ 触发录音异常: {e}")


# ── 麦克风流 (ALSA) ───────────────────────────────────────────────────────────
def open_microphone():
    """用 PyAudio 打开 ALSA 麦克风"""
    import pyaudio

    pa = pyaudio.PyAudio()

    # 查找 USB PnP Sound Device (card 2)
    target_idx = None
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        name = info.get("name", "")
        if "USB PnP" in name or "plughw:2" in name or "hw:2" in name:
            if info["maxInputChannels"] > 0:
                target_idx = i
                print(f"🎤 找到麦克风: [{i}] {name}")
                break

    if target_idx is None:
        # fallback: 用默认输入设备
        print("⚠️ 未找到 USB PnP 麦克风，使用默认输入设备")
        target_idx = None  # PyAudio 会用 default

    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=target_idx,
        frames_per_buffer=SAMPLES_PER_READ,
    )
    return pa, stream


# ── 主循环 ────────────────────────────────────────────────────────────────────
def main():
    print("🦊 南溪唤醒词检测启动")
    print(f"   模型: {MODEL_DIR}")
    print(f"   关键词: {KEYWORDS_FILE}")
    print(f"   冷却时间: {COOLDOWN_SECS}s")
    print()

    kws = create_keyword_spotter()
    print("✅ sherpa-onnx 模型加载完成")

    pa, mic_stream = open_microphone()
    print("✅ 麦克风已打开，开始监听...")
    print("─" * 40)

    # 优雅退出
    running = True
    def handle_signal(sig, frame):
        nonlocal running
        print("\n🛑 收到退出信号，停止监听...")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    stream = kws.create_stream()
    last_trigger_time = 0

    try:
        while running:
            # 读取麦克风数据
            data = mic_stream.read(SAMPLES_PER_READ, exception_on_overflow=False)

            # int16 → float32
            import array
            samples = array.array("h", data)
            float_samples = [s / 32768.0 for s in samples]

            # 送入 sherpa-onnx
            stream.accept_waveform(SAMPLE_RATE, float_samples)

            while kws.is_ready(stream):
                kws.decode(stream)

            result = kws.get_result(stream)
            if result:
                keyword = result.strip()
                now = time.time()

                if now - last_trigger_time < COOLDOWN_SECS:
                    print(f"⏳ 冷却中，忽略: {keyword}")
                    continue

                print(f"🔔 检测到唤醒词: {keyword}")
                last_trigger_time = now

                # 1. 播放提示音
                play_ding()

                # 2. 触发录音
                trigger_record()

                # 3. 冷却等待
                print(f"⏳ 冷却 {COOLDOWN_SECS}s...")
                time.sleep(COOLDOWN_SECS)
                print("👂 继续监听...")

    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        pa.terminate()
        print("🔇 麦克风已关闭")


if __name__ == "__main__":
    main()
