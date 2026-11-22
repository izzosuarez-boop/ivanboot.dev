"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { storeHref } from "@/lib/site";
import { addToCart } from "../cart-client";

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL ?? "https://api.ivanboot.dev";
const STORE_KEY = "ardea-chat-v1";

type Mode = "skin" | "builder";
type Card = { handle: string; title: string; image: string | null; price: number | null; multi: boolean; soldOut: boolean; url: string };
type Line = { variantId: string; quantity: number; title: string; size: string; image: string | null; handle: string };
type Action =
  | { type: "add_to_cart"; lines: Line[]; result?: { ok: boolean; message?: string } }
  | { type: "product_cards"; cards: Card[] }
  | { type: "escalated"; ref: string };
// The model occasionally leaks tool-call markup like "</parameter>"; never show or resend it.
const stripMarkup = (s: string) => s.replace(/<\/?\s*[A-Za-z][\w:.-]*\b[^<>]*>/g, "").trim();

type Msg = { role: "user" | "assistant" | "notice"; text: string; actions?: Action[]; tools?: string[]; suggestions?: string[] };

// Opening buttons: one per branch, a different wording on every new chat (2026-11-21 request)
const STARTERS: Record<"en" | "es", Record<Mode, string[]>> = {
  en: {
    skin: ["Help me with my skin", "Build me a simple skincare routine", "Which serum suits my skin?", "What helps with redness and sensitivity?", "I have oily skin — where do I start?"],
    builder: ["How is this site built?", "What tech stack powers this store?", "How does this AI chat work?", "How were the product videos made?", "What did it cost to build this demo?"],
  },
  es: {
    skin: ["Ayúdame con mi piel", "Arma una rutina sencilla para mí", "¿Qué sérum le va a mi piel?", "¿Qué ayuda con la rojez y la sensibilidad?", "Tengo la piel grasa, ¿por dónde empiezo?"],
    builder: ["¿Cómo está construido este sitio?", "¿Qué tecnologías usa esta tienda?", "¿Cómo funciona este chat con IA?", "¿Cómo se hicieron los videos de producto?", "¿Cuánto costó construir esta demo?"],
  },
};
const pickOne = (list: string[], avoid?: string) => {
  const pool = list.filter((x) => x !== avoid);
  return pool[Math.floor(Math.random() * pool.length)] ?? list[0];
};

const T = {
  en: {
    open: "Ask Ardea", title: "Ardea Advisor", subtitle: "AI assistant · demo store",
    hello: "Hi! I can help you build a routine for your skin — or explain how this site and this chat were built. What would you like?",
    helloPortfolio: "Hi! I see you're coming from my creator's portfolio. I'm here — ask me anything.",
    skin: "Help me with my skin", builder: "How is this site built?", placeholder: "Ask anything…", send: "Send",
    added: "Added to your bag", viewBag: "View bag", from: "from", soldOut: "Sold out", reference: "Reference",
    tools: { get_live_stock: "checked live stock", add_to_bag: "added to bag", show_products: "showed products", escalate_to_owner: "notified the store team", get_chat_stats: "read live stats" } as Record<string, string>,
    cost: "this chat", reset: "New chat", nudge: "Built with AI — ask me how",
  },
  es: {
    open: "Pregúntale a Ardea", title: "Asesora Ardea", subtitle: "Asistente con IA · tienda demo",
    hello: "¡Hola! Puedo ayudarte a armar una rutina para tu piel, o contarte cómo se construyó este sitio y este chat. ¿Qué prefieres?",
    helloPortfolio: "¡Hola! Veo que vienes del portafolio de mi creador. Estoy aquí, pregúntame lo que quieras.",
    skin: "Ayúdame con mi piel", builder: "¿Cómo está construido este sitio?", placeholder: "Escribe tu pregunta…", send: "Enviar",
    added: "Agregado a tu bolsa", viewBag: "Ver bolsa", from: "desde", soldOut: "Agotado", reference: "Referencia",
    tools: { get_live_stock: "consultó stock en vivo", add_to_bag: "agregó a la bolsa", show_products: "mostró productos", escalate_to_owner: "avisó al equipo", get_chat_stats: "leyó estadísticas en vivo" } as Record<string, string>,
    cost: "este chat", reset: "Nuevo chat", nudge: "Hecho con IA — pregúntame cómo",
  },
};

