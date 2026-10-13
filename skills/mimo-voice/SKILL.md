---
name: mimo-voice
description: 语音合成/朗读/配音/语音输入：文本转语音（MiMo-V2.5-TTS）和语音转文字（MiMo-V2.5-ASR）。当用户要"读给我听"、"朗读这段"、"合成语音"、"生成配音/旁白"、"做音频"、"TTS"、"给视频配音"，或者"语音输入"、"听写"、"我说你写"、"用说的"，或消息仅为单独一个「听」字时使用（句中的"听"不算）。输出 wav 并可直接播放，或录音转文字。不负责视频画面生成（那是 video-render）。
---

# mimo-voice —— MiMo 语音工具箱（听 + 说）

文本↔语音双向：`tts.py` 说话，`asr.py` 听写。配置由 `config.py` 统一解析（首次使用先跑 `setup.py`）。

## 语音合成（tts.py）

```bash
python ~/.claude/skills/mimo-voice/tts.py "文本" -o out.wav --play
python ~/.claude/skills/mimo-voice/tts.py --file 长文本.txt -o out.wav
python ~/.claude/skills/mimo-voice/tts.py "文本" --voice 苏打 --style 沉稳
python ~/.claude/skills/mimo-voice/tts.py --list
```

| 用户意图 | 做法 |
|---|---|
| "读给我听 / 朗读" | 合成后加 `--play`，告知文件路径与时长 |
| "配音 / 旁白" | 生成 wav 交给后续流程；多段旁白每段一个文件 |
| 长文本（>500 字） | 用 `--file`（先写 UTF-8 临时 txt） |
| 用户描述想要的感觉 | 自由描述直接传 `--style`（优先于预设） |

- 音色 `--voice`：冰糖（默认女）/ 茉莉（女）/ 苏打（男）/ 白桦（男）
- 风格预设 `--style`：解说（默认）/ 沉稳 / 温柔 / 活泼 / 新闻
- 输出 24kHz 单声道 wav；拼接混音交给 ffmpeg（见 video-render）

## 语音输入（asr.py）

```bash
python ~/.claude/skills/mimo-voice/asr.py                # 弹录音窗，说完按回车
python ~/.claude/skills/mimo-voice/asr.py --seconds 8    # 定时录 8 秒（不弹窗）
python ~/.claude/skills/mimo-voice/asr.py --file x.wav   # 转写已有音频
python ~/.claude/skills/mimo-voice/asr.py --lang en      # zh/en/auto，默认 zh
```

| 用户意图 | 做法 |
|---|---|
| 消息是单独一个「听」字（可带标点） | 立即启动语音输入弹窗流程；**句中"听"（听起来/听你的）不算** |
| "语音输入 / 听写 / 我说你写" | 跑 `asr.py`，拿到文字**当作用户消息**继续处理 |
| 转写会议录音等已有文件 | `--file`；超 10MB 先用 ffmpeg 压 16kHz 单声道 |
| 方言/中英混说 | 默认 zh 即可；混说用 `--lang auto` |

弹窗模式新开控制台（Windows）或当前终端交互（macOS），用户说完按回车，脚本等待并返回文字。

## 缓存清理（自动）

每次生成自动清理 `~/tts-output/`：3 天前删除 + 最多 30 个 + 合计 100MB 封顶（删最旧）。手动：`tts.py --clean`。

## 安全规则（重要）

- API Key 只存 `~/.config/mimo-tts/`（setup.py 写入），**禁止**打印 Key、写入 skill 文件、上传或提交仓库
- 401 → 提示检查 Key 与网关是否匹配（Token Plan 的 Key 只认 Token Plan 网关）
- 其他 API 错误 → 给用户看 HTTP 状态和错误体前 300 字

## 故障速查

| 现象 | 处理 |
|---|---|
| 找不到 API Key | 运行 `setup.py`，或设 `MIMO_API_KEY` 环境变量 |
| 401 | Key 错/网关不匹配，重跑 `setup.py` 第 5 步选对网关 |
| 录音报缺 sounddevice | `pip install sounddevice` |
| 播放没声音 | 检查 ffplay（Mac: brew install ffmpeg）；wav 仍会生成 |
| 控制台中文乱码 | 脚本已强制 UTF-8；仍乱码就 `PYTHONUTF8=1` |
