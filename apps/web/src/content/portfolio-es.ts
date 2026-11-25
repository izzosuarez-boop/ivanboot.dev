// Spanish portfolio content (the Workana site, 2026-11-25). Same slugs and structure as portfolio.ts. The
// headlines, intros and most project texts are the user's own Spanish words (written for the site and translated
// to English then); the rest is translated from the English version.
import type { About, Content, HubIntro, Section, Ui } from "./types";

const GH = "https://github.com/izzosuarez-boop";

/** The Spanish version (Workana site). `store` is the demo store's address for this version (server env). */
export function spanish(store: string): Content {
  const STORE_CHAT = `${store}/?ref=portfolio&chat=1`;
  const sections: Section[] = [
    {
      slug: "ai-agents",
      label: "Agentes de IA y LLMs",
      short: "Agentes de IA",
      pitch: "Agentes de IA: sistemas que piensan, planifican y actúan.",
      intro:
        "Más allá de un chat: de pedirles cosas a delegarles el trabajo. Hoy los agentes de IA trabajan por ti: " +
        "integrados en tus plataformas y flujos de trabajo, actúan como un factor multiplicador.",
      video: { media: "ai-agents", title: "El agente de la tienda y el agente del dueño en Telegram, en 67 segundos" },
      projects: [
        {
          title: "Agente de la tienda Ardea Skin",
          status: "Live demo",
          summary: [
            "Un agente de demostración que puedes probar en vivo en la tienda que creé para clientes de Shopify: [[link]]",
            "Ideal como primer contacto para los clientes potenciales que quieran saber más sobre tus productos y tu "
              + "sitio, y un potente agente integrado a tu plataforma, a tus apps y a herramientas de terceros que "
              + "simplifica la administración de tu negocio.",
            "Como muestra de mi portafolio, también responde preguntas técnicas sobre el sitio, su estructura y las "
              + "tecnologías con las que fue hecho, sin exponer información delicada o confidencial.",
          ],
          problem: "Los usuarios quieren un sistema que les dé soluciones, no un chat que responda con reglas simples. El "
            + "dueño del sitio quiere un agente al que pueda delegarle funciones, pedirle información y confiarle la "
            + "administración del sitio según sus directrices: lo que hoy haría una persona, delegado a un agente de IA, "
            + "todo en un mismo lugar.",
          how: "Claude Haiku 5.5 con herramientas que leen Shopify (catálogo, stock y carrito) y un prompt de sistema en "
            + "caché. Las quejas y las preguntas médicas se escalan al dueño con un código de referencia. Tope de gasto "
            + "diario y límites por visitante.",
          result: "Entre 0,0002 y 0,001 dólares por turno; las conversaciones, los tokens y el costo se guardan en Supabase "
            + "y una prueba en el navegador comprueba el flujo completo. Lo que hace hoy: recomienda rutinas y añade "
            + "productos a la bolsa; del lado del dueño, en Telegram, repone o ajusta el stock (siempre tras pulsar "
            + "Confirmar), crea gráficas, envía un resumen diario y un informe semanal, recuerda la conversación y escala "
            + "quejas, problemas con pedidos y preguntas médicas desde el chat de la tienda.",
          stack: ["Claude API", "Uso de herramientas", "FastAPI", "Shopify Storefront API", "Shopify Admin API", "Telegram Bot API", "Supabase", "Playwright"],
          link: { label: "Pruébalo en la tienda", href: STORE_CHAT },
          demoHref: STORE_CHAT,
          repos: [{ label: "Código en GitHub", href: `${GH}/ardea-skin` }],
          loop: { media: "loop-store", label: "La tienda Ardea Skin y su agente de IA: navegar, preguntar, añadido a la bolsa" },
        },
      ],
    },
    {
      slug: "automation",
      label: "Web Scraping, automatización y datos",
      ring: "Scraping, automatización y datos",
      short: "Automatización",
      pitch: "Bots que realizan el trabajo rutinario y automatizan tu trabajo de principio a fin.",
      intro:
        "Hoy más que nunca es posible crear flujos de trabajo con una intervención humana mínima. El software trabaja " +
        "24/7; una persona, no. Delega todo lo que puedas automatizar al software o a los agentes de IA: el trabajo " +
        "sistemático, la recopilación de información, su análisis y la toma de decisiones según tus propias directrices.",
      video: { media: "automation-overview", title: "Un caso real: la venta de moneda de un juego automatizada de principio a fin, en 86 segundos" },
      projects: [
        {
          title: "Web scraping de principio a fin: de los datos a las decisiones",
          status: "Case study",
          summary: "El valor del web scraping no está en recopilar datos, sino en usarlos bien: conectarlos a scripts y "
            + "bots que actúan según las reglas del propio cliente.",
          problem: "Muchas decisiones dependen de información que cambia cada minuto, y una persona no puede vigilarla todo "
            + "el día. Este caso es la venta de moneda de un juego, pero el mismo patrón sirve para trading, supermercados "
            + "en línea, aerolíneas, búsqueda de hoteles, inmobiliarias y bolsas de empleo: trabajo manual que se vuelve "
            + "mucho más rentable al automatizarlo. Solo tiene sentido cuando la plataforma no tiene API; si la tiene, lo "
            + "correcto es una integración con la API.",
          how: "Python de principio a fin. Los precios se leen sin navegador: la página trae sus datos como JSON "
            + "incrustado, así que la lectura es rápida y ligera. Playwright maneja un Chrome real solo para vender: elige "
            + "el servidor y llena el formulario. Una interfaz de escritorio (Tkinter) corre la lectura de precios y el "
            + "navegador en hilos separados para que nunca se congele. Los datos van a CSV y JSON, o a Excel o a una base "
            + "de datos SQL o NoSQL si el cliente lo necesita. También trabajo con Node.js y C# cuando el proyecto lo pide.",
          result: "El cliente fija un precio mínimo y una cantidad. El software revisa 7 servidores de 3 juegos cada minuto, "
            + "decide cuándo vender, prepara la venta y avisa al cliente, que solo confirma. Cada paso queda registrado, y "
            + "cuando algo falla (una sesión caducada, un servidor que deja de comprar) lo informa en vez de fallar en "
            + "silencio.",
          stack: ["Python", "Playwright", "Chrome", "Tkinter", "Hilos", "CSV / JSON"],
          repos: [{ label: "Código en GitHub", href: `${GH}/web-scraping-automation` }],
          loop: { media: "loop-sale", label: "El monitor llega al precio, el cliente acepta en el teléfono, venta completada" },
        },
      ],
    },
    {
      slug: "web-api",
      label: "Integración web y API",
      short: "Web y APIs",
      pitch: "Webs hechas a tu medida, conectadas a todos los servicios con los que funciona tu negocio.",
      intro:
        "Plataformas web a medida e integraciones con APIs: pagos, notificaciones, IA y contratos inteligentes " +
        "trabajando juntos en un solo producto, del primer boceto a producción.",
      video: { media: "web-api-overview", title: "KamasMarket de principio a fin: nueve integraciones de API, contratos inteligentes y un agente de IA, en 115 segundos" },
      projects: [
        {
          title: "Web creada a tu medida",
          status: "Case study",
          summary: "Una web creada a la medida del cliente, pensada para la facilidad de los usuarios y para resolver un "
            + "problema real del mercado.",
          problem: "El cliente pidió un producto completo: una página con registro de usuarios que funcionara como un "
            + "mercado P2P, donde los vendedores publicaran sus productos (en este caso, ítems y moneda de un juego) y los "
            + "compradores compraran y pagaran dentro de la plataforma. La página es la intermediaria de cada intercambio y "
            + "gana una comisión por cada venta.",
          how: "Usé tecnologías pensando en la rapidez y la sencillez que el cliente necesitaba, y en tener mayor control al "
            + "hacer los cambios que pidiera antes de ir a producción. FastAPI para el backend, con Supabase (Postgres) "
            + "como base de datos. Caddy como puerta de entrada en producción: sirve HTTPS y es el único acceso al backend, "
            + "detrás de Cloudflare. Redis, compartido por los procesos del servidor, guarda en caché los listados más "
            + "pesados y mantiene los límites de uso cuando se conectan muchos usuarios a la vez. En el núcleo de cada "
            + "intercambio, un contrato inteligente escrito en Solidity en BNB Chain: el pago se verifica en la blockchain y "
            + "el contrato paga al vendedor o devuelve el dinero al comprador según lo que reporte el backend, sin una "
            + "tercera opción. Un programa aparte, con visión por computadora y OCR y una segunda verificación con IA, "
            + "trabaja por su cuenta coordinado a través de la API, y recibe y entrega los productos dentro del juego "
            + "según el estado de cada pago.",
          result: "Un producto de tres partes trabajando juntas: el contrato inteligente, el software con IA dentro del "
            + "juego y el backend que crea y gestiona las órdenes, muchas a la vez, con cada tarea asignada a un solo bot "
            + "para que nada se haga dos veces. Encima, un agente de IA conectado a la página y a cada orden, para que cada "
            + "usuario sepa siempre dónde están su producto y su dinero. Un flujo constante de compra y venta en un entorno "
            + "seguro.",
          stack: ["FastAPI", "Supabase", "Redis", "Caddy", "Cloudflare", "Solidity", "BNB Chain", "Docker", "DeepSeek API", "Claude API"],
          repos: [
            { label: "Contrato inteligente", href: `${GH}/escrow-smart-contract` },
            { label: "Agente de IA", href: `${GH}/llm-support-agent` },
            { label: "Infraestructura", href: `${GH}/marketplace-infra` },
          ],
          loop: { media: "loop-kamas", label: "KamasMarket: se elige una oferta, el pedido avanza, el contrato paga al vendedor" },
        },
      ],
    },
    {
      slug: "ai-media-shopify",
      label: "IA, Social Media y Shopify",
      short: "Social Media",
      pitch: "Contenido generado con IA: producción con sentido que vende ideas.",
      intro:
        "Producir contenido con IA tiene valor cuando el significado de lo que se quiere transmitir llega a los " +
        "clientes o usuarios de una forma consistente y fácil de comprender, mientras construyes una identidad a " +
        "través de lo que comunicas.",
      video: { media: "media-overview", title: "Cómo se hace el contenido: idea, coherencia, correcciones reales y un presupuesto de menos de 25 dólares, en 143 segundos" },
      projects: [
        {
          title: "IA y Social Media: de la idea al producto",
          status: "Case study",
          summary: "Generar contenido se ha convertido en uno de los sectores de mayor crecimiento de los últimos años. Hoy, "
            + "más allá de lo que se crea, lo que realmente le da valor al contenido es lo que transmite y cómo lo "
            + "entienden aquellos a quienes llega.",
          problem: "Generar contenido es cada vez más fácil, y eso ha hecho que las redes sociales, los medios y las páginas "
            + "web inunden a los usuarios con más información de la que pueden digerir. No es lo mismo vender una idea "
            + "desde tu sitio si hay otros veinte lugares intentando hacer lo mismo. Por eso, hoy más que nunca, lo "
            + "importante no está en el medio que transmite la idea, sino en la idea misma: presentada de forma que sea "
            + "fácil de entender y digerir, y que cree una identidad que los usuarios recuerden a mediano y largo plazo.",
          how: "Todos los videos de este sitio siguen una estructura pensada para transmitir una idea y lo que quiero "
            + "vender. Usé modelos de inteligencia artificial de Google (Gemini Omni y su versión Flash, y Gemini para "
            + "imágenes y voz), Seedance y DaVinci AI, y herramientas de código como Claude Opus 5.5. Esto último es "
            + "importante: un buen resultado sale de una base sólida y de un modelo que acompañe todo el proceso creativo "
            + "durante el desarrollo. El código no reemplaza a la IA: la complementa.",
          result: "Videos que transmiten una intención y una idea. La finalidad de este sitio es mostrar mi portafolio y "
            + "mis capacidades a quienes necesiten construir, mejorar o simplemente encontrar talento para sus proyectos, y "
            + "eso es lo que intento transmitir en cada video: un problema, su solución y cuál es mi papel en todo ello, "
            + "mientras demuestro mis habilidades.",
          stack: ["Gemini Omni", "Gemini (imagen)", "Gemini TTS", "Seedance", "DaVinci AI", "Claude Opus 5.5", "ffmpeg", "Playwright"],
          repos: [{ label: "Código en GitHub", href: `${GH}/ai-media` }],
          loop: { media: "loop-media", label: "La idea, fotogramas coherentes, una corrección real, listo para publicar" },
        },
        {
          title: "Ardea Skin: tienda Shopify diseñada con identidad propia",
          status: "Live demo",
          summary: "Una tienda funcional para una marca ficticia de cuidado de la piel: catálogo real, carrito y pago de "
            + "Shopify en modo de prueba, con un asesor de IA integrado.",
          problem: "Cada cliente quiere algo hecho a su gusto. Muchas tiendas en línea ofrecen funcionalidades útiles, pero "
            + "con un molde hecho para todos. Así nace la necesidad de construir una identidad propia sobre un sitio, que "
            + "represente aquello que el cliente quiere vender a sus usuarios.",
          how: "Para el frontend usé Next.js 16, React 19, TypeScript y Tailwind 4: es la misma app que sirve a este "
            + "portafolio, así que hay un solo código y un solo despliegue. Shopify se encarga del catálogo, el inventario, "
            + "el pago, los pedidos y las imágenes y videos (desde su propio CDN). El agente del chat funciona con Claude "
            + "Haiku 5.5, con costos medidos y límites por visitante para evitar spam. La base de datos, Supabase (Postgres "
            + "gestionado), guarda las conversaciones del chat, el costo en tokens de cada mensaje, los casos escalados y "
            + "la fecha de los últimos informes, para no enviarlos dos veces. Una integración con Telegram permite "
            + "gestionar la tienda desde fuera, con un agente de IA entre los dos.",
          result: "Un sitio diseñado a la medida de un cliente potencial. Los productos son de demostración, pero muestra "
            + "una identidad que se traslada a cada parte de la tienda y a cada producto nuevo, y hace su gestión mucho más "
            + "simple y automatizada sin perder la esencia humana que buscan los usuarios.",
          stack: ["Shopify Storefront API", "Next.js 16", "React 19", "Tailwind 4", "TypeScript", "Claude API", "Supabase", "Telegram"],
          link: { label: "Abrir la tienda", href: store },
          repos: [{ label: "Código en GitHub", href: `${GH}/ardea-skin` }],
          loop: { media: "loop-ardea", label: "Ardea Skin: una identidad en cada página, y la tienda gestionada desde Telegram" },
        },
      ],
    },
  ];

  const hubIntro: HubIntro = {
    eyebrow: "Empieza aquí",
    title: "Cómo pongo la IA a trabajar para ti e integro sus herramientas en tus flujos de trabajo para que seas más productivo.",
    videoTitle: "Cómo encajan los agentes de IA en tu trabajo, en 75 segundos",
    media: "ai-agents-overview",
  };

  const about: About = {
    name: "Iván",
    role: "Ingeniero de IA y desarrollador de automatizaciones",
    bio:
      "Construyo agentes de IA, automatizaciones y el software que los rodea: desde sistemas con LLMs en producción y " +
      "procesos de web scraping hasta tiendas Shopify y servidores Linux que trabajan 24/7. Mido antes de concluir y " +
      "dejo por escrito por qué se tomó cada decisión, para que el cliente sepa qué está pagando.",
    education: [],
    highlights: [
      "Sistemas con LLMs en producción sobre Anthropic y DeepSeek",
      "Shopify headless, Next.js y FastAPI",
      "Bots y automatización con Telegram, webhooks y n8n",
      "Servidores Linux, Docker y redes",
    ],
    skills: ["Claude / APIs de LLMs", "Agentes de IA y herramientas", "Python", "TypeScript", "Next.js", "FastAPI", "Shopify",
      "Web scraping", "Playwright", "Supabase / Postgres", "Docker", "Linux"],
  };

  return { lang: "es", sections, hubIntro, about, ui: UI };
}

