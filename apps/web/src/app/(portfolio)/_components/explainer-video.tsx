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

/** Explainer video with a voice switch (one file per language: browsers can't switch audio tracks inside one
 *  file, except Safari) and a subtitles switch (native text tracks, so they also show in full screen).
 *  Both default to the browser's language; switching voice keeps the position and the play state. */
export function ExplainerVideo({ media, title }: { media: ExplainerMedia; title: string }) {
  const video = useRef<HTMLVideoElement>(null);
  const resume = useRef<{ frac: number; play: boolean } | null>(null);
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

  const changeVoice = (l: Lang) => {
    const el = video.current;
    if (el && l !== voice && el.duration) resume.current = { frac: el.currentTime / el.duration, play: !el.paused };
    setVoiceChoice(l);
  };

  const [hi, lo] = [...v.sources].sort((a, b) => b.height - a.height);
  return (
    <figure>
      <div className="overflow-hidden rounded-2xl border border-line bg-black shadow-[0_30px_80px_-40px_rgba(94,234,212,0.25)]">
        <video
          key={voice} /* a new element per voice: <source> changes alone don't reload a video */
          ref={video}
          controls
          playsInline
          preload="metadata"
          poster={v.poster}
          className="explainer aspect-video w-full"
          aria-label={title}
          onLoadedMetadata={(e) => {
            const r = resume.current;
            if (!r) return;
            resume.current = null;
            const el = e.currentTarget;
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
