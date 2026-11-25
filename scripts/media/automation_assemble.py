"""Automation section video: a real client case, selling an online game's currency end to end (approved 2026-11-23).

    python scripts/media/automation_assemble.py voice        # the English voice lines, transcribed to verify them

Shots (voice in English, Spanish as subtitles, like the home page video):
  1 pipeline  the whole flow as a diagram, a pulse running through it (code)
  2 manual    the client copying prices by hand at night (Omni clip)
  3 app       the real price monitor (venta_kamas/interfaz.pyw) recorded with simulated prices (screen capture)
  4a radar    a price page polled every minute, a match lights up (code)
  4b ask      the client on the couch, a Telegram question over the phone, Accept is tapped (Omni clip + code)
  4c form     a fictitious buyer site's sell form filling itself (code)
  5 deliver   a bot waiting for its token, then gold travelling to the site (robot emblem + code)
  6 done      the client in profile, "transaction complete" over the phone (Omni clip + code)
Neither the game nor the buyer sites are named anywhere.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import generate_category_media as g  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
SLUG = "automation-overview"
WORK = g.out_dir(f"portfolio-{SLUG}")
VOICE_NAME = "Charon"          # the home page video's voice

VOICE = {
    "pipeline": "Today, in the age of AI, automating a workflow from start to finish is a reality. Let's look at a "
                "real case from one of my clients.",
    "manual": "My client wanted to automate selling the virtual currency of a massive online game to one of the many "
              "sites that buy it. Until then, the whole process was done by hand.",
    "app": "The proposal: software that scrapes the prices of the servers my client cares about on three of these "
           "sites. With that data, the same software makes the decisions, following my client's own rules: a minimum "
           "selling price and the amount to sell.",
    "radar": "Prices are monitored 24/7, checking every minute.",
    "ask": "When it finds a match, it first asks my client on Telegram whether to go ahead, with a summary of the deal.",
    "form": "If the answer is yes, the script triggers the sale: a bot opens a browser in the background, logs in to "
            "the buyer's site, fills in the details and creates the sell order.",
    "deliver": "Once the order is created, a bot waits on standby with the order's details, server and amount, until "
               "the site's staff contacts it to take the delivery.",
    "done": "When the delivery is done, the bot tells my client the operation was successful, with a summary of the "
            "transaction. All my client has to do is check that the site's payment arrived.",
}
VOICE_ES = {
    "pipeline": "Hoy, en la era de la IA, automatizar un flujo de trabajo de principio a fin es una realidad. Veamos un "
                "caso real de uno de mis clientes.",
    "manual": "Mi cliente quería automatizar la venta de la moneda virtual de un juego masivo en línea a una de las "
              "muchas páginas que la compran. Hasta entonces, todo el proceso se hacía a mano.",
    "app": "La propuesta: un software que hace scraping de los precios de los servidores que le interesan a mi cliente "
           "en tres de estas páginas. Con esos datos, el mismo software toma las decisiones según las reglas de mi "
           "cliente: un precio mínimo de venta y la cantidad a vender.",
    "radar": "Los precios se vigilan 24/7, revisando cada minuto.",
    "ask": "Cuando encuentra una coincidencia, primero le pregunta a mi cliente por Telegram si quiere seguir "
           "adelante, con un resumen de la operación.",
    "form": "Si la respuesta es sí, el script dispara la venta: un bot abre un navegador en segundo plano, inicia "
            "sesión en la página compradora, llena los datos y crea la orden de venta.",
    "deliver": "Una vez creada la orden, un bot queda en espera con los datos de la orden, servidor y cantidad, hasta "
               "que el personal de la página lo contacta para recibir la entrega.",
    "done": "Cuando termina la entrega, el bot le informa a mi cliente que la operación fue un éxito, con un resumen "
            "de la transacción. Mi cliente solo tiene que comprobar que llegó el pago de la página.",
}


def transcribe(wav: Path) -> str:
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(wav.read_bytes()).decode()}},
        {"text": "Transcribe exactly what is spoken, word for word. Output only the transcript."}]}]}
    res = g.post(f"{g.API}/models/gemini-flash-latest:generateContent", body)
    return "".join(p.get("text", "") for p in res["candidates"][0]["content"]["parts"]).strip()


def voice(*keys: str) -> None:
    """Generate (or regenerate the given) voice lines and print each one's length and transcript."""
    total = 0.0
    for key, text in VOICE.items():
        path = WORK / f"v-{key}-en.wav"
        if keys and key not in keys and path.exists():
            pass
        elif not path.exists() or key in keys:
            g.tts_line("portfolio", text, path, VOICE_NAME)
        d = g.media_seconds(path)
        total += d
        print(f"{key:9s} {d:5.1f}s | {transcribe(path)}")
    print(f"voice total {total:.1f}s")


# ── shared drawing ───────────────────────────────────────────────────────────────────────────────────────
import json  # noqa: E402
import subprocess  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

import overview_assemble as ov  # noqa: E402  (fonts, easing, frame reader, speech segments)

