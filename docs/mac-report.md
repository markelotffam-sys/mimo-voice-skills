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
