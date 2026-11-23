"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useVideoRecovery } from "@/lib/use-video-recovery";
import { attachSubtitles } from "@/lib/vtt";

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

// iPhone/iPad Safari never lets a page start a video WITH sound by itself: try muted straight away there, so a
// refused attempt can't race the visitor's own tap on play
const isIOS = () =>
  /iP(hone|od|ad)/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

type FsVideo = HTMLVideoElement & { webkitDisplayingFullscreen?: boolean };
const inFullScreen = (el: FsVideo) => !!document.fullscreenElement || !!el.webkitDisplayingFullscreen;

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
  const stage = useRef<HTMLDivElement>(null);
  const idle = useRef<number | undefined>(undefined);
  const resume = useRef<{ frac: number; play: boolean } | null>(null);
  const [muted, setMuted] = useState(false);
  const [cue, setCue] = useState("");
  const [full, setFull] = useState(false);
  const [active, setActive] = useState(false);
  const [paused, setPaused] = useState(true);
  const detected = useSyncExternalStore(noop, browserLang, () => "en" as const);
  // iPhone/iPad: Safari draws its own controls over the picture and takes every tap in its top corners
  // (expand at top left, speaker at top right), so the page's buttons there never got the tap (2026-11-23)
  const ios = useSyncExternalStore(noop, isIOS, () => false);
  const [voiceChoice, setVoiceChoice] = useState<Lang | null>(null);
  const [subsChoice, setSubsChoice] = useState<Subs | null>(null);
  const voices = (Object.keys(media.versions) as Lang[]).filter((l) => media.versions[l]);
  const voice: Lang = voiceChoice ?? (media.versions[detected] ? detected : "en");
  const subs: Subs = subsChoice ?? detected;
  const v = media.versions[voice] ?? media.versions.en;
  // One file, picked on the client and set as the video's src, the way the store's players do it (they always
  // played on the user's iPhone). The <source> list sent in the page's HTML started loading before the page's
  // code ran and failed on reloads on iPhone Safari (2026-11-23, PLAYBOOK E27). Wide screens get 1080p,
  // phones and small windows 720p (about half the size).
  const wide = useSyncExternalStore(noop, () => window.matchMedia("(min-width: 1100px)").matches, () => null);
  const [hi, lo] = [...v.sources].sort((a, b) => b.height - a.height);
  const src = wide === null ? undefined : (wide || !lo ? hi : lo).url;

  // The subtitle tracks are created by script (lib/vtt.ts), never as <track src> children: those made iPhone
  // Safari fail the whole video with error 4 (2026-11-23, PLAYBOOK E28). Runs before the effect below so its
  // first apply() already sees them.
  useEffect(() => {
    const el = video.current;
    if (!el) return;
    const ctrl = new AbortController();
    attachSubtitles(el, [
      { lang: "en", label: "English", url: v.captions.en },
      { lang: "es", label: "Español", url: v.captions.es },
    ], ctrl.signal);
    return () => ctrl.abort();
  }, [voice, v.captions.en, v.captions.es]);

  // Subtitles are drawn by the page (the overlay below), not by the browser: Chrome on some Windows GPUs drops
  // native cues in full screen as soon as its control bar hides (reported 2026-11-22). The chosen track stays
  // "hidden" (loaded, fires cuechange, not painted). Only when the <video> itself goes full screen (Firefox and
  // iPhone, where the page's own full screen button isn't used) does it switch to native "showing".
  useEffect(() => {
    const el = video.current as (HTMLVideoElement & { webkitDisplayingFullscreen?: boolean }) | null;
    if (!el) return;
    let track: TextTrack | null = null;
    const show = () => {
      const c = track?.activeCues;
      setCue(c && c.length ? Array.from(c).map((x) => (x as VTTCue).text).join("\n") : "");
    };
    const apply = () => {
      const nativeFull = document.fullscreenElement === el || !!el.webkitDisplayingFullscreen;
      track?.removeEventListener("cuechange", show);
      track = null;
      for (const t of Array.from(el.textTracks)) {
        const on = t.language === subs;
        t.mode = on ? (nativeFull ? "showing" : "hidden") : "disabled";
        if (on) track = t;
      }
      track?.addEventListener("cuechange", show);
      show();
    };
    apply();
    el.textTracks.addEventListener("addtrack", apply); // tracks can register after the effect runs
    document.addEventListener("fullscreenchange", apply);
    el.addEventListener("webkitbeginfullscreen", apply);
    el.addEventListener("webkitendfullscreen", apply);
    return () => {
      track?.removeEventListener("cuechange", show);
      el.textTracks.removeEventListener("addtrack", apply);
      document.removeEventListener("fullscreenchange", apply);
      el.removeEventListener("webkitbeginfullscreen", apply);
      el.removeEventListener("webkitendfullscreen", apply);
    };
  }, [subs, voice]);

  useEffect(() => {
    const onFull = () => setFull(!!stage.current && document.fullscreenElement === stage.current);
    document.addEventListener("fullscreenchange", onFull);
    return () => {
      document.removeEventListener("fullscreenchange", onFull);
      window.clearTimeout(idle.current);
    };
  }, []);

  // Full screen on the player box (video + subtitles), not on the bare <video>
  const toggleFull = () => {
    const box = stage.current;
    const el = video.current as (HTMLVideoElement & { webkitEnterFullscreen?: () => void }) | null;
    if (!box || !el) return;
    if (document.fullscreenElement) { void document.exitFullscreen().catch(() => {}); return; }
    if (typeof box.requestFullscreen === "function") void box.requestFullscreen().catch(() => {});
    else el.webkitEnterFullscreen?.(); // iPhone: only the video itself can go full screen (native subtitles)
  };

  // Follows the native control bar (shown on pointer movement, hidden ~2.5 s later while playing) so the
  // subtitles move above it instead of being covered
  const wake = () => {
    setActive(true);
    window.clearTimeout(idle.current);
    idle.current = window.setTimeout(() => setActive(false), 2600);
  };
  const sleep = () => { window.clearTimeout(idle.current); setActive(false); };
  const lifted = active || paused;

  // last resort if the browser still refuses the file: reload it under a fresh address (PLAYBOOK E26/E27)
  useVideoRecovery(video, { key: src, wanted: () => autoStarted.has(title) });

  useEffect(() => {
    const el = video.current as FsVideo | null;
    if (!el) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const io = new IntersectionObserver(
      ([e]) => {
        // "fully visible", allowing for a player taller than the viewport on small screens
        const target = Math.min(1, window.innerHeight / e.boundingClientRect.height);
        const fully = e.intersectionRatio >= target * 0.98;
        if (fully && !autoStarted.has(title) && !reduceMotion) {
          autoStarted.add(title);
          const muted = () => {
            el.muted = true;
            setMuted(true);
            // some browsers block even muted autoplay (iPhone in Low Power Mode, data saver); controls still work
            el.play().catch(() => {});
          };
          if (isIOS()) muted();
          else {
            el.muted = false;
            el.play().catch(() => {
              // the visitor may have pressed play meanwhile: don't touch a video that is already playing
              if (el.paused) muted();
            });
          }
        } else if (e.intersectionRatio <= 0.5 && !el.paused && !inFullScreen(el)) {
          // (in full screen the page's copy of the player can read as off screen, iPhone especially)
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

  return (
    <figure>
      {/* Chrome greys out its own full screen button under controlsList="nofullscreen"; hidden here because the
          CSS build drops vendor pseudo-elements it doesn't know (same pitfall as ::cue). React hoists and
          dedupes it across players. */}
      <style href="explainer-video-controls" precedence="default">
        {"video.explainer::-webkit-media-controls-fullscreen-button{display:none}"}
      </style>
      <div
        ref={stage}
        onPointerMove={wake}
        onPointerDown={wake}
        onPointerLeave={sleep}
        className={full
          ? "flex items-center justify-center bg-black"
          : "relative overflow-hidden rounded-2xl border border-line bg-black shadow-[0_30px_80px_-40px_rgba(94,234,212,0.25)]"}
      >
      {/* the 16:9 box: the subtitles sit inside the picture, also when a 5:4 or 21:9 screen letterboxes it */}
      <div className={`@container relative ${full ? "w-[min(100vw,calc(100vh*16/9))]" : "w-full"}`}>
        {!ios && (
        <button
          type="button"
          onClick={toggleFull}
          aria-label={full ? "Exit full screen" : "Full screen"}
          title={full ? "Exit full screen" : "Full screen"}
          className={`absolute right-3 top-3 z-10 grid h-9 w-9 place-items-center rounded-full border border-line bg-night/75 text-text-2 backdrop-blur transition hover:text-glow focus-visible:opacity-100 ${
            lifted ? "opacity-100" : "opacity-0"
          }`}
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            {full
              ? <path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5" />
              : <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />}
          </svg>
        </button>
        )}
        {muted && !ios && (
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
          key={voice} /* a new element per voice: a clean start for the new file and its tracks */
          ref={video}
          src={src}
          controls
          playsInline
          preload="metadata"
          poster={v.poster}
          controlsList="nofullscreen" /* Chrome/Edge: the page's own button replaces it (Firefox keeps its own) */
          className="explainer block aspect-video w-full"
          aria-label={title}
          onDoubleClick={(e) => { e.preventDefault(); toggleFull(); }}
          onVolumeChange={(e) => setMuted(e.currentTarget.muted)}
          onPause={() => setPaused(true)}
          onPlay={(e) => {
            setPaused(false);
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
        />
        {cue && (
          <div
            aria-hidden /* the same text is in the captions file; screen readers get the video's own tracks */
            data-cue
            className="pointer-events-none absolute inset-x-0 flex justify-center px-[11%] text-center transition-[bottom] duration-200"
            style={{ bottom: lifted ? 74 : "4.5%" }}
          >
            {/* sizes match the browser's own rendering (5% of the picture height x 0.72); the hub asks for 50%
                more inside the page, full screen keeps the standard size */}
            <p className={`whitespace-pre-line leading-[1.45] text-white ${
              largeCues && !full ? "text-[max(13px,3.04cqw)]" : "text-[max(11px,2.03cqw)]"
            }`}>
              <span className="bg-[rgba(9,11,14,0.78)] px-[0.35em] py-[0.08em] [box-decoration-break:clone] [-webkit-box-decoration-break:clone]">
                {cue}
              </span>
            </p>
          </div>
        )}
      </div>
      </div>
      {muted && ios && (
        <button
          type="button"
          onClick={() => {
            const el = video.current;
            if (el) { el.muted = false; void el.play().catch(() => {}); }
          }}
          className="mt-3 inline-flex items-center gap-2 rounded-full border border-glow/60 bg-glow/10 px-4 py-2 text-sm text-glow transition hover:bg-glow/20"
        >
          🔊 Tap for sound
        </button>
      )}
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
