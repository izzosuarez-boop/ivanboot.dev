"""Spanish text of the code-made scenes (2026-11-25): the Workana site and the Spanish voice versions show the
scenes in Spanish. automation_assemble.scene(name, lang="es") swaps every visible text node that matches a key
below, on every frame; text being typed (a prefix of a key) gets the same share of its translation. Brand names,
numbers, addresses and code are left as they are.
"""

ES = {
    # ── automation: pipeline, radar, form, deliver ──
    "AUTOMATED WORKFLOW": "FLUJO AUTOMATIZADO",
    "Scrape": "Extraer", "3 buyer sites": "3 sitios compradores",
    "Decide": "Decidir", "your own rules": "con tus reglas",
    "Ask": "Preguntar", "on Telegram": "por Telegram",
    "Sell": "Vender", "browser bot": "bot de navegador",
    "Deliver": "Entregar", "delivery bot": "bot de entrega",
    "Report": "Informar", "summary": "resumen",
    "● Real client case": "● Caso real de un cliente",
    "Selling an online game's currency, end to end": "Venta de la moneda de un juego en línea, de principio a fin",
    "Buyer site A": "Sitio comprador A", "Buyer site B": "Sitio comprador B", "Buyer site C": "Sitio comprador C",
    "We buy game currency": "Compramos moneda de juegos",
    "Price paid per million, updated live": "Precio pagado por millón, actualizado en vivo",
    "Server": "Servidor", "Price / M": "Precio / M", "Status": "Estado", "Buying": "Comprando",
    "PRICE MONITOR": "MONITOR DE PRECIOS", "TIME-LAPSE": "CÁMARA RÁPIDA", "next check (s)": "próxima lectura (s)",
    "Every minute · 24/7 · target": "Cada minuto · 24/7 · objetivo",
    "✓ Match found → asking the owner": "✓ Coincidencia → preguntando al dueño",
    "21:02  3 sites checked · no match": "21:02  3 sitios revisados · sin coincidencia",
    "21:03  3 sites checked · no match": "21:03  3 sitios revisados · sin coincidencia",
    "21:04  3 sites checked · no match": "21:04  3 sitios revisados · sin coincidencia",
    "match found": "coincidencia",
    "21:05  MATCH  3.52 ≥ 3.50 · 40 M": "21:05  COINCIDE  3.52 ≥ 3.50 · 40 M",
    "◌ Headless browser · running in the background": "◌ Navegador sin interfaz · trabajando en segundo plano",
    "Log in": "Iniciar sesión", "Welcome back": "Hola de nuevo", "Log in to sell": "Inicia sesión para vender",
    "EMAIL": "CORREO", "PASSWORD": "CONTRASEÑA",
    "Create a sell order": "Crea una orden de venta",
    "We pay as soon as the delivery is confirmed": "Pagamos en cuanto se confirma la entrega",
    "SERVER": "SERVIDOR", "AMOUNT": "CANTIDAD", "PRICE PER MILLION": "PRECIO POR MILLÓN", "TOTAL": "TOTAL",
    "FULL NAME": "NOMBRE COMPLETO", "LOCATION": "UBICACIÓN", "PAYOUT": "COBRO",
    "Create sell order": "Crear orden de venta",
    "owner approved on Telegram": "el dueño aprobó en Telegram",
    "sale: 40 M at 3.52 USDT / M": "venta: 40 M a 3.52 USDT / M",
    "launching headless browser…": "abriendo el navegador sin interfaz…",
    "buyer-site-a: logging in": "sitio comprador A: iniciando sesión",
    "logged in": "sesión iniciada",
    "filling the sell order": "llenando la orden de venta",
    "Signed in · Alex M.": "Sesión iniciada · Alex M.",
    "Lisbon, Portugal": "Lisboa, Portugal",
    "order #48213 created": "orden #48213 creada",
    "✓ Sell order #48213 created": "✓ Orden de venta #48213 creada",
    "Delivery bot": "Bot de entrega", "STANDBY": "EN ESPERA", "ORDER TOKEN": "TOKEN DE LA ORDEN",
    "Amount": "Cantidad", "Buyer": "Comprador",
    "Staff · support chat": "Personal · chat de soporte",
    "Hi! Ready to receive your 40 M. Meet you at the trade point 👋": "¡Hola! Listos para recibir tus 40 M. Nos vemos en el punto de intercambio 👋",
    "Waiting for the delivery": "Esperando la entrega",
    "DELIVERING": "ENTREGANDO", "Delivery in progress…": "Entrega en curso…",
    "DELIVERED ✓": "ENTREGADO ✓", "✓ Received 40 M": "✓ Recibidos 40 M",

    # ── KamasMarket (web & API) ──
    "THE SITE'S AI AGENT": "EL AGENTE DE IA DEL SITIO",
    "Tracks your orders": "Sigue tus órdenes",
    "Tells you how a payment is going": "Te dice cómo va un pago",
    "Explains any section of the site": "Explica cualquier sección del sitio",
    "e.g. register your BEP-20 address": "p. ej., registrar tu dirección BEP-20",
    "Live chat": "Chat en vivo",
    "Hi! Ask me how the site works, how to set up your payout method or the status of one of your orders, or report a bug to me.":
        "¡Hola! Pregúntame cómo funciona el sitio, cómo configurar tu método de cobro o el estado de una de tus órdenes, o repórtame un error.",
    "How is my order #1042 going?": "¿Cómo va mi orden #1042?",
    "Typing…": "Escribiendo…",
    "Order #1042: your payment of 100 USDT was confirmed on BNB Chain ✓\nThe bot already has the seller's kamas and is delivering them to you now.":
        "Orden #1042: tu pago de 100 USDT se confirmó en BNB Chain ✓\nEl bot ya tiene los kamas del vendedor y te los está entregando ahora.",
    "How do I register my BEP-20 address?": "¿Cómo registro mi dirección BEP-20?",
    "Go to Profile → Payout methods and choose \"Crypto (BEP-20)\". Paste your USDT address on BNB Smart Chain (it starts with 0x) and save.\nMake sure it's BEP-20: sending on another network loses the money. No address yet? Our BEP-20 guide shows how to create one on Binance in under a minute.":
        "Ve a Perfil → Métodos de cobro y elige \"Cripto (BEP-20)\". Pega tu dirección USDT de BNB Smart Chain (empieza por 0x) y guarda.\nAsegúrate de que sea BEP-20: enviar por otra red pierde el dinero. ¿Aún no tienes dirección? Nuestra guía BEP-20 muestra cómo crear una en Binance en menos de un minuto.",
    "Type something": "Escribe algo", "Send": "Enviar",
    "Need our team? Message us on Discord": "¿Necesitas a nuestro equipo? Escríbenos en Discord",
    "ARTIFICIAL INTELLIGENCE": "INTELIGENCIA ARTIFICIAL",
    "powers the site's agent": "impulsa el agente del sitio",
    "How is my order going?": "¿Cómo va mi orden?",
    "Your payment was confirmed ✓ The bot is delivering now.": "Tu pago se confirmó ✓ El bot está entregando ahora.",
    "second check of every trade, with vision": "segunda revisión de cada intercambio, con visión",
    "IN-GAME TRADE · SCREEN CAPTURE": "INTERCAMBIO EN EL JUEGO · CAPTURA DE PANTALLA",
    "Kamas offered": "Kamas ofrecidos", "Buyer's key": "Clave del comprador",
    "Seller": "Vendedor", "Commission wallet": "Billetera de comisión", "Platform": "Plataforma",
    "if delivered": "si se entrega", "if the order falls through → refund": "si la orden no se concreta → reembolso",
    "SMART CONTRACT · BNB CHAIN": "CONTRATO INTELIGENTE · BNB CHAIN",
    "Order #1042": "Orden #1042", "0x7f3a…c91e · its own address": "0x7f3a…c91e · su propia dirección",
    "Waiting for the buyer's payment": "Esperando el pago del comprador",
    "✓ Delivery confirmed": "✓ Entrega confirmada",
    "Network fee ≈ $0.02 per order": "Comisión de red ≈ 0,02 $ por orden",
    "paying…": "pagando…", "Receiving payment…": "Recibiendo el pago…", "paid ✓": "pagado ✓",
    "🔒 Locked: seller or buyer only": "🔒 Bloqueado: solo vendedor o comprador",
    "Paying out…": "Pagando…", "✓ Paid out · order closed": "✓ Pagado · orden cerrada",
    "posts 40 M kamas": "publica 40 M kamas", "pays 100 USDT": "paga 100 USDT",
    "In-game bot": "Bot en el juego", "receives & delivers": "recibe y entrega",
    "Order contract": "Contrato de la orden",
    "📢 Posts an offer": "📢 Publica una oferta", "✓ Accepts it": "✓ La acepta",
    "Kamas received in-game": "Kamas recibidos en el juego", "Pays the order's contract": "Paga al contrato de la orden",
    "✓ Payment confirmed on the blockchain": "✓ Pago confirmado en la blockchain",
    "Delivered to the buyer ✓": "Entregado al comprador ✓",
    "NOTIFICATIONS": "NOTIFICACIONES", "WhatsApp · via Zavu": "WhatsApp · con Zavu",
    "TO THE SELLER": "AL VENDEDOR", "TO THE BUYER": "AL COMPRADOR",
    "New order #1042: a buyer wants your 40 M kamas.": "Nueva orden #1042: un comprador quiere tus 40 M kamas.",
    "Confirm availability": "Confirmar disponibilidad",
    "The seller is ready. Pay 100 USDT to your order's contract.": "El vendedor está listo. Paga 100 USDT al contrato de tu orden.",
    "Pay now": "Pagar ahora",
    "Delivered ✓ Your 40 M kamas are in your inventory.": "Entregado ✓ Tus 40 M kamas están en tu inventario.",
    "WhatsApp messages": "Mensajes de WhatsApp",
    "a template per step, with its action button": "una plantilla por paso, con su botón de acción",
    "Telegram & Discord": "Telegram y Discord",
    "the same updates, wherever the user prefers": "los mismos avisos, donde el usuario prefiera",
    "Account emails": "Correos de la cuenta",
    "verify your email · reset your password": "verificar tu correo · recuperar tu contraseña",
    "1 INTEGRATION": "1 INTEGRACIÓN", "4 INTEGRATIONS": "4 INTEGRACIONES",
    "7 INTEGRATIONS": "7 INTEGRACIONES", "9 INTEGRATIONS": "9 INTEGRACIONES",
    "PAYMENTS": "PAGOS", "Contracts on BNB Chain": "Contratos en BNB Chain",
    "buyers pay in USDT (BEP-20)": "los compradores pagan en USDT (BEP-20)",
    "Payouts in pesos": "Pagos en pesos", "to sellers in Colombia": "a vendedores en Colombia",
    "Payouts abroad": "Pagos al exterior", "to sellers outside Colombia": "a vendedores fuera de Colombia",

    # ── loops ──
    "ARDEA SKIN · SHOPIFY": "ARDEA SKIN · SHOPIFY",
    "One brand identity": "Una identidad de marca",
    "On every page and product": "En cada página y producto",
    "Run from Telegram": "Gestionada desde Telegram",
    "Ardea Skin bot": "Bot de Ardea Skin", "to the store owner": "al dueño de la tienda",
    "Low stock:": "Poco stock:", "Clarifying Gel Cleanser — only 8 left": "Clarifying Gel Cleanser: quedan solo 8",
    "● KamasMarket · a live P2P marketplace": "● KamasMarket · un mercado P2P en vivo",
    "ORDER": "ORDEN", "#1042 · 40 M kamas": "#1042 · 40 M kamas",
    "Seller ready": "Vendedor listo", "Kamas received by the bot": "Kamas recibidos por el bot",
    "Paid to the contract": "Pagado al contrato", "Delivered to the buyer": "Entregado al comprador",
    "Commission 7 %": "Comisión 7 %",
    "THE IDEA": "LA IDEA", "Manual work": "Trabajo manual", "→ automatic work": "→ trabajo automático",
    "Same person · same light · same style": "Misma persona · misma luz · mismo estilo",
    "THEN IT GETS CORRECTED": "LUEGO SE CORRIGE", "BEFORE": "ANTES", "AFTER": "DESPUÉS",
    "real photo": "foto real", "✕ The beard didn't match": "✕ La barba no coincidía",
    "· An AI agent that works for you, 24/7.": "· Un agente de IA que trabaja para ti, 24/7.",
    "✓ Ready to post": "✓ Listo para publicar", "AI CONTENT": "CONTENIDO CON IA",
    "The idea": "La idea", "Consistent frames": "Fotogramas coherentes", "Real corrections": "Correcciones reales",
    "Ready to post": "Listo para publicar", "✓ Edited to match the real photo": "✓ Editada para coincidir con la foto real",
    "● Price monitor · every minute, 24/7": "● Monitor de precios · cada minuto, 24/7",
    "Monday, 23 November": "lunes, 23 de noviembre",
    "Sale bot": "Bot de ventas", "now": "ahora",
    "Do you want to make this sale?": "¿Quieres hacer esta venta?",
    "40 M at 3.52 · Buyer site A": "40 M a 3.52 · Sitio comprador A",
    "✓ Accept": "✓ Aceptar", "× Cancel": "× Cancelar", "✓ Accepted": "✓ Aceptada",
    "● Creating the sell order…": "● Creando la orden de venta…",
    "✓ Transaction complete": "✓ Transacción completada",
    "Order #48213 · 40 M delivered": "Orden #48213 · 40 M entregados",
    "Check your balance": "Revisa tu saldo",
    "✓ Sell order created": "✓ Orden de venta creada",
    "● Delivering 40 M…": "● Entregando 40 M…",
    "ARDEA SKIN · AI AGENT": "ARDEA SKIN · AGENTE DE IA",
    "Browse the store": "Navega la tienda", "Ask the agent": "Pregunta al agente", "Added to your bag": "Añadido a tu bolsa",

    # ── AI media (section 4) ──
    "▶ Brand film · AI video": "▶ Video de marca · video con IA",
    "Product photos · AI images": "Fotos de producto · imágenes con IA",
    "Category cover · AI image": "Portada de categoría · imagen con IA",
    "▶ Tutorial video · AI video + voice": "▶ Video tutorial · video y voz con IA",
    "Product photo · AI image": "Foto de producto · imagen con IA",
    "One art direction · every piece has a job on the page": "Una dirección de arte · cada pieza cumple una función en la página",
    "AI CONTENT · PORTFOLIO + ARDEA SKIN": "CONTENIDO CON IA · PORTAFOLIO + ARDEA SKIN",
    "What it really cost": "Lo que costó de verdad",
    "Product photos (17)": "Fotos de producto (17)",
    "Category covers + tutorial videos": "Portadas de categoría + videos tutoriales",
    "Store brand film": "Video de marca de la tienda",
    "AI Agents video": "Video de agentes de IA",
    "Home video, with its corrections": "Video de inicio, con sus correcciones",
    "Automation video": "Video de automatización",
    "Web & API + this video (voice only)": "Web y API + este video (solo voz)",
    "Total, retakes included": "Total, con repeticiones",
    "Nothing made at random": "Nada se hace al azar",
    "Every step measured": "Cada paso medido",
    "cost printed by every generation": "cada generación muestra su costo",
    "What AI does badly → done in code": "Lo que la IA hace mal → se hace con código",
    "and it costs nothing": "y no cuesta nada",
    "Screens": "Pantallas", "Speech bubbles": "Globos de diálogo", "Subtitles": "Subtítulos",
    "Circles": "Círculos", "Diagrams": "Diagramas",
    "Content with intent,": "Contenido con intención,", "not just with AI.": "no solo con IA.",
    "WHAT AI DOESN'T DO WELL, CODE SOLVES": "LO QUE LA IA NO HACE BIEN, LO RESUELVE EL CÓDIGO",
    "SCREENS INVENTED BY AI": "PANTALLAS INVENTADAS POR LA IA", "OUR REAL CODE": "NUESTRO CÓDIGO REAL",
    "AI CLIP": "CLIP DE IA", "+ DRAWN IN CODE": "+ DIBUJADO CON CÓDIGO", "Text": "Texto",
    "TRANSCRIPT OF THE VOICE LINE": "TRANSCRIPCIÓN DE LA FRASE DE VOZ",
    "✓ Matches the script word for word": "✓ Coincide con el guion palabra por palabra",
    "Invented screens → real content": "Pantallas inventadas → contenido real",
    "Text, bubbles and subtitles → drawn separately": "Textos, globos y subtítulos → dibujados aparte",
    "Every voice line → transcribed and checked": "Cada frase de voz → transcrita y comprobada",
    "What AI doesn't do well, code solves: the screens it invents are replaced with real content…":
        "Lo que la IA no hace bien lo resuelve el código: las pantallas que inventa se reemplazan por contenido real…",
    "CONSISTENCY IS DESIGNED": "LA COHERENCIA SE DISEÑA", "reference": "referencia",
    "Same man · same hoodie · same night mood": "Mismo hombre · misma sudadera · misma noche",
    "same office": "misma oficina",
    "✕ First version": "✕ Primera versión",
    "✕ Over the shoulder": "✕ Por encima del hombro", "✓ Switched to a profile": "✓ Cambiado a perfil",
    "✕ Phone at the far end": "✕ Teléfono al otro extremo", "✓ Phone under his hand": "✓ Teléfono bajo su mano",
    "✕ AI drawing the circles": "✕ La IA dibujando los círculos", "✓ Circles drawn in code": "✓ Círculos dibujados con código",
    "The beard didn't match the real photo": "La barba no coincidía con la foto real",
    "From behind I wasn't recognizable": "De espaldas no se me reconocía",
    "The phone was out of his reach": "El teléfono estaba fuera de su alcance",
    "The AI couldn't draw believable circles": "La IA no podía dibujar círculos creíbles",
    "Checked frame by frame before moving on": "Revisado fotograma a fotograma antes de seguir",
    "THE IDEA FIRST": "PRIMERO, LA IDEA", "Manual work → automatic work": "Trabajo manual → trabajo automático",
    "Pain": "El problema", "Done by hand, at night": "A mano, de noche",
    "The tool": "La herramienta", "Rules: price and amount": "Reglas: precio y cantidad",
    "Checks every minute": "Revisa cada minuto",
    "Control": "Control", "Asks before selling": "Pregunta antes de vender",
    "Delivery": "Entrega", "A bot hands it over": "Un bot la entrega",
    "Relief": "Alivio", "Just check the payment": "Solo revisa el pago",
    "Home": "Inicio", "AI Agents": "Agentes de IA", "Automation": "Automatización", "Web & API": "Web y API",
    "PROMPT": "PROMPT", "What to say": "Qué decir", "the one idea": "la idea central",
    "What to show": "Qué mostrar", "which part of the product": "qué parte del producto",
    "How to tell it": "Cómo contarlo", "understood the first time": "que se entienda a la primera",
    "make me a video about my business": "hazme un video sobre mi negocio",
    "HOME · AI AT WORK": "INICIO · LA IA EN EL TRABAJO",
    "SECTION 1 · AI AGENTS": "SECCIÓN 1 · AGENTES DE IA",
    "SECTION 2 · AUTOMATION": "SECCIÓN 2 · AUTOMATIZACIÓN",
    "SECTION 3 · WEB & API": "SECCIÓN 3 · WEB Y API",
    "FOR YOUR SOCIAL MEDIA": "PARA TUS REDES SOCIALES",
    "Web scraping": "Web scraping", "trends and what your competitors post": "tendencias y lo que publica tu competencia",
    "Competitor A · reel": "Competidor A · reel", "48k views": "48 mil vistas",
    "Competitor B · carousel": "Competidor B · carrusel", "12k likes": "12 mil me gusta",
    "Content": "Contenido", "made with the same care": "hecho con el mismo cuidado",
    "Your morning routine in 3 steps ✨": "Tu rutina de mañana en 3 pasos ✨",
    "it runs by itself": "funciona sola",
    "🗓 Scheduling": "🗓 Programar", "✓ Publishing": "✓ Publicar", "💬 Replying to comments": "💬 Responder comentarios",
}

