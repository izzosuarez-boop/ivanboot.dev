"""Brand intro for every Ivan Dev video: a slate with "By Ivan Dev" whose clapper snaps shut (2 s, with sound).

    python scripts/media/intro_clapper.py --reuse-frames       # -> scripts/media/out/brand/intro-by-ivan-dev.mp4 (real clap)
    python scripts/media/intro_clapper.py --variants --reuse-frames  # intro-sound-A/B/C.mp4 to choose by ear

Made in code, not with a video model, so it is identical in every video, the lettering is exact and it costs
nothing. Frames are drawn with Pillow at 2x and downsampled (clean edges); the clap is synthesized with numpy
(a wood "tock" + a short noise burst + a small room tail) and lands on the exact frame the arm closes.
"""
from __future__ import annotations

import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
OUT = HERE / "out" / "brand"
FONTS = HERE / "fonts"

W, H, S = 1920, 1080, 2          # output size, supersampling factor
FPS, DURATION = 30, 2.0
IMPACT = 1.10                    # seconds: the arm closes and the clap sounds
SR = 48000

NIGHT, PANEL, LINE, TEXT, MUTED, GLOW, LAMP = "#090b0e", "#12161b", "#2a333d", "#e6e9ed", "#8b95a1", "#5eead4", "#f2b45c"


def font(name: str, size: int, weight: int | None = None, opsz: int | None = None) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTS / name), size * S)
    try:
        axes = {a["name"].lower() if isinstance(a["name"], str) else a["name"].decode().lower(): a for a in f.get_variation_axes()}
        values = []
        for a in f.get_variation_axes():
            n = (a["name"] if isinstance(a["name"], str) else a["name"].decode()).lower()
            if n.startswith("weight") and weight:
                values.append(weight)
            elif n.startswith("optical") and opsz:
                values.append(opsz)
            else:
                values.append(a["default"])
        if axes:
            f.set_variation_by_axes(values)
    except (OSError, AttributeError):
        pass  # static font: use as is
    return f


def ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3


def clamp01(t: float) -> float:
    return max(0.0, min(1.0, t))


# ── geometry (in output pixels; multiplied by S when drawing) ─────────────────────────────────────────
BW, BH = 640, 360                       # slate body
BX, BY = (W - BW) // 2, 442             # body top-left: the closed slate sits just below center, and the
BAR = 62                                 # open arm (26°) still fits inside the frame
HINGE = (BX + 8, BY - 2 * BAR + 4)       # hinge point of the top arm (left end)
OPEN_DEG = 26


def stripes_layer(x: int, y: int, w: int, h: int) -> Image.Image:
    """A striped bar (45° diagonal stripes, ink / off-white) as an RGBA layer the size of the canvas."""
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    bar = Image.new("RGBA", (w * S, h * S), PANEL)
    d = ImageDraw.Draw(bar)
    step = 54 * S
    for k in range(-h * S, w * S + h * S, step * 2):
        d.polygon([(k, h * S), (k + h * S, 0), (k + h * S + step, 0), (k + step, h * S)], fill=TEXT)
    mask = Image.new("L", bar.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=10 * S, fill=255)
    layer.paste(bar, (x * S, y * S), mask)
    ImageDraw.Draw(layer).rounded_rectangle([x * S, y * S, (x + w) * S - 1, (y + h) * S - 1], radius=10 * S,
                                            outline=LINE, width=2 * S)
    return layer


