# MiMo 语音工具箱（mimo-voice-skills）

把「听」和「说」交给 AI 助手：**语音输入**（说话变文字）+ **语音合成**（文字变声音），附带可选的**语音简报**和**代码渲染视频**能力。为 Claude Code 设计的本地 Skill 集合，Windows / macOS 通用。

## 功能一览

| 能力 | 触发方式 | 底层模型 |
|---|---|---|
| 语音输入（听写） | 说「听」/「听写」/「语音输入」 | `mimo-v2.5-asr` |
| 语音合成（朗读/配音） | 说「读给我听」/「合成语音」 | `mimo-v2.5-tts` |
| 语音简报（可选装） | 每轮回答自动语音总结 | `mimo-v2.5-tts` |
| 代码渲染视频（可选） | 说「做个介绍视频」 | 画帧 + ffmpeg + TTS 旁白 |

## 适用对象（重要）

本工具调用 **小米 MiMo 开放平台** 的语音模型，需要自备 API Key：

1. **MiMo Token Plan 订阅用户**：套餐内含 `mimo-v2.5-tts`（含 voicedesign / voiceclone）、`mimo-v2.5-asr`、`mimo-v2.5` / `mimo-v2.6` 系列模型——本工具开箱即用
2. **其他用户**：需自行到 [platform.xiaomimimo.com](https://platform.xiaomimimo.com) 注册并开通对应模型的 API 调用权限

> 计费以官网为准（语音模型曾限时免费）。Token Plan 用户注意：你的 Key 需使用 Token Plan 专属网关，配置时在 `setup.py` 里选择对应项即可。

## 安全声明

- **本仓库不含任何密钥、账号、个人信息**，可放心 fork / 分发
- 你的 API Key 只保存在**本机** `~/.config/mimo-tts/`（`setup.py` 写入），不会进入 skill 文件、不会被上传
- 请勿把 `~/.config/mimo-tts/` 目录打包外传

## 安装

```bash
# 1. 把两个 skill 复制到 Claude Code 的技能目录
cp -r skills/* ~/.claude/skills/

# 2. 首次配置（交互式向导：装依赖 → 输入 Key → 选网关 → 连通测试）
python3 ~/.claude/skills/mimo-voice/setup.py

# 3. 重启 Claude Code（或新开会话）
```

依赖：Python ≥ 3.8；`sounddevice`（录音，setup.py 会装）；`ffplay` 或 `afplay`（播放，Mac 自带 afplay）。

## 使用

- **语音输入**：对 AI 说「听」（或「听写」），弹出录音窗口，说完按回车，内容变成你的消息
- **语音合成**：说「读给我听：……」，后台无窗口播放；「给这几句做配音」生成 wav 文件
- **视频**：说「做个 XX 的介绍视频」，自动生成分镜 + 旁白 + 1080p MP4（依赖 ffmpeg）
- 命令行直用：`python ~/.claude/skills/mimo-voice/tts.py --help` / `asr.py --help`

## 可选：语音简报

开启后 AI 每轮回答附带 ≤15 秒语音总结。默认关闭，启用方法见 [optional/voice-reply.md](optional/voice-reply.md)。

## 存储与清理

语音文件统一在 `~/tts-output/`，自动三层清理：**3 天**过期 + 最多 **30 个** + 合计 **100MB** 封顶，无需手动维护。

## Mac 测试要点

见 [docs/mac-test.md](docs/mac-test.md)。

## FAQ

| 问题 | 解决 |
|---|---|
| 提示找不到 API Key | 运行 `setup.py`；或设环境变量 `MIMO_API_KEY` |
| 401 认证失败 | Key 与网关不匹配：Token Plan 的 Key 要选 Token Plan 网关 |
| 录音报缺 sounddevice | `pip install sounddevice` |
| 播放没声音但 wav 已生成 | 装 ffmpeg（Mac: `brew install ffmpeg`） |
| 中文乱码 | `PYTHONUTF8=1` 前缀运行；脚本已内置 UTF-8 修复 |
