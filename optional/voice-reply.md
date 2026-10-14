# 可选：语音简报（每轮回答自动语音总结）

开启后，Claude 每次回答会在**文字回复之后**追加一段 ≤15 秒的语音摘要（先文字后语音，避免长对话里等待收尾的"卡住"感）。默认**不启用**。

## 启用

0. **偷懒方式**：运行 `setup.py`，第 8 步选 y，钩子和开关会自动配好（下面手动步骤可跳过）

1. 确保 `mimo-voice` skill 已安装（`~/.claude/skills/mimo-voice/`）
2. 在 `~/.claude/settings.json` 的顶层合并以下配置（注意保留你已有的内容）：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/skills/mimo-voice/voice_reply_hook.py",  // Windows 上把 python3 换成 python（或 py -3）
            "timeout": 10
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(python3 ~/.claude/skills/mimo-voice/tts.py *)",
      "Bash(python ~/.claude/skills/mimo-voice/tts.py *)",
      "Bash(py -3 ~/.claude/skills/mimo-voice/tts.py *)"
    ]
  }
}
```

> **为什么是 SessionStart 而不是 UserPromptSubmit**：SessionStart 只在会话开始注入一次指令（进缓存前缀，此后每轮近乎零成本）；UserPromptSubmit 每轮注入 ~140 字，全部作为新输入计费，长会话多花 3000+ token。harness 级方案的代价：**开关中途切换，下次会话才生效**。
> `permissions.allow` 是免确认白名单：没有它每轮播报都会弹权限确认。`setup.py` 第 7 步会自动写入；手动配置别漏。

3. 开启开关（默认关闭；开启后**下次会话生效**）：

```bash
python3 ~/.claude/skills/mimo-voice/voice_reply_switch.py on   # Windows 用 python 或 py -3
```

4. 重启 Claude Code 或在会话里敲一次 `/hooks` 重载配置。

## 关闭 / 切换

```bash
python3 ~/.claude/skills/mimo-voice/voice_reply_switch.py off     # 关
python3 ~/.claude/skills/mimo-voice/voice_reply_switch.py toggle  # 切换
python3 ~/.claude/skills/mimo-voice/voice_reply_switch.py status  # 查看
# Windows：把 python3 换成 python（或 py -3）
```

开关关掉后钩子静默不注入，不用改 settings.json；切换后**下次会话生效**。
