#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音简报开关 —— 控制"每次回答是否附带语音摘要"

用法：python voice_reply_switch.py on|off|toggle|status
"""
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FLAG = os.path.expanduser("~/.config/mimo-tts/voice_reply.on")

def _touch_flag():
    """创建开关文件；目标目录可能还不存在（全新机器），先建目录"""
    os.makedirs(os.path.dirname(FLAG), exist_ok=True)
    open(FLAG, "w").close()


def state():
    return "开" if os.path.exists(FLAG) else "关"


cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
if cmd == "on":
    _touch_flag()
elif cmd == "off":
    if os.path.exists(FLAG):
        os.remove(FLAG)
elif cmd == "toggle":
    if os.path.exists(FLAG):
        os.remove(FLAG)
    else:
        _touch_flag()
elif cmd != "status":
    print(__doc__)
    sys.exit(1)

print(f"语音简报：{state()}")