W, H, FPS = 1920, 1080, 30
BG = (11, 13, 16)
GLOW = (94, 234, 212)
VOICE_OFFSET = 0.35


def ease(t: float) -> float:
    return ov.ease(t)


def encoder(path: Path, w: int = W, h: int = H) -> subprocess.Popen:
    return subprocess.Popen([g.ffmpeg(), "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "15",
                             "-preset", "slow", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)


def keyed(keys: list[tuple], t: float):
    """Value at time t from (time, value...) keys, eased between them. Values are numbers or tuples of numbers."""
    if t <= keys[0][0]:
        return keys[0][1:]
    for (t0, *a), (t1, *b) in zip(keys, keys[1:]):
        if t <= t1:
            u = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            return tuple(np.asarray(x, float) + (np.asarray(y, float) - np.asarray(x, float)) * u for x, y in zip(a, b))
    return keys[-1][1:]


def pointer(scale: float = 1.0, pressed: float = 0.0) -> Image.Image:
    """A classic arrow pointer, white with a dark outline, 4x supersampled."""
    S = 4
    pts = [(0, 0), (0, 25), (6, 19.5), (10.5, 29), (14.2, 27.4), (9.8, 18.2), (17.5, 18.2)]
    k = 1.55 * scale * (1 - 0.12 * pressed)
    im = Image.new("RGBA", (int(40 * k * S), int(44 * k * S)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = [((x + 3) * k * S, (y + 3) * k * S) for x, y in pts]
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).polygon([(x + 2 * k * S, y + 3 * k * S) for x, y in p], fill=120)
    im.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(2.5 * k * S)))
    d.polygon(p, fill=(255, 255, 255, 255), outline=(20, 22, 26, 255), width=int(1.6 * k * S))
    return im.resize((im.width // S, im.height // S), Image.LANCZOS)


def ripple(img: Image.Image, at: tuple[float, float], age: float) -> None:
    """A soft ring spreading from a click."""
    if not 0 <= age < 0.45:
        return
    u = age / 0.45
    r = 10 + 34 * u
    a = int(200 * (1 - u))
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse([at[0] - r, at[1] - r, at[0] + r, at[1] + r], outline=GLOW + (a,), width=4)
    img.alpha_composite(lay)


# ── shot 3: the real price monitor (record_app.py states) ───────────────────────────────────────────────
APP = WORK / "app"
APP_PAD = (700, 460)                     # dark margin around the window in the world canvas


def app_world(name: str, meta: dict) -> Image.Image:
    """One captured state on a dark canvas: names blurred, rounded corners, soft shadow."""
    st = next(s for s in meta["states"] if s["name"] == name)
    im = Image.open(APP / f"{name}.png").convert("RGB")
    for x0, y0, x1, y1 in st["blur"]:
        box = (int(x0), int(y0), int(x1), int(y1))
        im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(11)), box[:2])
    w, h = im.size
    world = Image.new("RGB", (w + 2 * APP_PAD[0], h + 2 * APP_PAD[1]), BG)
    glow = Image.new("L", world.size, 0)
    ImageDraw.Draw(glow).rounded_rectangle([APP_PAD[0] - 10, APP_PAD[1] + 30, APP_PAD[0] + w + 10, APP_PAD[1] + h + 50], 40, fill=255)
    world.paste((0, 0, 0), (0, 0), glow.filter(ImageFilter.GaussianBlur(60)).point(lambda v: int(v * 0.85)))
    halo = Image.new("L", world.size, 0)
    ImageDraw.Draw(halo).rounded_rectangle([APP_PAD[0], APP_PAD[1], APP_PAD[0] + w, APP_PAD[1] + h], 30, fill=255)
    world.paste(GLOW, (0, 0), halo.filter(ImageFilter.GaussianBlur(120)).point(lambda v: int(v * 0.10)))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], 26, fill=255)
    world.paste(im, APP_PAD, mask)
    return world


def camera(world: Image.Image, scale: float, center: tuple[float, float]) -> Image.Image:
    """Output frame of a virtual camera over the world canvas (center in window coordinates)."""
    cx, cy = center[0] + APP_PAD[0], center[1] + APP_PAD[1]
    inv = 1 / scale
    return world.transform((W, H), Image.AFFINE, (inv, 0, cx - W / 2 * inv, 0, inv, cy - H / 2 * inv), Image.BICUBIC)


APP_DUR = 15.2
# (time, state): the visible UI state from that moment on
APP_STATES = [(0.0, "00-start"), (1.15, "01-dropdown"), (1.85, "02-selected"), (2.65, "03-price-1"),
              (2.8, "03-price-2"), (2.95, "03-price-3"), (3.75, "04-millions-1"), (3.9, "04-millions-2"),
              (4.6, "05-added"), (5.7, "06-monitoring"), (6.5, "07-reading-1"), (9.4, "07-reading-2"),
              (12.3, "07-reading-3")]
