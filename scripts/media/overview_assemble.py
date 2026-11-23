"""AI Agents section overview video ("will you get into the AI race, or stay out?"), approved 2026-11-22.

    python scripts/media/overview_assemble.py coding     # shot 1: real screens composited onto the Omni clip
    python scripts/media/overview_assemble.py sample     # intro + shot 1 + its voice line, for review

Shot 1: the Omni clip (locked-off camera, explainer_video.py ai-agents-overview coding) shows the three monitors
with model-made, unreadable content. The center and right screens are replaced with real content rendered here
(our own code being typed; an AI agent chat answering), warped in perspective onto the measured screen corners,
then blurred and color-matched to the shot's depth of field and grade. Iván's profile covers the right edge of the
right screen, so warm (skin / shirt) pixels there always stay on top. The slow push-in is done here too, so the
screens never have to be tracked.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import generate_category_media as g  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
WORK = HERE / "out/portfolio-ai-agents-overview"
FONTS = HERE / "fonts"
W, H, FPS = 1920, 1080, 30
GLOW = (94, 234, 212)

# Screen corners in the 1920x1080 clip (tl, tr, br, bl), measured on frame 0 (camera drift <= 1 px).
MAIN_Q = [(487, 278), (968, 303), (968, 595), (497, 626)]
RIGHT_Q = [(980, 304), (1415, 317), (1415, 588), (982, 598)]
# Grade: canvas black/white -> the shot's screen background / brightest UI (sampled from the clip)
MAIN_GRADE = ((22, 46, 54), (190, 222, 226))
RIGHT_GRADE = ((34, 62, 72), (212, 234, 238))


def f(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS / name   # Windows fonts are not in git (licence): fall back to the system copy
    return ImageFont.truetype(str(path if path.exists() else Path("C:/Windows/Fonts") / name), size)


def ease(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


# ── screen 1: code editor, our own code being typed ────────────────────────────────────────────────────────
CODE = textwrap.dedent('''\
    async def propose(chat_id, product, units, mode="add"):
        """Returns (result for the model, proposal id). Never writes to Shopify."""
        if chat_id != config.TELEGRAM_OWNER_CHAT_ID:
            return {"error": "Only the store owner can change stock."}, None
        live = await shopify.catalog()
        variants = await shopify_admin.variants_with_inventory()
        found = _match(product, [v for v in variants if v["handle"] in live])
        if not found:
            return {"error": f"No product on sale matches '{product}'."}, None
        v = found[0]
        to_qty = v["qty"] + units if mode == "add" else units
        change = to_qty - v["qty"]
        if abs(change) > MAX_UNITS or to_qty > MAX_STOCK:
            return {"error": "Bigger adjustments are done in Shopify admin."}, None
        pid = secrets.token_hex(4)
        _PENDING[pid] = Proposal(chat_id, v["name"], v["qty"], to_qty)
        return {"proposal": {"product": v["name"], "new_units": to_qty},
                "status": "NOT applied yet: waiting for Confirm"}, pid
''').splitlines()
TYPED_FROM = 10          # lines before this are already on screen; the rest is typed during the shot
KW = {"async", "def", "return", "if", "not", "else", "await", "for", "in", "None", "True", "False", "or", "and"}
C_DEF, C_KW, C_STR, C_FN, C_NUM, C_CMT = (171, 178, 191), (198, 120, 221), (152, 195, 121), (97, 175, 239), (209, 154, 102), (127, 132, 142)


def tokens(line: str):
    """Tiny Python highlighter: (text, color) runs."""
    out, i, n = [], 0, len(line)
    while i < n:
        ch = line[i]
        if ch in "\"'":
            q = line[i:i + 3] if line[i:i + 3] in ('"""', "'''") else ch
            j = line.find(q, i + len(q))
            j = n if j < 0 else j + len(q)
            out.append((line[i:j], C_STR)); i = j
        elif ch.isalpha() or ch == "_":
            j = i
            while j < n and (line[j].isalnum() or line[j] == "_"):
                j += 1
            word = line[i:j]
            color = C_KW if word in KW else C_FN if (j < n and line[j] == "(") else C_DEF
            out.append((word, color)); i = j
        elif ch.isdigit():
            j = i
            while j < n and line[j].isdigit():
                j += 1
            out.append((line[i:j], C_NUM)); i = j
        else:
            out.append((ch, C_DEF)); i += 1
    return out


def editor(t: float) -> Image.Image:
    cw, ch = 1440, 960
    im = Image.new("RGB", (cw, ch), (24, 27, 32))
    d = ImageDraw.Draw(im)
    ui, mono, monob = f("segoeui.ttf", 22), f("consola.ttf", 27), f("consolab.ttf", 27)
    d.rectangle([0, 0, cw, 40], fill=(33, 37, 43))
    d.rectangle([0, 40, 250, ch], fill=(30, 34, 40))                       # file tree
    for k, (name, depth, active) in enumerate([("apps", 0, 0), ("api", 1, 0), ("app", 2, 0), ("agent.py", 3, 0),
                                                ("owner_agent.py", 3, 0), ("restock.py", 3, 1), ("shopify.py", 3, 0),
                                                ("shopify_admin.py", 3, 0), ("webhooks.py", 3, 0), ("web", 1, 0)]):
        y = 64 + k * 36
        if active:
            d.rectangle([0, y - 6, 250, y + 28], fill=(44, 50, 60))
        d.text((18 + depth * 18, y), name, font=ui, fill=(200, 205, 212) if active else (140, 148, 158))
    d.rectangle([250, 40, 470, 84], fill=(24, 27, 32))                     # tabs
    d.text((270, 50), "restock.py", font=ui, fill=(220, 224, 230))
    d.line([(250, 82), (470, 82)], fill=GLOW, width=3)
    d.text((490, 50), "agent.py", font=ui, fill=(120, 128, 138))
    # how much of the typed part is on screen (typing starts at 0.4 s, ~30 chars/s, as he types)
    typed_chars = max(0, int((t - 0.4) * 30))
    lh, x0, y0 = 40, 330, 104
    cursor = None
    for k, line in enumerate(CODE):
        if k >= TYPED_FROM:
            if typed_chars <= 0:
                break
            vis = line[:typed_chars]
            typed_chars -= len(line) + 1
        else:
            vis = line
        y = y0 + k * lh
        d.text((262, y), f"{68 + k:>3}", font=mono, fill=(90, 98, 108))
        x = x0
        for text, color in tokens(vis):
            d.text((x, y), text, font=monob if color == C_KW else mono, fill=color)
            x += mono.getlength(text)
        cursor = (x, y)
    if cursor and int(t * 2.2) % 2 == 0:
        d.rectangle([cursor[0] + 2, cursor[1] + 2, cursor[0] + 16, cursor[1] + 32], fill=(220, 224, 230))
    d.rectangle([0, ch - 34, cw, ch], fill=(0, 122, 204))                  # status bar
    d.text((16, ch - 30), "main   Python 3.12   Ln 85, Col 9", font=ui, fill=(235, 240, 245))
    return im


# ── screen 2: an AI agent chat that answers ───────────────────────────────────────────────────────────────
def bubble(d, xy, text, font, fill, color, maxw, align="left"):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        test = (cur + " " + w_).strip()
        if font.getlength(test) > maxw and cur:
            lines.append(cur); cur = w_
        else:
            cur = test
    if cur:
        lines.append(cur)
    lh = int(font.size * 1.3)
    bw = int(max((font.getlength(x) for x in lines), default=0)) + 44
    bh = lh * len(lines) + 30
    x, y = xy
    if align == "right":
        x -= bw
    d.rounded_rectangle([x, y, x + bw, y + bh], radius=24, fill=fill)
    for k, line in enumerate(lines):
        d.text((x + 22, y + 14 + k * lh), line, font=font, fill=color)
    return y + bh


