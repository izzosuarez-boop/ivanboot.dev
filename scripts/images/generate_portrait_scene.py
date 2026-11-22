"""Generate the portfolio hub scene (Iván at his desk, night office) from his real photo as identity reference.

    python scripts/images/generate_portrait_scene.py C:/Users/Trollo/Desktop/ivan.jpeg [--tag v1] [--extra "..."]

The scene sits inside the hub circle, so it is square, subject centered, and its edges fall off into the
page background (#0b0d10) to blend without a hard border. Output goes to scripts/images/out/ (not in git)
and is reviewed for likeness before it is copied to apps/web/public/portfolio/.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_product_image import OUT, ROOT, cost_usd, load_key  # noqa: E402

MODEL = "gemini-3-pro-image"

PROMPT = (
    "The attached photo is the identity reference: the person in the new image is this exact same real man and "
    "must stay instantly recognizable — same face shape, same skin tone, same short dark hair, same thin dark "
    "metal rectangular glasses, same light beard stubble and the same warm, friendly expression. He wears the same "
    "light beige button-up shirt.\n\n"
    "Create ONE single continuous cinematic photograph, not a collage, no panels, no dividing lines. "
    "Scene: a calm, modern home office at night. He sits in a black ergonomic office chair at a wide dark walnut "
    "desk. His body is in three-quarter view toward the camera, turned slightly away from his monitors as if he "
    "just looked up from work; relaxed and confident, a natural slight smile, one forearm resting on the desk. "
    "On the desk: a low-profile keyboard and a mouse, a compact desktop PC tower with a faint soft glow, and three "
    "slim monitors on arms arranged in a gentle arc, angled so their screens are partly visible to the camera. "
    "The screens show soft, abstract software interfaces — a dark code editor with colored lines, a simple line "
    "chart, a product web page — as blurred shapes with no readable text. A small potted plant with fresh green "
    "leaves sits at the edge of the desk.\n\n"
    "Lighting: the monitors cast a cool teal-cyan glow on his face and the desk; a warm amber desk lamp adds a "
    "gentle golden rim light from behind him. The room falls off gradually into deep near-black darkness "
    "(#0b0d10) toward every edge of the frame, like a soft natural vignette, so the photo blends seamlessly into "
    "a black web page.\n\n"
    "Camera: eye level, 50mm lens, medium shot from his head down to the desk surface, subject centered, shallow "
    "depth of field, photorealistic, natural skin texture, sharp focus on his face. "
    "No text, no logos, no brand names, no watermark, no other people."
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("photo", type=Path)
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--extra", default="")
    ap.add_argument("--size", default="2K", choices=["1K", "2K", "4K"])
    a = ap.parse_args()
    mime = mimetypes.guess_type(a.photo.name)[0] or "image/jpeg"
    body = {
        "contents": [{"role": "user", "parts": [
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(a.photo.read_bytes()).decode()}},
            {"text": PROMPT + (f"\n\n{a.extra}" if a.extra else "")},
        ]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1", "imageSize": a.size}},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": load_key()})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Gemini HTTP {e.code}: {e.read().decode()[:600]}") from None
    usage = res.get("usageMetadata", {})
    for part in res.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        data = part.get("inlineData") or part.get("inline_data")
        if data:
            ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(data.get("mimeType"), "png")
            OUT.mkdir(exist_ok=True)
            path = OUT / f"portrait-scene--{a.tag}--{time.strftime('%Y%m%d-%H%M%S')}.{ext}"
            path.write_bytes(base64.b64decode(data["data"]))
            cost = cost_usd(MODEL, usage)
            print(f"saved {path.relative_to(ROOT)} in {time.time() - t0:.1f}s | cost ≈ ${cost:.4f}")
            return
    raise SystemExit(f"No image in response: {json.dumps(res)[:600]}")


if __name__ == "__main__":
    main()