APP_CLICKS = [1.15, 1.85, 2.5, 3.6, 4.6, 5.7]
# the rules the voice names: "a minimum selling price" (11.53 s into the line) and "the amount to sell" (12.76 s)
APP_HILITE = [("precio_min", 11.8), ("millones", 13.05)]
COL_X = {"precio_min": (450, 670), "millones": (1050, 1210)}   # inside the table, at 2x


def app_shot() -> Path:
    meta = json.loads((APP / "meta.json").read_text(encoding="utf-8"))
    B = meta["boxes"]
    mid = lambda b, dx=0.5, dy=0.5: (b[0] + (b[2] - b[0]) * dx, b[1] + (b[3] - b[1]) * dy)
    path_keys = [(0.0, (2350, 1300)), (0.35, (2350, 1300)), (1.05, mid(B["combo"], 0.55)), (1.25, mid(B["combo"], 0.55)),
                 (1.75, mid(B["dropdown_target"], 0.3)), (1.95, mid(B["dropdown_target"], 0.3)),
                 (2.4, mid(B["precio"], 0.4)), (3.05, mid(B["precio"], 0.4)), (3.5, mid(B["millones"], 0.4)),
                 (4.05, mid(B["millones"], 0.4)), (4.5, mid(B["add"])), (4.75, mid(B["add"])),
                 (5.6, mid(B["monitor"], 0.45)), (6.3, mid(B["monitor"], 0.45)), (7.4, (1500, 1500)), (APP_DUR, (1500, 1500))]
    cam_keys = [(0.0, 0.66, (1080, 720)), (0.8, 0.66, (1080, 720)), (1.9, 0.9, (1080, 640)), (4.75, 0.9, (1080, 640)),
                (5.6, 0.92, (1150, 720)), (6.8, 0.92, (1150, 720)), (7.9, 1.12, (1090, 975)), (APP_DUR, 1.2, (1090, 990))]
    worlds = {}
    hand = {p: pointer(1.0, p) for p in (0.0, 1.0)}
    out = WORK / "app-composite.mp4"
    enc = encoder(out)
    t0x, t0y = B["table"][0], B["table"][1]
    for i in range(int(APP_DUR * FPS)):
        t = i / FPS
        name = [n for at, n in APP_STATES if t >= at][-1]
        if name not in worlds:
            worlds[name] = app_world(name, meta)
        scale, center = keyed(cam_keys, t)
        scale = float(scale)
        frame = camera(worlds[name], scale, tuple(center)).convert("RGBA")
        to_out = lambda p: ((p[0] - center[0]) * scale + W / 2, (p[1] - center[1]) * scale + H / 2)
        # the two rules, outlined when the voice names them
        lay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for col, at in APP_HILITE:
            u = ease((t - at) / 0.35)
            if u <= 0:
                continue
            x0, x1 = COL_X[col]
            a, b = to_out((t0x + x0 - 6, t0y - 6)), to_out((t0x + x1 + 6, t0y + 60 + 3 * 60 + 6))
            d.rounded_rectangle([a[0], a[1], b[0], b[1]], 14, outline=GLOW + (int(255 * u),), width=5,
                                fill=GLOW + (int(28 * u),))
        frame.alpha_composite(lay)
        # pointer and clicks
        p = keyed(path_keys, t)[0]
        press = max([1 - abs(t - c) / 0.12 for c in APP_CLICKS if abs(t - c) < 0.12] + [0.0])
        for c in APP_CLICKS:
            ripple(frame, to_out(p), t - c)
        sprite = hand[1.0 if press > 0.5 else 0.0]
        sc = max(0.75, min(1.25, scale))
        sp = sprite.resize((int(sprite.width * sc), int(sprite.height * sc)), Image.LANCZOS)
        q = to_out(p)
        frame.alpha_composite(sp, (int(q[0] - 4 * sc), int(q[1] - 4 * sc)))
        enc.stdin.write(np.asarray(frame.convert("RGB")).tobytes())
        if i in (20, 50, 85, 118, 160, 200, 260, 370, 420):
            frame.convert("RGB").save(WORK / f"app_{i:03d}.jpg", quality=90)
    enc.stdin.close(); enc.wait()
    print("shot 3 ->", out.name)
    return out


# ── code-made shots: scenes/<name>.html, each exposing render(t) and DUR, filmed frame by frame ─────────────
SCENES = HERE / "scenes"