def chat(t: float) -> Image.Image:
    cw, ch = 1440, 950
    im = Image.new("RGB", (cw, ch), (22, 25, 30))
    d = ImageDraw.Draw(im)
    ui, uib, small = f("segoeui.ttf", 40), f("segoeuib.ttf", 44), f("segoeui.ttf", 28)
    right = int(cw * 0.76)    # Iván's profile covers the right quarter of this screen: keep it empty
    # header: glowing agent icon + name
    cx, cy = 80, 66
    for r, a in ((46, 40), (38, 90), (30, 255)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(int(c * a / 255 + 22 * (1 - a / 255)) for c in GLOW))
    star = [(cx, cy - 20), (cx + 6, cy - 6), (cx + 20, cy), (cx + 6, cy + 6), (cx, cy + 20), (cx - 6, cy + 6), (cx - 20, cy), (cx - 6, cy - 6)]
    d.polygon(star, fill=(12, 40, 38))
    d.text((140, 28), "AI Agent", font=uib, fill=(235, 240, 244))
    d.ellipse([142, 90, 156, 104], fill=(80, 220, 120))
    d.text((166, 80), "online · connected to Shopify, Gmail, Sheets", font=small, fill=(140, 150, 160))
    d.line([(0, 130), (cw, 130)], fill=(45, 52, 60), width=2)
    y = 160
    y = bubble(d, (right, y), "Best sellers this week?", ui, (34, 92, 86), (225, 245, 240), 640, "right") + 18
    y = bubble(d, (40, y), "Barrier Cream leads with 31 orders, up 18%.", ui, (40, 46, 54), (205, 212, 220), 760) + 26
    # new request slides in at 0.3 s, typing dots, then the answer streams in word by word
    if t > 0.3:
        k = ease((t - 0.3) / 0.35)
        y = bubble(d, (right, y + int((1 - k) * 30)), "Draft replies to the 3 open customer emails", ui,
                   (34, 92, 86), (225, 245, 240), 640, "right") + 18
    answer = "On it. 3 replies drafted and ready for your review. I also flagged 1 delayed order."
    if 1.2 < t < 2.2:
        d.rounded_rectangle([40, y, 190, y + 70], radius=24, fill=(40, 46, 54))
        for i in range(3):
            on = int(t * 6) % 3 == i
            d.ellipse([72 + i * 36, y + 26, 90 + i * 36, y + 44], fill=(200, 210, 220) if on else (100, 110, 120))
    elif t >= 2.2:
        words = answer.split()
        n = min(len(words), 1 + int((t - 2.2) * 6.5))
        bubble(d, (40, y), " ".join(words[:n]), ui, (40, 46, 54), (225, 232, 238), 760)
    d.rounded_rectangle([30, ch - 96, right, ch - 30], radius=30, outline=(60, 68, 78), width=2)
    d.text((64, ch - 82), "Ask your agent…", font=small, fill=(110, 120, 130))
    return im


# ── compositing ──────────────────────────────────────────────────────────────────────────────────────────
def coeffs(src: list[tuple], dst: list[tuple]) -> list[float]:
    """PIL perspective coefficients mapping output (dst) points back to input (src) points."""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        b += [u, v]
    return np.linalg.solve(np.array(A, float), np.array(b, float)).tolist()


