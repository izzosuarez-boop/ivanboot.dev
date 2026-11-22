"""Assemble the AI Agents explainer: intro + people shots + real phone recordings + voice + EN/ES captions.

    python scripts/media/explainer_assemble.py voice      # Gemini TTS, one file per line, each transcribed back
    python scripts/media/explainer_assemble.py render     # timeline -> MP4 (1080p + 720p) + poster + cues JSON
    python scripts/media/explainer_assemble.py all

Inputs (scripts/media/out/): brand/intro-by-ivan-dev.mp4, portfolio-ai-agents/{couch,office,closing}-*.mp4 and
raw/{store-chat,store-restock,telegram}.mp4. Captions are NOT burned in: the site's player draws them from
apps/web/src/content/video-cues/ai-agents.json so the viewer can switch English / Spanish.
Every phone screen is a real recording; nothing on a screen is generated.
"""
from __future__ import annotations

import base64
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import generate_category_media as g  # noqa: E402  (post, ffmpeg, media_seconds, tts helpers)
import intro_clapper as ic  # noqa: E402  (background, fonts, palette)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "scripts/media/out"
WORK = OUT / "portfolio-ai-agents"
RAW = WORK / "raw"
VOICE_DIR = WORK / "voice"
CUES = ROOT / "apps/web/src/content/video-cues/ai-agents.json"
W, H, FPS, SR = 1920, 1080, 30, 48000
VOICE = "Charon"

# id, spoken English (also the English caption), Spanish caption
SCRIPT = [
    ("customer", "Are you a customer? Try asking a question to the sales agent of our demo skincare store.",
     "¿Eres cliente? Hazle una pregunta al agente de ventas de nuestra tienda demo de skincare."),
    ("ask", "Just ask, like you would ask a person in the store.",
     "Pregunta como le preguntarías a alguien en la tienda."),
    ("checks", "It checks the live catalog and stock, recommends a routine, and adds it to your bag.",
     "Consulta el catálogo y el stock en vivo, recomienda una rutina y la añade a tu bolsa."),
    ("owner", "Are you the store owner? Connect your platforms and let an AI agent run the back office, "
              "from the app you're most comfortable with.",
     "¿Eres el dueño? Conecta tus plataformas y deja que un agente de IA gestione tu tienda desde la app con la "
     "que te sientas más cómodo."),
    ("plain", "Ask in plain words.", "Pregunta con tus palabras."),
    ("chart", "The agent pulls the real orders from Shopify and sends the chart in seconds.",
     "El agente toma los pedidos reales de Shopify y envía la gráfica en segundos."),
    ("acts", "And it doesn't just report, it acts. Restock a sold-out product with one message; it always asks "
             "before changing anything.",
     "Y no solo informa: actúa. Repón un producto agotado con un mensaje; siempre pide confirmación antes de "
     "cambiar algo."),
    ("back", "Moments later, it's back on sale.", "Momentos después, vuelve a estar a la venta."),
    ("close", "From answering customers to running your store: AI agents that work for you.",
     "De atender clientes a gestionar tu tienda: agentes de IA que trabajan por ti."),
]
LINES = {k: (en, es) for k, en, es in SCRIPT}


def latest(pattern: str) -> Path:
    files = sorted(WORK.glob(pattern))
    if not files:
        raise SystemExit(f"missing {pattern}")
    return files[-1]


