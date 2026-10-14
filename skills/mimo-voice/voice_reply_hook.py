#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart 钩子：语音简报开关开着时，会话开始时注入一次"每轮出语音摘要"的指令。
harness 级注入：指令进缓存前缀，每轮不再重复计费（UserPromptSubmit 逐轮注入已弃用）。
开关：~/.config/mimo-tts/voice_reply.on（存在=开；中途切换下次会话生效）
输出兼容 Claude Code hooks 的 hookSpecificOutput.additionalContext。"""
import json
import os

FLAG = os.path.expanduser("~/.config/mimo-tts/voice_reply.on")

if os.path.exists(FLAG):
    msg = (
        "语音简报已开启（本会话全程有效）：每次回答先输出完整文字回复，然后把语音摘要作为"
        "最后一个动作——用 ~/.claude/skills/mimo-voice/tts.py 生成一段不超过 15 秒的中文语音摘要"
        "（默认冰糖音色），加 --play 后台播放，播报后只留一句极简收尾。"
        "摘要用一两句话概括本次回复的核心结论或进展。"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": msg,
        }
    }, ensure_ascii=True))