def grade(im: Image.Image, lo_hi) -> Image.Image:
    """Map the canvas background to the shot's screen background and white to its brightest UI."""
    a = np.asarray(im, np.float32)
    bg = a[a.shape[0] // 2, -5]                       # right edge, mid height: always background on our canvases
    lo, hi = np.array(lo_hi[0], np.float32), np.array(lo_hi[1], np.float32)
    k = np.clip((a - bg) / (255.0 - bg), 0, 1) ** 0.8
    return Image.fromarray(np.clip(lo + k * (hi - lo), 0, 255).astype(np.uint8))


def warp(canvas: Image.Image, quad, grade_, blur: float):
    xs, ys = [p[0] for p in quad], [p[1] for p in quad]
    bx0, by0, bx1, by1 = int(min(xs)) - 4, int(min(ys)) - 4, int(max(xs)) + 5, int(max(ys)) + 5
    local = [(x - bx0, y - by0) for x, y in quad]
    cw, ch = canvas.size
    c = coeffs([(0, 0), (cw, 0), (cw, ch), (0, ch)], local)
    size = (bx1 - bx0, by1 - by0)
    img = grade(canvas, grade_).transform(size, Image.PERSPECTIVE, c, Image.BICUBIC)
    mask = Image.new("L", canvas.size, 255).transform(size, Image.PERSPECTIVE, c, Image.BILINEAR)
    img = img.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(img, np.float32)
    hl = Image.fromarray(np.clip((a - 110) * 1.6, 0, 255).astype(np.uint8))   # glow only from bright UI, not the background
    a = a + 0.35 * np.asarray(hl.filter(ImageFilter.GaussianBlur(6)), np.float32)
    a += np.random.default_rng().normal(0, 2.2, a.shape)                     # the clip's grain
    m = np.asarray(mask.filter(ImageFilter.GaussianBlur(1.2)), np.float32)[..., None] / 255.0
    return a, m, (bx0, by0)


def occluder(frame: np.ndarray, box, from_x: int = 0) -> np.ndarray:
    """1 where Iván (skin / shirt: warm pixels) is in front of the right screen, feathered."""
    x0, y0, x1, y1 = box
    r, g_, b = (frame[y0:y1, x0:x1, k].astype(int) for k in range(3))
    # the screens are graded teal (blue > red); skin, shirt and even the dark glasses rims are redder than blue
    warm = (r > b + 8) & (r > 25)
    warm[:, :from_x] = False
    occ = np.zeros(warm.shape, np.float32)
    lefts = np.full(warm.shape[0], warm.shape[1], int)
    for row in range(warm.shape[0]):
        run = np.convolve(warm[row].astype(int), np.ones(3, int), "valid")
        hit = np.nonzero(run == 3)[0]
        if hit.size:
            lefts[row] = hit[0]
    pad = np.array([lefts[max(0, i - 3):i + 4].min() for i in range(len(lefts))]) - 3   # follow the profile closely
    for row, lx in enumerate(pad):
        if lx < warm.shape[1]:
            occ[row, max(0, lx):] = 1
    return np.asarray(Image.fromarray((occ * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255


def push_in(img: Image.Image, t: float, dur: float, z1=1.10, focus=(990, 470)) -> Image.Image:
    z = 1 + (z1 - 1) * ease(t / dur)
    fx, fy = focus
    x0, y0 = fx * (1 - 1 / z), fy * (1 - 1 / z)
    return img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + W / z, y0 + H / z))


def latest(pattern: str) -> Path:
    files = sorted(WORK.glob(pattern), key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit(f"missing {pattern} in {WORK}")
    return files[-1]


def frames(src: Path):
    p = subprocess.Popen([g.ffmpeg(), "-loglevel", "error", "-i", str(src), "-vf", f"fps={FPS},scale={W}:{H}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while len(buf := p.stdout.read(W * H * 3)) == W * H * 3:
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    p.wait()


def coding() -> Path:
    src = latest("coding-[0-9]*.mp4")
    out = WORK / "coding-composite.mp4"
    enc = subprocess.Popen([g.ffmpeg(), "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "15",
                            "-preset", "slow", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    dur = 6.0
    for i, fr in enumerate(frames(src)):
        t = i / FPS
        base = fr.astype(np.float32)
        for canvas, quad, gr, blur in ((editor(t), MAIN_Q, MAIN_GRADE, 1.0), (chat(t), RIGHT_Q, RIGHT_GRADE, 0.8)):
            a, m, (bx, by) = warp(canvas, quad, gr, blur)
            h_, w_ = m.shape[:2]
            if quad is RIGHT_Q:
                # computed on the same box as the warped screen, only where his profile can be (x >= 1250)
                m = m * (1 - occluder(fr, (bx, by, bx + w_, by + h_), from_x=1250 - bx)[..., None])
            region = base[by:by + h_, bx:bx + w_]
            base[by:by + h_, bx:bx + w_] = region * (1 - m) + a * m
        img = push_in(Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)), t, dur)
        enc.stdin.write(np.asarray(img).tobytes())
        if i in (0, 45, 90, 135, 175):
            img.save(WORK / f"cmp_{i:03d}.jpg", quality=92)
    enc.stdin.close(); enc.wait()
    print("shot 1 ->", out.relative_to(g.ROOT))
    return out


# ── shot 2: the owner circles, on her whiteboard, the tasks where AI makes sense ─────────────────────────────
# 15 sticky notes, row by row (found by color on the board still). Notes 0, 7 and 11 get circled, so they carry
# the repetitive tasks; the rest are the work that stays human.
NOTES_TEXT = {
    "en": ["Reply to emails", "Meet clients", "Product ideas", "Hire a designer", "Brand vision",
           "Supplier deals", "Set prices", "Update stock", "Plan launch", "Team 1:1s",
           "Partner calls", "Send invoices", "Budget review", "Train staff", "Store layout"],
    "es": ["Responder correos", "Reunión con clientes", "Ideas de producto", "Contratar diseñador", "Visión de marca",
           "Negociar proveedores", "Definir precios", "Actualizar stock", "Planear lanzamiento", "Reuniones de equipo",
           "Llamadas con socios", "Enviar facturas", "Revisar presupuesto", "Capacitar equipo", "Diseño de tienda"],
}
CIRCLED = (0, 7, 11)
INK = (38, 40, 58)


def note_text(text: str, size: int = 300) -> Image.Image:
    """Marker handwriting on a transparent square: the biggest size that fits in 2 lines, else in 3."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def wrap(font):
        words, lines, cur = text.split(), [], ""
        for w_ in words:
            test = (cur + " " + w_).strip()
            if font.getlength(test) > size * 0.84 and cur:
                lines.append(cur); cur = w_
            else:
                cur = test
        return lines + [cur]

    fit = None
    for max_lines, smallest in ((2, 50), (3, 30)):
        for fs in range(80, smallest - 1, -3):
            font = f("Inkfree.ttf", fs)
            lines = wrap(font)
            if len(lines) <= max_lines and max(font.getlength(x) for x in lines) <= size * 0.86:
                fit = (fs, font, lines)
                break
        if fit:
            break
    fs, font, lines = fit
    lh = int(fs * 1.12)
    y = (size - lh * len(lines)) // 2
    for k, line in enumerate(lines):
        x = (size - font.getlength(line)) / 2 + (k % 2) * 4 - 2          # a slightly uneven hand
        d.text((x, y + k * lh), line, font=font, fill=INK + (235,))
    return im.rotate(-1.5, resample=Image.BICUBIC)


def badge(size: int = 64) -> Image.Image:
    """Small teal 'AI' sparkle badge, our brand color, popped next to each circled note."""
    S = 4
    im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c, r = size * S / 2, size * S / 2 - 2 * S
    d.ellipse([c - r, c - r, c + r, c + r], fill=GLOW + (255,), outline=(255, 255, 255, 255), width=3 * S)
    k = r * 0.62
    star = [(c, c - k), (c + k * .28, c - k * .28), (c + k, c), (c + k * .28, c + k * .28), (c, c + k),
            (c - k * .28, c + k * .28), (c - k, c), (c - k * .28, c - k * .28)]
    d.polygon(star, fill=(9, 40, 38, 255))
    return im.resize((size, size), Image.LANCZOS)


def find_notes(still: np.ndarray) -> list[dict]:
    """The 15 sticky notes of the board still, by color, row by row: corner quads and centers."""
    from scipy import ndimage
    a = still.astype(int)
    r, g_, b = a[..., 0], a[..., 1], a[..., 2]
    yellow = (r > 160) & (g_ > 140) & (r - b > 35) & (g_ - b > 20) & (r - g_ < 45)
    mint = (g_ > 160) & (g_ - r > 20) & (g_ - b > 0) & (r > 90)
    notes = []
    for m in (yellow, mint):
        lab, n = ndimage.label(ndimage.binary_fill_holes(ndimage.binary_opening(m, iterations=2)))
        for i in range(1, n + 1):
            ys, xs = np.nonzero(lab == i)
            if len(xs) < 6000:
                continue
            # the notes face the camera: a robust box (percentiles ignore curled corners and stray pixels)
            l, r_, t, b_ = (int(np.percentile(xs, 2)), int(np.percentile(xs, 98)), int(np.percentile(ys, 2)),
                            int(np.percentile(ys, 98)))
            notes.append({"quad": [[l, t], [r_, t], [r_, b_], [l, b_]], "cx": float(xs.mean()), "cy": float(ys.mean()),
                          "side": float(np.sqrt(len(xs)))})
    rows = sorted(notes, key=lambda n: n["cy"])
    if len(rows) != 15:
        raise SystemExit(f"expected 15 notes, found {len(rows)}")
    return [n for k in range(3) for n in sorted(rows[k * 5:(k + 1) * 5], key=lambda n: n["cx"])]


def circle_path(n: dict, seed: int) -> np.ndarray:
    """A hand-drawn loop around a note: starts top-left, goes counter-clockwise, overshoots its start a little,
    slightly wobbly and not quite round, like a quick stroke with a marker. Points in still pixels."""
    rng = np.random.default_rng(seed)
    R = n["side"] * 0.80
    th0 = np.deg2rad(-130 + rng.uniform(-15, 15))
    th = th0 - np.linspace(0, np.deg2rad(392), 240)               # counter-clockwise on screen (y grows down)
    ph = rng.uniform(0, 6.28, 3)
    k = np.linspace(0, 1, th.size)
    rad = R * (1 + 0.05 * np.sin(2 * th + ph[0]) + 0.025 * np.sin(3 * th + ph[1]) + 0.06 * k)   # spirals out a bit
    sx, sy = 1.08, 0.94                                            # a little wider than tall
    return np.stack([n["cx"] + sx * rad * np.cos(th), n["cy"] + 5 + sy * rad * np.sin(th)], 1)


def draw_stroke(img: Image.Image, path: np.ndarray, upto: float, width: float = 7.5) -> None:
    """Draw the first `upto` (0..1) of a marker stroke, anti-aliased (3x supersampled in its box)."""
    if upto <= 0:
        return
    pts = path[: max(2, int(len(path) * min(1.0, upto)))]
    S = 3
    x0, y0 = (pts.min(0) - 20).astype(int)
    x1, y1 = (pts.max(0) + 20).astype(int)
    layer = Image.new("L", ((x1 - x0) * S, (y1 - y0) * S), 0)
    d = ImageDraw.Draw(layer)
    p = [((x - x0) * S, (y - y0) * S) for x, y in pts]
    d.line(p, fill=235, width=int(width * S), joint="curve")
    for e in (p[0], p[-1]):                                       # round marker tip
        d.ellipse([e[0] - width * S / 2, e[1] - width * S / 2, e[0] + width * S / 2, e[1] + width * S / 2], fill=235)
    mask = layer.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    ink = Image.new("RGB", mask.size, (34, 36, 50))
    img.paste(ink, (x0, y0), mask)


CIRCLE_AT = (1.4, 2.6, 3.8)   # start of each circle (s); each stroke takes CIRCLE_DUR
CIRCLE_DUR = 0.55
WB_DUR = 9.6


def whiteboard(lang: str = "en") -> Path:
    """Shot 2 v2 (2026-11-22): the empty board still; tasks written on the notes, then three circles drawn stroke
    by stroke around the repetitive ones, each followed by the AI badge; a slow push-in with film grain."""
    still = Image.open(WORK / "whiteboard-empty-still.png").convert("RGB")
    notes = find_notes(np.asarray(still))
    base = np.asarray(still, np.float32).copy()
    for k, n in enumerate(notes):                                 # handwriting, baked once
        q = n["quad"]
        xs, ys = [p[0] for p in q], [p[1] for p in q]
        bx0, by0, bx1, by1 = min(xs) - 2, min(ys) - 2, max(xs) + 3, max(ys) + 3
        c = coeffs([(0, 0), (300, 0), (300, 300), (0, 300)], [(x - bx0, y - by0) for x, y in q])
        a = np.asarray(note_text(NOTES_TEXT[lang][k]).transform((bx1 - bx0, by1 - by0), Image.PERSPECTIVE, c,
                                                                Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.6)), np.float32)
        region = base[by0:by1, bx0:bx1]
        m = (a[..., 3] / 255.0)[..., None]
        base[by0:by1, bx0:bx1] = region * (1 - m) + (region * (np.array(INK, np.float32) / 255.0) * 0.9 + 12) * m
    board = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    paths = {k: circle_path(notes[k], seed=k) for k in CIRCLED}
    bsize = int(notes[0]["side"] * 0.42)
    bdg = badge(bsize)
    SW, SH = board.size
    out = WORK / f"whiteboard-composite-{lang}.mp4"
    enc = subprocess.Popen([g.ffmpeg(), "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "15",
                            "-preset", "slow", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    rng = np.random.default_rng(7)
    fx, fy = np.mean([n["cx"] for n in notes]), np.mean([n["cy"] for n in notes])
    for i in range(int(WB_DUR * FPS)):
        t = i / FPS
        img = board.copy()
        for j, k in enumerate(CIRCLED):
            u = (t - CIRCLE_AT[j]) / CIRCLE_DUR
            draw_stroke(img, paths[k], ease(u) if u < 1 else 1.0)
            p = ease((t - CIRCLE_AT[j] - CIRCLE_DUR - 0.08) / 0.28)
            if p > 0:
                cx = notes[k]["cx"] + notes[k]["side"] * 0.78        # just outside the loop, top right
                cy = notes[k]["cy"] - notes[k]["side"] * 0.70
                s = 0.6 + 0.4 * p + 0.12 * np.sin(min(1.0, p) * np.pi)
                bb = bdg.resize((max(1, int(bsize * s)),) * 2, Image.LANCZOS)
                bb.putalpha(Image.fromarray((np.asarray(bb)[..., 3] * min(1.0, p * 1.4)).astype(np.uint8)))
                img.paste(bb, (int(cx - bb.width / 2), int(cy - bb.height / 2)), bb)
        # slow push-in on the still (it is 2752 px wide: always downscaled, always sharp)
        z = 1 + 0.12 * ease(t / WB_DUR)
        vw = min(SW, SH * 16 / 9) / z      # the still is a hair wider than 16:9
        vh = vw * 9 / 16
        x0 = min(max(0, fx - vw / 2), SW - vw)
        y0 = min(max(0, fy - vh / 2), SH - vh)
        frame = np.asarray(img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + vw, y0 + vh)), np.float32)
        frame += rng.normal(0, 2.6, frame.shape)                   # grain, so the still never looks frozen
        enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
        if i in (0, 50, 66, 90, 130, 160, 280):
            Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).save(WORK / f"wb2_{lang}_{i:03d}.jpg", quality=92)
    enc.stdin.close(); enc.wait()
    whiteboard_audio()
    print(f"shot 2 ({lang}) ->", out.name)
    return out


def whiteboard_audio() -> Path:
    """Room tone + real marker strokes, both cut from the first whiteboard clip's own audio (Omni), placed on
    the drawn circles: no synthesized sounds."""
    src = WORK / "whiteboard-175715.mp4"
    out = WORK / "whiteboard-room.wav"
    strokes = [(1.85, 2.40), (3.30, 3.90), (1.85, 2.40)]
    ins, parts, mix = ["-i", str(src)], ["[0:a]atrim=6.0:9.9,asetpts=PTS-STARTPTS,aloop=loop=2:size=187200,"
                                          f"atrim=0:{WB_DUR},afade=t=in:d=0.3[room]"], ["[room]"]
    for j, (a, b) in enumerate(strokes):
        ms = int(CIRCLE_AT[j] * 1000)
        parts.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st={b - a - 0.08:.2f}:d=0.08,"
                     f"volume=2.2,adelay={ms}|{ms}[m{j}]")
        mix.append(f"[m{j}]")
    graph = ";".join(parts + ["".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first[a]"])
    subprocess.run([g.ffmpeg(), "-loglevel", "error", "-y", *ins, "-filter_complex", graph, "-map", "[a]",
                    "-ar", "48000", "-ac", "2", str(out)], check=True)
    return out


# ── shot 3: the AI brain and the tools it connects to, orbiting in from outside the frame ──────────────────
# Groups enter as the voice names them (word times measured on v-logos-en.wav: pauses at 5.79, 7.89, 11.04 s).
# A name-only chip (no logo) is used for brands that asked Simple Icons to remove theirs.
LOGO_GROUPS = [
    (2.0, ["n8n", "zapier", "python", "chip:API"]),                       # "delegating repetitive tasks"
    (4.6, ["whatsapp", "telegram", "instagram", "facebook"]),             # "attention 24/7"
    (7.0, ["claude", "googlegemini", "notion", "googledrive", "chip:ChatGPT"]),   # "the tools you use every day"
    (8.8, ["gmail"]),                                                     # "your email"
    (9.3, ["shopify", "googlesheets", "chip:Excel"]),                     # "inventory"
    (10.2, ["stripe", "quickbooks", "odoo"]),                             # "invoicing"
    (11.3, ["youtube", "tiktok", "elevenlabs", "figma", "chip:Adobe"]),   # "video and content creation"
]
LOGOS_DUR = 13.8
VOICE_OFFSET = 0.35          # the voice starts this long after the shot
RINGS = [(390, 0, 0.045), (490, 0, 0.045), (590, 0, 0.045), (690, 0, 0.045)]   # radius, -, orbit speed: all together
TILT = 0.65                  # orbit plane seen in perspective
CENTER = (960, 520)


def tile(name: str, size: int = 240) -> Image.Image:
    """App-icon style tile: brand color with the white glyph, or a dark chip with the name."""
    import json
    S = 2
    im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    box = [6 * S, 6 * S, (size - 6) * S, (size - 6) * S]
    rad = int(size * 0.26 * S)
    if name.startswith("chip:"):
        text = name[5:]
        d.rounded_rectangle(box, rad, fill=(24, 30, 37, 255), outline=GLOW + (255,), width=4 * S)
        for fs in range(96, 20, -4):
            font = f("segoeuib.ttf", fs * S)
            if font.getlength(text) < (size - 50) * S:
                break
        bb = d.textbbox((0, 0), text, font=font)
        d.text(((size * S - (bb[2] - bb[0])) / 2 - bb[0], (size * S - (bb[3] - bb[1])) / 2 - bb[1]), text,
               font=font, fill=(236, 242, 245, 255))
    else:
        colors = json.loads((HERE / "out/logos/colors.json").read_text())
        hx = colors[name]["hex"].lstrip("#")
        rgb = tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))
        dark = sum(rgb) < 120
        fill = (240, 242, 244) if dark else rgb
        d.rounded_rectangle(box, rad, fill=fill + (255,))
        # soft top highlight, like a real app icon
        hl = Image.new("L", im.size, 0)
        ImageDraw.Draw(hl).rounded_rectangle([box[0], box[1], box[2], box[1] + (box[3] - box[1]) // 2], rad, fill=38)
        im.paste(Image.new("RGBA", im.size, (255, 255, 255, 255)), (0, 0), hl)
        glyph = Image.open(HERE / f"out/logos/{name}.png").convert("RGBA")
        gs = int(size * 0.56 * S)
        glyph = glyph.resize((gs, gs), Image.LANCZOS)
        if dark:
            a = glyph.split()[3]
            glyph = Image.new("RGBA", glyph.size, (20, 20, 24, 255)); glyph.putalpha(a)
        im.alpha_composite(glyph, ((size * S - gs) // 2, (size * S - gs) // 2))
    return im.resize((size, size), Image.LANCZOS)


def logos_background() -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = CENTER
    d = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2)
    night = np.array([9, 11, 14], np.float32)
    glow = np.array(GLOW, np.float32)
    bg = night + glow[None, None, :] * (0.10 * np.exp(-(d / 0.28) ** 2))[..., None]
    bg *= (1 - 0.35 * np.clip(d / 0.75, 0, 1) ** 2)[..., None]
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img, "RGBA")
    for r, _, _ in RINGS:                                                   # faint orbit guides
        dr.ellipse([cx - r, cy - r * TILT, cx + r, cy + r * TILT], outline=GLOW + (16,), width=1)
    return np.asarray(img, np.float32)


def logos_shot() -> Path:
    rng = np.random.default_rng(3)
    names = [n for _, grp in LOGO_GROUPS for n in grp]
    starts = {}
    for t0, grp in LOGO_GROUPS:
        for k, n in enumerate(grp):
            starts[n] = t0 - 0.3 + k * 0.16
    # slots: farthest-point sampling on the four orbits (screen space), capped per orbit, so no two tiles touch
    # once everyone has arrived; all orbits then turn together, which keeps that spacing. Logos are dealt to the
    # slots (sorted by angle) with a step of 9, so the members of one group land far apart.
    N = len(names)
    caps = [5, 6, 7, 7]
    cand = [(ri, a) for ri in range(len(RINGS)) for a in np.arange(0, 2 * np.pi, 0.03)]
    pos = np.array([(RINGS[ri][0] * np.cos(a), RINGS[ri][0] * np.sin(a) * TILT) for ri, a in cand])
    chosen = [int(rng.integers(len(cand)))]
    count = [0] * len(RINGS); count[cand[chosen[0]][0]] += 1
    dmin = np.linalg.norm(pos - pos[chosen[0]], axis=1)
    while len(chosen) < N:
        ok = np.array([count[ri] < caps[ri] for ri, _ in cand])
        k = int(np.argmax(np.where(ok, dmin, -1)))
        chosen.append(k); count[cand[k][0]] += 1
        dmin = np.minimum(dmin, np.linalg.norm(pos - pos[k], axis=1))
    print(f"logo slots: closest pair {dmin[chosen].max() if False else min(np.linalg.norm(pos[a] - pos[b]) for a in chosen for b in chosen if a < b):.0f} px apart")
    slots = sorted((cand[k] for k in chosen), key=lambda c: c[1])
    plan = {}
    for j, n in enumerate(names):
        ri, a = slots[(j * 9) % N]
        plan[n] = {"ring": ri, "base": a, "dur": float(rng.uniform(1.2, 2.5)), "sweep": float(rng.uniform(1.4, 2.6))}
    tiles = {n: tile(n) for n in names}
    bg = logos_background()
    brain_src = Image.open(WORK / "brain-still.png").convert("RGB")
    out = WORK / "logos-composite.mp4"
    enc = subprocess.Popen([g.ffmpeg(), "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "15",
                            "-preset", "slow", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    cx, cy = CENTER
    stars = rng.uniform([0, 0], [W, H], (160, 2))
    star_ph = rng.uniform(0, 6.28, 160)
    finale = 12.35                         # every connection lights up at once, on "content creation"
    for i in range(int(LOGOS_DUR * FPS)):
        t = i / FPS
        frame = bg.copy()
        lines = Image.new("L", (W * 2, H * 2), 0)                           # glow layer (2x, anti-aliased)
        ld = ImageDraw.Draw(lines)
        for (sx, sy), ph in zip(stars, star_ph):                            # slow twinkle
            v = int(40 + 40 * np.sin(t * 1.3 + ph))
            ld.ellipse([sx * 2 - 2, sy * 2 - 2, sx * 2 + 2, sy * 2 + 2], fill=max(0, v))
        placed, pulse = [], 0.0
        for n in names:
            p = plan[n]
            r, _, w = RINGS[p["ring"]]
            u = (t - starts[n]) / p["dur"]
            if u <= 0:
                continue
            e_ = 1 - (1 - min(u, 1.0)) ** 3                                 # ease-out: fast in, gentle landing
            ang = p["base"] + w * t - p["sweep"] * (1 - e_)
            rad = r + (1500 - r) * (1 - e_)
            x, y = cx + rad * np.cos(ang), cy + rad * np.sin(ang) * TILT
            depth = (np.sin(ang) + 1) / 2                                   # 0 back .. 1 front
            scale = (0.80 + 0.20 * depth) * (0.55 + 0.45 * e_) * 0.44
            arrived = t - starts[n] - p["dur"]
            if arrived > 0:
                k = min(1.0, arrived / 0.5)
                a_line = 40 + 120 * max(0.0, 1 - arrived / 0.9)
                if t > finale:
                    a_line = max(a_line, 170 * max(0.0, 1 - (t - finale) / 1.2) + 40)
                ld.line([(x * 2, y * 2), (cx * 2, cy * 2)], fill=int(a_line), width=2)
                if k < 1:                                                   # a light pulse runs to the brain
                    px, py = x + (cx - x) * k, y + (cy - y) * k
                    ld.ellipse([px * 2 - 9, py * 2 - 9, px * 2 + 9, py * 2 + 9], fill=255)
                    rr = 70 * scale * 2 * (1 + 1.4 * k)
                    ld.ellipse([x * 2 - rr, y * 2 - rr, x * 2 + rr, y * 2 + rr], outline=int(200 * (1 - k)), width=3)
                else:
                    pulse += max(0.0, 1 - (arrived - 0.5) / 0.6)
            placed.append((depth, n, x, y, scale, e_))
        if t > finale:
            pulse += 1.2 * max(0.0, 1 - (t - finale) / 1.0)
        glow_l = lines.resize((W, H), Image.LANCZOS)
        gl = np.asarray(glow_l, np.float32) / 255.0
        gb = np.asarray(glow_l.filter(ImageFilter.GaussianBlur(5)), np.float32) / 255.0
        frame += (gl * 0.9 + gb * 1.2)[..., None] * np.array(GLOW, np.float32)[None, None, :]
        img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).convert("RGBA")

        def draw_tiles(front: bool):
            for depth, n, x, y, scale, e_ in sorted(placed):
                if (depth >= 0.5) != front:
                    continue
                sz = max(4, int(240 * scale))
                tl = tiles[n].resize((sz, sz), Image.LANCZOS)
                a = np.asarray(tl, np.float32)
                bright = 0.72 + 0.28 * depth
                a[..., :3] *= bright
                a[..., 3] *= min(1.0, e_ * 1.6)
                tl = Image.fromarray(a.clip(0, 255).astype(np.uint8))
                img.alpha_composite(tl, (int(x - sz / 2), int(y - sz / 2)))

        draw_tiles(front=False)
        # the brain: fades and grows in, beats a little with every arrival; screen blend (its black disappears)
        appear = ease((t - 0.1) / 1.1)
        bs = int(570 * (0.86 + 0.14 * appear) * (1 + 0.035 * min(pulse, 1.5)))
        br = np.asarray(brain_src.resize((bs, bs), Image.LANCZOS), np.float32) / 255.0 * appear * (1 + 0.25 * min(pulse, 1.2))
        base = np.asarray(img, np.float32)
        x0, y0 = cx - bs // 2, cy - bs // 2
        reg = base[y0:y0 + bs, x0:x0 + bs, :3] / 255.0
        base[y0:y0 + bs, x0:x0 + bs, :3] = (1 - (1 - reg) * (1 - np.clip(br, 0, 1))) * 255
        img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
        draw_tiles(front=True)
        img = push_in(img.convert("RGB"), t, LOGOS_DUR, z1=1.06, focus=CENTER)
        enc.stdin.write(np.asarray(img).tobytes())
        if i in (30, 90, 160, 230, 300, 380, 405):
            img.save(WORK / f"lg_{i:03d}.jpg", quality=92)
    enc.stdin.close(); enc.wait()
    # a quiet room-tone bed (from the whiteboard clip's own audio) so the voice never sits on digital silence
    subprocess.run([g.ffmpeg(), "-loglevel", "error", "-y", "-i", str(WORK / "whiteboard-175715.mp4"), "-filter_complex",
                    f"[0:a]atrim=6.0:9.9,asetpts=PTS-STARTPTS,aloop=loop=3:size=187200,atrim=0:{LOGOS_DUR},"
                    "afade=t=in:d=0.3[a]", "-map", "[a]", "-ar", "48000", "-ac", "2", str(WORK / "logos-room.wav")],
                   check=True)
    print("shot 3 ->", out.name)
    return out


# ── shot 4: a shop owner talks to his AI agent from his phone; the chat floats up out of the phone ─────────
# The phone's screen is never shown: the messages rise from the phone as speech bubbles (user: white, agent: teal)
# and older ones drift up and fade. The phone is tracked frame by frame so the bubbles always come out of it.
PHONE_MSGS = {
    "en": [("user", "Answer today's customer emails and send the overdue invoices."),
           ("ai", "Sure, I'm on it! 💪"),
           ("ai", "✅ Done: 14 emails answered,|3 invoices sent.")],
    "es": [("user", "Responde los correos de clientes de hoy y envía las facturas vencidas."),
           ("ai", "¡Listo, me pongo en ello! 💪"),
           ("ai", "✅ Hecho: 14 correos respondidos,|3 facturas enviadas.")],
}
PHONE_T = {"user": 0.6, "typing_end": 2.8, "dots": 3.2, "ai1": 4.0, "ai2": 6.0}
PHONE_DUR = 8.0
PHONE_TPL = (1630, 290, 1710, 350)          # phone top with the camera lenses, on frame 0
PHONE_TIP0 = (1662, 282)                    # where the bubbles' tail points on frame 0 (just above the phone)


def track_phone(src: Path) -> list[tuple[float, float]]:
    import cv2
    fr0 = next(frames(src))
    x0, y0, x1, y1 = PHONE_TPL
    tpl = cv2.cvtColor(np.ascontiguousarray(fr0[y0:y1, x0:x1]), cv2.COLOR_RGB2GRAY)
    out, last = [], (x0, y0)
    for fr in frames(src):
        sx, sy = last[0] - 40, last[1] - 40
        win = cv2.cvtColor(np.ascontiguousarray(fr[sy:sy + (y1 - y0) + 80, sx:sx + (x1 - x0) + 80]), cv2.COLOR_RGB2GRAY)
        res = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
        _, _, _, (mx, my) = cv2.minMaxLoc(res)
        last = (sx + mx, sy + my)
        out.append((last[0] - x0, last[1] - y0))
    a = np.array(out, np.float32)
    k = np.ones(7) / 7                       # smooth the jitter, keep the motion
    sm = np.stack([np.convolve(np.pad(a[:, i], 3, mode="edge"), k, "valid") for i in range(2)], 1)
    return [(float(dx), float(dy)) for dx, dy in sm]


def wrap_text(text: str, font, maxw: float) -> list[str]:
    """Word wrap; "|" forces a line break (keeps a number with its noun)."""
    out = []
    for para in text.split("|"):
        lines, cur = [], ""
        for w_ in para.split():
            test = (cur + " " + w_).strip()
            if font.getlength(test) > maxw and cur:
                lines.append(cur); cur = w_
            else:
                cur = test
        out += lines + [cur]
    return out


def speech_bubble(text: str, kind: str, shown: int | None = None, dots: float | None = None) -> Image.Image:
    """A rounded speech bubble with a tail at the bottom, 2x supersampled, with a soft shadow. `shown` limits the
    visible characters (typing); `dots` draws the 'typing…' dots instead of text."""
    S = 2
    font = f("segoeui.ttf", 27 * S)
    emoji = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 25 * S)
    maxw = 370 * S
    lines = wrap_text(text, font, maxw) if dots is None else ["   "]
    lh = int(37 * S)
    tw = max(font.getlength(x) for x in lines) if dots is None else 90 * S
    pw, ph = int(tw + 52 * S), int(lh * len(lines) + 30 * S)
    tail = 22 * S
    pad = 24 * S
    im = Image.new("RGBA", (pw + 2 * pad, ph + tail + 2 * pad), (0, 0, 0, 0))
    fill = (255, 255, 255, 246) if kind == "user" else GLOW + (246,)
    ink = (22, 26, 32, 255) if kind == "user" else (6, 40, 37, 255)
    sh = Image.new("L", im.size, 0)
    sd = ImageDraw.Draw(sh)
    bx0, by0 = pad, pad
    sd.rounded_rectangle([bx0, by0 + 8 * S, bx0 + pw, by0 + ph + 8 * S], 30 * S, fill=110)
    sh = sh.filter(ImageFilter.GaussianBlur(10 * S))
    im.paste(Image.new("RGBA", im.size, (0, 0, 0, 255)), (0, 0), sh)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([bx0, by0, bx0 + pw, by0 + ph], 30 * S, fill=fill)
    tx = bx0 + pw * 0.62                                       # tail toward the phone (bottom, a bit right)
    d.polygon([(tx - 18 * S, by0 + ph - 2), (tx + 14 * S, by0 + ph - 2), (tx + 6 * S, by0 + ph + tail)], fill=fill)
    if dots is not None:
        for i in range(3):
            on = int(dots * 5) % 3 == i
            cx_, cy_ = bx0 + pw / 2 + (i - 1) * 26 * S, by0 + ph / 2
            r_ = (8 if on else 6) * S
            d.ellipse([cx_ - r_, cy_ - r_, cx_ + r_, cy_ + r_], fill=ink[:3] + ((255 if on else 120),))
    else:
        left = len(text) if shown is None else shown
        for k, line in enumerate(lines):
            x, y = bx0 + 26 * S, by0 + 14 * S + k * lh
            for ch in line:
                if left <= 0:
                    break
                ef = ord(ch) > 0x2600
                d.text((x, y + (4 * S if ef else 0)), ch, font=emoji if ef else font, fill=ink, embedded_color=ef)
                x += (emoji if ef else font).getlength(ch)
                left -= 1
            left -= 1                                          # the space eaten by the line break
    im = im.resize((im.width // S, im.height // S), Image.LANCZOS)
    im.info["tail"] = (int((tx) / S), int((by0 + ph + tail) / S))
    return im


def phone_shot(lang: str = "en") -> Path:
    src = latest("phone-[0-9]*.mp4")
    track = track_phone(src)
    print(f"phone moves up to {max(abs(x) for x, _ in track):.0f}px x, {max(abs(y) for _, y in track):.0f}px y")
    msgs = PHONE_MSGS[lang]
    T = PHONE_T
    out = WORK / f"phone-composite-{lang}.mp4"
    enc = subprocess.Popen([g.ffmpeg(), "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "15",
                            "-preset", "slow", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    full = {k: speech_bubble(m[1], m[0]) for k, m in enumerate(msgs)}

    def pop(t0, t):                                            # ease-out-back: a small overshoot when it appears
        u = min(1.0, max(0.0, (t - t0) / 0.32))
        c = 1.7
        return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2 if u > 0 else 0.0

    for i, fr in enumerate(frames(src)):
        t = i / FPS
        if t > PHONE_DUR:
            break
        dx, dy = track[min(i, len(track) - 1)]
        tipx, tipy = PHONE_TIP0[0] + dx, PHONE_TIP0[1] + dy
        # the stack, newest at the bottom (closest to the phone)
        stack = []
        if t >= T["user"]:
            n = len(msgs[0][1])
            shown = int(n * min(1.0, (t - T["user"] - 0.1) / (T["typing_end"] - T["user"] - 0.1)))
            stack.append((T["user"], speech_bubble(msgs[0][1], "user", shown=max(0, shown)) if shown < n else full[0]))
        if T["dots"] <= t < T["ai1"]:
            stack.append((T["dots"], speech_bubble("", "ai", dots=t)))
        if t >= T["ai1"]:
            stack.append((T["ai1"], full[1]))
        if t >= T["ai2"]:
            stack.append((T["ai2"], full[2]))
        img = Image.fromarray(fr).convert("RGBA")
        y_bottom = tipy
        for j, (t0, b) in enumerate(reversed(stack)):
            p = pop(t0, t)
            if p <= 0:
                continue
            sc = 0.65 + 0.35 * p
            bb = b.resize((max(1, int(b.width * sc)), max(1, int(b.height * sc))), Image.LANCZOS)
            tx, ty = b.info["tail"]
            # newest bubble: tail on the phone; older ones stacked above it, gliding up as new ones arrive
            if j == 0:
                x = tipx - tx * sc
                y = y_bottom - ty * sc
            else:
                x = tipx - tx * sc
                y = y_bottom - bb.height + 18
            x = min(max(x, 1405), W - bb.width - 20)                   # never over his face, never off the edge
            a = np.asarray(bb, np.float32)
            fade = np.clip((y + bb.height * 0.2) / 70.0, 0, 1)          # older bubbles fade out fully at the top
            a[..., 3] *= min(1.0, p * 1.5) * fade
            img.alpha_composite(Image.fromarray(a.clip(0, 255).astype(np.uint8)), (int(x), int(y)))
            y_bottom = y + 18
        frame = img.convert("RGB")
        frame = push_in(frame, t, PHONE_DUR, z1=1.04, focus=(1600, 140))   # focus high: keeps the bubbles in frame
        enc.stdin.write(np.asarray(frame).tobytes())
        if i in (30, 75, 105, 130, 190, 230):
            frame.save(WORK / f"ph_{lang}_{i:03d}.jpg", quality=92)
    enc.stdin.close(); enc.wait()
    print(f"shot 4 ({lang}) ->", out.name)
    return out


# ── shot 5a: client requests arrive, in first person, over Iván's main screen ───────────────────────────────
# Generic initials (no real clients). Each new message slides in at the bottom and pushes the others up.
REQUESTS = {
    "en": ["I need several Odoo e-commerce sites built for my current clients.",
           "I want AI to handle my emails, messages, inventory and invoicing.",
           "I need a secure, automated CEO command center in our Google Workspace, with Looker Studio dashboards.",
           "I need a Python web app that connects to a third-party API, processes the data and shows clear results."],
    "es": ["Necesito varios sitios de comercio electrónico en Odoo para mis clientes actuales.",
           "Quiero que la IA gestione mis correos, mensajes, inventario y facturación.",
           "Necesito un centro de mando del CEO, seguro y automatizado, en nuestro Google Workspace, con paneles de "
           "Looker Studio.",
           "Necesito una app web en Python que se conecte a una API externa, procese los datos y muestre resultados "
           "claros."],
}
REQ_AVATARS = [("LM", (242, 180, 92)), ("DK", (94, 234, 212)), ("SR", (167, 139, 250)), ("AT", (96, 165, 250))]
REQ_AT = (0.9, 3.5, 6.1, 8.7)
REQ_SPEED = 0.813                    # the 10 s Omni clip, slowed to the length of the voice line
REQ_DUR = 12.3
REQ_BOX = (272, 712)             # left edge of the cards and bottom of the stack (over the main monitor)


def message_card(text: str, initials: str, color) -> Image.Image:
    """Incoming message: avatar with initials + white bubble, soft shadow, 2x supersampled."""
    S = 2
    font, fb = f("segoeui.ttf", 27 * S), f("segoeuib.ttf", 24 * S)
    lines = wrap_text(text, font, 500 * S)
    lh = 37 * S
    av = 58 * S
    bw = int(max(font.getlength(x) for x in lines) + 48 * S)
    bh = int(lh * len(lines) + 30 * S)
    pad = 26 * S
    w, h = av + 16 * S + bw + 2 * pad, max(av, bh) + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("L", im.size, 0)
    bx = pad + av + 16 * S
    ImageDraw.Draw(sh).rounded_rectangle([bx, pad + 10 * S, bx + bw, pad + bh + 10 * S], 26 * S, fill=120)
    im.paste(Image.new("RGBA", im.size, (0, 0, 0, 255)), (0, 0), sh.filter(ImageFilter.GaussianBlur(12 * S)))
    d = ImageDraw.Draw(im)
    ay = pad + bh - av                                           # avatar aligned with the bubble's last line
    d.ellipse([pad, ay, pad + av, ay + av], fill=color + (255,))
    tb = d.textbbox((0, 0), initials, font=fb)
    d.text((pad + (av - (tb[2] - tb[0])) / 2 - tb[0], ay + (av - (tb[3] - tb[1])) / 2 - tb[1]), initials, font=fb,
           fill=(12, 16, 20, 255))
    d.rounded_rectangle([bx, pad, bx + bw, pad + bh], 26 * S, fill=(255, 255, 255, 248))
    d.rounded_rectangle([bx, pad + bh - 30 * S, bx + 30 * S, pad + bh], 6 * S, fill=(255, 255, 255, 248))  # flat corner by the avatar
    for k, line in enumerate(lines):
        d.text((bx + 24 * S, pad + 14 * S + k * lh), line, font=font, fill=(22, 26, 32, 255))
    return im.resize((w // S, h // S), Image.LANCZOS)


def requests_shot(lang: str = "en") -> Path:
    src = latest("requests-[0-9]*.mp4")
    cards = [message_card(t, *REQ_AVATARS[k]) for k, t in enumerate(REQUESTS[lang])]
    out = WORK / f"requests-composite-{lang}.mp4"
    enc = subprocess.Popen([g.ffmpeg(), "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "15",
                            "-preset", "slow", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    dec = subprocess.Popen([g.ffmpeg(), "-loglevel", "error", "-i", str(src), "-vf",
                            f"setpts=PTS/{REQ_SPEED},fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    x_left, y_base = REQ_BOX
    for i in range(int(REQ_DUR * FPS)):
        buf = dec.stdout.read(W * H * 3)
        if len(buf) == W * H * 3:
            fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        t = i / FPS
        img = Image.fromarray(fr).convert("RGBA")
        # stack from the newest (bottom) up; each arrival slides in and pushes the rest with an ease
        visible = [k for k, t0 in enumerate(REQ_AT) if t >= t0]
        y = y_base
        for k in reversed(visible):
            c = cards[k]
            u = ease((t - REQ_AT[k]) / 0.45)
            if k == visible[-1]:
                y_card = y - c.height * u                            # the newest grows the stack as it slides in
                xo = int((1 - u) * 40)
            else:
                y_card = y - c.height
                xo = 0
            a = np.asarray(c, np.float32)
            fade = np.clip((y_card - 20) / 70.0, 0, 1)                # leaving at the top: gone before the edge
            a[..., 3] *= (u if k == visible[-1] else 1.0) * fade
            img.alpha_composite(Image.fromarray(a.clip(0, 255).astype(np.uint8)), (int(x_left + xo), int(y_card)))
            y = y_card + 14
        frame = push_in(img.convert("RGB"), t, REQ_DUR, z1=1.05, focus=(REQ_BOX[0] + 330, 360))
        enc.stdin.write(np.asarray(frame).tobytes())
        if i in (40, 120, 200, 280, 360):
            frame.save(WORK / f"rq_{lang}_{i:03d}.jpg", quality=92)
    dec.stdout.close(); dec.wait()
    enc.stdin.close(); enc.wait()
    print(f"shot 5a ({lang}) ->", out.name)
    return out


# ── shot 5b: the three key questions, as titles over the 5a scene going out of focus ─────────────────────
# Continues 5a without a cut: its last frame blurs and darkens while the questions come in, each one when the voice
# asks it. Timings come from the pauses of that language's voice line, so the ES version syncs by itself.
QUESTIONS = {
    "en": ("THE KEY QUESTIONS",
           ["How do I make my workflow more productive?",
            "How do I make my products and services more appealing?",
            "And above all: how does AI grow my profits?"]),
    "es": ("LAS PREGUNTAS CLAVE",
           ["¿Cómo hago más productivo mi flujo de trabajo?",
            "¿Cómo hago mis productos y servicios más atractivos?",
            "Y sobre todo: ¿cómo hace crecer la IA mis ganancias?"]),
}


def speech_segments(wav: Path, min_pause: float = 0.1) -> list[tuple[float, float]]:
    """(start, end) of each spoken stretch, split at pauses of at least `min_pause` s."""
    raw = subprocess.run([g.ffmpeg(), "-v", "error", "-i", str(wav), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32)
    hop = 160
    db = 20 * np.log10(np.array([np.sqrt(np.mean(a[i:i + hop] ** 2)) for i in range(0, len(a) - hop, hop)]) + 1e-9)
    loud = db >= db.max() - 38
    segs, start, quiet_run = [], None, 0
    for k, on in enumerate(loud):
        if on:
            if start is None:
                start = k
            quiet_run = 0
        elif start is not None:
            quiet_run += 1
            if quiet_run >= int(min_pause * 100):
                segs.append((start / 100, (k - quiet_run + 1) / 100)); start = None; quiet_run = 0
    if start is not None:
        segs.append((start / 100, len(loud) / 100))
    return segs


def last_frame(path: Path) -> np.ndarray:
    fr = None
    for fr in frames(path):
        pass
    return fr


def questions_shot(lang: str = "en") -> Path:
    header, qs = QUESTIONS[lang]
    voice = WORK / f"v-questions-{lang}.wav"
    if not voice.exists():
        g.tts_line("portfolio", VOICE[lang]["questions"], voice, "Charon")
    segs = speech_segments(voice)
    # header, Q1, Q2, then Q3 may be split in two ("And above all" / "how does AI…"): Q3 starts at the 4th stretch
    starts = [s for s, _ in segs]
    if len(starts) < 4:
        raise SystemExit(f"expected at least 4 spoken stretches, got {segs}")
    t_head, t_q = starts[0], starts[1:4]
    dur_voice = segs[-1][1]
    dur = round(dur_voice + VOICE_OFFSET + 0.9, 2)
    print(f"5b ({lang}): header {t_head:.2f}s, questions at {[round(x, 2) for x in t_q]}, shot {dur}s")
    bg = Image.fromarray(last_frame(WORK / f"requests-composite-{lang}.mp4"))
    small = f("consolab.ttf", 26)
    maxw = 1760
    for size in range(62, 44, -2):                                 # one line per question when it fits
        title = f("Fraunces.ttf", size)
        if all(title.getlength(q) <= maxw for q in qs):
            break
    blocks = [wrap_text(q, title, maxw) for q in qs]
    lh = int(size * 1.26)
    gap = 46
    total = 60 + sum(len(b) * lh for b in blocks) + gap * (len(blocks) - 1)
    y0 = (H - total) // 2
    out = WORK / f"questions-composite-{lang}.mp4"
    enc = subprocess.Popen([g.ffmpeg(), "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "15",
                            "-preset", "slow", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    for i in range(int(dur * FPS)):
        t = i / FPS
        tv = t - VOICE_OFFSET                                       # voice time
        # background: 5a's last frame, a slow continuing push-in, going out of focus and dark
        k = ease(t / 0.9)
        z = 1.0 + 0.035 * (t / dur)          # 5a's frame is already pushed in to 1.05 around the same point
        x0, y0b = 602 * (1 - 1 / z), 360 * (1 - 1 / z)
        b = bg.resize((W, H), Image.LANCZOS, box=(x0, y0b, x0 + W / z, y0b + H / z))
        if k > 0:
            b = b.filter(ImageFilter.GaussianBlur(22 * k))
        a = np.asarray(b, np.float32) * (1 - 0.58 * k)
        img = Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        # header (letter-spaced, teal)
        p = ease((tv - t_head + 0.15) / 0.5)
        if p > 0:
            spaced = " ".join(header)
            tw = small.getlength(spaced)
            d.text(((W - tw) / 2, y0 + (1 - p) * 16), spaced, font=small, fill=GLOW + (int(255 * p),))
        y = y0 + 60
        for qi, lines in enumerate(blocks):
            p = ease((tv - t_q[qi] + 0.1) / 0.55)
            if p > 0:
                newest = qi == len(blocks) - 1 or tv < t_q[qi + 1] - 0.1
                last = qi == len(blocks) - 1
                dim = 1.0 if newest else 0.5                         # earlier questions step back
                color = GLOW if last else (240, 243, 246)
                for li, line in enumerate(lines):
                    tw = title.getlength(line)
                    d.text(((W - tw) / 2, y + li * lh + (1 - p) * 26), line, font=title,
                           fill=color + (int(255 * p * dim),))
            y += len(lines) * lh + gap
        img.alpha_composite(layer)
        enc.stdin.write(np.asarray(img.convert("RGB")).tobytes())
        if i in (20, 90, 180, 300, int(dur * FPS) - 5):
            img.convert("RGB").save(WORK / f"q_{lang}_{i:03d}.jpg", quality=92)
    enc.stdin.close(); enc.wait()
    print(f"shot 5b ({lang}) ->", out.name)
    return out


# ── shot 6: pull out of the video into a phone; a business owner watching it taps "Hire me on Upwork" ─────────
# The phone stands still on a desk stand with a black screen (Omni, locked-off camera). Everything on the screen is
# ours: first 5b's last frame (the video itself, playing full screen) shrinking and going soft as we pull out, then
# the real portfolio page (captured with Playwright at 844x390 @3x). Anything not black over the screen (her finger,
# the stand's lip) stays in front.
VIEW_Q = [(581, 793), (848, 772), (864, 895), (600, 919)]   # screen corners on the clip (camera and phone static)
VIEW_TAP = 4.0               # her fingertip presses the glass on the button (measured on viewer-202559)
VIEW_DUR = 7.0
PAGE_BTN = (663.8, 16, 156.2, 36)  # "Hire me on Upwork" box on the 844x390 page (CSS px)


def capture_page(path: Path) -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 844, "height": 390}, device_scale_factor=3, is_mobile=True, has_touch=True)
        pg.goto("https://ivanboot.dev/ai-agents", wait_until="load")
        pg.wait_for_timeout(3500)
        pg.screenshot(path=str(path))
        b.close()


def cam_keys(t: float) -> tuple[float, tuple[float, float]]:
    """Virtual camera on the clip: zoom and center. Pull-out, a look at her, a push-in for the tap, back out."""
    sc = np.mean(VIEW_Q, axis=0)
    z0 = H / (np.mean([VIEW_Q[3][1] - VIEW_Q[0][1], VIEW_Q[2][1] - VIEW_Q[1][1]]))
    wide, phone = (1.5, (1080.0, 600.0)), (2.0, (760.0, 822.0))
    keys = [(0.0, (z0, tuple(sc))), (1.9, wide), (2.6, wide), (VIEW_TAP - 0.05, phone), (VIEW_TAP + 0.6, phone),
            (6.4, wide), (VIEW_DUR, wide)]
    for n, ((t0, a), (t1, b)) in enumerate(zip(keys, keys[1:])):
        if t <= t1:
            u = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            z = float(np.exp(np.log(a[0]) + (np.log(b[0]) - np.log(a[0])) * u))
            if n == 0:
                # pull-out: the screen glides on the OUTPUT from the frame center to where it ends up, so it never
                # jumps to a corner while the zoom is still huge
                end = ((sc[0] - b[1][0]) * b[0] + W / 2, (sc[1] - b[1][1]) * b[0] + H / 2)
                px, py = W / 2 + (end[0] - W / 2) * u, H / 2 + (end[1] - H / 2) * u
                return z, (sc[0] - (px - W / 2) / z, sc[1] - (py - H / 2) / z)
            return z, (a[1][0] + (b[1][0] - a[1][0]) * u, a[1][1] + (b[1][1] - a[1][1]) * u)
    return keys[-1][1][0], keys[-1][1][1]


def viewer_shot(lang: str = "en") -> Path:
    src = latest("viewer-[0-9]*.mp4")
    page_path = WORK / "page-landscape.png"
    if not page_path.exists():
        capture_page(page_path)
    page = Image.open(page_path).convert("RGB")
    PW, PH = page.size
    # 5b's last frame, played "full screen" on the landscape phone: 16:9 centered with black side bars
    vid = Image.fromarray(last_frame(WORK / f"questions-composite-{lang}.mp4"))
    vw = int(PH * 16 / 9)
    bar = (PW - vw) // 2
    # where the 16:9 picture must be at t=0 (filling the output) -> the whole screen canvas sits a bit wider
    sx = W / vw
    full_q = [(-bar * sx, 0), (W + bar * sx, 0), (W + bar * sx, H), (-bar * sx, H)]
    scr_mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(scr_mask).polygon(VIEW_Q, fill=255)
    # occluders use the full screen area (the bezel edge in front of the picture is physically right, and a smaller
    # mask left a strip of picture over her hand at the edge); reflections stay off the bright bezel
    omask = np.asarray(scr_mask.filter(ImageFilter.MaxFilter(7)), np.float32) / 255.0   # a bit past the edge
    smask = np.asarray(scr_mask.filter(ImageFilter.MinFilter(5)), np.float32) / 255.0
    bx, by, bw, bh = (v * 3 for v in PAGE_BTN)
    btn_c = (bx + bw / 2, by + bh / 2)
    out = WORK / f"viewer-composite-{lang}.mp4"
    enc = subprocess.Popen([g.ffmpeg(), "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "15",
                            "-preset", "slow", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    for i, fr in enumerate(frames(src)):
        t = i / FPS
        if t >= VIEW_DUR:
            break
        z, (cx, cy) = cam_keys(t)
        box = (cx - W / (2 * z), cy - H / (2 * z), cx + W / (2 * z), cy + H / (2 * z))

        def cam(p):                                                  # clip px -> output px
            return ((p[0] - box[0]) * z, (p[1] - box[1]) * z)
        src_img = Image.fromarray(fr)
        bg = np.asarray(src_img.transform((W, H), Image.EXTENT, box, Image.BICUBIC), np.float32)
        # what the screen shows
        canvas = Image.new("RGB", (PW, PH), (0, 0, 0))
        k_page = ease((t - 2.25) / 0.35)
        if k_page < 1:
            blur = 9 * ease(t / 1.6)                                  # the picture goes soft as it recedes
            v = vid.filter(ImageFilter.GaussianBlur(blur)) if blur > 0.2 else vid
            canvas.paste(v.resize((vw, PH), Image.LANCZOS), (bar, 0))
        if k_page > 0:
            pg = page.copy()
            if t >= VIEW_TAP - 0.02:                                  # the press: button darkens, a ripple spreads
                u = (t - VIEW_TAP) / 1.1                               # long enough to see it as her hand leaves
                d = ImageDraw.Draw(pg, "RGBA")
                if u < 0.3:
                    d.rounded_rectangle([bx, by, bx + bw, by + bh], bh / 2, fill=(0, 0, 0, 70))
                if 0 <= u <= 1:
                    r = 40 + 380 * ease(u)
                    d.ellipse([btn_c[0] - r, btn_c[1] - r, btn_c[0] + r, btn_c[1] + r],
                              outline=GLOW + (int(220 * (1 - u)),), width=10)
            canvas = Image.blend(canvas, pg, k_page) if k_page < 1 else pg
        # screen corners in the output: exactly the frame at t=0, then the true (camera-mapped) screen
        true_q = [cam(p) for p in VIEW_Q]
        s = ease(t / 0.35)                      # snap to the true screen while it still overflows the frame
        q_out = [(fx + (tx - fx) * s, fy + (ty - fy) * s) for (fx, fy), (tx, ty) in zip(full_q, true_q)]
        cfs = coeffs([(0, 0), (PW, 0), (PW, PH), (0, PH)], q_out)
        content = np.asarray(canvas.transform((W, H), Image.PERSPECTIVE, cfs, Image.BICUBIC), np.float32)
        alpha = np.asarray(Image.new("L", (PW, PH), 255).transform((W, H), Image.PERSPECTIVE, cfs, Image.BILINEAR),
                           np.float32) / 255.0
        # in front of the screen: whatever isn't black on the clip's screen (finger, stand), once the phone is in frame
        lum = fr.mean(2)
        occ_src = np.clip((lum - 70) / 30, 0, 1) * omask           # lit skin/metal; the dim reflections on the glass are not in front
        occ = np.asarray(Image.fromarray((occ_src * 255).astype(np.uint8)).transform((W, H), Image.EXTENT, box,
                                                                                       Image.BILINEAR), np.float32) / 255.0
        occ *= ease((t - 1.2) / 0.6)
        # the glass: the clip's faint reflections stay on top of the picture
        refl = np.asarray(Image.fromarray((fr * smask[..., None]).astype(np.uint8)).transform((W, H), Image.EXTENT, box,
                                                                                                Image.BILINEAR), np.float32)
        a = (alpha * (1 - occ))[..., None]
        g_in = ease(t / 1.0)                    # starts identical to 5b's last frame, then becomes a lit screen
        img = bg * (1 - a) + (content * (1 - 0.06 * g_in) + refl * 0.5 * g_in) * a
        frame = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        enc.stdin.write(np.asarray(frame).tobytes())
        if i in (0, 15, 30, 57, 80, 112, 121, 135, 200):
            frame.save(WORK / f"vw_{lang}_{i:03d}.jpg", quality=92)
    enc.stdin.close(); enc.wait()
    print(f"shot 6 ({lang}) ->", out.name)
    return out


# ── samples for review ─────────────────────────────────────────────────────────────────────────────────────
VOICE = {
    "en": {
        "coding": "Today, AI is forcing us to change the way we work to stay competitive.",
        "whiteboard": "The question we should all be asking isn't whether to use AI at work, but where and how to "
                      "bring it in, so it makes sense and boosts productivity.",
        "logos": "Bringing it into your workflow means delegating repetitive tasks and work that needs attention "
                 "24/7, connected to the tools you use every day: your email, inventory, invoicing, video and "
                 "content creation.",
        "phone": "All of this in one place: an AI agent you can talk to like a person, and hand tasks it completes "
                 "in seconds.",
        "requests": "The integration and the hard part are on me. You don't need to have it all figured out: tell me "
                    "what you need, or the idea you have in mind, and I'll design the architecture and the integration "
                    "around you,",
        "questions": "answering the key questions: How do I make my workflow more productive? How do I make my "
                     "products and services more appealing? And above all: how does AI grow my profits?",
        "viewer": "So... will you get into the AI race, or stay out?",
    },
}
SHOTS = [("coding", "coding-composite.mp4", "coding-[0-9]*.mp4"),
         ("whiteboard", "whiteboard-composite-{lang}.mp4", "whiteboard-room.wav"),
         ("logos", "logos-composite.mp4", "logos-room.wav"),
         ("phone", "phone-composite-{lang}.mp4", "phone-[0-9]*.mp4"),
         ("requests", "requests-composite-{lang}.mp4", "requests-[0-9]*.mp4"),
         ("questions", "questions-composite-{lang}.mp4", "logos-room.wav"),
         ("viewer", "viewer-composite-{lang}.mp4", "viewer-[0-9]*.mp4")]
JOINED = {"questions", "viewer"}       # continues the previous shot without a cut: no fade between them


def sample(lang: str = "en", upto: int = 2) -> Path:
    """Intro + the first `upto` shots with their voice lines and the clips' room tone, loudness -16 LUFS."""
    upto = int(upto)
    intro = HERE / "out/brand/intro-by-ivan-dev.mp4"
    ins, vf, af, mix, t0 = ["-i", str(intro)], [f"[0:v]fps={FPS},scale={W}:{H},setsar=1[v0]"], \
        ["[0:a]aresample=48000[a0]"], ["[a0]"], 2.0
    k = 1
    for n, (key, comp, raw) in enumerate(SHOTS[:upto], 1):
        shot = WORK / comp.format(lang=lang)
        voice = WORK / f"v-{key}-{lang}.wav"
        if not voice.exists():
            g.tts_line("portfolio", VOICE[lang][key], voice, "Charon")
        d = g.media_seconds(shot)
        ins += ["-i", str(shot), "-i", str(latest(raw)), "-i", str(voice)]
        nxt = SHOTS[n][0] if n < upto else None
        fin = "" if key in JOINED else "fade=t=in:st=0:d=0.25,"
        fout = "" if nxt in JOINED else f"fade=t=out:st={d - 0.35:.2f}:d=0.35,"
        vf.append(f"[{k}:v]setsar=1,{fin}{fout}null[v{n}]")
        ms, vs = int(t0 * 1000), int((t0 + 0.35) * 1000)
        af.append(f"[{k + 1}:a]aresample=48000,volume=0.30,afade=t=in:d=0.3,afade=t=out:st={d - 0.5:.2f}:d=0.5,adelay={ms}|{ms}[r{n}]")
        af.append(f"[{k + 2}:a]aresample=48000,adelay={vs}|{vs}[s{n}]")
        mix += [f"[r{n}]", f"[s{n}]"]
        print(f"shot {n}: {d:.1f}s at {t0:.1f}s · voice {g.media_seconds(voice):.1f}s")
        t0 += d
        k += 3
    total = t0
    graph = ";".join(vf + ["".join(f"[v{i}]" for i in range(upto + 1)) + f"concat=n={upto + 1}:v=1:a=0[v]"] + af +
                     ["".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{total:.2f},"
                      "loudnorm=I=-16:TP=-1.5:LRA=11[a]"])
    out = WORK / f"sample-shots1-{upto}-{lang}.mp4"
    subprocess.run([g.ffmpeg(), "-loglevel", "error", "-y", *ins, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(out)], check=True)
    print("sample ->", out.relative_to(g.ROOT), f"({total:.1f}s)")
    return out


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"coding": coding, "whiteboard": whiteboard, "logos": logos_shot, "phone": phone_shot, "requests": requests_shot, "questions": questions_shot, "viewer": viewer_shot, "sample": sample}[cmd](*args)
