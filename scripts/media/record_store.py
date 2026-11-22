"""Screen recordings of the live store for the explainer videos (phone viewport, captured at device pixels).

    python scripts/media/record_store.py chat      # the store agent answering "oily skin" and adding to bag
    python scripts/media/record_store.py restock   # Vitamin C product page: sold out -> back on sale

Everything recorded is real: the production store, the real agent (~$0.002 per run) and real Shopify stock.
`restock` sets Vitamin C to 0, records the sold-out page, puts the stock back (to what it was before) and
reloads the page; the store refreshes within seconds through the inventory webhook.

How it captures (2026-11-22): Playwright's video recorder and Chrome's screencast both deliver CSS pixels
(390x844) under mobile emulation, so text came out soft. Screenshots are taken at device pixels (780x1688 at
DPR 2), so a capture loop takes them back to back (~15-25 fps) while the actions run concurrently, and the
frames are assembled with their real timestamps into a constant 30 fps MP4.
Outputs: scripts/media/out/portfolio-ai-agents/raw/<name>.mp4 (gitignored).
"""
from __future__ import annotations

import asyncio
import base64
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "scripts/media/out/portfolio-ai-agents/raw"
STORE = "https://tienda.ivanboot.dev"
VIEW = {"width": 390, "height": 844}
DPR = 2
NL = chr(10)


class Recorder:
    def __init__(self, page, name: str):
        self.page, self.name = page, name
        self.dir = OUT / f"_frames-{name}"
        shutil.rmtree(self.dir, ignore_errors=True)
        self.dir.mkdir(parents=True)
        self.frames: list[tuple[float, Path]] = []
        self.running = False
        self.t0 = 0.0

    async def _loop(self) -> None:
        cdp = await self.page.context.new_cdp_session(self.page)
        while self.running:
            t = time.perf_counter()
            try:
                # clip is in document coordinates: follow the scroll, or a scrolled page comes out blank on top
                pos = await cdp.send("Runtime.evaluate", {"expression": "[scrollX, scrollY]", "returnByValue": True})
                sx, sy = pos["result"]["value"]
                shot = await cdp.send("Page.captureScreenshot", {
                    "format": "jpeg", "quality": 90, "optimizeForSpeed": True,  # scale: CDP defaults to CSS pixels
                    "clip": {"x": sx, "y": sy, "width": VIEW["width"], "height": VIEW["height"], "scale": DPR}})
            except Exception:  # noqa: BLE001 — a navigation in progress: try again
                await asyncio.sleep(0.02)
                continue
            path = self.dir / f"{len(self.frames):05d}.jpg"
            path.write_bytes(base64.b64decode(shot["data"]))
            self.frames.append((t - self.t0, path))

    def start(self) -> None:
        self.running, self.t0 = True, time.perf_counter()
        self.task = asyncio.create_task(self._loop())

    def now(self) -> float:
        return time.perf_counter() - self.t0

    async def stop(self) -> Path:
        self.running = False
        await self.task
        import imageio_ffmpeg
        lines = []
        for k, (ts, path) in enumerate(self.frames):
            dur = (self.frames[k + 1][0] - ts) if k + 1 < len(self.frames) else 0.3
            lines += [f"file '{path.name}'", f"duration {max(dur, 0.001):.4f}"]
        lines.append(f"file '{self.frames[-1][1].name}'")
        (self.dir / "list.txt").write_text(NL.join(lines), encoding="utf-8")
        dst = OUT / f"{self.name}.mp4"
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", "list.txt", "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "16",
                        "-preset", "slow", str(dst)], check=True, cwd=self.dir)
        span = self.frames[-1][0] - self.frames[0][0]
        print(f"   {len(self.frames)} frames in {span:.1f}s ({len(self.frames) / max(span, 0.1):.1f} fps captured)")
        return dst


async def _browser(p):
    browser = await p.chromium.launch(channel="chrome")
    ctx = await browser.new_context(viewport=VIEW, device_scale_factor=DPR, is_mobile=True, has_touch=True, locale="en-US")
    return browser, ctx, await ctx.new_page()


async def chat() -> None:
    for attempt in range(1, 4):  # the agent decides whether to show product cards; the video wants them
        cards = await _chat_take()
        if cards:
            return
        print(f"   take {attempt}: no product cards, recording again")


