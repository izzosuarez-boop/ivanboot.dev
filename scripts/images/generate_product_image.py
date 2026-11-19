"""Generate a natural-style product photo for an Ardea Skin product with Gemini.

    python generate_product_image.py niacinamide-zinc-serum
    python generate_product_image.py niacinamide-zinc-serum --model gemini-3.1-flash-image --ref out/approved.png

The prompt is built from catalog.json, so every product shares one art direction
(the brand look) and only the packaging and label text change. --ref passes an
approved image as a style reference to keep the whole line consistent.
Outputs go to scripts/images/out/ and are reviewed before anything reaches Shopify.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
CATALOG = json.loads((ROOT / "scripts/shopify/catalog.json").read_text(encoding="utf-8"))
OUT = Path(__file__).parent / "out"

# v2 (2026-11-18): v1 read as "lab/pharmacy" (stock dropper + paper sticker). Luxury cues:
# heavy thick-walled glass, brushed champagne-gold metal, decoration printed ON the glass,
# sculptural travertine, editorial warm light, fewer props.
ART_DIRECTION = (
    "High-end editorial product photograph for ARDEA SKIN, a premium natural skincare brand, in the style of a "
    "luxury beauty campaign. Setting: the product stands on a sculptural, softly rounded pedestal of honed "
    "travertine stone; behind it a seamless warm sand backdrop; a single soft fold of raw silk-linen and one small, "
    "elegant sprig of eucalyptus placed with restraint, softly out of focus. Warm late-afternoon sunlight from the "
    "left creating long, soft, graceful shadows and a gentle glow through the glass; refined, calm, expensive, "
    "quiet-luxury mood. Color palette strictly limited to warm sand (#f5f0e8, #ebe3d6), muted sage green (#8a9a7b), "
    "soft blush terracotta (#d9b8a3), deep clay brown (#2f2a24) and brushed champagne gold. Square 1:1 composition, "
    "product centered and dominant in the frame with refined negative space, slightly low camera angle that makes "
    "the packaging feel monumental, 100mm macro lens look, shallow depth of field, tack-sharp focus on the "
    "lettering. Decoration: NO paper sticker label; all lettering is screen-printed directly onto the packaging "
    "surface in deep clay brown, with the brand name 'ARDEA' in an elegant thin high-contrast serif typeface with "
    "wide letter spacing, and below it, in small refined sans-serif capitals, the product name and size exactly as "
    "given. Spell every word exactly as written. No other text anywhere, no logos, no watermark, no people, no hands."
)

GOLD = "a brushed champagne-gold metal"
PACKAGING = {
    "Cleanser": f"a premium soft-touch matte tube in warm sand color with {GOLD} cap, standing upright on its cap",
    "Toner": f"a tall, heavy, thick-walled frosted glass bottle with rounded shoulders and {GOLD} screw cap",
    "Exfoliant": f"a tall, heavy, thick-walled frosted glass bottle with rounded shoulders and {GOLD} screw cap",
    "Serum": f"a heavy, thick-walled 30 ml glass bottle with soft rounded shoulders and a thick weighted base, "
             f"{GOLD} dropper collar and a matte cream-colored dropper bulb",
    "Moisturizer": f"a heavy, thick-walled frosted glass jar with a weighted base and a wide {GOLD} lid",
    "Sunscreen": f"a premium soft-touch matte tube in pale blush color with {GOLD} cap, standing upright on its cap",
    "Mask": "three flat, premium soft-touch matte sachets in sand and pale blush tones with a thin champagne-gold "
            "foil edge, one leaning against the others",
}

# Published price per image output (Standard tier, checked 2026-11-18 on aistudio.google.com/docs/pricing)
PRICES = {  # model: (input $/M, text+thinking $/M, image $/M)
    "gemini-3-pro-image": (2.0, 12.0, 120.0),
    "gemini-3.1-flash-image": (0.5, 3.0, 60.0),
}


def cost_usd(model: str, usage: dict) -> float | None:
    if model not in PRICES:
        return None
    p_in, p_txt, p_img = PRICES[model]
    image_tokens = sum(d["tokenCount"] for d in usage.get("candidatesTokensDetails", []) if d.get("modality") == "IMAGE")
    text_tokens = usage.get("candidatesTokenCount", 0) - image_tokens + usage.get("thoughtsTokenCount", 0)
    return (usage.get("promptTokenCount", 0) * p_in + text_tokens * p_txt + image_tokens * p_img) / 1e6


def load_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*GEMINI_API_KEY\s*=\s*(.*?)\s*$", line)
        if m:
            return m.group(1).strip("'\"")
    raise SystemExit("GEMINI_API_KEY not found in .env")


# v3 (2026-11-18): the brand is shared, the set is not. Each category gets its own scene so the
# shop grid doesn't look like 13 copies; serums share one bottle and differ by liquid tint.
SCENES = {
    "Serum": None,  # the approved concept A set (ART_DIRECTION as written)
    "Cleanser": "Set: the product stands on wet, honed travertine with fresh water droplets beading on the "
                "packaging and a few small, crisp water splashes frozen mid-air beside it; a shallow pool of water "
                "reflects the product; clean, fresh, invigorating morning light.",
    "Toner": "Set: the product stands at the edge of a still, shallow basin of water on travertine; dappled "
             "sunlight refracts through the water and glass, casting delicate caustic light patterns on the stone; "
             "crystal-clear, airy, serene.",
    "Exfoliant": "Set: the product stands at the edge of a still, shallow basin of water on travertine; dappled "
                 "sunlight refracts through the water and glass, casting delicate caustic light patterns; serene.",
    "Moisturizer": "Set: the jar stands open-lidded on travertine with the champagne-gold lid resting beside it; "
                   "a single, elegant swirl swatch of the rich cream is smeared on the stone in front, showing its "
                   "velvety texture; a fold of soft cream linen behind; cosy, nourishing, tactile.",
    "Sunscreen": "Set: bright, warm summer sunlight with crisp, graphic shadows of palm leaves falling across the "
                 "product and a sun-bleached travertine block; a hint of soft blush sky tone in the backdrop; "
                 "radiant, summery, protective.",
    "Mask": "Set: an evening self-care ritual: the sachets rest on a folded, waffle-weave linen towel in pale "
            "lilac-grey on travertine, a lit cream-colored candle softly out of focus, a small dish of dried "
            "chamomile flowers; dimmer, golden, intimate candlelight mood with soft lilac undertones.",
}
SERUM_TINTS = {
    "niacinamide-zinc-serum": "The serum inside is pale and milky-clear.",
    "vitamin-c-brightening-serum": "The glass is tinted a soft warm amber-gold and the serum glows golden in the light.",
    "hyaluronic-hydration-serum": "The glass is crystal-clear frosted and the serum is perfectly clear and water-like, with tiny suspended bubbles.",
    "retinal-night-serum": "The glass is tinted a deep, rich amber (light-protective) and the serum is warm golden; slightly moodier dusk light.",
    "centella-calming-serum": "The serum inside is a soft, pale blush pink; the glass frosted.",
}


def build_prompt(p: dict, extra: str = "") -> str:
    size = p["variants"][0]["size"]
    label = f"{p['title'].upper()} — {size.upper()}" if p["type"] != "Mask" else f"{p['title'].upper()}"
    scene = SCENES.get(p["type"])
    scene_line = (f"\n\nOVERRIDE THE SETTING ABOVE (keep brand, palette, lettering and photographic quality): {scene}"
                  if scene else "")
    tint = SERUM_TINTS.get(p["handle"], "")
    return (
        f"{ART_DIRECTION}{scene_line}\n\nProduct: {p['title']} ({p['type'].lower()}, {p['texture'].lower()} texture). "
        f"Packaging: {PACKAGING.get(p['type'], PACKAGING['Serum'])}. {tint} {extra} "
        f"Printed text, exactly: 'ARDEA' and below it '{label}'."
    )


def generate(model: str, prompt: str, key: str, ref: Path | None, image_size: str) -> tuple[bytes, str, dict]:
    parts: list[dict] = [{"text": prompt}]
    if ref:
        parts.insert(0, {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(ref.read_bytes()).decode()}})
        parts.append({"text": "The reference image is the approved ARDEA brand look. Match its lettering style and "
                              "placement, champagne-gold metal finish, color grading and photographic quality. Do NOT "
                              "copy its packaging shape or its set: use the packaging and setting described above."})
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1", "imageSize": image_size}},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Gemini HTTP {e.code}: {e.read().decode()[:600]}") from None
    for part in res.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        data = part.get("inlineData") or part.get("inline_data")
        if data:
            return base64.b64decode(data["data"]), data.get("mimeType") or data.get("mime_type"), res.get("usageMetadata", {})
    raise SystemExit(f"No image in response: {json.dumps(res)[:600]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("handle")
    ap.add_argument("--model", default="gemini-3-pro-image")
    ap.add_argument("--ref", type=Path)
    ap.add_argument("--size", default="2K", choices=["1K", "2K", "4K"])
    ap.add_argument("--extra", default="", help="extra art direction appended to the packaging line")
    ap.add_argument("--tag", default="", help="suffix for the output filename, e.g. conceptA")
    a = ap.parse_args()
    product = next((p for p in CATALOG["products"] if p["handle"] == a.handle), None)
    if not product:
        raise SystemExit(f"Unknown handle {a.handle}")
    prompt = build_prompt(product, a.extra)
    t0 = time.time()
    img, mime, usage = generate(a.model, prompt, load_key(), a.ref, a.size)
    OUT.mkdir(exist_ok=True)
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "png")
    tag = f"--{a.tag}" if a.tag else ""
    path = OUT / f"{a.handle}{tag}--{a.model}--{time.strftime('%Y%m%d-%H%M%S')}.{ext}"
    path.write_bytes(img)
    cost = cost_usd(a.model, usage)
    print(f"saved {path.relative_to(ROOT)} ({len(img)//1024} KB) in {time.time()-t0:.1f}s"
          + (f" | cost ≈ ${cost:.4f}" if cost is not None else "")
          + f" | tokens in={usage.get('promptTokenCount')} out={usage.get('candidatesTokenCount')} thinking={usage.get('thoughtsTokenCount', 0)}")


if __name__ == "__main__":
    main()
