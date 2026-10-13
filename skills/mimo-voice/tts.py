#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiMo TTS —— 文本转语音（MiMo-V2.5-TTS）

用法：
    python tts.py "要朗读的文本" -o out.wav
    python tts.py --file 长文本.txt -o out.wav --play
    python tts.py "文本" --voice 苏打 --style 沉稳
    python tts.py --list          # 查看音色与风格预设
    python tts.py --clean         # 清理旧音频
"""
import argparse
import base64
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ConfigError, get_api_base, get_api_key, get_pref

MODEL = "mimo-v2.5-tts"
VOICES = {"冰糖": "中文女声（默认）", "茉莉": "中文女声", "苏打": "中文男声", "白桦": "中文男声"}
PRESETS = {
    "解说": "声音明亮带点磁性，连贯自然，语速偏快，吐字干净利落，像一位熟练的科技区博主在给朋友介绍实用工具，节奏紧凑不拖沓。",
    "沉稳": "沉稳清晰的解说风格，语速适中，吐字清楚，有亲和力，娓娓道来。",
    "温柔": "温柔治愈的声音，语速舒缓，语气温柔自然，让人放松。",
    "活泼": "活泼轻快，语调上扬，充满活力，像在和朋友分享好消息。",
    "新闻": "标准新闻播报腔，字正腔圆，语速中等偏快，客观正式。",
}
DEFAULT_STYLE = "解说"
OUT_DIR = os.path.expanduser("~/tts-output")

PRUNE_DAYS = 3
PRUNE_MAX_FILES = 30
PRUNE_MAX_TOTAL_MB = 100


def synth(text, out_path, voice=None, style=None):
    voice = voice or get_pref("voice", "冰糖")
    style_text = PRESETS.get(style or DEFAULT_STYLE, style or get_pref("style") or PRESETS[DEFAULT_STYLE])
    body = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": style_text},
            {"role": "assistant", "content": text},
        ],
        "audio": {"format": "wav", "voice": voice},
    }
    req = urllib.request.Request(
        get_api_base() + "/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {get_api_key()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        hint = ""
        if e.code == 401:
            hint = "\n   → Key 无效或网关不匹配：检查 setup.py 里配置的 Key 与网关"
        raise SystemExit(f"❌ API 请求失败 HTTP {e.code}：{detail}{hint}")
    except urllib.error.URLError as e:
        raise SystemExit(f"❌ 网络错误：{e.reason}")
    audio = base64.b64decode(d["choices"][0]["message"]["audio"]["data"])
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(audio)
    with wave.open(out_path) as w:
        return w.getnframes() / w.getframerate()


def _find_ffplay():
    import glob as _glob
    p = shutil.which("ffplay")
    if p:
        return p
    if sys.platform == "win32":
        hits = _glob.glob(os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages",
            "Gyan.FFmpeg_*", "ffmpeg-*", "bin", "ffplay.exe"))
        if hits:
            return hits[0]
    return None


def play(path):
    """后台静默播放。首选 ffplay（-nodisp 无窗口）；兜底 SoundPlayer/afplay。
    注意：SoundPlayer.PlaySync() 在隐藏窗口下会挂死，禁止使用。"""
    path = os.path.abspath(path)
    ff = _find_ffplay()
    if ff:
        subprocess.Popen([ff, "-nodisp", "-autoexit", "-loglevel", "quiet", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    if sys.platform == "win32":
        with wave.open(path) as w:
            dur = w.getnframes() / w.getframerate()
        ps = ("$p = New-Object System.Media.SoundPlayer $args[0]; $p.Play(); "
              f"Start-Sleep -Seconds {int(dur) + 2}")
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps, path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif platform.system() == "Darwin":
        subprocess.Popen(["afplay", path])
    else:
        subprocess.Popen(["aplay", "-q", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def prune_old():
    out_dir = OUT_DIR
    if not os.path.isdir(out_dir):
        return 0
    n = 0
    cutoff = time.time() - PRUNE_DAYS * 86400
    wavs = []
    for name in os.listdir(out_dir):
        if not name.lower().endswith(".wav"):
            continue
        p = os.path.join(out_dir, name)
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
                n += 1
            else:
                wavs.append((os.path.getmtime(p), p))
        except OSError:
            pass
    wavs.sort()

    def drop():
        nonlocal n
        _, p = wavs.pop(0)
        try:
            os.remove(p)
            n += 1
        except OSError:
            pass

    while len(wavs) > PRUNE_MAX_FILES:
        drop()
    limit = PRUNE_MAX_TOTAL_MB * 1024 * 1024
    total = sum(os.path.getsize(p) for _, p in wavs)
    while wavs and total > limit:
        total -= os.path.getsize(wavs[0][1])
        drop()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="*", help="要合成的文本")
    ap.add_argument("--file", help="从文本文件读取内容（长文本推荐）")
    ap.add_argument("-o", "--output", help="输出 wav 路径")
    ap.add_argument("--voice", default=None, help="音色：冰糖/茉莉/苏打/白桦")
    ap.add_argument("--style", default=None, help="风格预设名或自然语言描述")
    ap.add_argument("--play", action="store_true", help="生成后后台播放（不弹窗口）")
    ap.add_argument("--list", action="store_true", help="列出音色和风格预设")
    ap.add_argument("--clean", action="store_true", help="清理旧音频后退出")
    args = ap.parse_args()

    if args.list:
        print("音色：")
        for k, v in VOICES.items():
            print(f"  {k}  {v}")
        print("风格预设（--style）：")
        for k, v in PRESETS.items():
            print(f"  {k}  {v[:30]}…")
        return

    if args.clean:
        n = prune_old()
        print(f"✅ 已清理 {n} 个旧音频" if n else "✅ 没有需要清理的旧音频")
        return

    text = open(args.file, encoding="utf-8").read().strip() if args.file else " ".join(args.text).strip()
    if not text:
        raise SystemExit("❌ 没有输入文本。用法：python tts.py \"文本\" -o out.wav")

    out = args.output or os.path.join(OUT_DIR, f"tts_{time.strftime('%Y%m%d_%H%M%S')}.wav")
    try:
        dur = synth(text, out, voice=args.voice, style=args.style)
    except ConfigError as e:
        raise SystemExit(str(e))
    print(f"✅ 已生成：{os.path.abspath(out)}（{dur:.1f} 秒）")
    removed = prune_old()
    if removed:
        print(f"   （顺手清理了 {removed} 个旧音频）")
    if args.play:
        play(out)
        print("▶ 已播放")


if __name__ == "__main__":
    main()
