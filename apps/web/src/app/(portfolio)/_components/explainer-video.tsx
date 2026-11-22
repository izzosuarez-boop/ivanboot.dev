"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

export type ExplainerMedia = {
  poster: string;
  duration: number;
  sources: { url: string; height: number }[];
  captions: { en: string; es: string };
};

type Lang = "en" | "es" | "off";
const LABEL: Record<Lang, string> = { en: "EN", es: "ES", off: "Off" };

// Browser language without a hydration mismatch: the server renders English, the client corrects it.
const noop = () => () => {};
const browserLang = () => (navigator.language?.toLowerCase().startsWith("es") ? "es" : "en");

/** Explainer video with subtitles the viewer can switch (English / Spanish / off).
 *  Subtitles are native text tracks, so they also show in full screen; the switch drives their mode. */
export function ExplainerVideo({ media, title }: { media: ExplainerMedia; title: string }) {
  const video = useRef<HTMLVideoElement>(null);
  const detected = useSyncExternalStore(noop, browserLang, () => "en" as const);
  const [choice, setChoice] = useState<Lang | null>(null);
  const lang: Lang = choice ?? detected;

  useEffect(() => {
    const el = video.current;
    if (!el) return;
    const apply = () => {
      for (const t of Array.from(el.textTracks)) t.mode = t.language === lang ? "showing" : "disabled";
    };
    apply();
    el.textTracks.addEventListener("addtrack", apply); // tracks can register after the effect runs
    return () => el.textTracks.removeEventListener("addtrack", apply);
  }, [lang]);

  const [hi, lo] = [...media.sources].sort((a, b) => b.height - a.height);
  return (
    <figure>
      <div className="overflow-hidden rounded-2xl border border-line bg-black shadow-[0_30px_80px_-40px_rgba(94,234,212,0.25)]">
        <video
          ref={video}
          controls
          playsInline
          preload="metadata"
          poster={media.poster}
          className="explainer aspect-video w-full"
          aria-label={title}
        >
          {/* wide screens get 1080p, phones and small windows 720p (about half the size) */}
          {lo && <source src={hi.url} type="video/mp4" media="(min-width: 1100px)" />}
          <source src={(lo ?? hi).url} type="video/mp4" />
          <track kind="subtitles" srcLang="en" label="English" src={media.captions.en} default={lang === "en"} />
          <track kind="subtitles" srcLang="es" label="Español" src={media.captions.es} default={lang === "es"} />
        </video>
      </div>
      <figcaption className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
        <span>{title}</span>
        <span className="flex items-center gap-1.5" role="group" aria-label="Subtitles">
          <span className="mr-1 font-mono text-xs uppercase tracking-widest">Subtitles</span>
          {(["en", "es", "off"] as Lang[]).map((l) => (
            <button
              key={l}
              type="button"
              onClick={() => setChoice(l)}
              aria-pressed={lang === l}
              className={`rounded-full border px-2.5 py-0.5 text-xs transition ${
                lang === l ? "border-glow/60 bg-glow/10 text-glow" : "border-line text-muted hover:text-text"
              }`}
            >
              {LABEL[l]}
            </button>
          ))}
        </span>
      </figcaption>
    </figure>
  );
}