# Addresses shown on screen that belong to one version of the portfolio: the Workana versions show their own.
# The domains come from sites.env (outside the public repo), like the site's.
def _sites() -> dict:
    from pathlib import Path
    f = Path(__file__).resolve().parents[2] / "sites.env"
    if not f.exists():
        return {}
    return dict(line.split("=", 1) for line in f.read_text(encoding="utf-8").splitlines()
                if "=" in line and not line.lstrip().startswith("#"))


_S = _sites()
DOMAINS = {"workana": [(_S["UPWORK_STORE_HOST"], _S["WORKANA_STORE_HOST"]), (_S["UPWORK_SITE_HOST"], _S["WORKANA_SITE_HOST"])]
           if _S.get("WORKANA_SITE_HOST") else []}

# The Telegram bubbles and banners of the automation video (drawn in Python, automation_assemble.card/banner)
CARD_ES = {
    "Sale bot": "Bot de ventas", "Telegram · now": "Telegram · ahora",
    "Match found: sale ready for your approval": "Coincidencia: venta lista para tu aprobación",
    "Delivery complete: order #48213": "Entrega completada: orden #48213",
    "Do you want to make this sale": "¿Quieres hacer esta venta", "for 140.80 USDT?": "por 140.80 USDT?",
    "Server": "Servidor", "Server ": "Servidor ",
    "Buyer site A · price matched at 21:05": "Sitio comprador A · precio alcanzado a las 21:05",
    "✓ Accepted": "✓ Aceptada", "✓ Accept": "✓ Aceptar", "× Cancel": "× Cancelar",
    "Transaction complete": "Transacción completada",
    "Sold 40 M for 140.80 USDT on Buyer site A.": "Vendidos 40 M por 140.80 USDT en el sitio comprador A.",
    "Order #48213 · delivered at 21:19": "Orden #48213 · entregada a las 21:19",
    "Check your balance to confirm the payment.": "Revisa tu saldo para confirmar el pago.",
}

TRANSLATE_JS = r"""(cfg) => {
  window.__i18n = cfg;
  const keys = Object.keys(cfg.dict).sort((a, b) => b.length - a.length);
  window.__tr = () => {
    const { dict, domains } = window.__i18n;
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n; (n = w.nextNode());) {
      const raw = n.nodeValue, t = raw.trim();
      if (!t) continue;
      let out = null;
      if (dict[t] !== undefined) out = raw.replace(t, dict[t]);
      else if (t.length >= 2 && /[A-Za-z]/.test(t)) {
        // text being typed: a prefix of a known line gets the same share of its translation
        const k = keys.find((k) => k.length > t.length && k.startsWith(t));
        if (k) out = raw.replace(t, dict[k].slice(0, Math.round(dict[k].length * t.length / k.length)));
      }
      let v = out ?? raw;
      for (const [a, b] of domains) v = v.split(a).join(b);
      if (v !== raw) n.nodeValue = v;
    }
  };
}"""
