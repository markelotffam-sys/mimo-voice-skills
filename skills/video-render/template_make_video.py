# -*- coding: utf-8 -*-
"""飞书跨租户文档誊写工具 - B站介绍视频生成器
输出: frames/ 逐帧PNG + narration.wav + 时长信息
然后由 ffmpeg 合成 MP4。
"""
import os
import subprocess
import wave

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FPS = 24
ROOT = os.path.dirname(os.path.abspath(__file__))
FRAME_DIR = os.path.join(ROOT, "frames")
os.makedirs(FRAME_DIR, exist_ok=True)

BG = (15, 23, 42)
PANEL = (30, 41, 59)
FG = (248, 250, 252)
MUTED = (148, 163, 184)
ACCENT = (86, 140, 255)      # 飞书蓝
GOLD = (255, 203, 77)

F_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
F_REG = "C:/Windows/Fonts/msyh.ttc"

font_cache = {}
def font(path, size):
    key = (path, size)
    if key not in font_cache:
        font_cache[key] = ImageFont.truetype(path, size)
    return font_cache[key]

def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

# ---------------- 场景定义 ----------------
# appear: 该元素在场景内第几秒开始淡入
SCENES = [
    dict(kind="title", dur_extra=1.2,
         narration="飞书跨租户文档誊写工具。把飞书文档从一个租户完整誊写到另一个租户，尽可能保留内容与格式。",
         items=[
            (0.3, ("title", "飞书跨租户文档誊写工具")),
            (1.1, ("sub", "Feishu Cross-Tenant Document Copy")),
            (1.9, ("ask", "把文档从一个租户完整誊写到另一个租户")),
         ]),
    dict(kind="problem",
         narration="跨租户复制的难点在于：图片和附件依赖资源令牌，在另一个租户里无法访问，直接复制容易丢失格式和资源。",
         items=[
            (0.3, ("h", "跨租户复制的难点")),
            (1.2, ("li", "图片、附件依赖资源 token")),
            (2.6, ("li", "跨租户时 token 失效，目标租户无法访问")),
            (4.2, ("root", "结果：直接复制 → 格式丢失、资源丢失")),
         ]),
    dict(kind="pipeline",
         narration="工具的原理是：不复制文档本身，而是把内容取出来，在目标租户重新构建。分四步：导出、清洗、写入、校验。",
         items=[
            (0.3, ("h", "核心原理")),
            (1.0, ("slogan", "不复制文档本身 —— 取出内容，在目标租户重新构建")),
            (2.6, ("pipe", None)),
         ]),
    dict(kind="step", num="01", name="导出",
         narration="第一步，导出。调用飞书开放接口，把文档内容转成通用格式；图片和附件下载到本地，绕开跨租户的令牌失效；画板自动导出为图片。",
         items=[
            (0.8, ("li", "调用飞书开放接口，文档内容 → 通用 XML")),
            (2.2, ("li", "图片、附件下载到本地，绕开跨租户 token 失效")),
            (3.8, ("li", "画板自动导出为图片")),
         ]),
    dict(kind="step", num="02", name="清洗",
         narration="第二步，清洗。修复服务端可能静默丢块的结构问题，把无法复制的资源替换为占位符，并立刻自校验。",
         items=[
            (0.8, ("li", "修复服务端会「静默丢块」的结构问题")),
            (2.2, ("li", "无法复制的资源替换为占位符")),
            (3.6, ("li", "导出即自校验，不通过就报错")),
         ]),
    dict(kind="step", num="03", name="写入",
         narration="第三步，写入。按每批六千字符分批写入目标文档，避免单次请求过大导致丢块；标题单独通过底层接口设置。",
         items=[
            (0.8, ("li", "按 6000 字符 / 120 块 分批写入")),
            (2.2, ("li", "避免单请求过大 → 服务端静默丢块")),
            (3.6, ("li", "标题单独走底层 API 设置")),
         ]),
    dict(kind="step", num="04", name="校验",
         narration="第四步，校验。比对源文档和目标文档的纯文本长度，差值为零，说明内容一个不少。",
         items=[
            (0.8, ("li", "比对源 / 目标 纯文本长度")),
            (2.2, ("li", "差值 = 0　→　内容一个不少")),
            (3.6, ("check", "实测：319 / 319 一致")),
         ]),
    dict(kind="usage",
         narration="使用方法：装好 Python 和命令行工具，完成认证后，依次运行三个脚本，导出、写入、设置标题。Windows 和 Mac 都能用。",
         items=[
            (0.3, ("h", "怎么用")),
            (1.0, ("li", "安装 Python 与 lark-cli，完成认证")),
            (2.4, ("cmd", "python check-env.py")),
            (3.4, ("cmd", "python lark_doc_export.py  源文档URL  ./output")),
            (4.4, ("cmd", "python lark_doc_write.py  目标文档URL  ./output/content.xml")),
            (5.4, ("cmd", "python lark_doc_set_title.py  文档ID  @./output/title.txt")),
         ]),
    dict(kind="end", dur_extra=1.6,
         narration="完整代码和使用说明都在 GitHub，搜索 feishu cross tenant copy，欢迎 Star 支持。",
         items=[
            (0.3, ("title", "飞书跨租户文档誊写工具")),
            (1.2, ("sub", "Windows / macOS 通用　·　纯命令行工具")),
            (2.2, ("url", "github.com/your-name/your-repo")),
            (3.4, ("star", "欢迎 Star 支持 ★")),
         ]),
]

