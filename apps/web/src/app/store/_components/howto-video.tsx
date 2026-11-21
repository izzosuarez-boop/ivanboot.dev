"use client";

import { useEffect, useRef, useState } from "react";

type Source = { url: string; width: number; height: number };

/** Smallest source that still covers the rendered width (Shopify serves 1080/720/480). */
export function pickSource(sources: Source[], cssWidth: number): Source | undefined {
  const needed = cssWidth * Math.min(window.devicePixelRatio || 1, 2);
  const asc = [...sources].sort((a, b) => a.width - b.width);
  return asc.find((s) => s.width >= needed) ?? asc[asc.length - 1];
}

/**
 * How-to video behaviour (requested 2026-11-20):
 *  - starts by itself once the whole player is in view (once per page view);
 *  - pauses when half or less of it is visible;
 *  - after that it only plays again when the visitor presses play.
 * Browsers refuse autoplay WITH sound until the visitor has interacted with the page, so we try
 * with sound first and fall back to muted playback plus a "Tap for sound" button.
 */
export function HowToVideo({ sources, poster, label }: { sources: Source[]; poster?: string; label: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  const autoStarted = useRef(false);
  const [src, setSrc] = useState<string>();
  const [muted, setMuted] = useState(false);

  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    setSrc(pickSource(sources, v.clientWidth)?.url);
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const io = new IntersectionObserver(
      ([e]) => {
        // "fully visible", allowing for a player taller than the viewport on small screens
        const visibleTarget = Math.min(1, window.innerHeight / e.boundingClientRect.height);
        const fully = e.intersectionRatio >= visibleTarget * 0.98;
        if (fully && !autoStarted.current && !reduceMotion) {
          autoStarted.current = true;
          v.muted = false;
          v.play().catch(() => {
            v.muted = true;
            setMuted(true);
            v.play().catch(() => {}); // some browsers block even muted autoplay (e.g. data saver) — controls still work
          });
        } else if (e.intersectionRatio <= 0.5 && !v.paused) {
          v.pause(); // from here on, only the visitor's play button resumes it
        }
      },
      { threshold: [0, 0.25, 0.5, 0.75, 0.9, 0.98, 1] },
    );
    io.observe(v);
    return () => io.disconnect();
  }, [sources]);

  return (
    <div className="relative">
      <video
        ref={ref}
        src={src}
        poster={poster}
        controls
        playsInline
        preload="metadata"
        aria-label={label}
        onVolumeChange={(e) => setMuted(e.currentTarget.muted)}
        className="aspect-video w-full rounded-3xl bg-clay object-cover"
      />
      {muted && (
        <button
          type="button"
          onClick={() => {
            const v = ref.current;
            if (v) { v.muted = false; v.play().catch(() => {}); }
          }}
          className="absolute left-4 top-4 rounded-full bg-clay/80 px-4 py-2 text-xs text-sand backdrop-blur transition hover:bg-clay"
        >
          🔊 Tap for sound
        </button>
      )}
    </div>
  );
}
