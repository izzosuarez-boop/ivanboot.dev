"""Playback rules of the portfolio explainer videos (real Chrome).

    python scripts/tests/explainer_playback_test.py [portfolio_base]

Checks: paused until the whole player is in view; then starts by itself; pauses when scrolled away and does
not resume by itself; pauses when the visitor leaves the section (client navigation); no second autoplay
after coming back without a reload; autoplays again after a full reload. Also that the old
"LLM integrations" card is gone.
"""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3100"
# the section's video (inside its project card): since 2026-11-22 the hub has its own intro video too
STATE = "() => { const v = document.querySelector('article video.explainer'); return v ? {paused: v.paused, t: v.currentTime, muted: v.muted} : null; }"


def to_video(pg):
    pg.evaluate("() => document.querySelector('article video.explainer').scrollIntoView({block: 'center'})")
    pg.wait_for_timeout(2500)


def to_top(pg):
    pg.evaluate("() => window.scrollTo(0, 0)")
    pg.wait_for_timeout(1200)


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    c = {}
    pg.goto(BASE + "/ai-agents", wait_until="networkidle")
    pg.wait_for_timeout(2500)
    c["tarjeta LLM eliminada"] = pg.get_by_text("LLM integrations in production").count() == 0
    c["un solo proyecto con video"] = pg.locator("article video.explainer").count() == 1
    c["en pausa fuera de vista"] = pg.evaluate(STATE)["paused"]

    to_video(pg)
    s = pg.evaluate(STATE)
    c["arranca solo al verse entero"] = not s["paused"] and s["t"] > 0.5
    print("autoplay:", s)

    to_top(pg)
    t_left = pg.evaluate(STATE)["t"]
    c["se pausa al bajar/subir"] = pg.evaluate(STATE)["paused"]
    to_video(pg)
    s = pg.evaluate(STATE)
    c["no se reanuda solo"] = s["paused"] and abs(s["t"] - t_left) < 0.3

    pg.evaluate("() => { const v = document.querySelector('article video.explainer'); v.muted = true; return v.play(); }")
    pg.wait_for_timeout(1500)
    c["play manual funciona"] = not pg.evaluate(STATE)["paused"]

    # leave the section with the site's own link (client navigation keeps the page alive but hidden)
    pg.get_by_role("link", name="All work").last.click()
    pg.wait_for_url(BASE + "/", timeout=15000)
    pg.wait_for_timeout(2500)
    c["se pausa al salir de la sección"] = pg.evaluate(
        "() => [...document.querySelectorAll('article video.explainer')].every(v => v.paused)")

    # come back through the ring, same document: no second autoplay
    pg.get_by_role("link", name="AI Agents").first.click()
    pg.wait_for_url(BASE + "/ai-agents", timeout=15000)
    pg.wait_for_timeout(2500)
    to_video(pg)
    c["al volver sin recargar no arranca solo"] = pg.evaluate(STATE)["paused"]

    pg.reload(wait_until="load")
    pg.wait_for_timeout(2500)
    to_video(pg)
    c["tras recargar arranca solo otra vez"] = not pg.evaluate(STATE)["paused"]
    c["sin errores de página"] = not errs

    w = max(len(k) for k in c)
    for k, v in c.items():
        print(f"{k:<{w}}  {'OK' if v else 'FALLA'}")
    print(f"{sum(c.values())}/{len(c)}")
    if errs:
        print(errs[:3])
    b.close()
    sys.exit(0 if all(c.values()) else 1)
