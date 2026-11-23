/* Subtitles handed to a <video> by script instead of <track> elements. iPhone Safari (iOS 18.7) failed the
 * whole video with MEDIA_ERR_SRC_NOT_SUPPORTED (error 4) whenever it had <track src> children: proven on the
 * user's iPhone on 2026-11-23 with ivanboot.dev/v/prueba2.html, same file, with and without tracks (PLAYBOOK
 * E28). Tracks created with addTextTrack() and filled with VTTCue objects never touch Safari's media loader. */

export type Cue = { start: number; end: number; text: string };

const toSec = (t: string) => t.split(":").reduce((acc, x) => acc * 60 + parseFloat(x), 0);

/** Minimal WebVTT reader: cue timings (hh:mm:ss.mmm or mm:ss.mmm) and text; cue settings are ignored. */
export function parseVtt(text: string): Cue[] {
  const cues: Cue[] = [];
  for (const block of text.replace(/\r/g, "").split(/\n{2,}/)) {
    const lines = block.split("\n");
    const i = lines.findIndex((l) => l.includes("-->"));
    if (i < 0) continue;
    const [a, b] = lines[i].split("-->");
    const start = toSec(a.trim());
    const end = toSec(b.trim().split(/\s+/)[0]);
    const body = lines.slice(i + 1).join("\n").trim();
    if (body && end > start) cues.push({ start, end, text: body });
  }
  return cues;
}

/** Adds one subtitles track per language to the video (once per element), filled from the given .vtt URLs.
 *  The tracks fire "addtrack" on video.textTracks right away; their cues arrive when each file has loaded. */
export function attachSubtitles(
  video: HTMLVideoElement,
  files: { lang: string; label: string; url: string }[],
  signal: AbortSignal,
) {
  for (const f of files) {
    if (Array.from(video.textTracks).some((t) => t.language === f.lang)) continue; // effects can run twice
    const track = video.addTextTrack("subtitles", f.label, f.lang);
    track.mode = "disabled";
    fetch(f.url, { signal })
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((txt) => { for (const c of parseVtt(txt)) track.addCue(new VTTCue(c.start, c.end, c.text)); })
      .catch(() => {}); // no subtitles is better than no video
  }
}
