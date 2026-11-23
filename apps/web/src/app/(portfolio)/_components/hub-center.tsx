"use client";

import Image from "next/image";
import { useRef } from "react";
import { about, hubIntro, sections } from "@/content/portfolio";
import portfolioMedia from "@/content/portfolio-media.json";
import { ExplainerVideo, type ExplainerMedia } from "./explainer-video";
import { hubGeometry, useShell, useShown } from "./portfolio-shell";

const MEDIA = portfolioMedia as Record<string, ExplainerMedia>;
// Until the intro video is published to the CDN, local development plays the review render (not in git).
const DEV_INTRO: ExplainerMedia | undefined = process.env.NODE_ENV === "development" ? {
  versions: { en: { poster: "/portfolio/dev/overview-poster.jpg", duration: 71,
    sources: [{ url: "/portfolio/dev/overview-en.mp4", height: 1080 }],
    captions: { en: "/portfolio/dev/none.vtt", es: "/portfolio/dev/none.vtt" } } },
} : undefined;

// The hub: the desk scene inside the circle (and the About card it opens), plus the intro video: beside the
// circle on wide screens, below it on narrow ones.
export function HubCenter() {
  const { vp, leaving, hovered, ringGrown } = useShell();
  const dialog = useRef<HTMLDialogElement>(null);
  // coming back from a section the ring is still large: appear once it has nearly shrunk home
  const shown = useShown(() => (ringGrown() ? 1100 : 150));
  if (!vp) return null;

  const { R, cx, cy, band, wide } = hubGeometry(vp);
  const r = R - band - 16;
  const hint = hovered >= 0 ? sections[hovered].pitch : "Choose an area of work";
  const below = cy + R + 18;
  const intro = MEDIA[hubIntro.media] ?? DEV_INTRO;
  const visible = shown && !leaving;

  return (
    <>
      <div
        className={`absolute z-0 transition-opacity duration-700 ${visible ? "opacity-100" : "opacity-0"}`}
        style={{ left: cx - r, top: cy - r, width: 2 * r, height: 2 * r }}
      >
        {/* soft light behind the scene: monitor glow and desk lamp */}
        <div
          aria-hidden
          className="absolute -inset-[8%] rounded-full opacity-60 blur-3xl"
          style={{ background: "radial-gradient(closest-side at 45% 55%, rgba(94,234,212,0.22), transparent), radial-gradient(closest-side at 75% 30%, rgba(242,180,92,0.18), transparent)" }}
        />
        <button
          type="button"
          onClick={() => dialog.current?.showModal()}
          className="group relative block h-full w-full cursor-pointer overflow-hidden rounded-full outline-none focus-visible:ring-2 focus-visible:ring-glow"
          aria-label={`About ${about.name}`}
        >
          <Image
            src="/portfolio/scene.webp"
            alt={`${about.name} working at a desk with three monitors`}
            fill
            priority
            sizes="(max-width: 640px) 90vw, 700px"
            className="object-cover transition duration-700 group-hover:scale-[1.03]"
            style={{ maskImage: "radial-gradient(closest-side, #000 74%, transparent 100%)" }}
          />
          <span className="absolute bottom-[9%] left-1/2 -translate-x-1/2 rounded-full border border-line bg-night/75 px-4 py-1.5 text-xs text-text-2 backdrop-blur transition group-hover:border-glow/60 group-hover:text-white sm:text-sm">
            About me
          </span>
        </button>
      </div>

      {(below + 24 < vp.h || !wide) && (
        <p
          className={`absolute z-0 text-center text-xs text-muted transition-opacity duration-500 sm:text-sm ${visible ? "" : "opacity-0"}`}
          style={{ top: below, left: cx - R, width: 2 * R }}
        >
          {hint}
        </p>
      )}

      <section
        aria-label="Intro video"
        // its box (and, on narrow screens, the space reserved above it for the circle) must not catch the ring's clicks
        className={`pointer-events-none z-20 transition-opacity duration-700 ${visible ? "opacity-100" : "opacity-0"} ${
          wide ? "absolute flex flex-col justify-center" : "relative px-4 pb-16"
        }`}
        style={wide ? { left: vp.w * 0.53, right: Math.max(32, vp.w * 0.04), top: 76, bottom: 32 }
          : { paddingTop: below + 56 }}
      >
        <div className={`pointer-events-auto ${wide ? "mx-auto w-full max-w-[860px]" : "mx-auto max-w-2xl"}`}>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-glow">{hubIntro.eyebrow}</p>
          <h2 className="mt-3 font-serif text-2xl leading-snug sm:text-3xl xl:text-[2.1rem]">{hubIntro.title}</h2>
          <div className="mt-6">
            {intro ? <ExplainerVideo media={intro} title={hubIntro.videoTitle} />
              : <div className="aspect-video rounded-2xl border border-line bg-ink-2" />}
          </div>
        </div>
      </section>

      <dialog
        ref={dialog}
        className="m-auto w-[min(92vw,640px)] rounded-2xl border border-line bg-ink-2 p-0 text-text backdrop:bg-black/70 backdrop:backdrop-blur-sm"
        onClick={(e) => e.target === dialog.current && dialog.current?.close()}
      >
        <div className="p-6 sm:p-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-serif text-3xl">{about.name}</h2>
              <p className="mt-1 text-sm text-glow">{about.role}</p>
            </div>
            <button type="button" onClick={() => dialog.current?.close()} className="rounded-full border border-line px-3 py-1 text-sm text-muted hover:text-text" aria-label="Close">
              ✕
            </button>
          </div>
          <p className="mt-5 leading-relaxed text-text-2">{about.bio}</p>

          {about.education.length > 0 && (
            <>
              <h3 className="mt-6 font-mono text-xs uppercase tracking-widest text-muted">Education</h3>
              <ul className="mt-3 space-y-2">
                {about.education.map((e) => (
                  <li key={e.title} className="text-sm">
                    <span className="text-text">{e.title}</span> <span className="text-muted">· {e.place} · {e.years}</span>
                  </li>
                ))}
              </ul>
            </>
          )}

          <h3 className="mt-6 font-mono text-xs uppercase tracking-widest text-muted">Highlights</h3>
          <ul className="mt-3 space-y-1.5 text-sm text-text-2">
            {about.highlights.map((h) => (
              <li key={h} className="flex gap-2"><span className="text-lamp">▸</span>{h}</li>
            ))}
          </ul>

          <h3 className="mt-6 font-mono text-xs uppercase tracking-widest text-muted">Skills</h3>
          <ul className="mt-3 flex flex-wrap gap-2">
            {about.skills.map((s) => (
              <li key={s} className="rounded-md border border-line px-2.5 py-1 font-mono text-xs text-text-2">{s}</li>
            ))}
          </ul>
        </div>
      </dialog>
    </>
  );
}
