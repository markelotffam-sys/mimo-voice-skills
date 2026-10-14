# 可选：语音简报（每轮回答自动语音总结）

开启后，Claude 每次回答会在**文字回复之后**追加一段 ≤15 秒的语音摘要（先文字后语音，避免长对话里等待收尾的"卡住"感）。默认**不启用**。

## 启用

1. 确保 `mimo-voice` skill 已安装（`~/.claude/skills/mimo-voice/`）
2. 在 `~/.claude/settings.json` 的顶层合并以下配置（注意保留你已有的内容）：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/skills/mimo-voice/voice_reply_hook.py",  // Windows 上把 python3 换成 python（或 py -3），否则找不到命令
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

3. 开启开关（默认不开启，运行后才生效）：

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

开关关掉后钩子静默不注入，不用改 settings.json。
