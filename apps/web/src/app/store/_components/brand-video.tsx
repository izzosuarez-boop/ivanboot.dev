"use client";

import { useEffect, useRef, useState } from "react";
import { pickSource } from "./howto-video";

type Source = { url: string; width: number; height: number };

/** Muted background loop for the store homepage. Poster only for people who ask for reduced motion. */
export function BrandVideo({ sources, poster }: { sources: Source[]; poster?: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  const [src, setSrc] = useState<string>();

  useEffect(() => {
    const v = ref.current;
    if (!v || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const saveData = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection?.saveData;
    if (saveData) return; // keep the poster on data-saver connections
    setSrc(pickSource(sources, v.clientWidth)?.url);
  }, [sources]);

  return (
    <video
      ref={ref}
      src={src}
      poster={poster}
      autoPlay
      muted
      loop
      playsInline
      preload="none"
      aria-hidden
      className="absolute inset-0 h-full w-full object-cover"
    />
  );
}
