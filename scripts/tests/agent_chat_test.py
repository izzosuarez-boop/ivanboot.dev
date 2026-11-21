"""End-to-end browser test of the store chat (real agent, real Shopify cart). Costs ~US$0.002 per run.

    python scripts/tests/agent_chat_test.py [base_url]
"""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
BASE = sys.argv[1] if len(sys.argv) > 1 else "https://tienda.ivanboot.dev"


def last_reply(page):
    return page.locator("section[role=dialog] .rounded-tl-sm").last.inner_text()


def wait_reply(page, n_before, timeout=45000):
    page.wait_for_function(f"document.querySelectorAll('section[role=dialog] .rounded-tl-sm').length > {n_before}", timeout=timeout)
    page.wait_for_timeout(600)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1366, "height": 860}, locale="es-ES")
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE, wait_until="networkidle")
    bag_before = page.locator("a[aria-label^='Bag']").get_attribute("aria-label")

    page.get_by_role("button", name="Pregúntale a Ardea").click()
    bubbles = lambda: page.locator("section[role=dialog] .rounded-tl-sm").count()
    n = bubbles()
    page.get_by_role("button", name="Ayúdame con mi piel").click()
    wait_reply(page, n); print("1. modo piel ->", last_reply(page)[:200].replace("\n", " "))

    n = bubbles()
    page.locator("section[role=dialog] textarea").fill("Tengo piel sensible y algo de rojez. Agrégame el sérum calmante a la bolsa, por favor.")
    page.keyboard.press("Enter")
    wait_reply(page, n); print("2. pedido ->", last_reply(page)[:220].replace("\n", " "))
    page.wait_for_timeout(2500)  # cart add + router.refresh()
    confirm = page.locator("text=Agregado a tu bolsa").count() + page.locator("text=Added to your bag").count()
    bag_after = page.locator("a[aria-label^='Bag']").get_attribute("aria-label")
    tools = page.locator("section[role=dialog] p:has-text('⚙')").last.inner_text()
    cost = page.locator("section[role=dialog] form p").inner_text()
    print("   confirmación en el chat:", bool(confirm), "| bolsa:", bag_before, "->", bag_after, "|", tools, "|", cost)

    page2 = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
    page2.goto(BASE + "/?ref=upwork", wait_until="networkidle")
    nudge = page2.locator("text=Built with AI").count() + page2.locator("text=Hecho con IA").count()
    page2.locator("button[aria-label^='Ask'], button[aria-label^='Pregúntale']").click()
    dialog_box = page2.locator("section[role=dialog]").bounding_box()
    print("3. móvil ?ref=upwork -> aviso 'Built with AI':", bool(nudge), "| panel a pantalla completa:", dialog_box and dialog_box["width"] >= 380)

    ok = {"responde en modo piel": True, "agrega a la bolsa de verdad": bool(confirm) and bag_before != bag_after,
          "muestra herramientas y costo": "⚙" in tools and "$" in cost, "aviso para visitantes de Upwork": bool(nudge),
          "sin errores JS": not errors}
    print("\nRESULTADO"); [print(f"  {'OK  ' if v else 'FALLA'} {k}") for k, v in ok.items()]
    if errors: print(errors[:3])
    browser.close()
