#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UserPromptSubmit 钩子：语音简报开关开着时，向模型注入"本轮要出语音摘要"的指令。
开关：~/.config/mimo-tts/voice_reply.on（存在=开）"""
import json
import os

FLAG = os.path.expanduser("~/.config/mimo-tts/voice_reply.on")

if os.path.exists(FLAG):
    msg = (
        "语音简报开关已开启：本轮先输出完整文字回复，然后把语音摘要作为最后一个动作——"
        "用 ~/.claude/skills/mimo-voice/tts.py 生成一段不超过 15 秒的中文语音摘要"
        "（默认冰糖音色），加 --play 后台播放，播报后只留一句极简收尾。"
        "摘要用一两句话概括本次回复的核心结论或进展，文字回复保持完整。"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": msg,
        }
    }, ensure_ascii=True))