/** Minimal, safe markdown: escape everything, then allow **bold**, [text](https://…) and simple lists. */
function Markdown({ text }: { text: string }) {
  const inline = (s: string, key: string): ReactNode[] => {
    const out: ReactNode[] = [];
    const re = /\*\*([^*]+)\*\*|\[([^\]]+)\]\((https:\/\/[^)\s]+)\)/g;
    let last = 0, m: RegExpExecArray | null, i = 0;
    while ((m = re.exec(s))) {
      if (m.index > last) out.push(s.slice(last, m.index));
      if (m[1]) out.push(<strong key={`${key}b${i++}`}>{m[1]}</strong>);
      else out.push(<a key={`${key}a${i++}`} href={m[3]} target={m[3].includes("ivanboot.dev") ? undefined : "_blank"} rel="noopener noreferrer" className="underline underline-offset-2">{m[2]}</a>);
      last = m.index + m[0].length;
    }
    if (last < s.length) out.push(s.slice(last));
    return out;
  };
  const blocks: ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  const flush = () => {
    if (!list) return;
    const L = list.ordered ? "ol" : "ul";
    blocks.push(<L key={`l${blocks.length}`} className={`my-1 space-y-1 pl-5 ${list.ordered ? "list-decimal" : "list-disc"}`}>{list.items.map((it, j) => <li key={j}>{inline(it, `li${blocks.length}-${j}`)}</li>)}</L>);
    list = null;
  };
  text.split("\n").forEach((raw, idx) => {
    const line = raw.trimEnd();
    const ul = line.match(/^\s*[-*]\s+(.*)/), ol = line.match(/^\s*\d+[.)]\s+(.*)/);
    if (ul || ol) {
      const ordered = Boolean(ol);
      if (!list || list.ordered !== ordered) { flush(); list = { ordered, items: [] }; }
      list.items.push((ul ?? ol)![1]);
    } else {
      flush();
      if (line.trim()) blocks.push(<p key={`p${idx}`} className="my-1">{inline(line, `p${idx}`)}</p>);
    }
  });
  flush();
  return <>{blocks}</>;
}

