"""Publish a portfolio explainer: video (1080p + 720p) and poster to Shopify Files (CDN), captions as WebVTT.

    python scripts/media/publish_explainer.py ai-agents

Reads scripts/media/out/portfolio-<slug>/{<slug>-explainer-1080.mp4, -720.mp4, <slug>-poster.jpg} and the cues
written by explainer_assemble.py (apps/web/src/content/video-cues/<slug>.json). Writes:
  apps/web/public/portfolio/captions/<slug>.{en,es}.vtt   (served by the site, same origin as the page)
  apps/web/src/content/portfolio-media.json             (slug -> poster, sources, captions)
Videos are uploaded as generic files so they are served byte-for-byte (Shopify's own video transcodes came
out 2-3x larger, PLAYBOOK S3).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/shopify"))
from shopify_admin import ShopifyAdmin  # noqa: E402
from upload_files import upload  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
MEDIA = ROOT / "apps/web/src/content/portfolio-media.json"
NL = chr(10)


def vtt(cues: list[dict]) -> str:
    def ts(x: float) -> str:
        h, rem = divmod(x, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"
    out = ["WEBVTT", ""]
    for i, c in enumerate(cues, 1):
        out += [str(i), f"{ts(c['start'])} --> {ts(c['end'])} size:78% align:center", c["text"], ""]  # narrower block
    return NL.join(out)


def main(slug: str) -> int:
    work = ROOT / f"scripts/media/out/portfolio-{slug}"
    cues = json.loads((ROOT / f"apps/web/src/content/video-cues/{slug}.json").read_text(encoding="utf-8"))
    cap_dir = ROOT / "apps/web/public/portfolio/captions"
    cap_dir.mkdir(parents=True, exist_ok=True)
    captions = {}
    for lang in ("en", "es"):
        (cap_dir / f"{slug}.{lang}.vtt").write_text(vtt(cues[lang]), encoding="utf-8", newline="\n")
        captions[lang] = f"/portfolio/captions/{slug}.{lang}.vtt"

    if "--captions-only" in sys.argv:
        print("captions ->", captions)
        return 0
    s = ShopifyAdmin()
    poster = upload(s, work / f"{slug}-poster.jpg", "IMAGE", f"{slug} explainer video")
    print("poster ->", poster["url"][:90])
    sources = []
    for height in (1080, 720):
        f = upload(s, work / f"{slug}-explainer-{height}.mp4", "FILE", f"{slug} explainer video {height}p")
        sources.append({"url": f["url"], "height": height, "id": f["id"]})
        print(f"{height}p  ->", f["url"][:90])
    media = json.loads(MEDIA.read_text(encoding="utf-8")) if MEDIA.exists() else {}
    media[slug] = {"poster": poster["url"], "duration": cues["duration"], "sources": sources, "captions": captions}
    MEDIA.write_text(json.dumps(media, indent=2) + NL, encoding="utf-8", newline="\n")
    print(f"-> {MEDIA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))  # add --captions-only to rewrite only the .vtt files
