"""Hub intro video (real Chrome): layout beside / below the circle, CDN playback, EN/ES subtitles, autoplay.

    python scripts/tests/hub_intro_test.py [portfolio_base]
"""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3100"
STATE = """() => { const v = document.querySelector('video.explainer'); if (!v) return null;
  const t = [...v.textTracks].map(x => ({l: x.language, n: x.cues ? x.cues.length : -1}));
  return {src: v.currentSrc, dur: v.duration, paused: v.paused, t: v.currentTime, tracks: t}; }"""

c = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for label, vp, mob in (("desktop", (1440, 900), False), ("móvil", (390, 844), True)):
        pg = b.new_page(viewport={"width": vp[0], "height": vp[1]}, is_mobile=mob, has_touch=mob)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/", wait_until="load")
        pg.wait_for_timeout(3000)
        c[f"[{label}] título"] = pg.get_by_text("How I put AI to work for you").count() == 1
        video = pg.locator("video.explainer")
        ring = pg.locator("svg title", has_text="Areas of work").locator("..")
        vb, rb = video.bounding_box(), ring.locator("a.ring-seg").first.bounding_box()
        if label == "desktop":
            seg_boxes = [pg.locator("a.ring-seg").nth(i).bounding_box() for i in range(6)]
            ring_right = max(s["x"] + s["width"] for s in seg_boxes)
            c[f"[{label}] video a la derecha del círculo"] = vb["x"] > ring_right
        else:
            c[f"[{label}] video debajo del círculo"] = vb["y"] > rb["y"]
            pg.evaluate("() => document.querySelector('video.explainer').scrollIntoView({block: 'center'})")
        pg.wait_for_timeout(3500)
        for tr in ("en", "es"):                                  # load both tracks to count their cues
            pg.evaluate(f"() => {{ for (const x of document.querySelector('video.explainer').textTracks) "
                        f"if (x.language === '{tr}') x.mode = 'hidden'; }}")
        pg.wait_for_timeout(1500)
        s = pg.evaluate(STATE)
        print(label, {k: s[k] for k in ("dur", "paused", "t")}, s["tracks"], s["src"][:70])
        c[f"[{label}] video del CDN (~74.6 s)"] = "cdn.shopify.com" in s["src"] and abs(s["dur"] - 74.6) < 0.6
        c[f"[{label}] arranca solo al verse"] = not s["paused"] and s["t"] > 0.5
        c[f"[{label}] subtítulos EN y ES"] = all(t["n"] > 10 for t in s["tracks"]) and len(s["tracks"]) == 2
        c[f"[{label}] sin selector de voz (solo inglés)"] = pg.locator("[role=group][aria-label=Voice]").count() == 0
        if label == "desktop":
            # full screen goes to the player box (video + the page's own subtitles), and the subtitles stay
            # visible once the control bar would have hidden (Chrome dropped native cues there on some GPUs)
            pg.mouse.move(vb["x"] + 100, vb["y"] + 100)
            pg.get_by_role("button", name="Full screen").click()
            pg.wait_for_timeout(5000)
            fs = pg.evaluate("""() => { const c = document.querySelector('[data-cue]'), v = document.querySelector('video.explainer');
              const r = c && c.getBoundingClientRect(), b = v.getBoundingClientRect();
              return {el: document.fullscreenElement?.tagName, cue: !!c, inside: !!r && r.bottom <= b.bottom && r.top >= b.top,
                      native: [...v.textTracks].some(t => t.mode === 'showing')}; }""")
            print("fullscreen", fs)
            c[f"[{label}] pantalla completa del reproductor"] = fs["el"] == "DIV"
            c[f"[{label}] subtítulos visibles en pantalla completa"] = fs["cue"] and fs["inside"] and not fs["native"]
            pg.evaluate("() => document.exitFullscreen()")
            pg.wait_for_timeout(500)
        if label == "móvil":
            pg.evaluate("() => window.scrollTo(0, 0)")
            pg.wait_for_timeout(500)
            pg.locator('a.ring-seg[aria-label="AI Agents & LLMs"]').click()
            pg.wait_for_url(BASE + "/ai-agents", timeout=15000)
            c[f"[{label}] el círculo sigue siendo clicable"] = True
        c[f"[{label}] sin errores de página"] = not errs
        pg.close()
    b.close()

w = max(len(k) for k in c)
for k, v in c.items():
    print(f"{'✅' if v else '❌'} {k}")
print(f"{sum(c.values())}/{len(c)}")
sys.exit(0 if all(c.values()) else 1)