export function AgentChat() {
  const router = useRouter();
  const [lang, setLang] = useState<"en" | "es">("en");
  const t = T[lang];
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [convId, setConvId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);
  const [ref, setRef] = useState<string | null>(null);
  const [cost, setCost] = useState(0);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [starters, setStarters] = useState<Record<Mode, string>>({ skin: T.en.skin, builder: T.en.builder });
  const endRef = useRef<HTMLDivElement>(null);

  const newStarters = (l: "en" | "es", prev?: Record<Mode, string>) =>
    setStarters({ skin: pickOne(STARTERS[l].skin, prev?.skin), builder: pickOne(STARTERS[l].builder, prev?.builder) });

  // restore + language + ?ref (visitors coming from Upwork start in "how it's built")
  useEffect(() => {
    const l = navigator.language?.toLowerCase().startsWith("es") ? "es" : "en";
    setLang(l);
    newStarters(l); // random wording, picked after mount so server and client HTML match
    try {
      const saved = JSON.parse(sessionStorage.getItem(STORE_KEY) || "null");
      if (saved) { setMsgs(saved.msgs ?? []); setConvId(saved.convId ?? null); setMode(saved.mode ?? null); setCost(saved.cost ?? 0); setRef(saved.ref ?? null); }
      const q = new URLSearchParams(location.search);
      const r = q.get("ref");
      // ?chat=1 (the portfolio's "Live demo" button): open the chat at once, greet the visitor as coming from the
      // portfolio and leave both options to them instead of preselecting "how it's built"
      const openChat = q.get("chat") === "1";
      if (r) { setRef(r.slice(0, 40)); if (!saved?.mode && !openChat && /upwork|workana|portfolio/i.test(r)) setMode("builder"); }
      if (openChat) setOpen(true);
    } catch { /* storage may be blocked — chat still works */ }
  }, []);
  useEffect(() => {
    try { sessionStorage.setItem(STORE_KEY, JSON.stringify({ msgs: msgs.slice(-40), convId, mode, cost, ref })); } catch {}
  }, [msgs, convId, mode, cost, ref]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs, busy, open]);

  async function runActions(actions: Action[]) {
    for (const a of actions) {
      if (a.type !== "add_to_cart") continue;
      let ok = true, message: string | undefined;
      for (const l of a.lines) {
        const r = await addToCart(l.variantId, l.quantity);
        if (!r.ok) { ok = false; message = r.message; } else if (r.message) message = r.message;
      }
      a.result = { ok, message };
      if (ok) router.refresh(); // bag counter in the header
    }
    return actions;
  }

  async function send(text: string, chosenMode: Mode | null = mode) {
    const clean = stripMarkup(text);
    if (!clean || busy) return;
    setMsgs((m) => [...m, { role: "user", text: clean }]);
    setInput("");
    setBusy(true);
    try {
      const res = await fetch(`${AGENT_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: clean, conversation_id: convId, mode: chosenMode, ref }),
      });
      const data = await res.json();
      if (!res.ok) { setMsgs((m) => [...m, { role: "notice", text: data.error ?? "Something went wrong." }]); return; }
      setConvId(data.conversation_id);
      setCost(data.usage?.cost_usd ?? 0);
      const actions = await runActions(data.actions ?? []);
      const branch: Mode = (data.mode as Mode) ?? chosenMode ?? "skin";
      let suggestions: string[] = (data.suggestions ?? []).map(stripMarkup).filter(Boolean).slice(0, 2);
      if (suggestions.length < 2) { // always offer two options from the current branch
        const pool = STARTERS[lang][branch].filter((s) => s !== clean && !suggestions.includes(s));
        while (suggestions.length < 2 && pool.length) suggestions = [...suggestions, pool.splice(Math.floor(Math.random() * pool.length), 1)[0]];
      }
      setMsgs((m) => [...m, { role: "assistant", text: data.reply, actions, tools: data.tools_used, suggestions }]);
    } catch {
      setMsgs((m) => [...m, { role: "notice", text: lang === "es" ? "No pude conectar con el asistente. Inténtalo de nuevo." : "Couldn't reach the assistant. Please try again." }]);
    } finally {
      setBusy(false);
    }
  }

  function pick(m: Mode) {
    setMode(m);
    send(starters[m], m);
  }

  function reset() {
    setMsgs([]); setConvId(null); setCost(0); setMode(null);
    newStarters(lang, starters); // a new chat gets new wordings for both branches
  }

  const lastAssistant = (() => { for (let i = msgs.length - 1; i >= 0; i--) if (msgs[i].role !== "user") return i; return -1; })();

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-clay px-5 py-3.5 text-sm text-sand shadow-xl shadow-clay/20 transition hover:bg-sage-dark"
          aria-label={t.open}
        >
          <span aria-hidden>✦</span> {t.open}
          {ref && mode === "builder" && msgs.length === 0 && (
            <span className="absolute -top-9 right-0 whitespace-nowrap rounded-full bg-sand px-3 py-1 text-xs text-clay shadow">{t.nudge}</span>
          )}
        </button>
      )}

      {open && (
        <section
          role="dialog"
          aria-label={t.title}
          className="fixed inset-0 z-50 flex flex-col bg-sand text-clay sm:inset-auto sm:bottom-5 sm:right-5 sm:h-[600px] sm:max-h-[calc(100vh-2.5rem)] sm:w-[400px] sm:rounded-3xl sm:border sm:border-sand-2 sm:shadow-2xl sm:shadow-clay/20"
        >
          <header className="flex items-center justify-between border-b border-sand-2 px-5 py-4">
            <div>
              <p className="font-serif text-lg leading-tight">{t.title}</p>
              <p className="text-[11px] text-clay-muted">{t.subtitle}</p>
            </div>
            <div className="flex items-center gap-2">
              {msgs.length > 0 && <button type="button" onClick={reset} className="rounded-full px-2 py-1 text-xs text-clay-muted hover:bg-sand-2">{t.reset}</button>}
              <button type="button" onClick={() => setOpen(false)} className="rounded-full px-2 py-1 text-lg leading-none text-clay-muted hover:bg-sand-2" aria-label="Close">×</button>
            </div>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4 text-[14px] leading-relaxed">
            <div className="max-w-[88%] rounded-2xl rounded-tl-sm bg-white/70 px-4 py-3">{ref && /portfolio/i.test(ref) ? t.helloPortfolio : t.hello}</div>
            {msgs.length === 0 && (
              <div className="flex flex-wrap gap-2">
                {(["skin", "builder"] as Mode[]).map((m) => (
                  <button key={m} type="button" data-mode={m} onClick={() => pick(m)}
                    className={`rounded-full border px-3.5 py-2 text-[13px] transition hover:border-clay ${mode === m ? "border-clay bg-clay text-sand" : "border-sand-2 bg-white/50"}`}>
                    {starters[m]}
                  </button>
                ))}
              </div>
            )}

            {msgs.map((m, i) => m.role === "user" ? (
              <div key={i} className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm bg-clay px-4 py-2.5 text-sand">{m.text}</div>
            ) : m.role === "notice" ? (
              <p key={i} className="rounded-xl bg-blush/30 px-3 py-2 text-xs text-clay">{m.text}</p>
            ) : (
              <div key={i} className="max-w-[92%] space-y-2">
                {m.text.trim() && <div className="rounded-2xl rounded-tl-sm bg-white/70 px-4 py-3"><Markdown text={m.text} /></div>}
                {m.actions?.map((a, j) => a.type === "product_cards" ? (
                  <div key={j} className="flex gap-2 overflow-x-auto pb-1">
                    {a.cards.map((c) => (
                      <Link key={c.handle} href={storeHref(`/products/${c.handle}`)} className="w-36 shrink-0 overflow-hidden rounded-2xl border border-sand-2 bg-white/60 transition hover:border-clay-muted">
                        <div className="relative aspect-square bg-sand-2">{c.image && <Image src={c.image} alt={c.title} fill sizes="144px" className="object-cover" />}</div>
                        <div className="p-2.5 text-xs">
                          <p className="font-medium leading-snug">{c.title}</p>
                          <p className="mt-0.5 text-clay-muted">{c.soldOut ? t.soldOut : c.price != null ? `${c.multi ? t.from + " " : ""}$${c.price.toFixed(2)}` : ""}</p>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : a.type === "add_to_cart" ? (
                  <div key={j} className={`rounded-2xl border px-3 py-2.5 text-xs ${a.result?.ok === false ? "border-blush bg-blush/20" : "border-sage/50 bg-sage/10"}`}>
                    <p className="font-medium">{a.result?.ok === false ? (a.result.message ?? "—") : `✓ ${t.added}`}</p>
                    <ul className="mt-1 text-clay-muted">{a.lines.map((l) => <li key={l.variantId}>{l.quantity} × {l.title} · {l.size}</li>)}</ul>
                    {a.result?.ok !== false && <Link href={storeHref("/cart")} className="mt-1.5 inline-block underline underline-offset-2">{t.viewBag} →</Link>}
                    {a.result?.message && a.result.ok && <p className="mt-1 text-clay-muted">{a.result.message}</p>}
                  </div>
                ) : (
                  <p key={j} className="inline-block rounded-full bg-sage/15 px-3 py-1 text-xs text-sage-dark">{t.reference}: <b>{a.ref}</b></p>
                ))}
                {m.tools && m.tools.length > 0 && (
                  <p className="text-[11px] text-clay-muted">⚙ {[...new Set(m.tools)].map((x) => t.tools[x] ?? x).join(" · ")}</p>
                )}
                {i === lastAssistant && !busy && m.suggestions && m.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-2 pt-1" data-testid="suggestions">
                    {m.suggestions.map(stripMarkup).filter(Boolean).map((s) => (
                      <button key={s} type="button" onClick={() => send(s)}
                        className="rounded-full border border-sand-2 bg-white/50 px-3.5 py-1.5 text-left text-[13px] transition hover:border-clay">
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {busy && <div className="flex w-16 gap-1 rounded-2xl bg-white/70 px-4 py-3" aria-label="typing">{[0, 1, 2].map((d) => <span key={d} className="h-1.5 w-1.5 animate-bounce rounded-full bg-clay-muted" style={{ animationDelay: `${d * 120}ms` }} />)}</div>}
            <div ref={endRef} />
          </div>

          <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="border-t border-sand-2 p-3">
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value.slice(0, 800))}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
                rows={1}
                placeholder={t.placeholder}
                className="max-h-28 min-h-[44px] flex-1 resize-none rounded-2xl border border-sand-2 bg-white/70 px-4 py-2.5 text-[14px] outline-none focus:border-clay-muted"
              />
              <button type="submit" disabled={busy || !input.trim()} className="h-11 rounded-full bg-clay px-4 text-sm text-sand transition hover:bg-sage-dark disabled:opacity-40">{t.send}</button>
            </div>
            <p className="mt-2 text-center text-[10px] text-clay-muted">Claude Haiku 5.5 · {t.cost}: ${cost.toFixed(4)}</p>
          </form>
        </section>
      )}
    </>
  );
}
