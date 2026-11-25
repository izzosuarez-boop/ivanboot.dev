"""Section 3 video (Web & API Integration): KamasMarket end to end, its APIs, its smart contracts and its AI agent.
Approved 2026-11-23. Everything is made in code (real page captures + HTML scenes); only the voice costs cents.

    python scripts/media/kamas_assemble.py voice            # English voice lines, transcribed to verify them
    python scripts/media/kamas_assemble.py logos            # brand SVGs + colors (Simple Icons, pinned version)
    python scripts/media/kamas_assemble.py capture          # the real offers page, usernames blurred
    python scripts/media/kamas_assemble.py scene <name> [t1,t2]
    python scripts/media/kamas_assemble.py assemble explainer

Reuses automation_assemble.py (scene filming, assembly, captions) by pointing its globals at this video.
Wompi, NOWPayments and Zavu have no Simple Icons logo: they are name tiles (nominative use, PLAYBOOK E16).
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import automation_assemble as aa  # noqa: E402
import generate_category_media as g  # noqa: E402

SLUG = "web-api-overview"
WORK = g.out_dir(f"portfolio-{SLUG}")
SITE = "https://kamasmarket.com/es/ofertas"

VOICE = {
    "intro": "This is KamasMarket, a marketplace that acts as a safe middleman for buying and selling an online "
             "game's currency. Let's see how it works from start to finish, and which services it's connected to.",
    "flow": "The seller posts an offer and the buyer accepts it. A bot receives the currency from the seller inside the "
            "game, the buyer pays in USDT to their order's contract, and once the payment is confirmed on the "
            "blockchain, the bot delivers what they bought.",
    "contract": "Each order has its own smart contract. The buyer's money can only end up in two places: with the "
                "seller, once the delivery is confirmed, or back with the buyer if the order falls through. No one, "
                "not even the platform, can divert it. When the delivery is confirmed, the contract pays the seller "
                "and sends the commission to its wallet, for a few cents per order.",
    "pay": "For payments: the contracts live on BNB Chain; Wompi pays in Colombian pesos to sellers who get paid "
           "through Nequi, Bancolombia or Bre-B; and Binance and NOWPayments handle payouts to sellers abroad.",
    "notify": "Every step is announced instantly: on WhatsApp through Zavu, with buttons like 'Confirm availability' "
              "or 'Pay now'; on Telegram and Discord; and account emails, like verification and password recovery, "
              "go out through Resend.",
    "ai": "Artificial intelligence works on two fronts: DeepSeek powers the site's agent, and Anthropic's Claude "
          "reviews every trade the bot makes with vision, as a second check of the amount and the key.",
    "agent": "And the agent looks after the users: it tracks their orders, tells them how a payment is going, and "
             "explains any section of the site, for example how to register their BEP-20 address to receive their "
             "payouts.",
    "outro": "One site, nine integrations, and a contract that makes sure no one is left without what's theirs.",
}
VOICE_ES = {
    "intro": "Esta es KamasMarket, un mercado que hace de intermediario seguro para comprar y vender la moneda de un "
             "juego en línea. Veamos cómo funciona de principio a fin y con qué servicios está conectada.",
    "flow": "El vendedor publica su oferta y el comprador la acepta. Un bot recibe la moneda del vendedor dentro del "
            "juego, el comprador paga en USDT al contrato de su orden y, cuando el pago se confirma en la blockchain, "
            "el bot le entrega lo que compró.",
    "contract": "Cada orden tiene su propio contrato inteligente. El dinero del comprador solo puede terminar en dos "
                "lugares: en el vendedor, cuando se confirma la entrega, o de vuelta en el comprador si la orden no se "
                "concreta. Nadie, ni siquiera la plataforma, puede desviarlo. Al confirmarse la entrega, el contrato "
                "paga al vendedor y envía la comisión a su billetera, por unos centavos por orden.",
    "pay": "Para los pagos: los contratos viven en BNB Chain; Wompi paga en pesos a quien cobra por Nequi, "
           "Bancolombia o Bre-B; y Binance y NOWPayments se encargan de los pagos a vendedores en el exterior.",
    "notify": "Cada paso se avisa al instante: por WhatsApp a través de Zavu, con botones como 'Confirmar "
              "disponibilidad' o 'Pagar ahora'; por Telegram y Discord; y los correos de la cuenta, como la "
              "verificación y la recuperación de contraseña, salen por Resend.",
    "ai": "La inteligencia artificial trabaja en dos frentes: DeepSeek impulsa el agente de la página, y Claude, de "
          "Anthropic, revisa con visión cada intercambio del bot como una segunda verificación de la cantidad y la "
          "clave.",
    "agent": "Y el agente atiende a los usuarios: hace seguimiento de sus órdenes, les dice cómo va un pago y explica "
             "cualquier sección de la página, por ejemplo cómo registrar su dirección BEP-20 para recibir sus cobros.",
    "outro": "Una sola página, nueve integraciones y un contrato que garantiza que nadie se quede sin lo suyo.",
}

# (voice key, composite, seconds, still): each shot = its voice line + 0.35 s lead + ~1 s; scenes/k-<key>.html
SHOTS = [("intro", "k-intro-composite.mp4", 11.8, None), ("flow", "k-flow-composite.mp4", 15.0, None),
         ("contract", "k-contract-composite.mp4", 21.2, None), ("pay", "k-pay-composite.mp4", 14.2, None),
         ("notify", "k-notify-composite.mp4", 14.3, None), ("ai", "k-ai-composite.mp4", 12.2, None),
         ("agent", "k-agent-composite.mp4", 12.8, None), ("outro", "k-outro-composite.mp4", 8.0, None)]


def point_aa() -> None:
    """Make automation_assemble's helpers work on this video."""
    aa.SLUG, aa.WORK, aa.VOICE, aa.VOICE_ES, aa.SHOTS, aa.ROOM = SLUG, WORK, VOICE, VOICE_ES, SHOTS, {}
    aa.POSTER_AT = ("contract", 19.8)   # paid out: seller +93, commission +7, network fee


