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
| 8 | 视频渲染（可选） | ⏸ 未测 | 本机未装 ffmpeg，需要时 `brew install ffmpeg` |
| 9 | 语音简报（可选） | ⏸ 未测 | 会改变日常会话行为，按需手动启用 |

## 发现的问题与修复（本次已 commit）

1. **录音依赖缺口（已修）**：`sounddevice` 的 `rec()` / `InputStream` 实际依赖 `numpy`，但 `pip install sounddevice` 不会自动带上（旧版 pip 环境下），首次录音报 `ModuleNotFoundError: No module named 'numpy'`。修复：
   - `asr.py`：`_require_sounddevice()` 增加 numpy 检查，报错给出精确安装命令
   - `setup.py`：第 2 步同时检查并安装 `sounddevice` + `numpy`
   - `docs/mac-test.md`、`README.md`：依赖说明与 FAQ 补充 numpy
2. **弹窗模式误报（非代码问题）**：第一次弹窗测试失败是测试环境打断所致（等待方被终止时窗口进程被连带关闭），重测通过，脚本本身无问题。

## 结论

**可用**。Token Plan 网关下 TTS/ASR 全链路正常。Windows 端复核时建议重点确认：numpy 补丁后 `setup.py` 全流程、以及视频渲染项（需 ffmpeg）。
