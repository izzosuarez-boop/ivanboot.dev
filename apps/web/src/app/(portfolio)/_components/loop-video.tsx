"use client";

import { useEffect, useRef } from "react";

/** A short silent loop for a project card (6 s, made in code: scripts/media/scenes/loop-*.html).
 *  Muted + playsInline, so every browser lets it play by itself, iPhone included. It only runs while on screen,
 *  and stays on its poster for visitors who ask for less motion. No <track>: nothing to read (PLAYBOOK E28). */
export function LoopVideo({ src, poster, label }: { src: string; poster: string; label: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) void el.play().catch(() => {});
      else el.pause();
    }, { threshold: 0.25 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-night shadow-[0_30px_80px_-40px_rgba(94,234,212,0.25)]">
      <video
        ref={ref}
        src={src}
        poster={poster}
        muted
        loop
        playsInline
        preload="metadata"
        aria-label={label}
        className="block aspect-[4/3] w-full"
      />
    </div>
  );
}
