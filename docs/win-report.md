# Windows 端测试报告

- **测试日期**：2026-10-15
- **环境**：Windows 11 Home China（build 26300）/ Python 3.13.3 / Windows PowerShell 5.1 / Git Bash
- **配置**：MiMo Token Plan 网关（`token-plan-cn.xiaomimimo.com/v1`）——不含 Key
- **复核基线**：main @ `2e61ac3`（Mac 端 12 项修复逐条对齐复核）

## 测试结果

| # | 项目 | 结果 | 说明 |
|---|---|---|---|
| 1 | setup.py 第 2 步自动安装 sounddevice+numpy | ✅ | 隔离 venv 实测：两包自动安装（sounddevice 0.5.6 / numpy 2.5.4）——今日 numpy 依赖修复验证；主环境已装时正确显示「已安装」 |
| 2 | setup.py 第 6 步失败友好提示 | ✅ | 故意喂无效 Key → 401，完整显示「❌ 测试失败…常见原因：Key 错误 / 选错网关（Token Plan 的 Key 需选 Token Plan 网关）」——今日 `except (Exception, SystemExit)` 修复验证 |
| 3 | setup.py 全 8 步 | ✅ | 第 6 步真合成 3.0s wav；第 7 步写入 5 条 allow 规则（`python3`/`python`/`py -3` 变体齐全）；第 8 步 SessionStart 钩子命令名为 `python `（非 python3），开关自动开启 |
| 4 | 听写弹窗：弹出/中文显示 | ✅ | PowerShell WinForms「MiMo 听写」置顶对话框正常弹出；截图目检标题、`正在录音...说完点「停止录音」`、「停止录音」按钮中文全部正常无乱码 |
| 5 | 听写弹窗：点「停止录音」→ 转写 | ✅ | 程序化 BM_CLICK 等效点击；另有一次**真实用户手动点击**同路径通过；真 Key 端到端转写返回带标点中文（环境人声，内容不录） |
| 6 | 听写弹窗：点右上角 X → 转写 | ✅ | WM_CLOSE 等效点 X：录音正常结束 → 转写 → 进程干净退出 |
| 7 | 听写弹窗：挂 5 分钟自动结束 | ✅ | 实测录音 300.3s（01:07:58→01:12:59）定时器自动收音并进入转写 |
| 8 | 听写弹窗：启动失败回退 | ✅ | 剥 PATH 使 powershell 不可见 → 输出「🎙 对话框启动失败（[WinError 2]…），已回退控制台窗口；说完按回车…」，`--_child` 控制台随 CREATE_NEW_CONSOLE 弹出，兜底录音链路端到端跑通 |
| 9 | 语音简报 SessionStart（新机制） | ✅ | 开关 on/off/status/toggle 四态全过，**on 不再 RecursionError**（今日修复验证）；hook 开=输出合法 JSON（`hookEventName: SessionStart`）、关=静默；**隔离验证**（临时摘掉旧 UserPromptSubmit 钩子）新会话仍产出 3.0s 语音摘要（≤15s），证明摘要确实来自 SessionStart 注入 |
| 10 | 播放不阻塞 | ✅ | ffplay 路径 `play()` 36ms 返回（后台 ffplay 继续播）；SoundPlayer 兜底 11ms 返回（后台 `Play()+Start-Sleep` 持有）；端到端 `tts.py "测试" --play` 生成 1.1s 音频、0.81s 命令返回 |
| 11 | 风格偏好（config.json `style`） | ✅ | 今日修复验证：请求体捕获确认 style=温柔 → PRESETS[温柔]、无偏好 → 默认解说、显式 `--style` 覆盖正常；实听对比温柔 5.8s vs 解说 3.7s（语速差异客观可测），已播给用户复核 |
| 12 | `asr.py --file` mp3 MIME | ✅ | 今日修复验证：请求体 .mp3→`data:audio/mpeg`、.wav→`data:audio/wav`；真实 mp3（ffmpeg libmp3lame 转换）转写「你好，这是一段风格测试语音，语气温柔自然。」与合成原文一字不差 |
| 13 | 清理机制 `tts.py --clean` | ✅ | 自动顺手清理多次观察正常 |
| 14 | 视频渲染（可选） | ✅ | Pillow 11.3.0 + winget ffmpeg 9.0.2；2 场景小样：TTS 旁白→452 帧→合成 18.8s 1080p mp4（libx264+aac），抽帧目检微软雅黑中文无乱码无溢出（Windows 字体分支生效） |

