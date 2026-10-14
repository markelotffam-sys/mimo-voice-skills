#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiMo 语音输入 —— 录音并转文字（MiMo-V2.5-ASR）

用法：
    python asr.py                # 弹出「MiMo 听写」对话框，说完点「停止录音」（双端一致）
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


def _stop_dialog_win(timeout=300):
    """Windows：PowerShell WinForms 对话框（与 macOS 对话框同标题同按钮）。
    ps1 用 UTF-8-BOM 写入，避免中文在 PowerShell 5.1 下乱码。"""
    ps1 = os.path.join(OUT_DIR, "_asr_stop_dialog.ps1")
    script = """Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$form = New-Object System.Windows.Forms.Form
$form.Text = "MiMo 听写"
$form.TopMost = $true
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.StartPosition = "CenterScreen"
$form.ClientSize = New-Object System.Drawing.Size(330, 150)
$lbl = New-Object System.Windows.Forms.Label
$lbl.Text = "正在录音...`n说完点「停止录音」"
$lbl.AutoSize = $true
$lbl.Location = New-Object System.Drawing.Point(36, 22)
$form.Controls.Add($lbl)
$btn = New-Object System.Windows.Forms.Button
$btn.Text = "停止录音"
$btn.Size = New-Object System.Drawing.Size(130, 38)
$btn.Location = New-Object System.Drawing.Point(100, 82)
$btn.Add_Click({ $form.Close() })
$form.Controls.Add($btn)
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = __MS__
$timer.Add_Tick({ $form.Close() })
$timer.Start()
$form.ShowDialog() | Out-Null
""".replace("__MS__", str(int(timeout * 1000)))
    with open(ps1, "w", encoding="utf-8-sig") as f:
        f.write(script)
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout + 30)
        if r.returncode != 0:
            # 对话框根本没弹出来（脚本/环境问题）→ 抛错走兜底，别让录音失控
            raise RuntimeError("WinForms 对话框启动失败")
    finally:
        try:
            os.remove(ps1)
        except OSError:
            pass


def record_dialog(path, samplerate=16000):
    """系统对话框当「停止录音」按钮，录音在本进程进行。双端同体验：
    macOS 用 osascript display dialog，Windows 用 PowerShell WinForms。
    - Tk 浮窗与 sounddevice 共存会冻死事件循环（点不动关不掉），弃用
    - macOS Terminal 弹窗的 close 会撞「终止进程」确认框 → 窗口永久残留，弃用
    点停止 / 关闭 / Esc / 5 分钟超时，均结束录音并转写。"""
    _require_sounddevice()
    import sounddevice as sd

    frames = []

    def cb(indata, _f, _t, _s):
        frames.append(indata.copy())

    stream = sd.InputStream(samplerate=samplerate, channels=1, dtype="int16", callback=cb)
    stream.start()
    try:
        if sys.platform == "win32":
            _stop_dialog_win()
        else:
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
    wav = os.path.join(OUT_DIR, f"asr_{time.strftime('%Y%m%d_%H%M%S')}.wav")
    if platform.system() == "Darwin" or sys.platform == "win32":
        # 双端统一体验：系统对话框「停止录音」按钮 + 本进程录音。
        try:
            record_dialog(wav)
        except SystemExit:
            raise
        except Exception as e:
            if sys.platform == "win32":
                # 兜底：旧控制台窗口 + 回车（体验不一致但可靠）
                script = os.path.abspath(__file__)
                subprocess.Popen(
                    [sys.executable, script, "--_child", "--lang", args.lang],
                    creationflags=subprocess.CREATE_NEW_CONSOLE)
                print(f"🎙 对话框启动失败（{e}），已回退控制台窗口；说完按回车…", flush=True)
                deadline = time.time() + 300
                while time.time() < deadline:
                    if os.path.exists(LAST_TXT):
                        time.sleep(0.3)
                        print(open(LAST_TXT, encoding="utf-8").read())
                        return
                    time.sleep(0.5)
                raise SystemExit("❌ 等待录音窗口超时（5 分钟）")
            raise SystemExit(
                f"❌ 弹窗录音失败：{e}\n"
                "   请改用定时模式：python3 asr.py --seconds 8")
        finish(wav, args.lang)
        return

    # Linux 交互终端等场景：当前终端直接录音，按回车结束
    record_until_enter(wav)
    finish(wav, args.lang)


if __name__ == "__main__":
    main()
