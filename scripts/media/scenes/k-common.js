// Shared helpers for the KamasMarket video scenes (scenes/k-*.html). Logos come from out/logos-kamas/logos.js
// (Simple Icons CC0 data, written by kamas_assemble.py logos); brands without one are name tiles.
const clamp = (x) => Math.max(0, Math.min(1, x));
const ease = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const back = (x) => { x = clamp(x); const c = 1.7; return x <= 0 ? 0 : 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2; };
const GOLD = "#f0c040";
// name tiles for brands with no Simple Icons logo: [wordmark, color]
const NAMED = { wompi: ["Wompi", "#1b1b1b"], nowpayments: ["NOWPayments", "#1f6fd1"], zavu: ["Zavu", "#7c3aed"] };

/** A logo tile: white rounded square with the brand glyph in its color, plus a label under it. */
function tile(slug, size = 150, label = true) {
  const d = document.createElement("div");
  d.className = "ktile";
  d.style.cssText = `position:absolute; width:${size}px; text-align:center; transform-origin: 50% 40%;`;
  const L = window.LOGOS && window.LOGOS[slug];
  let inner, title;
  if (L) {
    title = L.title;
    const svg = L.svg.replace("<svg ", `<svg width="${size * 0.52}" height="${size * 0.52}" fill="${L.hex}" `);
    inner = svg;
  } else {
    const [word, color] = NAMED[slug];
    title = word;
    const fs = Math.min(size * 0.2, (size * 1.22) / word.length);
    inner = `<span style="font: 800 ${fs}px Inter; color:${color}; letter-spacing:-0.02em">${word}</span>`;
  }
  d.innerHTML = `<div style="width:${size}px; height:${size}px; border-radius:${size * 0.24}px; background:#fff;
      display:grid; place-items:center; box-shadow: 0 24px 60px -20px rgba(0,0,0,0.85), 0 0 0 1px rgba(255,255,255,0.08)">${inner}</div>` +
    (label ? `<div style="margin-top:${size * 0.12}px; font: 600 ${Math.max(18, size * 0.15)}px Inter; color:#e6e9ed">${title}</div>` : "");
  return d;
}

/** Pop-in transform for an element at time t (appears at t0). */
function popIn(el, t, t0, dur = 0.4) {
  const a = back((t - t0) / dur);
  el.style.opacity = clamp((t - t0) / (dur * 0.5));
  el.style.transform = `scale(${0.5 + 0.5 * a})`;
}