def voice(*keys: str) -> None:
    point_aa()
    aa.voice(*keys)


LOGO_VERSION = "16.36.0"
LOGOS = ["binance", "bnbchain", "tether", "telegram", "discord", "resend", "whatsapp", "deepseek", "anthropic", "claude"]
LOGO_DIR = HERE / "out/logos-kamas"


def logos() -> None:
    """SVGs (CC0 data) and brand colors; scenes color them themselves."""
    cdn = f"https://cdn.jsdelivr.net/npm/simple-icons@{LOGO_VERSION}"
    get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "media-script"}), timeout=30).read()
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(get(f"{cdn}/data/simple-icons.json"))
    icons = data if isinstance(data, list) else data.get("icons", [])
    by = {(ic.get("slug") or "".join(c for c in ic["title"].lower() if c.isalnum())): ic for ic in icons}
    colors = {}
    for s in LOGOS:
        (LOGO_DIR / f"{s}.svg").write_bytes(get(f"{cdn}/icons/{s}.svg"))
        colors[s] = {"hex": "#" + by.get(s, {}).get("hex", "5eead4"), "title": by.get(s, {}).get("title", s)}
        print(s, colors[s])
    (LOGO_DIR / "colors.json").write_text(json.dumps(colors, indent=1), encoding="utf-8")
    # the scenes read it as a script (file:// pages can't fetch JSON)
    for s_, c in colors.items():
        c["svg"] = (LOGO_DIR / f"{s_}.svg").read_text(encoding="utf-8")
    (LOGO_DIR / "logos.js").write_text("window.LOGOS = " + json.dumps(colors) + ";", encoding="utf-8")


def capture() -> None:
    """The real offers page at 2x: viewport shot + full page, every username cell blurred before the shot."""
    from playwright.sync_api import sync_playwright
    out = WORK / "site"
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2, locale="es-ES")
        pg.goto(SITE, wait_until="load")
        pg.wait_for_timeout(3500)
        n = pg.evaluate("""() => { let n = 0;
            for (const t of document.querySelectorAll('table')) for (const r of t.querySelectorAll('tbody tr')) {
              const c = r.querySelector('td'); if (c) { c.style.filter = 'blur(7px)'; n++; } }
            return n; }""")
        print("usernames blurred:", n)
        pg.wait_for_timeout(500)
        pg.screenshot(path=str(out / "offers-full.png"), full_page=True)
        b.close()
    print("->", out)


def scene(name: str, preview: str = "") -> Path:
    point_aa()
    return aa.scene(name, preview)


def assemble(name: str = "sample", lang: str = "en", channel: str = "upwork") -> Path:
    point_aa()
    return aa.assemble(name, lang, channel)


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"voice": voice, "logos": logos, "capture": capture, "scene": scene, "assemble": assemble}[cmd](*args)
