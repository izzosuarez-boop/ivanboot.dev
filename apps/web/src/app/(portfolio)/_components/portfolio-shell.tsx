"use client";

// The hub circle and the transitions between the hub and its sections.
//
// The circle lives in the (portfolio) layout, so it survives navigation and every move is one continuous
// animation of four numbers: rotation, radius, center height and band width.
//   hub      → a screen-sized ring, section 0 at the top, the scene in the middle
//   section  → the same ring, rotated so the section sits at the top and grown so that only its arc (plus a
//              hint of the neighbours) shows as the page header: the section is a sub-area of the circle
// Entering: the ring turns the chosen segment to the top, then grows into the header.
// Back: the section fades, then the ring shrinks back slowly while turning back to its starting angle.

import { createContext, useCallback, useContext, useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { sections } from "@/content/portfolio";
import { site } from "@/lib/site";

type Ring = { rot: number; R: number; cx: number; cy: number; band: number };
type Viewport = { w: number; h: number };

const STEP = 360 / sections.length;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const smooth = (lo: number, hi: number, x: number) => {
  const t = clamp((x - lo) / (hi - lo), 0, 1);
  return t * t * (3 - 2 * t);
};
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Hub layout (2026-11-22): on wide screens the circle with the scene sits in the left half and the intro video in
// the right half; on narrow screens the circle is on top and the video below it (the page scrolls).
export const isWideHub = ({ w, h }: Viewport) => w >= 1024 && w >= h * 1.15;

export function hubGeometry(vp: Viewport) {
  const { w, h } = vp;
  const wide = isWideHub(vp);
  const D = wide ? Math.min(w * 0.46 - 24, h - 120, 860) : Math.min(w - 24, h * 0.62, 980);
  const R = D / 2;
  return {
    R,
    cx: wide ? w * 0.26 : w / 2,
    cy: wide ? Math.max(76 + R, h / 2 + 22) : 76 + R,
    band: clamp(D * 0.085, 40, 74),
    wide,
  };
}

export function sectionGeometry({ w }: Viewport) {
  const R = Math.max(w * 0.75, 300);
  const top = w < 640 ? 64 : 22;
  return { R, cx: w / 2, cy: top + R, band: w < 640 ? 46 : 64 };
}

function target(vp: Viewport, index: number, rot: number): Ring {
  const { R, cx, cy, band } = index < 0 ? hubGeometry(vp) : sectionGeometry(vp);
  const base = index < 0 ? 0 : -index * STEP;
  // nearest equivalent angle, so the ring always takes the short way round
  const r = base + 360 * Math.round((rot - base) / 360);
  return { rot: r, R, cx, cy, band };
}

type Ctx = {
  go: (slug: string | null) => void;
  ringGrown: () => boolean;
  leaving: boolean;
  vp: Viewport | null;
  hovered: number;
};
const ShellContext = createContext<Ctx>({ go: () => {}, ringGrown: () => false, leaving: false, vp: null, hovered: -1 });
export const useShell = () => useContext(ShellContext);

// True `delay` ms after the page is shown. Next keeps visited pages alive but hidden (React Activity), so a
// CSS entrance animation would not replay when coming back; effects do re-run on every show.
export function useShown(delay: number | (() => number)) {
  const [shown, setShown] = useState(false);
  const delayRef = useRef(delay);
  useEffect(() => {
    delayRef.current = delay; // latest closure (the first render may not know the viewport yet)
  });
  useEffect(() => {
    const d = typeof delayRef.current === "function" ? delayRef.current() : delayRef.current;
    const t = setTimeout(() => setShown(true), d);
    return () => {
      clearTimeout(t);
      setShown(false);
    };
  }, []);
  return shown;
}

export function PortfolioShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const slug = pathname.split("/")[1] || null;
  const index = slug ? sections.findIndex((s) => s.slug === slug) : -1;

  const [vp, setVp] = useState<Viewport | null>(null);
  const [ring, setRing] = useState<Ring | null>(null);
  // the page we are leaving fades out; as soon as the next page is mounted (new pathname) it shows again
  const [leavingFrom, setLeavingFrom] = useState<string | null>(null);
  const leaving = leavingFrom === pathname;
  const [hovered, setHovered] = useState(-1);
  const ringRef = useRef<Ring | null>(null);
  const busy = useRef(false);
  const frame = useRef(0);
  const wrap = useRef<HTMLDivElement>(null);

  const apply = useCallback((r: Ring) => {
    ringRef.current = r;
    setRing(r);
  }, []);

  const tween = useCallback(
    (to: Ring, ms: number) =>
      new Promise<void>((resolve) => {
        cancelAnimationFrame(frame.current);
        const from = ringRef.current ?? to;
        if (ms <= 0 || matchMedia("(prefers-reduced-motion: reduce)").matches) {
          apply(to);
          return resolve();
        }
        const t0 = performance.now();
        const step = (now: number) => {
          const k = ease(Math.min(1, (now - t0) / ms));
          apply({
            rot: from.rot + (to.rot - from.rot) * k,
            R: from.R + (to.R - from.R) * k,
            cx: from.cx + (to.cx - from.cx) * k,
            cy: from.cy + (to.cy - from.cy) * k,
            band: from.band + (to.band - from.band) * k,
          });
          if (k < 1) frame.current = requestAnimationFrame(step);
          else resolve();
        };
        frame.current = requestAnimationFrame(step);
      }),
    [apply],
  );

  // every destination is one click away from anywhere: prefetch them all
  useEffect(() => {
    router.prefetch("/");
    sections.forEach((s) => router.prefetch(`/${s.slug}`));
  }, [router]);

  // viewport size
  useEffect(() => {
    const read = () => setVp({ w: window.innerWidth, h: window.innerHeight });
    read();
    window.addEventListener("resize", read);
    return () => window.removeEventListener("resize", read);
  }, []);

  // keep the ring on its target when nothing is animating (first paint, resize, browser back/forward)
  const firstPaint = useRef(true);
  useEffect(() => {
    if (!vp || busy.current) return;
    const to = target(vp, index, ringRef.current?.rot ?? 0);
    if (firstPaint.current || !ringRef.current) {
      firstPaint.current = false;
      apply(to);
    } else {
      void tween(to, 1100);
    }
  }, [vp, index, apply, tween]);

  // in a section the ring header scrolls away with the page; so does the hub circle on narrow screens, where the
  // intro video sits below it
  const scrolls = index >= 0 || (vp !== null && !isWideHub(vp));
  useEffect(() => {
    const onScroll = () => {
      if (wrap.current && !busy.current) {
        wrap.current.style.transform = scrolls ? `translateY(${-window.scrollY}px)` : "";
      }
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [scrolls]);

  const go = useCallback(
    async (next: string | null) => {
      if (busy.current || !vp) return;
      const nextIndex = next ? sections.findIndex((s) => s.slug === next) : -1;
      if (nextIndex === index) return;
      busy.current = true;
      const path = next ? `/${next}` : "/";
      const resetScroll = () => {
        window.scrollTo(0, 0);
        if (wrap.current) wrap.current.style.transform = "";
      };
      try {
        if (index < 0) {
          // hub → section: turn the segment to the top, then grow into the header (moving to the middle)
          setLeavingFrom(pathname);
          resetScroll();
          await tween({ ...ringRef.current!, rot: target(vp, nextIndex, ringRef.current!.rot).rot }, 750);
          router.push(path, { scroll: false });
          await tween(target(vp, nextIndex, ringRef.current!.rot), 1000);
        } else if (nextIndex < 0) {
          // section → hub: fade the page, then shrink back slowly while turning back to the start
          setLeavingFrom(pathname);
          await wait(350);
          resetScroll();
          router.push(path, { scroll: false });
          await tween(target(vp, -1, ringRef.current!.rot), 1800);
        } else {
          // section → neighbouring section: slide along the ring
          setLeavingFrom(pathname);
          await wait(300);
          resetScroll();
          router.push(path, { scroll: false });
          await tween(target(vp, nextIndex, ringRef.current!.rot), 900);
        }
      } finally {
        busy.current = false;
        setLeavingFrom(null);
      }
    },
    [vp, index, pathname, router, tween],
  );

  const ringGrown = useCallback(
    () => Boolean(vp && ringRef.current && ringRef.current.R > hubGeometry(vp).R * 1.15),
    [vp],
  );

  return (
    <ShellContext.Provider value={{ go, ringGrown, leaving, vp, hovered }}>
      <div className="relative flex min-h-svh flex-1 flex-col bg-night text-text">
        <TopBar index={index} go={go} />
        <div ref={wrap} className="pointer-events-none fixed inset-0 z-10 will-change-transform">
          {vp && ring && <RingSvg vp={vp} ring={ring} active={index} onHover={setHovered} go={go} />}
        </div>
        {children}
      </div>
    </ShellContext.Provider>
  );
}

function TopBar({ index, go }: { index: number; go: (s: string | null) => void }) {
  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-30 flex items-start justify-between gap-3 px-4 py-3 sm:px-6 sm:py-4">
      {index < 0 ? (
        <div className="pointer-events-auto leading-tight">
          <p className="font-serif text-lg text-text sm:text-xl">{site.name}</p>
          <p className="text-xs text-muted sm:text-sm">AI engineer · automation developer</p>
        </div>
      ) : (
        <Link
          href="/"
          onClick={(e) => {
            e.preventDefault();
            go(null);
          }}
          className="pointer-events-auto inline-flex items-center gap-2 rounded-full border border-line bg-night/80 px-4 py-2 text-sm text-text backdrop-blur transition hover:border-glow/60 hover:text-white"
        >
          <span aria-hidden>←</span> All work
        </Link>
      )}
      {site.upworkUrl && (
        <a
          href={site.upworkUrl}
          target="_blank"
          rel="noopener"
          className="pointer-events-auto rounded-full bg-glow px-4 py-2 text-sm font-medium text-night shadow-[0_0_24px_-6px_var(--glow)] transition hover:brightness-110"
        >
          Hire me on Upwork
        </a>
      )}
    </header>
  );
}

// ── the ring ──────────────────────────────────────────────────────────────────────────────────────────

const rad = (deg: number) => (deg * Math.PI) / 180;
function pt(cx: number, cy: number, r: number, deg: number) {
  return [cx + r * Math.sin(rad(deg)), cy - r * Math.cos(rad(deg))] as const;
}
function arc(cx: number, cy: number, r: number, a: number, b: number, clockwise = true) {
  const [x0, y0] = pt(cx, cy, r, clockwise ? a : b);
  const [x1, y1] = pt(cx, cy, r, clockwise ? b : a);
  return `M${x0},${y0} A${r},${r} 0 ${Math.abs(b - a) > 180 ? 1 : 0} ${clockwise ? 1 : 0} ${x1},${y1}`;
}
function sector(cx: number, cy: number, R: number, r: number, a: number, b: number) {
  const [ax, ay] = pt(cx, cy, R, a);
  const [bx, by] = pt(cx, cy, R, b);
  const [cx2, cy2] = pt(cx, cy, r, b);
  const [dx, dy] = pt(cx, cy, r, a);
  const large = b - a > 180 ? 1 : 0;
  return `M${ax},${ay} A${R},${R} 0 ${large} 1 ${bx},${by} L${cx2},${cy2} A${r},${r} 0 ${large} 0 ${dx},${dy} Z`;
}

function RingSvg({ vp, ring, active, onHover, go }: {
  vp: Viewport; ring: Ring; active: number; onHover: (i: number) => void; go: (s: string | null) => void;
}) {
  const uid = useId().replace(/:/g, "");
  const { rot, R, cx, cy, band } = ring;
  const rIn = R - band;
  const rMid = R - band / 2;
  const gap = ((3 / R) * 180) / Math.PI; // ~3px between segments at any size
  const compact = R < 250;
  const fs = clamp(band * 0.19, 10, 13);

  // 0 = hub circle, 1 = section header. As the ring grows, everything below the header fades out, so the
  // sides of the circle never cross the page content on narrow screens.
  const hubR = hubGeometry(vp).R;
  const sec = sectionGeometry(vp);
  const k = clamp((R - hubR) / (sec.R - hubR), 0, 1);
  const fadeAt = vp.h + 300 + (sec.cy - sec.R + sec.band + (vp.w < 640 ? 120 : 220) - vp.h - 300) * k;
  const mask = k > 0 ? `linear-gradient(to bottom, #000 ${fadeAt}px, transparent ${fadeAt + 140}px)` : undefined;

  // dial ticks just outside the band: every 6°, longer every 30°
  let ticks = "";
  for (let k = 0; k < 60; k++) {
    const d = rot + k * 6;
    const long = k % 5 === 0;
    const [x0, y0] = pt(cx, cy, R + 6, d);
    const [x1, y1] = pt(cx, cy, R + (long ? 14 : 10), d);
    ticks += `M${x0},${y0}L${x1},${y1}`;
  }

  return (
    <svg width={vp.w} height={vp.h} className="absolute inset-0" style={{ maskImage: mask, WebkitMaskImage: mask }}>
      <title>Areas of work</title>
      <circle cx={cx} cy={cy} r={R + 10} fill="none" stroke="var(--line)" strokeWidth={1} opacity={0.7} />
      <path d={ticks} stroke="var(--muted)" strokeWidth={1} opacity={0.45} />
      <circle cx={cx} cy={cy} r={rIn - 9} fill="none" stroke="var(--line)" strokeWidth={1} opacity={0.8} />

      {sections.map((s, i) => {
        const c = rot + i * STEP;
        const a = c - STEP / 2 + gap;
        const b = c + STEP / 2 - gap;
        // top half: text along the clockwise arc; bottom half: along the reversed arc so it stays upright.
        // Near the horizontal both fade out for an instant instead of overlapping.
        const up = smooth(0.06, 0.3, Math.cos(rad(c)));
        const down = smooth(0.06, 0.3, -Math.cos(rad(c)));
        const isActive = i === active;
        const label = compact ? s.short : (s.ring ?? s.label);
        const num = String(i + 1).padStart(2, "0");
        const labelArc = (b - a) * 0.96;
        const text = (id: string, opacity: number) =>
          opacity > 0.01 && (
            <text
              opacity={opacity}
              fontSize={fs}
              dominantBaseline="central"
              className="select-none uppercase"
              style={{ letterSpacing: "0.14em", fontFamily: "var(--font-geist-sans)" }}
            >
              <textPath href={`#${id}`} startOffset="50%" textAnchor="middle">
                {!compact && <tspan fill="var(--glow)" style={{ fontFamily: "var(--font-geist-mono)" }}>{num}  </tspan>}
                <tspan className="ring-label" fill={isActive ? "#ffffff" : "var(--text-2)"}>{label}</tspan>
              </textPath>
            </text>
          );
        return (
          <a
            key={s.slug}
            href={`/${s.slug}`}
            aria-label={s.label}
            aria-current={isActive ? "page" : undefined}
            className={`ring-seg cursor-pointer outline-none ${
              k > 0.3 && Math.cos(rad(c)) < 0.3 ? "pointer-events-none" : "pointer-events-auto" // faded parts don't catch clicks
            }`}
            data-active={isActive || undefined}
            onMouseEnter={() => onHover(i)}
            onMouseLeave={() => onHover(-1)}
            onFocus={() => onHover(i)}
            onBlur={() => onHover(-1)}
            onClick={(e) => {
              e.preventDefault();
              go(s.slug);
            }}
          >
            <path className="ring-band" d={sector(cx, cy, R, rIn, a, b)} />
            {isActive && <path d={arc(cx, cy, R - 1, a, b)} fill="none" stroke="var(--glow)" strokeWidth={2} />}
            <path id={`${uid}-a${i}`} d={arc(cx, cy, rMid, c - labelArc / 2, c + labelArc / 2, true)} fill="none" />
            <path id={`${uid}-b${i}`} d={arc(cx, cy, rMid, c - labelArc / 2, c + labelArc / 2, false)} fill="none" />
            {text(`${uid}-a${i}`, up)}
            {text(`${uid}-b${i}`, down)}
          </a>
        );
      })}
    </svg>
  );
}
