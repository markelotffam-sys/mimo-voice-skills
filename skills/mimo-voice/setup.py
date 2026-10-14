#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiMo 语音工具箱 —— 首次配置向导

一步步引导你完成：依赖检查 → 输入 API Key → 选择网关 → 连通测试。
密钥只保存在本机 ~/.config/mimo-tts/，不会写入 skill 文件、不会上传。

用法：
    python setup.py
"""
import getpass
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CONFIG_DIR, CONFIG_FILE, DEFAULT_API_BASE, KEY_FILE

GATEWAYS = {
    "1": ("官方 API 网关（推荐）", "https://api.xiaomimimo.com/v1"),
    "2": ("MiMo Token Plan 网关", "https://token-plan-cn.xiaomimimo.com/v1"),
}


def step(n, title):
    print(f"\n【{n}】{title}")


def main():
    print("=" * 56)
    print("  MiMo 语音工具箱 · 首次配置向导")
    print("=" * 56)

    step(1, "检查 Python 版本")
    ok = sys.version_info >= (3, 8)
    print(f"  {'✅' if ok else '❌'} Python {sys.version.split()[0]}（需要 >= 3.8）")
    if not ok:
        raise SystemExit("请升级 Python 后重试")

    step(2, "检查录音依赖 sounddevice + numpy（语音输入需要，可选）")
    missing = []
    for mod in ("sounddevice", "numpy"):
        try:
            __import__(mod)
            print(f"  ✅ {mod} 已安装")
        except ImportError:
            missing.append(mod)
    if missing:
        ans = input(f"  未安装 {'、'.join(missing)}，现在安装吗？[Y/n] ").strip().lower()
        if ans in ("", "y", "yes"):
            subprocess.run([sys.executable, "-m", "pip", "install", *missing], check=False)
        else:
            print("  ⚠️ 跳过：语音输入（录音）将不可用，语音合成不受影响")

    step(3, "检查播放器 ffplay / afplay（语音播放需要）")
    import shutil
    import platform as plat
    if shutil.which("ffplay") or plat.system() == "Darwin" or shutil.which("afplay"):
        print("  ✅ 播放器可用（ffplay/afplay）")
    else:
        print("  ⚠️ 未找到 ffplay：仍可生成 wav 文件，但自动播放不可用")
        print("     安装 ffmpeg 后恢复（Mac: brew install ffmpeg；Windows: winget install Gyan.FFmpeg）")

    step(4, "配置 API Key（仅保存到本机）")
    print("  Key 获取：platform.xiaomimimo.com 控制台创建（详见 README）")
    key = getpass.getpass("  请粘贴你的 API Key（输入不回显）: ").strip()
    if not key:
        raise SystemExit("❌ 未输入 Key，退出")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key)
    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass  # Windows 不支持 Unix 权限位，文件本身仅本机可见
    print(f"  ✅ 已保存到 {KEY_FILE}")

    step(5, "选择 API 网关")
    for k, (name, url) in GATEWAYS.items():
        print(f"  {k}. {name}  ({url})")
    print("  3. 手动输入其他网关地址")
    choice = input("  请选择 [1]: ").strip() or "1"
    if choice in GATEWAYS:
        base = GATEWAYS[choice][1]
    else:
        base = input("  请输入网关地址: ").strip().rstrip("/")
    cfg = {"api_base": base}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 网关已保存：{base}")
    print("  （可选偏好后续可写入 config.json：voice / style / api_key）")

    step(6, "连通测试（合成一句 2 秒语音）")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tts
    try:
        out = os.path.join(tts.OUT_DIR, "setup_test.wav")
        dur = tts.synth("配置成功，语音工具箱已就绪。", out)
        print(f"  ✅ 语音合成正常（{dur:.1f} 秒）→ {out}")
    except (Exception, SystemExit) as e:  # synth 的 API 报错是 SystemExit
        print(f"  ❌ 测试失败：{e}")
        print("  常见原因：Key 错误 / 选错网关（Token Plan 的 Key 需选 Token Plan 网关）")
        return

    step(7, "配置 Claude Code 权限白名单（免去每次播报弹确认）")
    try:
        settings = os.path.expanduser("~/.claude/settings.json")
        if os.path.exists(settings):
            with open(settings, encoding="utf-8") as f:
                conf = json.load(f)
        else:
            conf = {}
        allow = conf.setdefault("permissions", {}).setdefault("allow", [])
        # 覆盖 macOS/Linux（python3）与 Windows（python / py -3）三种命令名
        rules = [
            "Bash(python3 ~/.claude/skills/mimo-voice/tts.py *)",
            "Bash(python ~/.claude/skills/mimo-voice/tts.py *)",
            "Bash(py -3 ~/.claude/skills/mimo-voice/tts.py *)",
            "Bash(python3 ~/.claude/skills/mimo-voice/voice_reply_switch.py *)",
            "Bash(python ~/.claude/skills/mimo-voice/voice_reply_switch.py *)",
        ]
        added = [r for r in rules if r not in allow]
        if added:
            allow.extend(added)
            with open(settings, "w", encoding="utf-8") as f:
                json.dump(conf, f, ensure_ascii=False, indent=2)
            print(f"  ✅ 已写入 {len(added)} 条 allow 规则 → {settings}")
        else:
            print("  ✅ allow 规则已存在，跳过")
        print("  （否则每次 tts.py 播报都会弹权限确认）")
    except Exception as e:
        print(f"  ⚠️ 自动写入失败（可手动添加）：{e}")

    step(8, "可选：语音简报（每轮回答后自动语音总结）")
    ans = input("  要开启语音简报吗？[y/N] ").strip().lower()
    if ans in ("y", "yes"):
        try:
            settings = os.path.expanduser("~/.claude/settings.json")
            conf = json.load(open(settings, encoding="utf-8")) if os.path.exists(settings) else {}
            hooks = conf.setdefault("hooks", {})
            sess = hooks.setdefault("SessionStart", [])
            # SessionStart 只在会话开始注入一次指令（进缓存前缀），比逐轮注入省 token
            hook_cmd = ("python " if sys.platform == "win32" else "python3 ") + (
                "~/.claude/skills/mimo-voice/voice_reply_hook.py")
            if not any(h.get("command") == hook_cmd
                       for grp in sess for h in grp.get("hooks", [])):
                sess.append({"hooks": [{"type": "command", "command": hook_cmd, "timeout": 10}]})
                with open(settings, "w", encoding="utf-8") as f:
                    json.dump(conf, f, ensure_ascii=False, indent=2)
            os.makedirs(CONFIG_DIR, exist_ok=True)
            open(os.path.join(CONFIG_DIR, "voice_reply.on"), "w").close()
            print(f"  ✅ 已写入 SessionStart 钩子并开启开关：{hook_cmd}")
            print("  （开关切换用 voice_reply_switch.py；改动下次会话生效）")
        except Exception as e:
            print(f"  ⚠️ 自动配置失败（可按 optional/voice-reply.md 手动配置）：{e}")
    else:
        print("  已跳过；以后要开见 optional/voice-reply.md")

    print("\n" + "=" * 56)
    print("  ✅ 配置完成！接下来安装 skill：")
    print("  1. 把 skills/ 下的两个文件夹复制到 ~/.claude/skills/")
    print("     cp -r skills/* ~/.claude/skills/")
    print("  2. 重启 Claude Code（或新开会话）")
    print("  3. 说「听」开始语音输入；说「读给我听」体验语音合成")
    print("  4. 语音简报管理：voice_reply_switch.py on/off/status（详见 optional/voice-reply.md）")
    print("=" * 56)


if __name__ == "__main__":
    main()
