"""Browser test of the portfolio hub circle (real Chrome via Playwright).

    python scripts/tests/portfolio_hub_test.py [base_url]     # default http://localhost:3100

Checks, on desktop and mobile: the six segments render, clicking one turns the ring and enters its section,
the scene hides while leaving and only reappears once the ring has shrunk back, neighbour links slide to the
next section, the About card opens, browser back works, and no page errors are thrown.
"""
from __future__ import annotations

import sys
import time

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3100"


def scene_opacity(pg) -> float:
    return pg.evaluate("""() => {
        const b = document.querySelector('button[aria-label^="About"]');
        return b ? parseFloat(getComputedStyle(b.parentElement).opacity) : -1;
    }""")


def run(pg, label: str, desktop: bool) -> dict[str, bool]:
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE + "/", wait_until="load")  # the hub plays its intro video: the network never goes idle
    time.sleep(1.2)
    c: dict[str, bool] = {}
    c["6 segmentos"] = pg.locator("a.ring-seg").count() == 6
    c["escena visible en el inicio"] = scene_opacity(pg) > 0.95
    c["botón Upwork"] = "upwork.com" in (pg.get_by_role("link", name="Hire me on Upwork").first.get_attribute("href") or "")

    pg.locator('a.ring-seg[aria-label="Automation & Bots"]').click()
    time.sleep(0.4)
    c["escena se oculta al entrar"] = scene_opacity(pg) < 0.6
    time.sleep(2.2)
    c["entra en la sección"] = pg.evaluate("location.pathname") == "/automation"
    # visited pages stay mounted but hidden (React Activity), so look for the visible heading only
    c["título de la sección"] = pg.get_by_role("heading", level=1, name="Bots that").is_visible()
    c["segmento activo arriba"] = pg.locator('a.ring-seg[aria-current="page"]').get_attribute("aria-label") == "Automation & Bots"

    pg.locator('nav[aria-label="Other areas"] a', has_text="Software, APIs & QA").click()
    time.sleep(2.0)
    c["vecino: siguiente sección"] = pg.evaluate("location.pathname") == "/software"

    pg.get_by_role("link", name="All work").first.click()
    time.sleep(0.9)
    c["escena espera al anillo al volver"] = scene_opacity(pg) < 0.3
    time.sleep(2.4)
    c["vuelve al inicio"] = pg.evaluate("location.pathname") == "/"
    c["escena visible al terminar"] = scene_opacity(pg) > 0.95

    pg.get_by_role("button", name="About Iván").click()
    time.sleep(0.4)
    c["tarjeta About"] = pg.locator("dialog[open]").count() == 1
    pg.keyboard.press("Escape")

    pg.locator('a.ring-seg[aria-label="AI Media"]').click()
    time.sleep(2.5)
    pg.go_back()
    time.sleep(2.0)
    c["atrás del navegador"] = pg.evaluate("location.pathname") == "/"
    c["sin errores de página"] = not errors
    return {f"[{label}] {k}": v for k, v in c.items()}


def main() -> int:
    results: dict[str, bool] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for label, vp in (("desktop", {"width": 1440, "height": 900}), ("móvil", {"width": 390, "height": 844})):
            page = browser.new_page(viewport=vp)
            results.update(run(page, label, label == "desktop"))
            page.close()
        browser.close()
    for k, v in results.items():
        print(("✅" if v else "❌"), k)
    ok = sum(results.values())
    print(f"{ok}/{len(results)}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