# Timeline. phone parts: (from s, to s, speed). zoom: (t in segment, zoom, focus y as a fraction of the screen)
def segments() -> list[dict]:
    return [
        {"kind": "intro", "src": OUT / "brand/intro-by-ivan-dev.mp4"},
        {"kind": "clip", "src": latest("couch-*.mp4"), "in": 0.0, "out": 7.0, "vo": "customer", "title": "Are you a customer?"},
        # zoom ~2x on every reading moment: at 1x the phone is a quarter of the frame and its text unreadable in
        # a ~1000 px wide player. Focus values come from measured positions in the recordings (fraction of screen).
        {"kind": "phone", "src": RAW / "store-chat.mp4", "parts": [(2.6, 11.2, 2.8)], "vo": "ask",
         "zoom": [(0, 2.0, 0.86), (0.9, 2.0, 0.86), (1.6, 2.0, 0.3)]},                      # typing -> sent
        {"kind": "phone", "src": RAW / "store-chat.mp4", "parts": [(11.2, 15.9, 1.0), (15.9, 23.0, 2.2)], "vo": "checks",
         "zoom": [(0, 2.0, 0.28), (2.2, 2.0, 0.3), (3.6, 2.0, 0.62), (4.6, 2.0, 0.62),        # answer -> product cards
                  (5.2, 2.0, 0.86), (6.2, 2.0, 0.78), (7.4, 2.0, 0.64)]},                  # add to bag -> confirmed
        {"kind": "clip", "src": latest("office-*.mp4"), "in": 1.6, "out": 7.0, "vo": "owner", "title": "Are you the store owner?"},
        {"kind": "phone", "src": RAW / "telegram.mp4", "parts": [(3.0, 28.4, 7.0)], "vo": "plain",
         "zoom": [(0, 2.0, 0.5), (3.6, 2.0, 0.5)]},                                       # typing the request
        {"kind": "phone", "src": RAW / "telegram.mp4", "parts": [(28.4, 36.2, 1.15)], "vo": "chart",
         "zoom": [(0, 2.0, 0.45), (0.7, 2.0, 0.2), (1.8, 2.0, 0.22), (2.6, 2.0, 0.46),       # text answer -> chart
                  (3.8, 2.15, 0.5), (6.2, 2.15, 0.5), (6.8, 2.0, 0.45)]},                  # chart full screen
        {"kind": "phone", "src": RAW / "telegram.mp4", "parts": [(37.0, 56.3, 7.0), (56.3, 59.0, 2.0), (59.0, 67.5, 1.0)],
         "vo": "acts", "zoom": [(0, 2.0, 0.52), (4.0, 2.0, 0.5), (4.6, 2.2, 0.52), (12.6, 2.2, 0.56)]},  # proposal, Confirm, Done
        # second part starts once the reloaded page shows "In stock" (right after reload it still flashes the old state)
        {"kind": "phone", "src": RAW / "store-restock.mp4", "parts": [(0.8, 4.2, 1.0), (11.2, 14.4, 1.0)], "vo": "back",
         "vo_at": 3.5, "zoom": [(0, 1.9, 0.66), (3.3, 1.9, 0.66), (3.45, 1.9, 0.38), (6.6, 1.9, 0.4)]},
        {"kind": "clip", "src": latest("closing-*.mp4"), "in": 0.0, "out": 6.0, "vo": "close"},
        {"kind": "card", "dur": 3.2},
    ]


# ── voice ─────────────────────────────────────────────────────────────────────────────────────────────

def transcribe(path: Path) -> str:
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(path.read_bytes()).decode()}},
        {"text": "Transcribe exactly what is spoken, word for word. Output only the words."}]}]}
    res = g.post(f"{g.API}/models/gemini-flash-latest:generateContent", body)
    return "".join(p.get("text", "") for p in res["candidates"][0]["content"]["parts"]).strip()


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("-", " ")).split().__str__()


def voice(only: list[str] | None = None) -> None:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    for key, en, _ in SCRIPT:
        if only and key not in only:
            continue
        path = VOICE_DIR / f"{key}.wav"
        g.tts_line("portfolio", en, path, VOICE)
        heard = transcribe(path)
        score = difflib.SequenceMatcher(None, norm(en), norm(heard)).ratio()
        flag = "OK " if score > 0.9 else "CHECK"
        print(f"   {flag} {score:.2f} heard: {heard}")


