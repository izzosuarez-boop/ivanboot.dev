import { useEffect, type RefObject } from "react";

/**
 * Last resort when the browser still refuses a video: reload it under a fresh address (nothing cached can
 * match it), at most twice per page. Fires when every source fails (or the video itself errors), or when
 * not a single byte has arrived 3 s after play. A slow but moving download (progress events) is left alone.
 * Works with a src attribute or with <source> children.
 *
 * `key`: re-arm when the file changes (a new src, a new voice); `wanted`: whether it should start playing
 * after the reload even if it is paused right now (e.g. its autoplay already fired); `note`: debug log.
 */
export function useVideoRecovery(
  ref: RefObject<HTMLVideoElement | null>,
  { key, wanted, note }: { key: unknown; wanted?: () => boolean; note?: (s: string) => void },
) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const log = (s: string) => note?.(s);
    const WAIT = 3000;
    let timer: number | undefined;
    let tries = 0;
    let moved = false;
    const sources = Array.from(el.querySelectorAll("source"));
    const hasFile = () => !!el.getAttribute("src") || sources.length > 0;
    const fresh = (u: string, tag: string) =>
      /[?&]r=/.test(u) ? u.replace(/([?&])r=[^&]*/, `$1${tag}`) : `${u}${u.includes("?") ? "&" : "?"}${tag}`;

    const reload = (why: string) => {
      window.clearTimeout(timer);
      if (tries >= 2) { log(`${why}: giving up (rs=${el.readyState} ns=${el.networkState})`); return; }
      tries++;
      const play = !el.paused || !!wanted?.();
      const at = el.currentTime;
      log(`${why}: reloading under a fresh address (${tries}/2)`);
      const tag = `r=${Date.now().toString(36)}`;
      const own = el.getAttribute("src");
      if (own) el.src = fresh(own, tag);
      else for (const s of sources) s.src = fresh(s.getAttribute("src") ?? "", tag);
      el.load();
      if (at) el.currentTime = at;
      if (play) el.play().catch((err) => log(`play after reload refused: ${err?.name}`));
    };

    // every source gone (the last <source> carries no media condition) or the video's own src failed
    const refused = () => el.networkState === 3 && el.readyState === 0 && hasFile();
    const onErr = () => window.setTimeout(() => { if (refused()) reload("every source refused"); }, 0);
    const last = sources.at(-1);
    last?.addEventListener("error", onErr);
    el.addEventListener("error", onErr);
    // refused before this ran? Checked a moment later: a freshly mounted <video> also reads networkState 3
    // for an instant before it starts loading (reported by ?vdebug on the Spanish voice switch)
    const early = window.setTimeout(() => { if (refused()) reload("every source refused"); }, 1500);

    const arm = () => { window.clearTimeout(timer); moved = false; timer = window.setTimeout(check, WAIT); };
    function check() {
      if (el!.paused || el!.readyState >= 2) return;
      if (moved) { arm(); return; } // data is coming, just slowly
      reload(`no data after ${WAIT / 1000} s`);
    }
    const onProgress = () => { moved = true; };
    const onData = () => { if (el.readyState >= 2) window.clearTimeout(timer); };
    el.addEventListener("play", arm);
    el.addEventListener("progress", onProgress);
    el.addEventListener("canplay", onData);
    el.addEventListener("playing", onData);
    return () => {
      window.clearTimeout(timer);
      window.clearTimeout(early);
      last?.removeEventListener("error", onErr);
      el.removeEventListener("error", onErr);
      el.removeEventListener("play", arm);
      el.removeEventListener("progress", onProgress);
      el.removeEventListener("canplay", onData);
      el.removeEventListener("playing", onData);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- wanted/note are read live; key re-arms it
  }, [ref, key]);
}