def scene(name: str, preview: str = "") -> Path:
    """Film scenes/<name>.html: render(t) for every frame, screenshot, encode. `preview` = comma-separated times:
    only those frames, saved as JPEGs."""
    import io
    from playwright.sync_api import sync_playwright
    out = WORK / f"{name}-composite.mp4"
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.goto((SCENES / f"{name}.html").as_uri())
        pg.wait_for_function("document.fonts.ready.then(() => true)")
        pg.evaluate("document.fonts.ready")
        dur = pg.evaluate("window.DUR")
        size = pg.evaluate("window.SIZE || null") or [W, H]
        pg.set_viewport_size({"width": size[0], "height": size[1]})
        if preview:
            for t in [float(x) for x in preview.split(",")]:
                pg.evaluate(f"render({t})")
                pg.screenshot(path=str(WORK / f"_{name}_{t:05.2f}.jpg"), type="jpeg", quality=88)
            b.close()
            print("previews:", preview)
            return out
        enc = encoder(out, *size)
        for i in range(round(dur * FPS)):
            pg.evaluate(f"render({i / FPS})")
            img = Image.open(io.BytesIO(pg.screenshot(type="png"))).convert("RGB")
            enc.stdin.write(np.asarray(img).tobytes())
        enc.stdin.close(); enc.wait()
        b.close()
    print(f"{name} ({dur} s) ->", out.name)
    if name.startswith("loop-"):                            # section loops: small silent web file + poster
        LOOPS.mkdir(exist_ok=True)
        subprocess.run([g.ffmpeg(), "-y", "-loglevel", "error", "-i", str(out), "-vf", "scale=1200:-2", "-an",
                        "-c:v", "libx264", "-crf", "24", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        str(LOOPS / f"{name}.mp4")], check=True)
        subprocess.run([g.ffmpeg(), "-y", "-loglevel", "error", "-i", str(out), "-frames:v", "1", "-vf", "scale=1200:-2",
                        "-q:v", "3", str(LOOPS / f"{name}-poster.jpg")], check=True)
        print("web loop ->", LOOPS / f"{name}.mp4", f"{(LOOPS / f'{name}.mp4').stat().st_size // 1024} KB")
    return out


LOOPS = HERE / "out/loops"


# ── shots 4b and 6: the client on the couch, the bot's Telegram messages over his phone ─────────────────────
from PIL import ImageFont  # noqa: E402

SS = 2                                    # supersampling of the cards


def inter(size: float, weight: int = 400) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(HERE / "fonts/Inter.ttf"), int(size * SS))
    try:
        names = [(a["name"].decode() if isinstance(a["name"], bytes) else a["name"]).lower() for a in f.get_variation_axes()]
        f.set_variation_by_axes([weight if n.startswith("weight") else min(32, max(14, size)) for n in names])
    except Exception:
        pass
    return f


EMOJI = lambda size: ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", int(size * SS))


def app_icon(d: ImageDraw.ImageDraw, x: float, y: float, s: float) -> None:
    """The bot's icon: a teal rounded square with a white paper plane (generic, not Telegram's logo)."""
    d.rounded_rectangle([x, y, x + s, y + s], s * 0.26, fill=(38, 166, 154))
    k = s / 64
    pts = [(14, 32), (50, 16), (42, 50), (31, 40), (24, 47), (25, 36)]
    d.polygon([(x + px * k, y + py * k) for px, py in pts], fill=(255, 255, 255))
    d.line([(x + 25 * k, y + 36 * k), (x + 50 * k, y + 16 * k)], fill=(38, 166, 154), width=max(1, int(2.5 * k)))


