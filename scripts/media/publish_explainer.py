"""Publish a portfolio explainer version: video (1080p + 720p) and poster to Shopify Files (CDN), captions as WebVTT.

    python scripts/media/publish_explainer.py ai-agents               # English-voice version
    python scripts/media/publish_explainer.py ai-agents --lang es     # Spanish-voice version
    python scripts/media/publish_explainer.py ai-agents --captions-only [--lang es]   # rewrite the .vtt files only

Reads scripts/media/out/portfolio-<slug>/{<base>-explainer-1080.mp4, -720.mp4, <base>-poster.jpg} and the cues
written by explainer_assemble.py (apps/web/src/content/video-cues/<base>.json), where base = <slug> for English
and <slug>-<lang> otherwise. Writes:
  apps/web/public/portfolio/captions/<base>.{en,es}.vtt   (subtitles timed to that version's voice)
  apps/web/src/content/portfolio-media.json             (slug -> versions -> poster, sources, captions)
Videos are uploaded as generic files so they are served byte-for-byte (Shopify's own video transcodes came
out 2-3x larger, PLAYBOOK S3).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/shopify"))

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


def main(slug: str, lang: str, captions_only: bool) -> int:
    base = slug if lang == "en" else f"{slug}-{lang}"
    work = ROOT / f"scripts/media/out/portfolio-{slug}"
    cues = json.loads((ROOT / f"apps/web/src/content/video-cues/{base}.json").read_text(encoding="utf-8"))
    cap_dir = ROOT / "apps/web/public/portfolio/captions"
    cap_dir.mkdir(parents=True, exist_ok=True)
    captions = {}
    for cl in ("en", "es"):
        (cap_dir / f"{base}.{cl}.vtt").write_text(vtt(cues[cl]), encoding="utf-8", newline="\n")
        captions[cl] = f"/portfolio/captions/{base}.{cl}.vtt"

    media = json.loads(MEDIA.read_text(encoding="utf-8")) if MEDIA.exists() else {}
    entry = media.get(slug) or {}
    if entry and "versions" not in entry:  # first format had a single (English) version at the top level
        entry = {"versions": {"en": entry}}
    entry.setdefault("versions", {})
    if captions_only:
        if lang in entry["versions"]:
            entry["versions"][lang]["captions"] = captions
    else:
        from shopify_admin import ShopifyAdmin
        from upload_files import upload
        s = ShopifyAdmin()
        poster = upload(s, work / f"{base}-poster.jpg", "IMAGE", f"{slug} explainer video ({lang})")
        print("poster ->", poster["url"][:90])
        sources = []
        for height in (1080, 720):
            f = upload(s, work / f"{base}-explainer-{height}.mp4", "FILE", f"{slug} explainer video {height}p ({lang})")
            sources.append({"url": f["url"], "height": height, "id": f["id"]})
            print(f"{height}p  ->", f["url"][:90])
        entry["versions"][lang] = {"poster": poster["url"], "duration": cues["duration"], "sources": sources,
                                   "captions": captions}
    media[slug] = entry
    MEDIA.write_text(json.dumps(media, indent=2, ensure_ascii=False) + NL, encoding="utf-8", newline="\n")
    print(f"-> {MEDIA.relative_to(ROOT)} · versions: {sorted(entry['versions'])} · captions {captions}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    lang = a[a.index("--lang") + 1] if "--lang" in a else "en"
    sys.exit(main(a[0], lang, "--captions-only" in a))
