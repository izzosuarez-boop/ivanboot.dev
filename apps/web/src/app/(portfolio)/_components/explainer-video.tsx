"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

type Version = {
  poster: string;
  duration: number;
  sources: { url: string; height: number }[];
  captions: { en: string; es: string };
};
export type ExplainerMedia = { versions: { en: Version; es?: Version } };

type Lang = "en" | "es";
type Subs = Lang | "off";
const LABEL: Record<Subs, string> = { en: "EN", es: "ES", off: "Off" };

// Browser language without a hydration mismatch: the server renders English, the client corrects it.
const noop = () => () => {};
const browserLang = (): Lang => (navigator.language?.toLowerCase().startsWith("es") ? "es" : "en");

function Switch<T extends string>({ label, options, value, onChange }: {
  label: string; options: T[]; value: T; onChange: (v: T) => void;
}) {
  return (
    <span className="flex items-center gap-1.5" role="group" aria-label={label}>
      <span className="mr-1 font-mono text-xs uppercase tracking-widest">{label}</span>
      {options.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => onChange(o)}
          aria-pressed={value === o}
          className={`rounded-full border px-2.5 py-0.5 text-xs transition ${
            value === o ? "border-glow/60 bg-glow/10 text-glow" : "border-line text-muted hover:text-text"
          }`}
        >
          {LABEL[o as Subs]}
        </button>
      ))}
    </span>
  );
}

// Videos that already started by themselves. Module state survives client-side navigation and resets on a
// full reload, which is exactly "autoplay the first time, or after reloading the page".
const autoStarted = new Set<string>();

/** Explainer video with a voice switch (one file per language: browsers can't switch audio tracks inside one
 *  file, except Safari) and a subtitles switch (native text tracks, so they also show in full screen).
 *  Both default to the browser's language; switching voice keeps the position and the play state.
 *  Playback rules (same as the store's how-to video, requested 2026-11-22):
 *   - starts by itself once the whole player is in view, only once per page load;
 *   - pauses when half or less of it is visible, when the visitor leaves the section or the tab;
 *   - after that it only plays again when the visitor presses play;
 *   - only one explainer plays at a time.
 *  Browsers refuse autoplay WITH sound until the visitor has interacted with the page (a direct visit or a
 *  reload), so it tries with sound first and falls back to muted playback plus a "Tap for sound" button. */
