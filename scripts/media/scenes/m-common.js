// Shared helpers for the section 4 video (scenes/m-*.html). Load after k-common.js (easing, popIn, tile).
// Real videos are shown by seeking them to the exact frame for each render(t): render is async and the filming
// script (automation_assemble.scene) waits for it before taking the screenshot.
// The Spanish versions of this video show the Spanish cuts of the other videos (window.__LANG is set by
// automation_assemble.scene before the page loads). The moments shown carry nothing that names a site.
const ES_CUT = window.__LANG === "es" ? "-es-workana" : "";
const VID = {
  hub: `../out/portfolio-ai-agents-overview/ai-agents-overview${ES_CUT}-explainer-720.mp4`,
  ai: `../out/portfolio-ai-agents/ai-agents${ES_CUT}-explainer-720.mp4`,
  auto: `../out/portfolio-automation-overview/automation-overview${ES_CUT}-explainer-720.mp4`,
  web: `../out/portfolio-web-api-overview/web-api-overview${ES_CUT}-explainer-720.mp4`,
  howto: "../out/cleansers/cleansers-howto.mp4",
  brand: "../out/home/brand-720.mp4",
};
const F = (n) => `../out/portfolio-media-overview/frames/${n}.jpg`;
const STILL = (dir, n) => `../out/${dir}/${n}`;

function video(src, css) {
  const v = document.createElement("video");
  v.src = src; v.muted = true; v.preload = "auto"; v.playsInline = true;
  v.style.cssText = "position:absolute; object-fit:cover; " + (css || "");
  return v;
}

async function seek(v, t) {
  if (v.readyState < 1) await new Promise((r) => { v.addEventListener("loadedmetadata", r, { once: true }); setTimeout(r, 4000); });
  t = Math.max(0, Math.min(t, (v.duration || 1) - 0.05));
  if (Math.abs(v.currentTime - t) < 0.001 && v.readyState >= 2) return;
  await new Promise((r) => { v.addEventListener("seeked", r, { once: true }); v.currentTime = t; setTimeout(r, 2000); });
}

/** Seek every visible video, then wait one frame so the new pictures are on screen. */
async function seekAll(pairs) {
  await Promise.all(pairs.filter(([v]) => v.style.opacity !== "0" && v.offsetParent !== null).map(([v, t]) => seek(v, t)));
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
}

function label(text, css, cls = "chip") {
  const d = document.createElement("div");
  d.className = cls; d.textContent = text; d.style.cssText = "position:absolute; white-space:nowrap; " + (css || "");
  return d;
}
