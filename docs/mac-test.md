# Mac 端安装与测试指引（给 AI 执行）

> **本文件写给 Mac 上的 Claude Code / AI 助手**：用户会让你按本文完成 mimo-voice-skills 的安装、配置与测试。请逐步执行，最后按「汇报格式」给出结果。

## 前提认知

- 本仓库**不含任何密钥**。API Key 由用户在对话中提供给你，你只写入用户本机 `~/.config/mimo-tts/`，**绝不**回显完整 Key、绝不写入仓库或日志
- 工具调用小米 MiMo 平台的 `mimo-v2.5-tts`（语音合成）与 `mimo-v2.5-asr`（语音识别）。用户若是 **MiMo Token Plan**，网关必须选 Token Plan 专属网关（见第 2 步），否则 401

## 执行步骤

### 1. 获取代码并安装 skill

```bash
git clone https://github.com/markelotffam-sys/mimo-voice-skills.git
cp -r mimo-voice-skills/skills/* ~/.claude/skills/
pip3 install sounddevice
```

依赖确认：`python3 --version` ≥ 3.8；播放用 Mac 自带 `afplay`（有 ffmpeg 更佳）。

### 2. 配置密钥与网关（二选一）

**方式 A（推荐，你来写配置文件）**——向用户索取 Key 后执行：

```bash
mkdir -p ~/.config/mimo-tts
# 把用户提供的 Key 写入下面文件（不要打印到对话里）
echo "USER_PROVIDED_KEY" > ~/.config/mimo-tts/mimo_key.txt
# Token Plan 用户写 Token Plan 网关；普通 API 用户写官方网关
echo '{"api_base": "https://token-plan-cn.xiaomimimo.com/v1"}' > ~/.config/mimo-tts/config.json
```

| 用户类型 | api_base |
|---|---|
| MiMo Token Plan | `https://token-plan-cn.xiaomimimo.com/v1` |
| 普通 API Key | `https://api.xiaomimimo.com/v1`（或不写 config.json，默认即官方） |

**方式 B（用户亲手配）**：让用户自己跑 `python3 ~/.claude/skills/mimo-voice/setup.py`（交互式向导）。

### 3. 连通测试

```bash
python3 ~/.claude/skills/mimo-voice/tts.py "配置测试" -o /tmp/t.wav --play
```

预期：生成 wav 并用 afplay 后台播放。401 → Key/网关不匹配，回到第 2 步核对。

### 4. 功能测试（逐项做，记录结果）

- [ ] **语音合成**：`tts.py "今天天气不错" --play` → 有声播放
- [ ] **风格控制**：`tts.py "测试" --style 温柔` → 成功出文件
- [ ] **语音输入**：`asr.py --seconds 5`（让用户对着麦克风说一句）→ 文字正确、有标点
- [ ] **弹窗模式**：`asr.py`（会弹出独立 Terminal 窗口，用户说完按回车）→ 文字正确返回
- [ ] **文件转写**：`asr.py --file /tmp/t.wav` → 转出刚才合成的文字
- [ ] **清理机制**：`tts.py --clean` → 正常执行
- [ ] **（可选）视频**：需 `brew install ffmpeg`，按 `video-render` SKILL 出一支短片
- [ ] **（可选）语音简报**：按 `optional/voice-reply.md` 启用一轮再关闭

### 5. 汇报格式

```
环境：macOS 版本 / Python 版本
配置：网关类型（Token Plan / 官方）——不要包含 Key
测试结果：逐项 ✅/❌ + 失败项报错原文
结论：可用 / 需修复（列出问题）
```

**测试结束后必须做**：把上述结果写入 `docs/mac-report.md`，连同你对代码的任何修复一起 commit 并 push 到本仓库（commit message 写明改了什么），供 Windows 端另一 AI 晚间 pull 复核。注意：push 不能包含任何 Key。

> 访问私有仓库需要 GitHub 认证：若 git clone/push 要求登录，让用户先跑 `gh auth login`，或提供一个有 repo 权限的 PAT。

## 给用户的开场白（可直接复制发给 Mac 端 AI）

```
请按 https://github.com/markelotffam-sys/mimo-voice-skills 仓库中 docs/mac-test.md 的指引，
帮我安装 mimo-voice-skills 并完成测试。我是 MiMo Token Plan 用户（网关用 Token Plan），
API Key 我马上发给你，注意不要把 Key 回显出来。
```

## 安全红线（必须遵守）

- Key 只进 `~/.config/mimo-tts/`，不进 git、不进对话回显、不进日志
- 测试中如需截图/粘贴日志，先检查是否含 Key
- 仓库本身保持私有，测试通过前不要改公开