const UI: Ui = {
  srTitle: "Iván: agentes de IA, automatización y desarrollo full-stack",
  roleLine: "Ingeniero de IA · desarrollador de automatizaciones",
  allWork: "Todo el trabajo",
  hire: "Contrátame en Workana",
  hireTitle: "¿Tienes un proyecto así?",
  hireBody: "Cuéntame lo que necesitas en Workana y te respondo con un plan y un presupuesto.",
  chooseArea: "Elige un área de trabajo",
  aboutMe: "Sobre mí",
  aboutOf: (name) => `Sobre ${name}`,
  sceneAlt: (name) => `${name} trabajando en un escritorio con tres monitores`,
  portraitAlt: (name) => `Retrato de ${name}`,
  close: "Cerrar",
  education: "Formación",
  highlights: "Lo más destacado",
  skills: "Habilidades",
  introVideo: "Video de presentación",
  explainerVideo: "Video explicativo",
  projects: "Proyectos",
  otherAreas: "Otras áreas",
  areasOfWork: "Áreas de trabajo",
  problem: "El problema",
  how: "Cómo lo construí",
  result: "Resultado",
  status: { "Live demo": "Demo en vivo", "Case study": "Caso de estudio", "In progress": "En curso" },
  screenshotsSoon: "Capturas próximamente",
  videoSoon: "Video explicativo · próximamente",
  onGithub: (label) => `${label}: GitHub`,
  player: { voice: "Voz", subtitles: "Subtítulos", tapForSound: "Toca para activar el sonido", fullScreen: "Pantalla completa", exitFullScreen: "Salir de pantalla completa", off: "No" },
};