async def _chat_take() -> int:
    async with async_playwright() as p:
        browser, ctx, page = await _browser(p)
        marks = {}
        await page.goto(STORE, wait_until="networkidle")
        rec = Recorder(page, "store-chat")
        rec.start()
        await page.wait_for_timeout(1800)
        await page.get_by_role("button", name="Ask Ardea").tap()
        await page.wait_for_timeout(900)
        box = page.locator("section[role=dialog] textarea")
        await box.evaluate("el => { el.spellcheck = false }")  # no red underlines in the video (the live store keeps it)
        await box.tap()
        marks["type_1"] = rec.now()
        await page.keyboard.type("What would work for my oily skin?", delay=65)
        await page.wait_for_timeout(400)
        bubbles = page.locator("section[role=dialog] .rounded-tl-sm")
        n = await bubbles.count()
        await page.keyboard.press("Enter")
        await page.wait_for_function(f"document.querySelectorAll('section[role=dialog] .rounded-tl-sm').length > {n}", timeout=90000)
        marks["reply_1"] = rec.now()
        await page.wait_for_timeout(5000)
        await box.tap()
        marks["type_2"] = rec.now()
        await page.keyboard.type("Add the niacinamide serum to my bag", delay=65)
        n = await bubbles.count()
        await page.keyboard.press("Enter")
        await page.wait_for_function(f"document.querySelectorAll('section[role=dialog] .rounded-tl-sm').length > {n}", timeout=90000)
        await page.wait_for_selector("text=Added to your bag", timeout=15000)
        marks["added"] = rec.now()
        await page.wait_for_timeout(3500)
        r1 = await bubbles.nth(1).inner_text()
        cards = await page.locator("section[role=dialog] a[href*='/products/']").count()
        dst = await rec.stop()
        await browser.close()
    print("reply 1:", r1[:200].replace(NL, " | "))
    print(f"-> {dst.relative_to(ROOT)} | product cards: {cards} | marks (s): " + ", ".join(f"{k}={v:.1f}" for k, v in marks.items()))
    return cards


# ── restock (needs the Admin API: load .env like the API does) ──────────────────────────────────────────
def _admin():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$", line)
        if m:
            os.environ.setdefault(m.group(1), m.group(2).strip("'\""))
    sys.path.insert(0, str(ROOT / "apps/api"))
    from app import shopify_admin
    return shopify_admin


async def _wait_for(url: str, text: str, limit: float = 150) -> float:
    """Poll the live page (server-rendered HTML) until it contains `text`; returns the seconds waited."""
    import urllib.request
    t0 = time.time()
    while time.time() - t0 < limit:
        try:
            html = await asyncio.to_thread(lambda: urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode())
            if text in html:
                return time.time() - t0
        except Exception:  # noqa: BLE001 — a network hiccup: keep polling
            pass
        await asyncio.sleep(3)
    raise SystemExit(f"the store never showed '{text}' within {limit:.0f}s")


async def restock() -> None:
    sa = _admin()
    v = next(v for v in await sa.variants_with_inventory() if v["name"].startswith("Vitamin C"))
    original = v["qty"]
    print(f"Vitamin C now {original}")
    url = f"{STORE}/products/vitamin-c-brightening-serum"
    back_to = original or 40
    if original > 0:
        errs = await sa.set_available(v["item_id"], v["location_id"], 0, original, ref=f"gid://ardea-video/SoldOut/{int(time.time())}")
        assert not errs, errs
    # Shopify's Storefront replicas need 15-45 s to agree on a new stock: wait until the store really shows
    # each state before filming it (the waiting is cut in the edit)
    print(f"   store shows sold out after {await _wait_for(url, 'Sold out — back soon'):.0f}s")
    marks = {}
    async with async_playwright() as p:
        browser, ctx, page = await _browser(p)
        await page.goto(url, wait_until="networkidle")
        rec = Recorder(page, "store-restock")
        rec.start()
        await page.wait_for_timeout(800)
        await page.mouse.wheel(0, 260)
        await page.wait_for_timeout(600)
        sold = await page.locator("text=/sold out/i").count()
        marks["sold_out_shown"] = rec.now()
        await page.wait_for_timeout(2500)
        errs = await sa.set_available(v["item_id"], v["location_id"], back_to, 0, ref=f"gid://ardea-video/Back/{int(time.time())}")
        assert not errs, errs
        marks["restocked"] = rec.now()
        print(f"   store shows it back on sale after {await _wait_for(url, 'Add to bag'):.0f}s")
        marks["reload"] = rec.now()
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(500)
        await page.mouse.wheel(0, 260)
        marks["back_on_sale"] = rec.now()
        await page.wait_for_timeout(3500)
        available = await page.get_by_role("button", name=re.compile("add to bag", re.I)).count()
        dst = await rec.stop()
        await browser.close()
    final = next(x for x in await sa.variants_with_inventory() if x["name"].startswith("Vitamin C"))["qty"]
    print(f"-> {dst.relative_to(ROOT)} | sold out visible: {bool(sold)} | add-to-bag visible after: {bool(available)} | "
          f"Vitamin C final stock {final} | marks (s): " + ", ".join(f"{k}={v:.1f}" for k, v in marks.items()))


if __name__ == "__main__":
    asyncio.run({"chat": chat, "restock": restock}[sys.argv[1]]())
