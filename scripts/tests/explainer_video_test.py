"""Browser test of the AI Agents explainer player (real Chrome via Playwright).

    python scripts/tests/explainer_video_test.py [base_url]     # default http://localhost:3100

Checks: the video loads from the CDN (metadata, ~67 s), plays, both subtitle tracks load, the default language
follows the browser (en / es), the EN / ES / Off switch drives the tracks, the right cue is on screen at a
given time, and the page throws no errors. Desktop gets the 1080p file, a phone the 720p one.
"""
from __future__ import annotations

import sys
import time

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3100"

STATE = """() => { const v = document.querySelector('video.explainer');
  const t = Array.from(v.textTracks).map(x => ({lang: x.language, mode: x.mode,
    cue: x.activeCues && x.activeCues.length ? x.activeCues[0].text : null, n: x.cues ? x.cues.length : 0}));
  return {ready: v.readyState, dur: v.duration, src: v.currentSrc, t: v.currentTime, paused: v.paused, tracks: t}; }"""


def run(p, label: str, locale: str, viewport: dict, mobile: bool) -> dict[str, bool]:
    browser = p.chromium.launch(channel="chrome")
    ctx = browser.new_context(locale=locale, viewport=viewport, is_mobile=mobile, has_touch=mobile)
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE + "/ai-agents", wait_until="networkidle")
    page.wait_for_function("document.querySelector('video.explainer')?.readyState >= 1", timeout=30000)
    c: dict[str, bool] = {}
    s = page.evaluate(STATE)
    c["video carga (~67 s)"] = 60 < s["dur"] < 75
    c["resolución según pantalla"] = ("-1080.mp4" in s["src"]) if not mobile else ("-720.mp4" in s["src"])
    is_es_file = "-es-explainer" in s["src"]
    c[f"voz por defecto = {'es' if locale.startswith('es') else 'en'}"] = is_es_file == locale.startswith("es")
    page.evaluate("() => { const v = document.querySelector('video.explainer'); v.muted = true; return v.play(); }")
    page.wait_for_timeout(1500)
    page.evaluate("() => { document.querySelector('video.explainer').currentTime = 4.0; }")
    page.wait_for_timeout(1200)
    s = page.evaluate(STATE)
    c["se reproduce"] = not s["paused"] and s["t"] > 4.0
    want = "es" if locale.startswith("es") else "en"
    showing = [t["lang"] for t in s["tracks"] if t["mode"] == "showing"]
    c[f"idioma por defecto = {want}"] = showing == [want]
    # browsers only fetch the track being shown; the other loads when switched to
    c["subtítulos cargados (9 cues)"] = all(t["n"] == 9 for t in s["tracks"] if t["mode"] == "showing")
    cue = next((t["cue"] for t in s["tracks"] if t["mode"] == "showing"), None) or ""
    c["cue correcto en pantalla"] = cue.startswith("¿Eres cliente?" if want == "es" else "Are you a customer?")
    other = "en" if want == "es" else "es"
    page.get_by_role("group", name="Subtitles").get_by_role("button", name=other.upper(), exact=True).click()
    page.wait_for_timeout(600)
    s = page.evaluate(STATE)
    c[f"cambiar a {other.upper()}"] = [t["lang"] for t in s["tracks"] if t["mode"] == "showing"] == [other]
    c[f"{other.upper()} cargado al cambiar"] = all(t["n"] == 9 for t in s["tracks"] if t["mode"] == "showing")
    page.locator("video.explainer").screenshot(path=f"{label.replace(' ', '_')}_player.png")
    page.get_by_role("group", name="Subtitles").get_by_role("button", name="Off", exact=True).click()
    page.wait_for_timeout(400)
    s = page.evaluate(STATE)
    c["Off oculta subtítulos"] = not any(t["mode"] == "showing" for t in s["tracks"])

    # voice switch: other language file, same relative position, keeps playing
    page.evaluate("() => { const v = document.querySelector('video.explainer'); v.currentTime = 20; }")
    page.wait_for_timeout(800)
    before = page.evaluate(STATE)
    target = "EN" if is_es_file else "ES"
    page.get_by_role("group", name="Voice").get_by_role("button", name=target, exact=True).click()
    page.wait_for_function("document.querySelector('video.explainer')?.readyState >= 1", timeout=30000)
    page.wait_for_timeout(2000)  # the player itself must resume playback (no play() from the test here)
    after = page.evaluate(STATE)
    c[f"cambiar voz a {target}"] = ("-es-explainer" in after["src"]) == (target == "ES")
    frac_b = before["t"] / before["dur"]
    frac_a = after["t"] / after["dur"]
    c["mantiene la posición"] = abs(frac_a - frac_b) < 0.06
    c["sigue reproduciendo"] = not after["paused"]
    c["sin errores de página"] = not errors
    browser.close()
    return {f"[{label}] {k}": v for k, v in c.items()}


def main() -> int:
    res: dict[str, bool] = {}
    with sync_playwright() as p:
        res.update(run(p, "desktop en", "en-US", {"width": 1440, "height": 900}, False))
        res.update(run(p, "móvil es", "es-ES", {"width": 390, "height": 844}, True))
    for k, v in res.items():
        print(("✅" if v else "❌"), k)
    ok = sum(res.values())
    print(f"{ok}/{len(res)}")
    return 0 if ok == len(res) else 1


if __name__ == "__main__":
    sys.exit(main())