def finish(im: Image.Image, tail_x: float, fill) -> Image.Image:
    """Add a shadow and a tail under the card (pointing down at tail_x), downsample. info['tail'] = tip."""
    w, h = im.size
    tail = 22 * SS
    pad = 30 * SS
    out = Image.new("RGBA", (w + 2 * pad, h + tail + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 10 * SS, pad + w, pad + h + 10 * SS], 26 * SS, fill=130)
    out.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(14 * SS)))
    d = ImageDraw.Draw(out)
    tx = pad + tail_x * w
    d.polygon([(tx - 18 * SS, pad + h - 4), (tx + 18 * SS, pad + h - 4), (tx, pad + h + tail)], fill=fill)
    out.alpha_composite(im, (pad, pad))
    out = out.resize((out.width // SS, out.height // SS), Image.LANCZOS)
    out.info["tail"] = (tx / SS, (pad + h + tail) / SS)
    return out


def banner(title: str, body: str, tail_x: float = 0.5) -> Image.Image:
    """A lock-screen style notification, dark glass."""
    w, h = 560 * SS, 112 * SS
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fill = (26, 30, 36, 242)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 26 * SS, fill=fill, outline=(255, 255, 255, 34), width=SS)
    app_icon(d, 22 * SS, 24 * SS, 62 * SS)
    d.text((102 * SS, 22 * SS), title, font=inter(24, 650), fill=(255, 255, 255))
    d.text((w - 22 * SS, 25 * SS), "now", font=inter(19), fill=(139, 149, 161), anchor="ra")
    d.text((102 * SS, 60 * SS), body, font=inter(22), fill=(195, 202, 211))
    return finish(im, tail_x, fill)


def card(kind: str, state: str = "", press: float = 0.0, hilite: float = 0.0, tail_x: float = 0.5) -> Image.Image:
    """The bot's Telegram message. kind 'ask': the sale question with Accept / Cancel (state '', 'accepted');
    kind 'done': the transaction summary (hilite: 0..1, the 'check your balance' line lights up)."""
    w = 620 * SS
    h = (392 if kind == "ask" else 330) * SS
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 26 * SS, fill=(255, 255, 255, 250))
    app_icon(d, 26 * SS, 24 * SS, 50 * SS)
    d.text((90 * SS, 26 * SS), "Sale bot", font=inter(23, 700), fill=(15, 30, 54))
    d.text((90 * SS, 54 * SS), "Telegram · now", font=inter(18), fill=(107, 118, 137))
    ink, muted = (27, 36, 51), (107, 118, 137)
    x0, y = 28 * SS, 100 * SS
    if kind == "ask":
        d.text((x0, y), "Do you want to make this sale", font=inter(28, 700), fill=ink)
        d.text((x0, y + 38 * SS), "for 140.80 USDT?", font=inter(28, 700), fill=ink)
        y += 92 * SS
        d.text((x0, y), "Server", font=inter(20), fill=muted)
        sx = x0 + d.textlength("Server ", font=inter(20))
        pill = Image.new("RGBA", (130 * SS, 22 * SS), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle([4 * SS, 4 * SS, 126 * SS, 18 * SS], 7 * SS, fill=(170, 180, 194, 255))
        im.alpha_composite(pill.filter(ImageFilter.GaussianBlur(3 * SS)), (int(sx), int(y + 2 * SS)))
        d.text((sx + 140 * SS, y), "· 40 M · 3.52 USDT / M", font=inter(20), fill=muted)
        d.text((x0, y + 32 * SS), "Buyer site A · price matched at 21:05", font=inter(20), fill=muted)
        by = y + 84 * SS
        bw = (w - 2 * x0 - 16 * SS) / 2
        acc = state == "accepted"
        g = (20, 110, 70) if press > 0.5 or acc else (30, 142, 90)
        shrink = 4 * SS * press
        d.rounded_rectangle([x0 + shrink, by + shrink, x0 + bw - shrink, by + 60 * SS - shrink], 14 * SS, fill=g)
        d.text((x0 + bw / 2, by + 30 * SS), "✓ Accepted" if acc else "✓ Accept", font=inter(24, 700), fill=(255, 255, 255), anchor="mm")
        cx = x0 + bw + 16 * SS
        d.rounded_rectangle([cx, by, cx + bw, by + 60 * SS], 14 * SS, fill=(243, 245, 249))
        d.text((cx + bw / 2, by + 30 * SS), "× Cancel", font=inter(24, 600), fill=(198, 47, 59) if not acc else (190, 196, 205), anchor="mm")
        im.info["accept"] = ((x0 + bw / 2) / SS, (by + 30 * SS) / SS)
    else:
        d.text((x0, y), "Transaction complete", font=inter(28, 700), fill=(30, 142, 90))
        d.text((x0, y + 46 * SS), "Sold 40 M for 140.80 USDT on Buyer site A.", font=inter(21), fill=ink)
        d.text((x0, y + 76 * SS), "Order #48213 · delivered at 21:19", font=inter(20), fill=muted)
        ly = y + 126 * SS
        if hilite > 0:
            # solid colors mixed by hand: drawing a translucent fill would punch a hole in the white card
            mixc = lambda a, b: tuple(int(x + (y - x) * hilite) for x, y in zip(a, b)) + (255,)
            d.rounded_rectangle([x0 - 10 * SS, ly - 8 * SS, w - x0 + 10 * SS, ly + 42 * SS], 12 * SS,
                                fill=mixc((255, 255, 255), (214, 247, 240)), outline=mixc((255, 255, 255), (38, 166, 154)), width=2 * SS)
        d.text((x0, ly), "Check your balance to confirm the payment.", font=inter(22, 650), fill=(15, 30, 54))
    acc = im.info.get("accept")
    out = finish(im, tail_x, (255, 255, 255, 250))
    if acc:
        out.info["accept"] = acc
    return out


def track(src: Path, box: tuple[int, int, int, int], ref_t: float, t_from: float, speed: float = 1.0) -> dict[int, tuple[float, float]]:
    """Offsets of a patch (taken on the frame at ref_t) on every frame from t_from on: {frame: (dx, dy)}."""
    import cv2
    x0, y0, x1, y1 = box
    fr_all = list(ov.frames(src))
    ref = fr_all[int(ref_t * FPS)]
    tpl = cv2.cvtColor(np.ascontiguousarray(ref[y0:y1, x0:x1]), cv2.COLOR_RGB2GRAY)
    out, last = {}, (x0, y0)
    for i in range(int(t_from * FPS), len(fr_all)):
        fr = fr_all[i]
        sx, sy = max(0, last[0] - 70), max(0, last[1] - 70)
        win = cv2.cvtColor(np.ascontiguousarray(fr[sy:sy + (y1 - y0) + 140, sx:sx + (x1 - x0) + 140]), cv2.COLOR_RGB2GRAY)
        res = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
        _, _, _, (mx, my) = cv2.minMaxLoc(res)
        last = (sx + mx, sy + my)
        out[i] = (last[0] - x0, last[1] - y0)
    keys = sorted(out)
    a = np.array([out[k] for k in keys], np.float32)
    kern = np.ones(9) / 9
    sm = np.stack([np.convolve(np.pad(a[:, j], 4, mode="edge"), kern, "valid") for j in range(2)], 1)
    return {k: (float(dx), float(dy)) for k, (dx, dy) in zip(keys, sm)}


def pop(t0: float, t: float) -> float:
    u = min(1.0, max(0.0, (t - t0) / 0.32))
    c = 1.7
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2 if u > 0 else 0.0


def put(frame: Image.Image, b: Image.Image, tip: tuple[float, float], p: float, alpha: float = 1.0) -> None:
    """Composite a bubble so its tail tip sits on `tip`, scaled by pop progress p."""
    if p <= 0 or alpha <= 0:
        return
    sc = 0.6 + 0.4 * p
    bb = b.resize((max(1, int(b.width * sc)), max(1, int(b.height * sc))), Image.LANCZOS)
    tx, ty = b.info["tail"]
    x, y = tip[0] - tx * sc, tip[1] - ty * sc
    x = min(max(x, -20), W - bb.width + 20)
    a = np.asarray(bb, np.float32).copy()
    a[..., 3] *= min(1.0, p * 1.5) * alpha
    frame.alpha_composite(Image.fromarray(a.clip(0, 255).astype(np.uint8)), (int(x), int(y)))


COUCH = {
    # 4b: notification over the phone on the sofa back, then the question over the phone in his hand; Accept tapped
    "ask": {"clip": "ask-[0-9]*.mp4", "dur": 8.0, "speed": 1.0,
            "rest_tip": (1490, 795), "hold_tip": (868, 486), "hold_box": (820, 486, 930, 560), "ref_t": 4.5, "hold_from": 3.9,
            "banner": ("Sale bot", "Match found: sale ready for your approval", 0.8, 2.5),
            "card_at": 4.1, "press": 6.45, "accepted": 6.6},
    # 6: notification over the phone on the side table, then the summary over the phone in his hand
    "done": {"clip": "done-[0-9]*.mp4", "dur": 11.0, "speed": 1.1,
             "rest_tip": (1310, 955), "hold_tip": (700, 530), "hold_box": (680, 520, 780, 600), "ref_t": 4.95, "hold_from": 4.5,
             "banner": ("Sale bot", "Delivery complete: order #48213", 1.0, 3.2),
             "card_at": 4.8, "hilite": 7.1},
}


def couch_shot(key: str) -> Path:
    c = COUCH[key]
    raw = ov_latest(c["clip"])
    src = raw
    if c["speed"] != 1.0:                                   # slowed to cover the voice line
        src = WORK / f"_{key}-slow.mp4"
        subprocess.run([g.ffmpeg(), "-loglevel", "error", "-y", "-i", str(raw), "-vf", f"setpts=PTS*{c['speed']},fps={FPS}",
                        "-an", "-c:v", "libx264", "-crf", "14", str(src)], check=True)
    offs = track(src, c["hold_box"], c["ref_t"], c["hold_from"])
    print(f"{key}: phone in hand moves up to {max(abs(v[0]) for v in offs.values()):.0f}px x, "
          f"{max(abs(v[1]) for v in offs.values()):.0f}px y")
    ban = banner(*c["banner"][:2], tail_x=0.5)
    out = WORK / f"{key}-composite.mp4"
    enc = encoder(out)
    cards = {}
    for i, fr in enumerate(ov.frames(src)):
        t = i / FPS
        if t >= c["dur"]:
            break
        img = Image.fromarray(fr).convert("RGBA")
        b0, b1 = c["banner"][2:]
        put(img, ban, c["rest_tip"], pop(b0, t), alpha=1 - ease((t - b1) / 0.3))
        if t >= c["card_at"]:
            dx, dy = offs.get(i, (0.0, 0.0))
            tip = (c["hold_tip"][0] + dx, c["hold_tip"][1] + dy)
            if key == "ask":
                press = max(0.0, 1 - abs(t - c["press"]) / 0.1) if abs(t - c["press"]) < 0.1 else 0.0
                state = "accepted" if t >= c["accepted"] else ""
                ck = (state, round(press, 1))
                if ck not in cards:
                    cards[ck] = card("ask", state, press)
                b = cards[ck]
            else:
                hl = round(ease((t - c["hilite"]) / 0.4), 2)
                if hl not in cards:
                    cards[hl] = card("done", hilite=hl)
                b = cards[hl]
            put(img, b, tip, pop(c["card_at"], t))
            if key == "ask" and 0 <= t - c["press"] < 0.45:
                tx, ty = b.info["tail"]
                ax, ay = b.info["accept"]
                pad = 30
                ripple(img, (tip[0] - tx + pad + ax, tip[1] - ty + pad + ay), t - c["press"])
        enc.stdin.write(np.asarray(img.convert("RGB")).tobytes())
        if i in (30, 75, 130, 170, 195, 215, 300):
            img.convert("RGB").save(WORK / f"{key}_{i:03d}.jpg", quality=90)
    enc.stdin.close(); enc.wait()
    print(f"{key} ->", out.name)
    return out


def ov_latest(pattern: str) -> Path:
    files = sorted(WORK.glob(pattern), key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit(f"missing {pattern} in {WORK}")
    return files[-1]


def manual_shot() -> Path:
    """Shot 2: the Omni clip slowed from 10 s to the shot's length (small natural movements hide it)."""
    raw = ov_latest("manual-[0-9]*.mp4")
    out = WORK / "manual-composite.mp4"
    subprocess.run([g.ffmpeg(), "-loglevel", "error", "-y", "-i", str(raw), "-vf", f"setpts=PTS*1.14,fps={FPS}",
                    "-an", "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", str(out)], check=True)
    print("manual ->", out.name, f"{g.media_seconds(out):.1f}s")
    return out


# ── the whole video: intro, 8 shots, end card ───────────────────────────────────────────────────────────
# (voice key, composite, seconds, still used until the Omni composite exists)
ROOM = {"manual": "manual-[0-9]*.mp4", "ask": "ask-[0-9]*.mp4", "done": "done-[0-9]*.mp4"}   # their room tone
SHOTS = [("pipeline", "pipeline-composite.mp4", 9.0, None),
         ("manual", "manual-composite.mp4", 11.4, "manual-still.png"),
         ("app", "app-composite.mp4", APP_DUR, None),
         ("radar", "radar-composite.mp4", 5.5, None),
         ("ask", "ask-composite.mp4", 8.0, "couch-back-still.png"),
         ("form", "form-composite.mp4", 11.2, None),
         ("deliver", "deliver-composite.mp4", 9.3, None),
         ("done", "done-composite.mp4", 11.0, "couch-profile-still.png")]
CARD_DUR = 3.2
INTRO = HERE / "out/brand/intro-by-ivan-dev.mp4"


def still_clip(png: Path, dur: float) -> Path:
    """Placeholder for an Omni shot: its still with a slow push-in (only for review samples)."""
    out = WORK / f"_still-{png.stem}.mp4"
    n = round(dur * FPS)
    subprocess.run([g.ffmpeg(), "-loglevel", "error", "-y", "-loop", "1", "-i", str(png), "-vf",
                    f"scale=3840:-2,zoompan=z='1+0.05*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS}",
                    "-frames:v", str(n), "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


TEMPO_MAX = 1.12   # a Spanish line is sped up at most this much; past it the shot holds its last frame instead


def voice_for(key: str, lang: str, dur: float) -> tuple[Path, float]:
    """The voice line in `lang` and how long the shot must hold its last frame so the line fits. Spanish lines run
    ~10% longer than the English ones the shots were timed to: speed them up a little, then hold if still needed."""
    path = WORK / f"v-{key}-{lang}.wav"
    if not path.exists():
        g.tts_line("portfolio", (VOICE if lang == "en" else VOICE_ES)[key], path, VOICE_NAME)
    if lang == "en":
        return path, 0.0
    room = dur - VOICE_OFFSET - 0.15
    d = g.media_seconds(path)
    if d <= room:
        return path, 0.0
    tempo = min(d / room, TEMPO_MAX)
    out = WORK / f"v-{key}-{lang}-fit.wav"
    subprocess.run([g.ffmpeg(), "-y", "-loglevel", "error", "-i", str(path), "-filter:a", f"atempo={tempo:.4f}",
                    str(out)], check=True)
    hold = round(max(0.0, d / tempo - room), 2)
    print(f"  {key}: voice {d:.2f}s in {room:.2f}s -> x{tempo:.3f}" + (f", shot holds +{hold:.2f}s" if hold else ""))
    return out, hold


def assemble(name: str = "sample", lang: str = "en", channel: str = "upwork") -> Path:
    """Intro + shots + end card with the voice lines; missing Omni composites are replaced by their stills.
    `lang` / `channel` build another version (2026-11-25: Spanish voice + Workana end card), files tagged -es-workana."""
    sys.path.insert(0, str(HERE))
    import explainer_assemble as ea
    ea.LANG, ea.CHANNEL = lang, channel
    tag = ("" if lang == "en" else f"-{lang}") + ("" if channel == "upwork" else f"-{channel}")
    card = WORK / f"end-card{tag}.png"
    ea.end_card().save(card)
    placed = []
    ins, vf, af, mix = ["-i", str(INTRO)], [f"[0:v]fps={FPS},scale={W}:{H},setsar=1[v0]"], ["[0:a]aresample=48000[a0]"], ["[a0]"]
    t0, k = 2.0, 1
    starts = {}
    for n, (key, comp, dur, still) in enumerate(SHOTS, 1):
        src = WORK / comp
        if not src.exists():
            src = still_clip(WORK / still, dur)
        voice_, hold = voice_for(key, lang, dur)
        ins += ["-i", str(src), "-i", str(voice_)]
        if key in ROOM and (WORK / comp).exists():
            ins += ["-i", str(ov_latest(ROOM[key]))]
            ms = int(t0 * 1000)
            af.append(f"[{k + 2}:a]aresample=48000,atrim=0:{dur},volume=0.30,afade=t=in:d=0.3,"
                      f"afade=t=out:st={dur - 0.5:.2f}:d=0.5,adelay={ms}|{ms}[r{n}]")
            mix.append(f"[r{n}]")
        pad = f"tpad=stop_mode=clone:stop_duration={hold},"  if hold else ""
        vf.append(f"[{k}:v]trim=0:{dur},setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H},setsar=1,{pad}"
                  f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur + hold - 0.3:.2f}:d=0.3[v{n}]")
        vs = int((t0 + VOICE_OFFSET) * 1000)
        af.append(f"[{k + 1}:a]aresample=48000,adelay={vs}|{vs}[s{n}]")
        mix.append(f"[s{n}]")
        starts[key] = t0
        placed.append((key, t0 + VOICE_OFFSET, voice_))
        t0 += dur + hold
        k += 3 if key in ROOM and (WORK / comp).exists() else 2
    nc = len(SHOTS) + 1
    ins += ["-loop", "1", "-t", f"{CARD_DUR}", "-i", str(card)]
    vf.append(f"[{k}:v]fps={FPS},scale={W}:{H},setsar=1,format=yuv420p,fade=t=in:st=0:d=0.4[v{nc}]")
    total = t0 + CARD_DUR
    graph = ";".join(vf + ["".join(f"[v{i}]" for i in range(nc + 1)) + f"concat=n={nc + 1}:v=1:a=0[v]"] + af +
                     ["".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,apad,atrim=0:{total:.2f},"
                      "loudnorm=I=-16:TP=-1.5:LRA=11[a]"])
    out = WORK / f"{SLUG}{tag}-{name}.mp4"
    subprocess.run([g.ffmpeg(), "-loglevel", "error", "-y", *ins, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(out)], check=True)
    print(f"{name} -> {out} ({total:.1f} s)")
    (WORK / f"starts{tag}.json").write_text(json.dumps(starts, indent=1), encoding="utf-8")
    if name == "explainer":                                 # the published files: web encodes, poster, captions
        for height, scale in ((1080, "scale=1920:-2"), (720, "scale=1280:-2")):
            subprocess.run([g.ffmpeg(), "-y", "-loglevel", "error", "-i", str(out), "-vf", scale, "-c:v", "libx264",
                            "-crf", "23", "-preset", "slow", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                            str(WORK / f"{SLUG}{tag}-explainer-{height}.mp4")], check=True)
        pk, pt = POSTER_AT
        subprocess.run([g.ffmpeg(), "-y", "-loglevel", "error", "-ss", f"{starts[pk] + pt:.2f}", "-i", str(out),
                        "-frames:v", "1", "-q:v", "3", str(WORK / f"{SLUG}{tag}-poster.jpg")], check=True)
        cues = write_cues(starts, total, placed, tag)
        print(f"web encodes, poster, {len(cues['en'])} EN / {len(cues['es'])} ES cues")
    return out


POSTER_AT = ("ask", 5.6)                     # the bot's question over his phone


def write_cues(starts: dict, total: float, placed: list | None = None, tag: str = "") -> dict:
    """EN/ES captions timed to the voice lines of the version (the other language: the translation of the same lines)."""
    placed = placed or [(key, starts[key] + VOICE_OFFSET, WORK / f"v-{key}-en.wav") for key, *_ in SHOTS]
    cues = {"duration": round(total, 2), "en": [], "es": []}
    for i, (key, at, wav) in enumerate(placed):
        cap = placed[i + 1][1] - 0.05 if i + 1 < len(placed) else total
        cues["en"] += ov.timed_cues(VOICE[key], at, wav, cap)
        cues["es"] += ov.timed_cues(VOICE_ES[key], at, wav, cap)
    path = g.ROOT / f"apps/web/src/content/video-cues/{SLUG}{tag}.json"
    path.write_text(json.dumps(cues, indent=1, ensure_ascii=False) + chr(10), encoding="utf-8", newline=chr(10))
    return cues


def publish_loops(*names: str) -> None:
    """Upload the section loops (silent 6 s MP4 + poster) to Shopify Files; URLs go to portfolio-loops.json."""
    sys.path.insert(0, str(g.ROOT / "scripts/shopify"))
    from shopify_admin import ShopifyAdmin
    from upload_files import upload
    path = g.ROOT / "apps/web/src/content/portfolio-loops.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    s = ShopifyAdmin()
    for n in names or ("loop-store", "loop-sale"):
        v = upload(s, LOOPS / f"{n}.mp4", "FILE", f"portfolio section loop {n}")
        im = upload(s, LOOPS / f"{n}-poster.jpg", "IMAGE", f"portfolio section loop {n} (poster)")
        data[n] = {"src": v["url"], "poster": im["url"]}
        print(n, "->", v["url"][:90])
    path.write_text(json.dumps(data, indent=2) + chr(10), encoding="utf-8", newline=chr(10))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"voice": voice, "app": app_shot, "scene": scene, "assemble": assemble, "couch": couch_shot, "manual": manual_shot, "publish-loops": publish_loops}[cmd](*args)
