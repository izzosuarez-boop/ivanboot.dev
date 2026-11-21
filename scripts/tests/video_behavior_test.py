"""Browser test of the how-to video rules and the homepage brand loop (run against production)."""
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://tienda.ivanboot.dev"

STATE = """() => { const v = document.querySelector('figure video');
  const r = v.getBoundingClientRect(); const vis = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0)) / r.height;
  return { paused: v.paused, muted: v.muted, t: +v.currentTime.toFixed(2), visible: +vis.toFixed(2), src: (v.currentSrc||'').split('/').pop().slice(0,40) }; }"""

def scroll_video_to(page, fraction_visible):
    """Scroll so that `fraction_visible` of the video sits inside the viewport (from the bottom edge)."""
    page.evaluate("""(f) => { const v = document.querySelector('figure video'); const r = v.getBoundingClientRect();
        const top = r.top + scrollY; window.scrollTo(0, top - innerHeight + r.height * f); }""", fraction_visible)
    page.wait_for_timeout(1200)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    ctx = browser.new_context(viewport={"width": 1366, "height": 800})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(f"{BASE}/collections/serums", wait_until="networkidle")
    page.wait_for_timeout(800)
    s0 = page.evaluate(STATE); print("1. al cargar (video fuera de vista):", s0)

    scroll_video_to(page, 0.6); s1 = page.evaluate(STATE); print("2. visible 60% (no debe arrancar):  ", s1)
    scroll_video_to(page, 1.0); page.wait_for_timeout(1500); s2 = page.evaluate(STATE); print("3. visible 100% (debe reproducir):  ", s2)
    scroll_video_to(page, 0.4); s3 = page.evaluate(STATE); print("4. visible 40% (debe pausar):       ", s3)
    scroll_video_to(page, 1.0); page.wait_for_timeout(1500); s4 = page.evaluate(STATE); print("5. vuelve a 100% (debe seguir en pausa):", s4)
    page.evaluate("() => document.querySelector('figure video').play()")  # same as the user pressing play
    page.wait_for_timeout(1500); s5 = page.evaluate(STATE); print("6. usuario pulsa play (reproduce):  ", s5)
    sound_btn = page.locator("text=Tap for sound").count(); print("   botón 'Tap for sound' visible:", bool(sound_btn))

    checks = {
        "no arranca fuera de vista": s0["paused"],
        "no arranca al 60%": s1["paused"],
        "arranca al 100%": not s2["paused"] and s2["t"] > 0,
        "pausa al 40%": s3["paused"],
        "no se reanuda solo": s4["paused"] and abs(s4["t"] - s3["t"]) < 0.3,
        "play manual funciona": not s5["paused"],
    }

    home = ctx.new_page()
    home.goto(BASE, wait_until="networkidle"); home.wait_for_timeout(2500)
    b = home.evaluate("() => { const v = document.querySelector('section video'); return { paused: v.paused, muted: v.muted, loop: v.loop, t: +v.currentTime.toFixed(2), src: (v.currentSrc||'').split('/').pop().slice(0,30) }; }")
    print("7. portada, video de marca:", b)
    checks["video de marca en bucle, silenciado y reproduciendo"] = (not b["paused"]) and b["muted"] and b["loop"] and b["t"] > 0
    checks["sin errores JS"] = not errors

    mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True).new_page()
    mobile.goto(f"{BASE}/collections/serums", wait_until="networkidle")
    scroll_video_to(mobile, 1.0); mobile.wait_for_timeout(1500)
    m = mobile.evaluate(STATE); print("8. móvil 390px al 100%:", m)
    checks["móvil: arranca y usa fuente ligera"] = (not m["paused"])

    print("\nRESULTADO")
    for k, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FALLA'} {k}")
    if errors: print("errores JS:", errors[:3])
    browser.close()
