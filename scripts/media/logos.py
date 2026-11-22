"""Brand glyphs for the overview video's logo orbit (shot 3), from Simple Icons (CC0 SVG data; the trademarks
belong to their owners and are shown only to name tools I integrate with).

    python scripts/media/logos.py

Writes scripts/media/out/logos/<slug>.png (white glyph, 512 px, transparent) and colors.json (brand hex).
Brands that asked Simple Icons to remove their logos (Microsoft Excel, Adobe, OpenAI/ChatGPT, Slack, Google AI
Studio) are NOT drawn from other sources: the video shows those as name-only chips.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
VERSION = "16.36.0"
CDN = f"https://cdn.jsdelivr.net/npm/simple-icons@{VERSION}"
OUT = Path(__file__).parent / "out/logos"
SLUGS = ["n8n", "zapier", "python", "whatsapp", "telegram", "instagram", "facebook", "claude", "googlegemini",
         "notion", "googledrive", "gmail", "shopify", "googlesheets", "stripe", "quickbooks", "odoo", "youtube",
         "tiktok", "elevenlabs", "figma"]


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "media-script"}), timeout=30) as r:
        return r.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads(get(f"{CDN}/data/simple-icons.json"))
    icons = data if isinstance(data, list) else data.get("icons", [])
    by_slug = {}
    for ic in icons:
        slug = ic.get("slug") or "".join(ch for ch in ic["title"].lower() if ch.isalnum())
        by_slug[slug] = ic
    colors = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 600, "height": 600})
        for s in SLUGS:
            svg = get(f"{CDN}/icons/{s}.svg").decode()
            svg = svg.replace("<svg ", '<svg width="512" height="512" fill="#ffffff" ', 1)
            pg.set_content(f"<html><body style='margin:0;background:transparent'><div id='i' style='width:512px;"
                           f"height:512px'>{svg}</div></body></html>")
            pg.locator("#i").screenshot(path=str(OUT / f"{s}.png"), omit_background=True)
            colors[s] = {"hex": "#" + by_slug.get(s, {}).get("hex", "5eead4"), "title": by_slug.get(s, {}).get("title", s)}
            print(s, colors[s])
        b.close()
    (OUT / "colors.json").write_text(json.dumps(colors, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
