"""AI Agents section layout + store chat deep link (real Chrome).

    python scripts/tests/section_ai_agents_test.py [portfolio_base] [store_base]

Checks the store opens its chat from ?ref=portfolio&chat=1 with the portfolio greeting (EN / ES) and both
options unselected, and that the section shows the explainer inside the store-agent card, the Live demo
button, the inline Try-it button and the coming-soon main video.
"""
import sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3100"
STORE = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:3100/store"
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    c = {}
    for loc in ("en-US", "es-ES"):
        pg = b.new_page(viewport={"width": 1366, "height": 860}, locale=loc)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(STORE + "/?ref=portfolio&chat=1", wait_until="networkidle"); pg.wait_for_timeout(800)
        dlg = pg.locator("section[role=dialog]")
        hello = dlg.locator(".rounded-tl-sm").first.inner_text() if dlg.count() else ""
        btns = dlg.locator("button[data-mode]")
        sel = [bt.get_attribute("class") for bt in btns.all()]
        c[f"[{loc}] chat abierto"] = dlg.count() == 1
        c[f"[{loc}] saludo portafolio"] = ("portfolio" in hello) if loc == "en-US" else ("portafolio" in hello)
        c[f"[{loc}] dos opciones sin preseleccionar"] = len(sel) == 2 and not any("bg-clay " in (x or "") + " " for x in sel)
        c[f"[{loc}] sin errores"] = not errs
        print(loc, "->", hello)
        pg.close()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(BASE + "/ai-agents", wait_until="networkidle"); pg.wait_for_timeout(1500)
    card = pg.locator("article").filter(has_text="Ardea Skin store agent")
    c["video dentro de la ficha"] = card.locator("video.explainer").count() == 1
    badge = card.get_by_role("link", name="Live demo")
    c["badge es botón al chat"] = badge.count() == 1 and "chat=1" in (badge.get_attribute("href") or "")
    inline = card.locator("p").filter(has_text="A demo agent you can try live").get_by_role("link", name="Try it in the store")
    c["botón 'Try it' en el texto"] = inline.count() == 1
    c["video principal = próximamente"] = pg.locator("section[aria-label='Explainer video'] video").count() == 0
    card.scroll_into_view_if_needed(); pg.wait_for_timeout(500)
    pass
    b.close()
for k, v in c.items(): print(("✅" if v else "❌"), k)
print(f"{sum(c.values())}/{len(c)}")
