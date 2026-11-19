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

ART_DIRECTION = (
    "Professional, photorealistic product photograph for ARDEA SKIN, a natural, fragrance-free skincare brand. "
    "Setting: the product stands on a slab of light, honed travertine stone; a few sprigs of eucalyptus and a "
    "fold of undyed natural linen softly out of focus behind it. Warm natural morning daylight from the left, "
    "gentle long soft shadows, calm, organic, quiet luxury mood. Color palette strictly limited to warm sand "
    "(#f5f0e8, #ebe3d6), muted sage green (#8a9a7b, #5d6b52), soft blush terracotta (#d9b8a3) and deep clay "
    "brown (#2f2a24). Square 1:1 composition, product centered with generous negative space, eye-level camera, "
    "85mm lens look, shallow depth of field, crisp focus on the label. "
    "Label design: minimal matte off-white paper label; the brand name 'ARDEA' in an elegant thin high-contrast "
    "serif typeface with wide letter spacing, and below it, in small clean sans-serif capitals, the product name "
    "and size exactly as given. Spell every word on the label exactly as written. "
    "No other text anywhere, no logos, no watermark, no people, no hands."
)

PACKAGING = {
    "Cleanser": "a soft-touch matte squeeze tube in warm sand color with a flat clay-brown flip cap, standing upright on its cap",
    "Toner": "a tall cylindrical frosted glass bottle with a matte sage-green screw cap",
    "Exfoliant": "a tall cylindrical frosted glass bottle with a matte sage-green screw cap",
    "Serum": "a 30 ml frosted glass dropper bottle with a matte sand-colored collar and a soft sage-green rubber bulb",
    "Moisturizer": "a wide, low frosted glass jar with a matte sand-colored lid",
    "Sunscreen": "a soft-touch matte squeeze tube in pale blush color with a clay-brown flip cap, standing upright on its cap",
    "Mask": "three flat matte paper sachets in pale lilac-grey and sand tones, one leaning against the others",
}


def load_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*GEMINI_API_KEY\s*=\s*(.*?)\s*$", line)
        if m:
            return m.group(1).strip("'\"")
    raise SystemExit("GEMINI_API_KEY not found in .env")


def build_prompt(p: dict) -> str:
    size = p["variants"][0]["size"]
    label = f"{p['title'].upper()} — {size.upper()}" if p["type"] != "Mask" else f"{p['title'].upper()}"
    return (
        f"{ART_DIRECTION}\n\nProduct: {p['title']} ({p['type'].lower()}, {p['texture'].lower()} texture). "
        f"Packaging: {PACKAGING.get(p['type'], PACKAGING['Serum'])}. "
        f"Label text, exactly: 'ARDEA' and below it '{label}'."
    )


def generate(model: str, prompt: str, key: str, ref: Path | None) -> tuple[bytes, str, dict]:
    parts: list[dict] = [{"text": prompt}]
    if ref:
        parts.insert(0, {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(ref.read_bytes()).decode()}})
        parts.append({"text": "Use the reference image only for the brand look: same lighting, stone, props, palette and label typography."})
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1"}},
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
    a = ap.parse_args()
    product = next((p for p in CATALOG["products"] if p["handle"] == a.handle), None)
    if not product:
        raise SystemExit(f"Unknown handle {a.handle}")
    prompt = build_prompt(product)
    t0 = time.time()
    img, mime, usage = generate(a.model, prompt, load_key(), a.ref)
    OUT.mkdir(exist_ok=True)
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "png")
    path = OUT / f"{a.handle}--{a.model}--{time.strftime('%Y%m%d-%H%M%S')}.{ext}"
    path.write_bytes(img)
    print(f"saved {path.relative_to(ROOT)} ({len(img)//1024} KB, {mime}) in {time.time()-t0:.1f}s | usage: {usage}")


if __name__ == "__main__":
    main()
