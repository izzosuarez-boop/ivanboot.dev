"use client";

import Image from "next/image";
import { useRef } from "react";
import { about, sections } from "@/content/portfolio";
import { hubGeometry, useShell, useShown } from "./portfolio-shell";

// The middle of the hub: the desk scene inside the circle, and the About card it opens.
export function HubCenter() {
  const { vp, leaving, hovered, ringGrown } = useShell();
  const dialog = useRef<HTMLDialogElement>(null);
  // coming back from a section the ring is still large: appear once it has nearly shrunk home
  const shown = useShown(() => (ringGrown() ? 1100 : 150));
  if (!vp) return null;

  const { R, cy, band } = hubGeometry(vp);
  const r = R - band - 16;
  const hint = hovered >= 0 ? sections[hovered].pitch : "Choose an area of work";
  const below = cy + R + 18;

  return (
    <>
      <div
        className={`fixed z-0 transition-opacity duration-700 ${shown && !leaving ? "opacity-100" : "opacity-0"}`}
        style={{ left: vp.w / 2 - r, top: cy - r, width: 2 * r, height: 2 * r }}
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

      {below + 24 < vp.h && (
        <p
          className={`fixed inset-x-4 z-0 text-center text-xs text-muted transition-opacity duration-500 sm:text-sm ${shown && !leaving ? "" : "opacity-0"}`}
          style={{ top: below }}
        >
          {hint}
        </p>
      )}

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
