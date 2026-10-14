#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiMo 语音输入 —— 录音并转文字（MiMo-V2.5-ASR）

用法：
    python asr.py                # 弹出录音浮窗（macOS）/录音终端（Windows），点停止/按回车结束
    python asr.py --seconds 8    # 直接录 8 秒（不弹窗，适合自动化调用）
    python asr.py --file x.wav   # 转写已有音频文件（wav/mp3）
    python asr.py --lang en      # 指定语种 zh/en/auto（默认 zh）

结果：打印识别文字，并保存到 ~/tts-output/asr_last.txt
"""
import argparse
import base64
import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ConfigError, get_api_base, get_api_key

MODEL = "mimo-v2.5-asr"
OUT_DIR = os.path.expanduser("~/tts-output")
LAST_TXT = os.path.join(OUT_DIR, "asr_last.txt")


def transcribe(wav_path, lang="zh"):
    audio = base64.b64encode(open(wav_path, "rb").read()).decode()
    mime = "audio/mpeg" if str(wav_path).lower().endswith(".mp3") else "audio/wav"  # 别把 mp3 硬标成 wav
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "input_audio", "input_audio": {"data": f"data:{mime};base64,{audio}"}}]}],
        "asr_options": {"language": lang},
    }
    req = urllib.request.Request(
        get_api_base() + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {get_api_key()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        hint = ""
        if e.code == 401:
            hint = "\n   → Key 无效或网关不匹配：检查 setup.py 里配置的 Key 与网关"
        raise RuntimeError(f"API HTTP {e.code}：{detail}{hint}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"网络错误：{e.reason}")
    return d["choices"][0]["message"]["content"].strip()


def save_wav(frames, samplerate, path):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(samplerate)
        w.writeframes(b"".join(frames))


def _require_sounddevice():
    try:
        import sounddevice  # noqa: F401
    except ImportError:
        raise SystemExit("❌ 缺少录音依赖 sounddevice。请运行：pip install sounddevice")
    try:
        import numpy  # noqa: F401
    except ImportError:
        raise SystemExit(
            "❌ 缺少 numpy（sounddevice 录音必需）。请运行：pip install numpy")


def record_timed(seconds, path, samplerate=16000):
    _require_sounddevice()
    import sounddevice as sd
    print(f"🎤 录音 {seconds} 秒…", flush=True)
    data = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype="int16")
    sd.wait()
    save_wav([data.tobytes()], samplerate, path)
    print("⏹ 录音结束", flush=True)


def record_dialog(path, samplerate=16000):
    """macOS：系统对话框当「停止录音」按钮，录音在本进程进行。
    - Tk 浮窗与 sounddevice 共存会冻死事件循环（点不动关不掉），弃用
    - Terminal 弹窗的 close 会撞上「终止进程」确认框 → 窗口永久残留，弃用
    原生 display dialog 由系统绘制，天然可靠；点停止/关闭/Esc/超时都结束录音。"""
    _require_sounddevice()
    import sounddevice as sd

    frames = []

    def cb(indata, _f, _t, _s):
        frames.append(indata.copy())

    stream = sd.InputStream(samplerate=samplerate, channels=1, dtype="int16", callback=cb)
    stream.start()
    try:
        subprocess.run(
            ["osascript", "-e",
             'display dialog "正在录音…\n说完点「停止录音」" with title "MiMo 听写" '
             'buttons {"停止录音"} default button 1 giving up after 300'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=320)
    except subprocess.TimeoutExpired:
        pass
    finally:
        stream.stop()
        stream.close()
    save_wav([f.tobytes() for f in frames], samplerate, path)
    print("⏹ 录音结束", flush=True)


def record_until_enter(path, samplerate=16000):
    _require_sounddevice()
    import sounddevice as sd
    frames = []

    def cb(indata, _f, _t, _s):
        frames.append(indata.copy())

    with sd.InputStream(samplerate=samplerate, channels=1, dtype="int16", callback=cb):
        input("🎤 录音中… 说完按【回车】结束 ")
    save_wav([f.tobytes() for f in frames], samplerate, path)
    print("⏹ 录音结束", flush=True)


def finish(wav_path, lang):
    try:
        text = transcribe(wav_path, lang)
    except Exception as e:
        text = f"ERROR: {e}"
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(LAST_TXT, "w", encoding="utf-8") as f:
        f.write(text)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from tts import prune_old
        removed = prune_old()
        if removed:
            print(f"（顺手清理了 {removed} 个旧音频）")
    except Exception:
        pass
    print(text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="转写已有音频文件（wav/mp3）")
    ap.add_argument("--seconds", type=int, help="定时录音 N 秒（不弹窗）")
    ap.add_argument("--lang", default="zh", choices=["zh", "en", "auto"])
    ap.add_argument("--_child", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    if args._child:
        wav = os.path.join(OUT_DIR, f"asr_{time.strftime('%Y%m%d_%H%M%S')}.wav")
        try:
            record_until_enter(wav)
            finish(wav, args.lang)
        except Exception as e:
            with open(LAST_TXT, "w", encoding="utf-8") as f:
                f.write(f"ERROR: {e}")
            print(f"ERROR: {e}")
        return

    if args.file:
        finish(args.file, args.lang)
        return

    if args.seconds:
        wav = os.path.join(OUT_DIR, f"asr_{time.strftime('%Y%m%d_%H%M%S')}.wav")
        record_timed(args.seconds, wav)
        finish(wav, args.lang)
        return

    if os.path.exists(LAST_TXT):
        os.remove(LAST_TXT)
    if platform.system() == "Darwin":
        # macOS：tkinter 浮窗，自开自关。勿用 Terminal 弹窗——macOS 26 上
        # AppleScript close 遇「终止进程」确认框静默失败，窗口会永久残留。
        wav = os.path.join(OUT_DIR, f"asr_{time.strftime('%Y%m%d_%H%M%S')}.wav")
        try:
            record_dialog(wav)
        except SystemExit:
            raise
        except Exception as e:
            raise SystemExit(
                f"❌ 弹窗录音失败：{e}\n"
                "   请改用定时模式：python3 asr.py --seconds 8")
        finish(wav, args.lang)
        return

    script = os.path.abspath(__file__)
    new_window = False
    if sys.platform == "win32":
        subprocess.Popen(
            [sys.executable, script, "--_child", "--lang", args.lang],
            creationflags=subprocess.CREATE_NEW_CONSOLE)
        new_window = True

    if new_window:
        print("🎙 已打开录音窗口，请说话；说完在那个窗口按回车。等待结果…", flush=True)
        deadline = time.time() + 300
        while time.time() < deadline:
            if os.path.exists(LAST_TXT):
                time.sleep(0.3)
                print(open(LAST_TXT, encoding="utf-8").read())
                return
            time.sleep(0.5)
        raise SystemExit("❌ 等待录音窗口超时（5 分钟）")
    else:
        # Linux 交互终端等场景：当前终端直接录音，按回车结束
        wav = os.path.join(OUT_DIR, f"asr_{time.strftime('%Y%m%d_%H%M%S')}.wav")
        record_until_enter(wav)
        finish(wav, args.lang)


if __name__ == "__main__":
    main()