# ---------------- TTS（MiMo-V2.5-TTS） ----------------
VOICE = "冰糖"   # 中文女声；备选 "苏打"（中文男声）
STYLE = "声音明亮带点磁性，连贯自然，语速偏快，吐字干净利落，像一位熟练的科技区博主在给朋友介绍实用工具，节奏紧凑不拖沓。"


def _api_conf():
    """密钥与网关解析（本文件不含密钥）：
    Key : MIMO_API_KEY 环境变量 > ~/.config/mimo-tts/config.json > mimo_key.txt
    网关: MIMO_API_BASE 环境变量 > config.json > 官方默认"""
    base = os.environ.get("MIMO_API_BASE", "").strip().rstrip("/")
    key = os.environ.get("MIMO_API_KEY", "").strip()
    cfg = {}
    try:
        cfg = json.load(open(os.path.expanduser("~/.config/mimo-tts/config.json"), encoding="utf-8"))
    except Exception:
        pass
    base = base or str(cfg.get("api_base", "")).strip().rstrip("/") or "https://api.xiaomimimo.com/v1"
    if not key:
        key = str(cfg.get("api_key", "")).strip()
    if not key:
        try:
            key = open(os.path.expanduser("~/.config/mimo-tts/mimo_key.txt"), encoding="utf-8").read().strip()
        except OSError:
            key = ""
    if not key:
        raise SystemExit("❌ 找不到 API Key：请先运行 mimo-voice 的 setup.py 完成配置")
    return base + "/chat/completions", key