# ── video ─────────────────────────────────────────────────────────────────────────────────────────────

def decode(src: Path, t_in: float, t_out: float, speed: float, w: int, h: int, vf_extra: str = ""):
    """Yield RGB frames (h, w, 3) at FPS for src[t_in:t_out] played at `speed`."""
    vf = f"setpts=(PTS-STARTPTS)/{speed},fps={FPS},{vf_extra}scale={w}:{h}:flags=lanczos"
    p = subprocess.Popen([g.ffmpeg(), "-loglevel", "error", "-ss", f"{t_in}", "-t", f"{t_out - t_in}", "-i", str(src),
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    size = w * h * 3
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 3)
    p.wait()


def smooth(keys: list[tuple], t: float) -> tuple[float, float]:
    if not keys:
        return 1.0, 0.5
    if t <= keys[0][0]:
        return keys[0][1], keys[0][2]
    for (t0, z0, f0), (t1, z1, f1) in zip(keys, keys[1:]):
        if t <= t1:
            k = (t - t0) / max(t1 - t0, 1e-6)
            k = k * k * (3 - 2 * k)
            return z0 + (z1 - z0) * k, f0 + (f1 - f0) * k
    return keys[-1][1], keys[-1][2]


# phone geometry on the 1920x1080 canvas
SW, SH = 440, 952                  # screen
BEZ = 14                           # bezel
PX, PY = (W - SW) // 2, (H - SH) // 2
HI = 2                             # hi-res factor for zoomed elements


def phone_assets():
    bg = ic.background().resize((W * HI, H * HI))                       # night background with glow, 2x
    bw, bh = (SW + 2 * BEZ) * HI, (SH + 2 * BEZ) * HI
    body = Image.new("RGBA", (bw + 200 * HI, bh + 200 * HI), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    o = 100 * HI
    d.rounded_rectangle([o + 16 * HI, o + 30 * HI, o + bw + 16 * HI, o + bh + 30 * HI], radius=62 * HI, fill=(0, 0, 0, 170))
    body = body.filter(ImageFilter.GaussianBlur(34 * HI))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle([o, o, o + bw, o + bh], radius=60 * HI, fill="#15181d", outline="#323a44", width=3 * HI)
    d.rounded_rectangle([o + 5 * HI, o + 5 * HI, o + bw - 5 * HI, o + bh - 5 * HI], radius=56 * HI, outline="#0b0d10", width=2 * HI)
    mask = Image.new("L", (SW * HI, SH * HI), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SW * HI - 1, SH * HI - 1], radius=46 * HI, fill=255)
    return bg, body, mask, o


def compose_phone(screen: np.ndarray, z: float, fy: float, assets) -> Image.Image:
    bg, body, mask, o = assets
    cy = PY + fy * SH
    vw, vh = W / z, H / z
    wx = min(max(W / 2 - vw / 2, 0), W - vw)
    wy = min(max(cy - vh / 2, 0), H - vh)
    frame = bg.crop((int(wx * HI), int(wy * HI), int((wx + vw) * HI), int((wy + vh) * HI))).resize((W, H), Image.BILINEAR)
    def place(x, y):
        return int(round((x - wx) * z)), int(round((y - wy) * z))
    bsz = (int(body.width / HI * z), int(body.height / HI * z))
    frame.paste(body.resize(bsz, Image.BILINEAR), place(PX - BEZ - o / HI, PY - BEZ - o / HI), body.resize(bsz, Image.BILINEAR))
    ssz = (int(SW * z), int(SH * z))
    scr = Image.fromarray(screen).resize(ssz, Image.LANCZOS if z > 1.01 else Image.BILINEAR)
    frame.paste(scr, place(PX, PY), mask.resize(ssz, Image.BILINEAR))
    cam = place(W / 2, PY + 16)  # punch-hole camera
    r = max(3, int(6 * z))
    ImageDraw.Draw(frame).ellipse([cam[0] - r, cam[1] - r, cam[0] + r, cam[1] + r], fill="#05060a")
    return frame


def title_layer(text: str) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad = np.zeros((H, W, 4), dtype=np.uint8)
    a = np.clip(1 - np.arange(H) / 380, 0, 1) ** 1.6 * 150
    grad[..., 3] = a[:, None].astype(np.uint8)
    layer = Image.fromarray(grad, "RGBA")
    d = ImageDraw.Draw(layer)
    f = ic.font("Fraunces.ttf", 34, weight=500, opsz=144)  # ic.font sizes are x2 (supersampling factor S)
    d.text((110, 92), text, font=f, fill="#ffffff")
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([110, 92 + 92, 110 + int(tw * 0.32), 92 + 96], radius=2, fill=ic.GLOW)
    return layer


def end_card() -> Image.Image:
    img = ic.background().resize((W, H), Image.LANCZOS).convert("RGBA")
    d = ImageDraw.Draw(img)
    big = ic.font("Fraunces.ttf", 60, weight=500, opsz=144)
    mid = ic.font("Inter.ttf", 17, weight=400)
    small = ic.font("Inter.ttf", 13, weight=500)
    def center(text, font, y, fill):
        tw = d.textlength(text, font=font)
        d.text(((W - tw) / 2, y), text, font=font, fill=fill)
        return tw
    tw = center("Ivan Dev", big, 380, "#ffffff")
    d.rounded_rectangle([(W - tw) / 2, 528, (W - tw) / 2 + tw, 533], radius=2, fill=ic.GLOW)
    center("AI agents that work for you", mid, 572, ic.TEXT)
    center("ivanboot.dev   ·   Hire me on Upwork", small, 650, ic.MUTED)
    return img.convert("RGB")


def render() -> None:
    segs = segments()
    vo_len = {k: g.media_seconds(VOICE_DIR / f"{k}.wav") for k in LINES}
    assets = phone_assets()
    enc = subprocess.Popen([g.ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                            "-pix_fmt", "yuv420p", str(WORK / "video-noaudio.mp4")], stdin=subprocess.PIPE)
    t = 0.0
    placed_vo, ambience = [], []
    for s in segs:
        start = t
        n = 0
        if s["kind"] == "intro":
            for fr in decode(s["src"], 0, 2.0, 1.0, W, H):
                enc.stdin.write(fr.tobytes()); n += 1
            ambience.append((s["src"], 0.0, 2.0, 1.0, start, 1.0))
        elif s["kind"] == "clip":
            need = vo_len[s["vo"]] + 0.9
            span = s["out"] - s["in"]
            speed = min(1.0, span / need)
            title = title_layer(s["title"]) if s.get("title") else None
            dur = span / speed
            for fr in decode(s["src"], s["in"], s["out"], speed, W, H):
                img = Image.fromarray(fr)
                if title is not None:
                    tt = n / FPS
                    a = min(1, max(0, (tt - 0.25) / 0.4)) * min(1, max(0, (dur - 0.3 - tt) / 0.4))
                    if a > 0:
                        lay = title.copy()
                        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
                        img = Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")
                enc.stdin.write(img.tobytes()); n += 1
            ambience.append((s["src"], s["in"], s["out"], speed, start, 0.35))
        elif s["kind"] == "phone":
            screens = []
            for a, b, sp in s["parts"]:
                screens += list(decode(s["src"], a, b, sp, SW * HI, SH * HI, vf_extra=f"scale={SW * HI}:-2,crop={SW * HI}:{SH * HI},"))
            hold = max(0, int((vo_len[s["vo"]] + 0.6 + s.get("vo_at", 0.25) - len(screens) / FPS) * FPS))
            screens += [screens[-1]] * hold  # the voice is longer than the footage: hold the last frame
            for k, sc in enumerate(screens):
                z, fy = smooth(s.get("zoom", []), k / FPS)
                enc.stdin.write(compose_phone(sc, z, fy, assets).tobytes()); n += 1
        elif s["kind"] == "card":
            card = np.asarray(end_card())
            total = int(s["dur"] * FPS)
            for k in range(total):
                a = min(1, k / 12)
                enc.stdin.write((card * a).astype(np.uint8).tobytes()); n += 1
        t = start + n / FPS
        if s.get("vo"):
            vo_start = start + s.get("vo_at", 0.25)
            placed_vo.append((s["vo"], vo_start, vo_len[s["vo"]]))
        print(f"   {s['kind']:5} {start:5.1f}–{t:5.1f}s" + (f"  voice '{s['vo']}' {vo_len[s['vo']]:.1f}s" if s.get("vo") else ""))
    enc.stdin.close(); enc.wait()
    total = t

    # ── audio: intro clap, room tone of the people shots (low), the voice lines; loudness -16 LUFS ──
    mix = np.zeros(int(total * SR) + SR, dtype=np.float32)
    def pcm(src: Path, a: float | None = None, b: float | None = None, speed: float = 1.0) -> np.ndarray:
        cmd = [g.ffmpeg(), "-loglevel", "error"] + (["-ss", f"{a}", "-t", f"{b - a}"] if a is not None else []) + \
              ["-i", str(src), "-af", f"atempo={max(speed, 0.5)}" if speed != 1.0 else "anull",
               "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
        return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, dtype=np.float32)
    for src, a, b, sp, at, gain in ambience:
        x = pcm(src, a, b, sp) * gain
        i = int(at * SR); mix[i:i + len(x)] += x[: len(mix) - i]
    for key, at, _ in placed_vo:
        x = pcm(VOICE_DIR / f"{key}.wav")
        i = int(at * SR); mix[i:i + len(x)] += x[: len(mix) - i]
    mix = mix[: int(total * SR)]
    raw = WORK / "mix.f32"
    raw.write_bytes(mix.astype(np.float32).tobytes())
    final = WORK / "ai-agents-explainer.mp4"
    subprocess.run([g.ffmpeg(), "-y", "-loglevel", "error", "-i", str(WORK / "video-noaudio.mp4"),
                    "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", str(raw),
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", str(SR),
                    "-shortest", "-movflags", "+faststart", str(final)], check=True)
    subprocess.run([g.ffmpeg(), "-y", "-loglevel", "error", "-i", str(final), "-vf", "scale=1280:-2", "-c:v", "libx264",
                    "-crf", "22", "-preset", "slow", "-c:a", "copy", "-movflags", "+faststart",
                    str(WORK / "ai-agents-explainer-720.mp4")], check=True)
    subprocess.run([g.ffmpeg(), "-y", "-loglevel", "error", "-ss", "4.5", "-i", str(final), "-frames:v", "1", "-q:v", "3",
                    str(WORK / "ai-agents-poster.jpg")], check=True)

    # ── captions for the site's player (EN / ES), timed to the voice ──
    cues = {"en": [], "es": []}
    for k, (key, at, ln) in enumerate(placed_vo):
        end = at + ln + 0.35
        if k + 1 < len(placed_vo):
            end = min(end, placed_vo[k + 1][1] - 0.05)
        for lang, text in (("en", LINES[key][0]), ("es", LINES[key][1])):
            cues[lang].append({"start": round(at, 2), "end": round(end, 2), "text": text})
    CUES.parent.mkdir(parents=True, exist_ok=True)
    CUES.write_text(json.dumps({"duration": round(total, 2), **cues}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {final.relative_to(ROOT)} ({final.stat().st_size // 1024} KB, {total:.1f}s), 720p copy, poster, "
          f"cues {CUES.relative_to(ROOT)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("voice", "all"):
        voice(sys.argv[2:] or None)
    if cmd in ("render", "all"):
        render()