## 发现的问题与修复（本次已 commit）

1. **setup.py 第 5 步覆盖 config.json 丢失偏好（已修）**：原实现 `cfg = {"api_base": base}` 整文件重写，重跑 setup 会抹掉用户已配置的 `style`/`voice`/`api_key` 偏好。改为读取原文件合并、只更新 `api_base`。实测：带 `style`/`voice` 偏好重跑后偏好保留、api_base 正常更新。
2. **听写弹窗 Esc 不关闭（已修）**：mac 报告称「点停止/关闭/Esc/超时均结束」，但 Windows 窗体未设 `CancelButton`，Esc 无反应。补 `$form.CancelButton = $btn`（Esc=点「停止录音」）与 macOS 对齐。实测前台确认后发送 ESC：录音正常结束并转写。
3. **setup.py 重跑无条件覆盖 Key 文件（已修）**：第 4 步原来不看旧 Key 直接覆盖——本次测试中误用无效 Key 跑失败路径时，把已保存的真实 Key 冲掉（测试流程教训：跑失败路径前应备份）。现改为：已存在 Key 时提示「直接回车保留原 Key，或输入新 Key 覆盖」，空输入保留原 Key（首次运行行为不变）。实测空输入重跑显示「✅ 已保留原 Key」。

## Windows 特有发现

1. **getpass 在 stdin 重定向下挂死**：Windows 的 `getpass.getpass()` 走 `msvcrt.getwch()` 直读控制台，管道喂参时永久阻塞（实测 8s 杀掉）。交互使用不受影响；自动化测试用包装器 monkeypatch 成 `input()` 跑原版 setup.py，产品代码未动。
2. **GBK 控制台编码**：非 UTF-8 控制台/管道下中文与 emoji 打印乱码甚至 `UnicodeEncodeError`。产品侧 `config.py`/`voice_reply_switch.py` 已有 `sys.stdout.reconfigure(encoding="utf-8")` 自护良好；跨 Git Bash↔PowerShell 传含中文用户名的路径会被 GBK↔UTF-8 转码搞坏（`C:\Users\<中文名>` 场景），测试脚本改进程内 spawn 规避。**建议**：脚本类工具文档可提示 Windows 用户 `PYTHONUTF8=1`。
3. **WinForms 控件窗口类名**：按钮是 `WindowsForms10.BUTTON.app.*` 而非 Win32 `BUTTON`，窗口自动化需 EnumChildWindows 模糊匹配（仅影响测试工具，产品无碍）。
4. **`_find_ffplay` 的 WinGet glob 兜底有效**：PATH 无 ffplay 也能经 `LOCALAPPDATA\...\WinGet\Packages\Gyan.FFmpeg_*` 找到——Windows 专有加分项，winget 装的 ffmpeg 天然可用。
5. **UTF-8-BOM 防乱码有效**：PowerShell 5.1 下 WinForms ps1 以 utf-8-sig 写入后中文渲染正确（截图目检）。
6. **双钩子并存提醒（非 bug）**：本机旧 skill 的 UserPromptSubmit 钩子与新 SessionStart 钩子可同时生效（指令重复但无害）。迁移完成后建议按 `optional/voice-reply.md` 移除旧钩子。

## 结论

**可用**。Token Plan 网关下 Windows 端 TTS/ASR/听写弹窗/语音简报/播放/视频渲染全链路实测通过；Mac 端今日 12 项修复在 Windows 逐条验证有效（其中 3 处 Windows 侧问题本次修复）。Windows 特有注意点主要是中文编码（GBK）与 getpass 管道行为，产品代码已有相应防御。
