# Mac 端测试报告

- **测试日期**：2026-10-14
- **环境**：macOS 26.6.2（Darwin）/ Python 3.9.6
- **配置**：MiMo Token Plan 网关（`token-plan-cn.xiaomimimo.com/v1`）——不含 Key

## 测试结果

| # | 项目 | 结果 | 说明 |
|---|---|---|---|
| 1 | 连通测试 `tts.py "配置测试" --play` | ✅ | 生成 1.3s wav，afplay 播放正常 |
| 2 | 语音合成（默认冰糖/解说） | ✅ | 同上 |
| 3 | 风格控制 `--style 温柔` | ✅ | 生成 2.1s wav |
| 4 | 语音输入 `asr.py --seconds 5` | ✅ | 录音+转写链路通（当时无人说话，转写为环境音的数字串，属正常） |
| 5 | 弹窗模式 `asr.py` | ✅ | 独立 Terminal 窗口录音，按回车结束，转写「嗯，再试一下。」正确带标点 |
| 6 | 文件转写 `asr.py --file t.wav` | ✅ | 转出「配置测试。」与合成文本一致 |
| 7 | 清理机制 `tts.py --clean` | ✅ | 正常执行 |
| 8 | 视频渲染（可选） | ✅ | ffmpeg 用 pip 的 imageio-ffmpeg（含 libx264/aac，无 Homebrew）；TTS 旁白→479 帧→合成 20s 1080p mp4，抽帧目检无乱码无溢出 |
| 9 | 语音简报（可选） | ✅ | hook 合并进 settings.json、开关开启；hook 注入 JSON 验证正确；实测一轮语音摘要（5.6s）播放正常 |

## 发现的问题与修复（本次已 commit）

1. **录音依赖缺口（已修）**：`sounddevice` 的 `rec()` / `InputStream` 实际依赖 `numpy`，但 `pip install sounddevice` 不会自动带上（旧版 pip 环境下），首次录音报 `ModuleNotFoundError: No module named 'numpy'`。修复：
   - `asr.py`：`_require_sounddevice()` 增加 numpy 检查，报错给出精确安装命令
   - `setup.py`：第 2 步同时检查并安装 `sounddevice` + `numpy`
   - `docs/mac-test.md`、`README.md`：依赖说明与 FAQ 补充 numpy
2. **弹窗模式误报（非代码问题）**：第一次弹窗测试失败是测试环境打断所致（等待方被终止时窗口进程被连带关闭），重测通过，脚本本身无问题。
3. **视频模板 json 未导入（已修）**：`template_make_video.py` 的 `_api_conf()` 用了 `json` 但顶部未 import，被 try/except 吞掉后 config.json 被静默忽略——Token Plan 网关会失效（回退官方网关导致 401）。修复：顶部补 `import json`。
4. **视频模板字体路径硬编码 Windows（已修）**：字体改为按平台自动选择——macOS 优先 PingFang.ttc，无则回退 STHeiti Medium/Light（实测 macOS 26.6 只有 STHeiti 可用），Windows 保持微软雅黑。
5. **ffmpeg 替代方案（环境适配，非仓库问题）**：本机无 Homebrew，改用 `pip install imageio-ffmpeg` 获取静态 ffmpeg，并 `ln -s` 到 `~/.local/bin/ffmpeg`，效果等同。

## 结论

**可用**。Token Plan 网关下 TTS/ASR 全链路正常。Windows 端复核时建议重点确认：numpy 补丁后 `setup.py` 全流程、以及视频渲染项（需 ffmpeg）。

## 复查补记（2026-10-14 二次审查）

信息泄漏 / 安全扫描全绿（无 eval、exec、shell=True、pickle；外联仅小米网关与 GitHub；全文无 Key / 个人邮箱 / 主机名；git 历史作者均为 noreply）。复查另发现并修复 3 个兼容性问题：

1. **Windows 的 `python3` 命令名**（已修）：python.org 的 Windows 安装包只提供 `python.exe`，文档统一改 `python3` 会弄坏 Windows 端。现改为 `python3` 为主、显式注明 Windows 用 `python`（或 `py -3`），hook 命令同理。
2. **`voice_reply_switch.py` 缺 `os.makedirs`**（已修）：全新机器 `~/.config/mimo-tts/` 不存在时开开关会 FileNotFoundError；现在自动建目录。
3. **`asr.py --file` mp3 MIME 硬编码**（已修）：转写 mp3 时曾标成 `audio/wav`，现按扩展名选 `audio/mpeg`/`audio/wav`。

另清理：视频模板死函数 `draw_item`（引用未定义 `item_appear`，被复制调用会 NameError）已删除；`mac-test.md` 写 Key 改 heredoc（避免 echo 进 shell 历史）；README / video-render SKILL.md 补 Pillow 依赖、imageio-ffmpeg 替代方案、macOS 字体回退说明。
4. **播报命令免确认（已修）**：`tts.py --play` 每轮都弹权限确认（摘要文本每次不同，「总是允许」按命令文本匹配覆盖不到）。`setup.py` 新增第 7 步初始化时自动把 tts.py / voice_reply_switch.py 命令写入 `~/.claude/settings.json` 的 `permissions.allow`；`optional/voice-reply.md` 的配置示例同步带上 allow 块。
5. **播放后残留加载核查（Mac 无此问题）**：Windows 端曾有播放结束后仍转圈的问题（PlaySync 阻塞，130e790 已修）。Mac 路径实测 `play()` 0.002s / 整命令 0.09s 返回（7.8s 音频后台继续播），端到端 `tts.py --play` 墙钟 = 纯合成耗时，不等播放。顺手加固 afplay：补上其他分支已有的 `stdout/stderr=DEVNULL` + `start_new_session=True`（避免个别环境下子进程持有管道导致命令等到播放结束）。