def tts(text, wav_path):
    import base64
    import json
    import urllib.request
    url, key = _api_conf()
    body = {
        "model": "mimo-v2.5-tts",
        "messages": [
            {"role": "user", "content": STYLE},
            {"role": "assistant", "content": text},
        ],
        "audio": {"format": "wav", "voice": VOICE},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    audio = base64.b64decode(d["choices"][0]["message"]["audio"]["data"])
    with open(wav_path, "wb") as f:
        f.write(audio)

def wav_duration(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / w.getframerate()

# ---------------- 绘制 ----------------
def draw_item(draw, item, t, total_hint):
    kind, payload = item
    alpha = (t - item_appear.get(id(item), 0)) / 0.45
    # appear 由外层传入处理, 这里 alpha 直接用 t-draw 逻辑外面算好? 简化: 在 render 里算
    return

def fade_text(draw, xy, text, fnt, color, alpha, anchor=None):
    alpha = max(0.0, min(1.0, alpha))
    c = mix(BG, color, alpha)
    draw.text(xy, text, font=fnt, fill=c, anchor=anchor)

def render_frame(scene, t, gtime, gtotal):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    kind = scene["kind"]

    # 底部进度条
    draw.rectangle([0, H - 8, int(W * gtime / gtotal), H], fill=ACCENT)

    def A(appear):
        return (t - appear) / 0.45

    if kind == "title":
        for appear, (k, txt) in scene["items"]:
            a = A(appear)
            if k == "title":
                fade_text(draw, (W // 2, 380), txt, font(F_BOLD, 84), FG, a, anchor="mm")
            elif k == "sub":
                fade_text(draw, (W // 2, 500), txt, font(F_REG, 40), ACCENT, a, anchor="mm")
            elif k == "ask":
                fade_text(draw, (W // 2, 640), txt, font(F_REG, 48), MUTED, a, anchor="mm")

    elif kind == "problem":
        for appear, (k, txt) in scene["items"]:
            a = A(appear)
            if k == "h":
                fade_text(draw, (160, 160), txt, font(F_BOLD, 72), FG, a)
                draw.line([160, 280, 160 + int(320 * min(1, a)), 280], fill=ACCENT, width=6)
            elif k == "li":
                fade_text(draw, (200, 380 + scene["items"].index((appear, (k, txt))) * 130),
                          "•", font(F_BOLD, 48), ACCENT, a)
                fade_text(draw, (270, 380 + scene["items"].index((appear, (k, txt))) * 130),
                          txt, font(F_REG, 48), FG, a)
            elif k == "root":
                yy = 800
                if a > 0:
                    draw.rectangle([160, yy - 30, 160 + int(1600 * min(1, a)), yy + 70],
                                   fill=mix(BG, PANEL, a))
                fade_text(draw, (200, yy), txt, font(F_REG, 42), GOLD, a)

    elif kind == "pipeline":
        for appear, (k, txt) in scene["items"]:
            a = A(appear)
            if k == "h":
                fade_text(draw, (W // 2, 170), txt, font(F_BOLD, 72), FG, a, anchor="mm")
            elif k == "slogan":
                fade_text(draw, (W // 2, 320), txt, font(F_REG, 46), MUTED, a, anchor="mm")
            elif k == "pipe":
                labels = ["导出", "清洗", "写入", "校验"]
                bw, bh, gap = 280, 150, 120
                total = len(labels) * bw + (len(labels) - 1) * gap
                x0 = (W - total) // 2
                for i, lab in enumerate(labels):
                    la = A(appear + i * 0.7)
                    x = x0 + i * (bw + gap)
                    y = 480
                    box_c = mix(BG, ACCENT, la)
                    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=18,
                                           outline=box_c, width=4, fill=mix(BG, PANEL, la))
                    fade_text(draw, (x + bw // 2, y + bh // 2), lab,
                              font(F_BOLD, 52), FG, la, anchor="mm")
                    if i < len(labels) - 1:
                        ax = x + bw + 20
                        aa = A(appear + (i + 1) * 0.7 - 0.3)
                        draw.polygon([(ax, y + bh // 2 - 18), (ax + 60, y + bh // 2),
                                      (ax, y + bh // 2 + 18)],
                                     fill=mix(BG, MUTED, aa))
                fade_text(draw, (W // 2, 780), "每一步都有校验，失败即报错，不静默",
                          font(F_REG, 40), MUTED, A(appear + 3.2), anchor="mm")

    elif kind == "step":
        num, name = scene["num"], scene["name"]
        fade_text(draw, (160, 130), num, font(F_BOLD, 150), ACCENT, A(0.1))
        fade_text(draw, (420, 190), name, font(F_BOLD, 88), FG, A(0.25))
        draw.line([160, 330, 160 + int(1500 * min(1, A(0.5))), 330], fill=PANEL, width=5)
        for i, (appear, (k, txt)) in enumerate(scene["items"]):
            a = A(appear)
            y = 430 + i * 130
            if k == "check":
                if a > 0:
                    draw.rounded_rectangle([190, y - 22, 190 + int(900 * min(1, a)), y + 72],
                                           radius=14, fill=mix(BG, PANEL, a))
                fade_text(draw, (230, y), "√", font(F_BOLD, 52), (94, 222, 155), a)
                fade_text(draw, (310, y + 4), txt, font(F_REG, 48), (94, 222, 155), a)
            else:
                fade_text(draw, (220, y), "•", font(F_BOLD, 52), ACCENT, a)
                fade_text(draw, (300, y + 4), txt, font(F_REG, 48), FG, a)

    elif kind == "usage":
        cmds = [it for it in scene["items"] if it[1][0] == "cmd"]
        for appear, (k, txt) in scene["items"]:
            a = A(appear)
            if k == "h":
                fade_text(draw, (160, 160), txt, font(F_BOLD, 72), FG, a)
                draw.line([160, 280, 160 + int(320 * min(1, a)), 280], fill=ACCENT, width=6)
            elif k == "li":
                fade_text(draw, (220, 370), "•", font(F_BOLD, 52), ACCENT, a)
                fade_text(draw, (300, 374), txt, font(F_REG, 48), FG, a)
            elif k == "cmd":
                i = cmds.index((appear, (k, txt)))
                y = 500 + i * 112
                if a > 0:
                    draw.rounded_rectangle([220, y - 14, 220 + int(1480 * min(1, a)), y + 74],
                                           radius=12, fill=mix(BG, PANEL, a))
                fade_text(draw, (260, y + 6), "$ " + txt, font(F_REG, 38), (125, 211, 252), a)

    elif kind == "end":
        for appear, (k, txt) in scene["items"]:
            a = A(appear)
            if k == "title":
                fade_text(draw, (W // 2, 300), txt, font(F_BOLD, 76), FG, a, anchor="mm")
            elif k == "sub":
                fade_text(draw, (W // 2, 430), txt, font(F_REG, 42), MUTED, a, anchor="mm")
            elif k == "url":
                if a > 0:
                    draw.rounded_rectangle([W // 2 - 690, 530, W // 2 + 690, 640],
                                           radius=16, outline=mix(BG, ACCENT, a), width=3)
                fade_text(draw, (W // 2, 585), txt, font(F_REG, 44), ACCENT, a, anchor="mm")
            elif k == "star":
                fade_text(draw, (W // 2, 760), txt, font(F_BOLD, 52), GOLD, a, anchor="mm")

    return img

# ---------------- 主流程 ----------------
def main():
    print("== 1/3 生成旁白 ==")
    scene_info = []  # (n_frames, wav_path, pad_to_len)
    for i, sc in enumerate(SCENES):
        wav = os.path.join(ROOT, f"scene_{i:02d}.wav")
        tts(sc["narration"], wav)
        d = wav_duration(wav)
        # 场景时长 = 0.35 前导 + 旁白 + 0.55 收尾 + 场景额外静默
        total = 0.35 + d + 0.55 + sc.get("dur_extra", 0)
        n_frames = round(total * FPS)
        scene_info.append((n_frames, wav, 0.35, d))
        print(f"  scene {i:02d} [{sc['kind']}] 旁白 {d:.1f}s → 场景 {n_frames/FPS:.1f}s")

    gtotal = sum(x[0] for x in scene_info) / FPS

    print("== 2/3 渲染帧 ==")
    frame_idx = 0
    for i, (n_frames, wav, lead, d) in enumerate(scene_info):
        sc = SCENES[i]
        for f in range(n_frames):
            t = f / FPS
            gtime = frame_idx / FPS
            img = render_frame(sc, t, gtime, gtotal)
            img.save(os.path.join(FRAME_DIR, f"{frame_idx:05d}.png"))
            frame_idx += 1
        print(f"  scene {i:02d} 完成 ({n_frames} 帧)")
    print(f"  总帧数 {frame_idx}, 总时长 {gtotal:.1f}s")

    print("== 3/3 合成旁白音轨 ==")
    with wave.open(scene_info[0][1], "rb") as w0:
        params = w0.getparams()
    out_wav = os.path.join(ROOT, "narration.wav")
    with wave.open(out_wav, "wb") as out:
        out.setparams(params)
        silence = b"\x00\x00" * int(params.framerate * 0.35)  # 16bit mono
        for i, (n_frames, wav, lead, d) in enumerate(scene_info):
            scene_len = n_frames / FPS
            out.writeframes(silence)
            with wave.open(wav, "rb") as w:
                out.writeframes(w.readframes(w.getnframes()))
            used = 0.35 + d
            pad_s = scene_len - used
            out.writeframes(b"\x00\x00" * int(params.framerate * max(0, pad_s)))
    # 补齐总长
    with wave.open(out_wav, "rb") as w:
        got = w.getnframes() / w.getframerate()
    need = frame_idx / FPS - got
    if need > 0.01:
        with wave.open(out_wav, "rb") as w:
            p = w.getparams()
            data = w.readframes(w.getnframes())
        with wave.open(out_wav, "wb") as w:
            w.setparams(p)
            w.writeframes(data + b"\x00\x00" * int(p.framerate * need))

    print(f"DONE frames={frame_idx} total={gtotal:.2f}s")

if __name__ == "__main__":
    main()
