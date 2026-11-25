"""Section 4 video (AI Media & Shopify): how the portfolio's videos were made: idea, consistency, corrections, what code
does better than AI, the Ardea Skin demo, social media, and the budget. Approved 2026-11-24. Made in code from the real
assets (the section videos, approved and discarded stills, the store); only the voice costs cents.

    python scripts/media/media_assemble.py voice
    python scripts/media/media_assemble.py capture          # Ardea Skin pages + where their videos sit
    python scripts/media/media_assemble.py scene m-<name> [t1,t2]
    python scripts/media/media_assemble.py assemble explainer

Scenes play the real videos by seeking them frame by frame (render(t) is async; Playwright waits for it).
Budget (2026-11-24, from PLAYBOOK costs and every saved generation): about $23.60 in all -> "less than 25 dollars".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import automation_assemble as aa  # noqa: E402
import generate_category_media as g  # noqa: E402

SLUG = "media-overview"
WORK = g.out_dir(f"portfolio-{SLUG}")
STORE = "https://tienda.ivanboot.dev"

VOICE = {
    "open": "Every video in this portfolio was made with AI. But a good video doesn't come from a prompt: it comes from "
            "deciding what you want to say, which part of the product to show, and how to tell it so it's understood "
            "the first time.",
    "idea": "It all starts with the idea. In the automation video, the story was a contrast: a client worn out, copying "
            "prices by hand, and then that same client resting while the bots do the work. Each shot carries a single "
            "message and one line that goes with it.",
    "consistency": "Consistency is designed: the same character and the same setting in every shot. Each new image is "
                   "generated from the previous one, so the viewer follows the story without getting distracted.",
    "fixes": "And then it gets corrected. The beard didn't match the real photo; from behind I wasn't recognizable, so I "
             "switched to a profile; the phone was out of his reach; and the AI couldn't draw believable circles on the "
             "whiteboard, so I drew them in code. Every fix is checked frame by frame before moving on.",
    "code": "What AI doesn't do well, code solves: the screens it invents are replaced with real content; text, speech "
            "bubbles and subtitles are drawn separately; and every voice line is transcribed to check it says exactly "
            "what it should.",
    "result": "That's how each section's video was born: each with its own story, its own pace, and the same visual "
              "identity.",
    "ardea": "The same goes for a store. In Ardea Skin, the demo store I built, the product photos, category covers and "
             "tutorial videos were made with AI under one art direction, and each one has a job on the page.",
    "social": "And all of this can be taken to your social media: with web scraping I spot trends and what your "
              "competitors post, I create the content with the same attention to detail, and I automate it all: "
              "scheduling, publishing and replying.",
    "budget": "And the budget? All the multimedia content created and corrected with AI for this portfolio and for Ardea "
              "Skin, retakes included, cost less than 25 dollars. Nothing is made at random: every step is measured and "
              "costs are cut, for example by doing in code what AI charges a lot for and does badly.",
    "close": "Content with intent, not just with AI.",
}
VOICE_ES = {
    "open": "Todos los videos de este portafolio los creé con IA. Pero un buen video no sale de un prompt: sale de "
            "decidir qué quieres decir, qué parte del producto mostrar y cómo contarlo para que se entienda a la primera.",
    "idea": "Todo empieza por la idea. En el video de automatización, la historia era un contraste: un cliente agotado "
            "copiando precios a mano y, después, ese mismo cliente descansando mientras los bots trabajan. Cada toma "
            "lleva un solo mensaje y una frase que lo acompaña.",
    "consistency": "La coherencia se diseña: el mismo personaje y el mismo ambiente en todas las tomas. Cada imagen nueva "
                   "se genera a partir de la anterior, para que quien la ve siga la historia sin distraerse.",
    "fixes": "Y luego se corrige. La barba no era la de la foto real; de espaldas no se me reconocía, así que pasé a un "
             "perfil; el celular quedaba lejos de su mano; y la IA no dibujaba círculos creíbles en la pizarra, así que "
             "los dibujé con código. Cada corrección se revisa fotograma a fotograma antes de seguir.",
    "code": "Lo que la IA no hace bien lo resuelve el código: las pantallas que inventa se reemplazan por contenido real; "
            "los textos, los globos y los subtítulos se dibujan aparte; y cada frase de la voz se transcribe para "
            "comprobar que dice exactamente lo que debe.",
    "result": "Así nacieron los videos de cada sección: cada uno con su historia, su ritmo y la misma identidad visual.",
    "ardea": "Lo mismo aplica a una tienda. En Ardea Skin, la tienda de prueba que construí, las fotos de producto, las "
             "portadas de categoría y los videos tutoriales se crearon con IA bajo una misma dirección de arte, y cada "
             "uno cumple una función en la página.",
    "social": "Y todo esto se puede llevar a tus redes sociales: con web scraping detecto tendencias y lo que publica tu "
              "competencia, creo el contenido con esta misma atención al detalle y lo automatizo todo: programar, "
              "publicar y responder.",
    "budget": "¿Y el presupuesto? Todo el contenido multimedia creado y corregido con IA de este portafolio y de Ardea "
              "Skin, incluidas las repeticiones, costó menos de 25 dólares. No se crea al azar: se mide cada paso y se "
              "reducen costos, por ejemplo haciendo con código lo que la IA cobra caro y hace mal.",
    "close": "Contenido con intención, no solo con IA.",
}
# (voice key, composite, seconds, still): seconds = voice line + 0.35 s lead + ~1 s, set once the voice exists
DUR = {"open": 13.2, "idea": 14.8, "consistency": 12.3, "fixes": 21.2, "code": 13.5, "result": 9.5, "ardea": 13.6,
       "social": 13.5, "budget": 21.2, "close": 5.0}
SHOTS = [(k, f"m-{k}-composite.mp4", DUR[k], None) for k in VOICE]


def point_aa() -> None:
    aa.SLUG, aa.WORK, aa.VOICE, aa.VOICE_ES, aa.SHOTS, aa.ROOM = SLUG, WORK, VOICE, VOICE_ES, SHOTS, {}
    aa.POSTER_AT = ("fixes", 4.2)   # the beard: before -> after


def voice(*keys: str) -> None:
    point_aa()
    aa.voice(*keys)


def capture() -> None:
    """Ardea Skin pages at 2x (full page) and the boxes of their videos, so the scene can play the real files there."""
    from playwright.sync_api import sync_playwright
    out = WORK / "store"
    out.mkdir(parents=True, exist_ok=True)
    boxes = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2, reduced_motion="reduce", locale="en-US")
        for name, path in (("home", "/"), ("cleansers", "/collections/cleansers"), ("product", "/products/clarifying-gel-cleanser")):
            pg.goto(STORE + path, wait_until="load")
            pg.wait_for_timeout(3000)
            pg.add_style_tag(content="nextjs-portal{display:none!important}")
            pg.screenshot(path=str(out / f"{name}.png"), full_page=True)
            boxes[name] = {
                "height": pg.evaluate("document.documentElement.scrollHeight"),
                "videos": pg.evaluate("""() => [...document.querySelectorAll('video')].map(v => { const r = v.getBoundingClientRect();
                    return {x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height, src: (v.currentSrc || v.src || '').split('/').pop().slice(0, 60)}; })"""),
                "images": pg.evaluate("""() => [...document.querySelectorAll('main img')].slice(0, 12).map(i => { const r = i.getBoundingClientRect();
                    return {x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height, alt: i.alt.slice(0, 40)}; })"""),
            }
            print(name, boxes[name]["height"], boxes[name]["videos"])
        b.close()
    (out / "boxes.json").write_text(json.dumps(boxes, indent=1), encoding="utf-8")
    (out / "boxes.js").write_text("window.BOXES = " + json.dumps(boxes) + ";", encoding="utf-8")


O = HERE / "out"
# frames used by the scenes: (output name, source video, time)
FRAMES = [("t-manual", "portfolio-automation-overview/manual-composite.mp4", 6.0),
          ("t-app", "portfolio-automation-overview/app-composite.mp4", 10.5),
          ("t-radar", "portfolio-automation-overview/radar-composite.mp4", 4.8),
          ("t-ask", "portfolio-automation-overview/ask-composite.mp4", 6.6),
          ("t-deliver", "portfolio-automation-overview/deliver-composite.mp4", 7.5),
          ("t-done", "portfolio-automation-overview/done-composite.mp4", 9.5),
          ("wb-code", "portfolio-ai-agents-overview/whiteboard-composite-en.mp4", 8.6),
          ("coding-real", "portfolio-ai-agents-overview/coding-composite.mp4", 3.0),
          ("ask-raw", "portfolio-automation-overview/ask-213150.mp4", 6.0),
          ("ask-comp", "portfolio-automation-overview/ask-composite.mp4", 6.0)]
SOCIAL = ["instagram", "tiktok", "youtube", "facebook"]


def prep() -> None:
    """Frames, the voice waveform for the 'transcribed' shot, and the social logos."""
    import subprocess
    import numpy as np
    import kamas_assemble as ka
    dst = WORK / "frames"
    dst.mkdir(exist_ok=True)
    for name, src, t in FRAMES:
        subprocess.run([g.ffmpeg(), "-y", "-loglevel", "error", "-ss", str(t), "-i", str(O / src), "-frames:v", "1",
                        "-vf", "scale=1920:-2", str(dst / f"{name}.jpg")], check=True)
    raw = subprocess.run([g.ffmpeg(), "-v", "error", "-i", str(WORK / "v-code-en.wav"), "-ac", "1", "-ar", "8000", "-f",
                          "f32le", "-"], capture_output=True, check=True).stdout
    a = np.abs(np.frombuffer(raw, np.float32))
    bars = [float(c.max()) for c in np.array_split(a, 120)]
    peak = max(bars) or 1
    (dst / "wave.js").write_text("window.WAVE = " + json.dumps([round(b / peak, 3) for b in bars]) + ";", encoding="utf-8")
    ka.LOGOS, ka.LOGO_DIR = SOCIAL, O / "logos-media"
    ka.logos()
    print("frames, waveform and logos ->", dst)


def scene(name: str, preview: str = "") -> Path:
    point_aa()
    return aa.scene(name, preview)


def assemble(name: str = "sample", lang: str = "en", channel: str = "upwork") -> Path:
    point_aa()
    return aa.assemble(name, lang, channel)


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"voice": voice, "capture": capture, "prep": prep, "scene": scene, "assemble": assemble}[cmd](*args)