export function ExplainerVideo({ media, title, largeCues = false }: {
  media: ExplainerMedia; title: string; largeCues?: boolean; // largeCues: subtitles 50% bigger outside full screen
}) {
  const video = useRef<HTMLVideoElement>(null);
  const resume = useRef<{ frac: number; play: boolean } | null>(null);
  const [muted, setMuted] = useState(false);
  const detected = useSyncExternalStore(noop, browserLang, () => "en" as const);
  const [voiceChoice, setVoiceChoice] = useState<Lang | null>(null);
  const [subsChoice, setSubsChoice] = useState<Subs | null>(null);
  const voices = (Object.keys(media.versions) as Lang[]).filter((l) => media.versions[l]);
  const voice: Lang = voiceChoice ?? (media.versions[detected] ? detected : "en");
  const subs: Subs = subsChoice ?? detected;
  const v = media.versions[voice] ?? media.versions.en;

  useEffect(() => {
    const el = video.current;
    if (!el) return;
    const apply = () => {
      for (const t of Array.from(el.textTracks)) t.mode = t.language === subs ? "showing" : "disabled";
    };
    apply();
    el.textTracks.addEventListener("addtrack", apply); // tracks can register after the effect runs
    return () => el.textTracks.removeEventListener("addtrack", apply);
  }, [subs, voice]);

  useEffect(() => {
    const el = video.current;
    if (!el) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const io = new IntersectionObserver(
      ([e]) => {
        // "fully visible", allowing for a player taller than the viewport on small screens
        const target = Math.min(1, window.innerHeight / e.boundingClientRect.height);
        const fully = e.intersectionRatio >= target * 0.98;
        if (fully && !autoStarted.has(title) && !reduceMotion) {
          autoStarted.add(title);
          el.muted = false;
          el.play().catch(() => {
            el.muted = true;
            setMuted(true);
            el.play().catch(() => {}); // some browsers block even muted autoplay (data saver); controls still work
          });
        } else if (e.intersectionRatio <= 0.5 && !el.paused) {
          el.pause(); // from here on, only the visitor's play button resumes it
        }
      },
      { threshold: [0, 0.25, 0.5, 0.75, 0.9, 0.98, 1] },
    );
    io.observe(el);
    const onHide = () => { if (document.hidden) el.pause(); };
    document.addEventListener("visibilitychange", onHide);
    return () => {
      io.disconnect();
      document.removeEventListener("visibilitychange", onHide);
      // runs when the visitor leaves the section: Next keeps the page alive but hidden, and a hidden
      // <video> would keep playing its sound
      el.pause();
    };
  }, [voice, title]);

  const changeVoice = (l: Lang) => {
    const el = video.current;
    if (el && l !== voice && el.duration) resume.current = { frac: el.currentTime / el.duration, play: !el.paused };
    setVoiceChoice(l);
  };

  const [hi, lo] = [...v.sources].sort((a, b) => b.height - a.height);
  return (
    <figure>
      <div className="relative overflow-hidden rounded-2xl border border-line bg-black shadow-[0_30px_80px_-40px_rgba(94,234,212,0.25)]">
        {muted && (
          <button
            type="button"
            onClick={() => {
              const el = video.current;
              if (el) { el.muted = false; void el.play().catch(() => {}); }
            }}
            className="absolute left-3 top-3 z-10 rounded-full border border-glow/50 bg-night/80 px-3.5 py-1.5 text-xs text-glow backdrop-blur transition hover:bg-night"
          >
            🔊 Tap for sound
          </button>
        )}
        <video
          key={voice} /* a new element per voice: <source> changes alone don't reload a video */
          ref={video}
          controls
          playsInline
          preload="metadata"
          poster={v.poster}
          className={`explainer aspect-video w-full ${largeCues ? "cues-lg" : ""}`}
          aria-label={title}
          onVolumeChange={(e) => setMuted(e.currentTarget.muted)}
          onPlay={(e) => {
            const me = e.currentTarget;
            for (const other of Array.from(document.querySelectorAll<HTMLVideoElement>("video.explainer"))) {
              if (other !== me && !other.paused) other.pause();
            }
          }}
          onLoadedMetadata={(e) => {
            const r = resume.current;
            if (!r) return;
            resume.current = null;
            const el = e.currentTarget;
            el.muted = muted; // after a voice switch, the new element keeps the muted state
            el.currentTime = r.frac * el.duration; // the two voices differ slightly in length: same relative point
            if (r.play) void el.play().catch(() => {});
          }}
        >
          {/* wide screens get 1080p, phones and small windows 720p (about half the size) */}
          {lo && <source src={hi.url} type="video/mp4" media="(min-width: 1100px)" />}
          <source src={(lo ?? hi).url} type="video/mp4" />
          <track kind="subtitles" srcLang="en" label="English" src={v.captions.en} default={subs === "en"} />
          <track kind="subtitles" srcLang="es" label="Español" src={v.captions.es} default={subs === "es"} />
        </video>
      </div>
      <figcaption className="mt-3 flex flex-wrap items-center justify-between gap-x-6 gap-y-3 text-sm text-muted">
        <span>{title}</span>
        <span className="flex flex-wrap items-center gap-x-5 gap-y-2">
          {voices.length > 1 && <Switch label="Voice" options={voices} value={voice} onChange={changeVoice} />}
          <Switch label="Subtitles" options={["en", "es", "off"] as Subs[]} value={subs} onChange={setSubsChoice} />
        </span>
      </figcaption>
    </figure>
  );
}
