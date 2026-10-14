---
name: video-render
description: 代码渲染视频：用 Python+Pillow 逐帧绘制 + ffmpeg 合成 MP4，配 MiMo 语音旁白。当用户要"做个视频"、"生成介绍/演示/讲解视频"、"代码渲染视频"、"视频配音合成"、"把XX做成视频"时使用。适合概念讲解、原理介绍、工具演示、幻灯片式短片。不负责 AI 文生视频（没有该能力）。
---

# video-render —— 代码渲染视频流水线

Python(Pillow) 画帧 → MiMo TTS 旁白 → ffmpeg 合成 MP4。全程本地代码渲染，无 AI 生视频。

> 依赖：`pip install Pillow`（画帧）+ ffmpeg（合成）；TTS 部分复用 mimo-voice 的 Key 配置（`~/.config/mimo-tts/`）。
> 下文命令用 `python3`（macOS/Linux）；Windows 换 `python`（或 `py -3`）。

## 工作流（依次执行，不要跳步）

### Step 1：设计分镜

和用户确认（或按需求拟定后告知）：主题、总时长（建议 60~90 秒）、场景列表。每个场景包含：
- **画面元素**：标题 / 正文行 / 列表 / 流程图 / 命令行框 / 结尾卡
- **旁白文本**：口语化短句，每场景 20~40 字，语速偏快时约 6~10 秒
- **出现时间**：每行文字在场景内第几秒淡入（配合旁白节奏）

### Step 2：写渲染脚本

以 `template_make_video.py` 为模板复制修改。模板结构：
- `SCENES` 列表定义分镜（`kind` 决定渲染分支：title / problem / pipeline / step / usage / end，按需增改）
- `tts()` 调 MiMo TTS（同 mimo-voice skill 的 API），`STYLE` 常量控制旁白风格
- 每场景时长自动 = 0.35s 前导 + 旁白实际时长 + 0.55s 收尾（可加 `dur_extra`）
- 帧渲染：`render_frame()` 按场景 kind 画图，文字淡入用颜色插值 `mix(BG, 目标色, alpha)`

### Step 3：渲染 + 合成

```bash
cd <工作目录>          # 所有产物放独立工作目录，别混进用户项目
PYTHONUTF8=1 python3 make_video.py       # 出 frames/ + narration.wav（Windows 用 python）
<ffmpeg> -y -framerate 24 -i frames/%05d.png -i narration.wav \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -preset medium \
  -c:a aac -b:a 192k -movflags +faststart 输出.mp4
```

ffmpeg 路径探测顺序：PATH 里的 `ffmpeg` → winget 安装路径（Windows）；Mac 无 Homebrew 可 `pip install imageio-ffmpeg` 并把其 ffmpeg 软链到 `~/.local/bin/ffmpeg`（实测可用，含 libx264/aac）
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*\bin\ffmpeg.exe`

### Step 4：验证再交付

1. 抽 3~5 帧用 Read 工具看图检查（各场景文字完整、无溢出、无乱码方框）
2. `ffmpeg -i 输出.mp4` 确认时长/分辨率
3. 交付时说明时长、分辨率、文件路径；发布类需求另给标题/简介/标签建议

## 已踩过的坑（务必遵守）

| 坑 | 解法 |
|---|---|
| 微软雅黑缺字形：✓ ⇒ ⭐ 等显示为 □ | 用 √ → ★ 等 CJK 字体自带符号；**所有新符号先画一帧验证** |
| 中文 Windows GBK 控制台崩溃 | 运行一律加 `PYTHONUTF8=1` |
| 长 URL/文本溢出边框 | 画框宽度按最长文本估算（约 22px/字），宁宽勿窄 |
| TTS 文本走命令行参数会乱码 | 文本写 UTF-8 文件再读（模板已处理） |
| PNG 帧序列占空间大 | 输出完可删 frames/，只留 mp4 与 narration.wav |
| 音画不同步 | 场景时长必须由旁白 wav 实测时长反推（模板已自动） |

## 设计默认值（可按需覆盖）

- 1920×1080 / 24fps / 深色底（RGB 15,23,42）+ 飞书蓝点缀（86,140,255）
- 字体：Windows 用 `C:/Windows/Fonts/msyhbd.ttc`（粗）/ `msyh.ttc`（常规）；macOS 优先 `PingFang.ttc`，无则回退 STHeiti（模板已按平台自动选择，macOS 26 实测只有 STHeiti 可用）
- 旁白风格默认「解说」（磁性、连贯、语速偏快）；换风格改 `STYLE`，音色改 `VOICE`
- 底部细进度条；场景切换直接切（不做转场特效）

## 磁盘与清理（重要）

单个项目产物体积：`frames/` 约 **300MB**（1080p × ~2000 帧）、`narration.wav` 约 2MB、成片 mp4 约 2~5MB。

**交付并确认成片无误后，必须立即删除 `frames/` 和抽帧检查用的 check_*.png / v_*.png**，只保留 mp4（和用户明确要留的 narration.wav）。模板跑完会打印提醒。多个项目的工作目录建议用独立子目录，方便整目录清理。

## 安全规则

- API Key 由 `setup.py` 配置、只存 `~/.config/mimo-tts/`，禁止打印、上传、写入产物
- 工作目录里的 key 文件、中间帧不要打包外传；交付只给最终 mp4

## 边界

- AI 文生视频（Sora/可灵那种）→ 没有，明确告知用户
- 真人剪辑/字幕特效 → 建议剪映等工具，本 skill 出的是排版动画式短片
- 语音单独使用（朗读/配音）→ 走 mimo-voice skill