def background() -> Image.Image:
    img = Image.new("RGB", (W * S, H * S), NIGHT)
    glow = Image.new("RGB", (W // 4, H // 4), NIGHT)
    g = np.zeros((H // 4, W // 4, 3), dtype=np.float32)
    yy, xx = np.mgrid[0:H // 4, 0:W // 4]
    for (cx, cy, r, col, a) in ((0.28, 0.75, 0.55, (94, 234, 212), 0.10), (0.78, 0.22, 0.45, (242, 180, 92), 0.07)):
        dist = np.sqrt(((xx / (W / 4)) - cx) ** 2 + ((yy / (H / 4)) - cy) ** 2 * 0.6) / r
        g += np.clip(1 - dist, 0, 1)[..., None] ** 2 * np.array(col) * a
    base = np.array(Image.new("RGB", (1, 1), NIGHT)).reshape(3).astype(np.float32)
    glow = Image.fromarray(np.clip(base + g, 0, 255).astype(np.uint8)).resize((W * S, H * S), Image.BICUBIC)
    img.paste(glow)
    return img


BG = None
ARM = None
BAR_FIXED = None


def frame(t: float) -> Image.Image:
    global BG, ARM, BAR_FIXED
    if BG is None:
        BG = background()
        BAR_FIXED = stripes_layer(BX, BY - BAR, BW, BAR)
        ARM = stripes_layer(BX, BY - 2 * BAR - 6, BW, BAR)
    img = BG.copy().convert("RGBA")

    # entrance: slate rises and fades in (0 → 0.35 s); small shake right after the impact
    k_in = ease_out(clamp01(t / 0.35))
    dy = (1 - k_in) * 40
    shake = 0.0
    if t >= IMPACT:
        u = t - IMPACT
        shake = 5 * math.exp(-u / 0.05) * math.sin(u * 2 * math.pi * 22)
    oy = dy + shake

    scene = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(scene)
    # soft shadow under the slate
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([(BX + 10) * S, (BY + 30) * S, (BX + BW + 10) * S, (BY + BH + 40) * S],
                                         radius=24 * S, fill=(0, 0, 0, 160))
    scene.alpha_composite(sh.filter(ImageFilter.GaussianBlur(30 * S)))
    # body
    d.rounded_rectangle([BX * S, BY * S, (BX + BW) * S, (BY + BH) * S], radius=18 * S, fill=PANEL, outline=LINE, width=2 * S)
    # slate rows (hairlines + tiny labels), like a real clapperboard
    small = font("Inter.ttf", 15, weight=500)
    rows_y = [BY + BH - 78, BY + BH - 39]
    for ry in rows_y:
        d.line([(BX + 24) * S, ry * S, (BX + BW - 24) * S, ry * S], fill=LINE, width=2 * S)
    d.line([(BX + BW // 2) * S, rows_y[0] * S, (BX + BW // 2) * S, (BY + BH - 12) * S], fill=LINE, width=2 * S)
    for (lx, ly, label, value) in ((BX + 24, rows_y[0] + 10, "PROD", "IVANBOOT.DEV"), (BX + BW // 2 + 18, rows_y[0] + 10, "SCENE", "01"),
                                   (BX + 24, rows_y[1] + 10, "DIR", "IVAN"), (BX + BW // 2 + 18, rows_y[1] + 10, "TAKE", "01")):
        d.text((lx * S, ly * S), label, font=small, fill=MUTED)
        d.text(((lx + 64) * S, ly * S), value, font=small, fill=TEXT)

    # the title written on the slate; it lights up when the clap lands
    lit = clamp01((t - IMPACT) / 0.12)
    title = font("Fraunces.ttf", 90, weight=500, opsz=144)
    by = font("Inter.ttf", 26, weight=400)
    col = tuple(int(a + (b - a) * lit) for a, b in zip((150, 158, 168), (255, 255, 255)))
    tw = d.textlength("Ivan Dev", font=title)
    bw_ = d.textlength("By", font=by)
    gap = 18 * S
    total = bw_ + gap + tw
    x0 = BX * S + (BW * S - total) / 2
    ty = (BY + 62) * S
    d.text((x0, ty + 45 * S), "By", font=by, fill=MUTED)
    d.text((x0 + bw_ + gap, ty), "Ivan Dev", font=title, fill=col)
    # teal underline that sweeps in after the clap
    sweep = ease_out(clamp01((t - IMPACT - 0.05) / 0.4))
    if sweep > 0:
        ux = x0 + bw_ + gap
        d.rounded_rectangle([ux, ty + 114 * S, ux + tw * sweep, ty + 118 * S], radius=2 * S, fill=GLOW)

    # fixed lower bar
    scene.alpha_composite(BAR_FIXED)
    # top arm: open, then falls with gravity-like acceleration, closes exactly at IMPACT
    fall = clamp01((t - 0.42) / (IMPACT - 0.42))
    angle = OPEN_DEG * (1 - fall ** 2.2)
    arm = ARM.rotate(angle, resample=Image.BICUBIC, center=(HINGE[0] * S, HINGE[1] * S))
    scene.alpha_composite(arm)
    # hinge
    d2 = ImageDraw.Draw(scene)
    hx, hy = HINGE
    d2.ellipse([(hx - 9) * S, (hy - 9) * S, (hx + 9) * S, (hy + 9) * S], fill=LAMP, outline=PANEL, width=3 * S)

    # impact flash: a soft teal bloom along the closing line
    if t >= IMPACT:
        u = t - IMPACT
        a = int(140 * math.exp(-u / 0.09))
        if a > 2:
            bloom = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(bloom).rounded_rectangle([(BX + 40) * S, (BY - BAR - 10) * S, (BX + BW - 40) * S, (BY - BAR + 10) * S],
                                                    radius=10 * S, fill=(94, 234, 212, a))
            scene.alpha_composite(bloom.filter(ImageFilter.GaussianBlur(26 * S)))

    # apply entrance offset/opacity to the whole slate
    if oy or k_in < 1:
        moved = Image.new("RGBA", img.size, (0, 0, 0, 0))
        moved.paste(scene, (0, int(oy * S)))
        scene = moved
        if k_in < 1:
            alpha = scene.getchannel("A").point(lambda v: int(v * k_in))
            scene.putalpha(alpha)
    img.alpha_composite(scene)
    return img.convert("RGB").resize((W, H), Image.LANCZOS)


# ── sound ─────────────────────────────────────────────────────────────────────────────────────────────
# v2 (2026-11-23): v1 (190 Hz "tock" + 72 Hz thump) sounded like a hollow wood block, not a slate. A real
# clapperboard is two hardwood sticks slapping: a very short broadband snap, the sticks' own inharmonic
# modes in the 1-6 kHz range (free-free bar ratios 1 : 2.756 : 5.404 : 8.933) decaying in tens of ms, often
# a double hit a few ms apart (one end lands first), almost no low end, and a small room's reflections.
BAR_MODES = (1.0, 2.756, 5.404, 8.933)
SOUNDS = {
    # f0: lowest stick mode (Hz) · decay of each mode (s) · gap between the two hits (s) · room mix · room RT60 (s)
    "A": {"label": "studio", "f0": 1350, "decay": (0.034, 0.021, 0.013, 0.008), "gap": 0.003, "snap": 0.9,
          "room": 0.16, "rt60": 0.32},
    "B": {"label": "bright, snappy", "f0": 1900, "decay": (0.022, 0.014, 0.009, 0.006), "gap": 0.0015, "snap": 1.2,
          "room": 0.10, "rt60": 0.25},
    "C": {"label": "woody, fuller", "f0": 950, "decay": (0.050, 0.030, 0.018, 0.010), "gap": 0.004, "snap": 0.7,
          "room": 0.22, "rt60": 0.45},
}


def _hit(v: dict, rng: np.random.Generator, length: float = 0.25) -> np.ndarray:
    t = np.arange(int(length * SR)) / SR
    modes = sum((0.9 / (k + 1) ** 0.6) * np.sin(2 * np.pi * v["f0"] * r * t + rng.uniform(0, 6.28)) * np.exp(-t / d)
                for k, (r, d) in enumerate(zip(BAR_MODES, v["decay"])))
    burst = rng.standard_normal(len(t)) * np.exp(-t / 0.0006)          # ~1 ms broadband snap
    snap = np.diff(burst, prepend=0) * v["snap"]                        # high-passed: bright, not boomy
    return modes + snap


def clap_audio(sound: str = "A") -> np.ndarray:
    from scipy.signal import butter, sosfilt
    v = SOUNDS[sound]
    rng = np.random.default_rng(11)
    hit = _hit(v, rng)
    gap = int(v["gap"] * SR)                                            # the second end of the arm lands
    dry = np.zeros(len(hit) + gap)
    dry[: len(hit)] += hit
    dry[gap:] += 0.6 * _hit(v, rng)
    dry = sosfilt(butter(4, 350, "highpass", fs=SR, output="sos"), dry)
    dry = np.tanh(dry / np.max(np.abs(dry)) * 1.6)                      # a little punch
    # small room: a few early reflections + a dark, decaying tail
    ir_len = int(v["rt60"] * SR)
    ir_t = np.arange(ir_len) / SR
    tail = rng.standard_normal(ir_len) * np.exp(-6.9 * ir_t / v["rt60"])
    tail = sosfilt(butter(2, 4500, "lowpass", fs=SR, output="sos"), tail)
    ir = tail * v["room"] / np.sqrt(np.sum(tail ** 2))  # by energy: the direct hit must stay the loudest part
    for ms, g in ((7, 0.35), (13, 0.25), (21, 0.18)):
        ir[int(ms / 1000 * SR)] += g * v["room"] * 2
    ir[0] = 1.0
    wet = np.convolve(dry, ir)
    n = int(DURATION * SR)
    out = np.zeros(n)
    i = int(IMPACT * SR)
    m = min(len(wet), n - i)
    out[i:i + m] += wet[:m]
    return out / np.max(np.abs(out)) * 10 ** (-1.5 / 20)               # peak -1.5 dBFS


# v3 (2026-11-22): the user rejected every synthesized version; the intro uses a real recorded slate clap
# (CC0, see sounds/SOURCES.md). Its onset is placed exactly on the frame where the arm closes.
SAMPLE = HERE / "sounds" / "slate-clap-194719-cc0.wav"


def sample_audio(path: Path = SAMPLE) -> np.ndarray:
    with wave.open(str(path)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32767
    a = a.reshape(-1, ch).mean(axis=1)
    if sr != SR:
        from scipy.signal import resample_poly
        a = resample_poly(a, SR, sr)
    onset = int(np.argmax(np.abs(a) > 0.1 * np.abs(a).max()))
    a = a[onset:]
    fade = min(len(a), int(0.01 * SR))
    a[-fade:] *= np.linspace(1, 0, fade)                                # no click at the end
    out = np.zeros(int(DURATION * SR))
    i = int(IMPACT * SR)
    m = min(len(a), len(out) - i)
    out[i:i + m] = a[:m]
    return out / np.max(np.abs(out)) * 10 ** (-1.0 / 20)               # peak -1 dBFS


def write_wav(path: Path, mono: np.ndarray) -> None:
    pcm = (np.clip(mono, -1, 1) * 32767).astype(np.int16)
    stereo = np.column_stack([pcm, pcm]).ravel()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())


def render(ff: str, frames_dir: Path, sound: str, mp4: Path) -> None:
    wav = OUT / f"clap-{sound}.wav"
    write_wav(wav, sample_audio() if sound == "real" else clap_audio(sound))
    subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames_dir / "%03d.png"),
                    "-i", str(wav), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "slow",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(mp4)], check=True)
    print(f"{mp4.name}: sound {sound} ({SOUNDS[sound]['label'] if sound in SOUNDS else SAMPLE.name})")


def main() -> None:
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    OUT.mkdir(parents=True, exist_ok=True)
    frames_dir = OUT / "frames"
    frames_dir.mkdir(exist_ok=True)
    total = int(FPS * DURATION)
    if "--reuse-frames" not in sys.argv or not (frames_dir / f"{total - 1:03d}.png").exists():
        for i in range(total):
            frame(i / FPS).save(frames_dir / f"{i:03d}.png")
    if "--variants" in sys.argv:          # one file per sound, to choose by ear
        for k in SOUNDS:
            render(ff, frames_dir, k, OUT / f"intro-sound-{k}.mp4")
        return
    sound = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--sound=")), "real")
    render(ff, frames_dir, sound, OUT / "intro-by-ivan-dev.mp4")
    if "--preview" in sys.argv:
        picks = [0, 6, 18, 28, 33, 34, 38, 59]
        thumbs = [Image.open(frames_dir / f"{i:03d}.png").resize((480, 270)) for i in picks]
        sheet = Image.new("RGB", (480 * 4, 270 * 2))
        for k, im in enumerate(thumbs):
            sheet.paste(im, ((k % 4) * 480, (k // 4) * 270))
        sheet.save(OUT / "preview.jpg", quality=90)


if __name__ == "__main__":
    main()
