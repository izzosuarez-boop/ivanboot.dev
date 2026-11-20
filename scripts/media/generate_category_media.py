"""Generate the media for an Ardea Skin category page.

    python generate_category_media.py serums hero      # 16:9 lifestyle image (Nano Banana Pro)   ~$0.14
    python generate_category_media.py serums clip      # 15 s how-to clip (Gemini Omni 1.2 Flash) ~$1.56 at 1080p
    python generate_category_media.py serums voice     # narration (Gemini 3.8 Flash TTS)         <$0.01
    python generate_category_media.py serums assemble  # ffmpeg: captions + narration over the clip, poster frame
    python generate_category_media.py serums all

Content (narration, captions, timecoded shots) lives in apps/web/src/content/categories.json so
the page and the video can't drift apart. Outputs: scripts/media/out/<slug>/ (gitignored).
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
ROOT = HERE.parents[1]
CATEGORIES = {c["slug"]: c for c in json.loads((ROOT / "apps/web/src/content/categories.json").read_text(encoding="utf-8"))["categories"]}
APPROVED = json.loads((ROOT / "scripts/images/approved.json").read_text(encoding="utf-8"))["images"]
API = "https://generativelanguage.googleapis.com/v1beta"

BRAND = (
    "ARDEA SKIN, a premium natural skincare brand: heavy frosted glass and soft-touch packaging with brushed "
    "champagne-gold metal, the brand name 'ARDEA' printed directly on the pack in a thin elegant serif. "
    "Warm natural light, honed travertine, raw linen, eucalyptus. Palette limited to warm sand, muted sage, "
    "soft blush terracotta and deep clay brown. Quiet luxury, calm, unhurried, photorealistic, natural skin texture."
)

HERO_SCENES = {
    # v2: v1 showed TWO droppers (one still on the bottle) and a flat blank panel as "negative space"
    "serums": "Close-up editorial lifestyle photograph in one continuous scene: a woman's hand holds the champagne-gold "
              "dropper of the ARDEA serum above her other open palm, a single clear drop just falling. The ARDEA bottle "
              "from the reference image stands OPEN on the travertine bathroom counter beside her — its dropper is the "
              "one in her hand, so the bottle has no dropper and no cap on it (there is only ONE dropper in the image). "
              "Late-afternoon window light, softly blurred linen and eucalyptus behind. Wide 16:9 framing with the "
              "subject in the right two thirds; the left third is the same softly out-of-focus bathroom background "
              "continuing naturally (no flat panels, borders, frames or split layout).",
}

PRICES = {"gemini-3-pro-image": (2.0, 12.0, 120.0)}  # $/M tokens: input, text+thinking, image (2026-11-18)
OMNI_PER_SECOND = {"720p": 0.07, "1080p": 0.104}       # published per-second equivalents (2026-11-20)


def key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*GEMINI_API_KEY\s*=\s*(.*?)\s*$", line)
        if m:
            return m.group(1).strip("'\"")
    raise SystemExit("GEMINI_API_KEY missing in .env")


def post(url: str, body: dict, timeout: int = 600) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key()})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode()[:800]}") from None


def ref_image(cat: dict) -> Path:
    handle = (cat.get("video") or {}).get("reference") or next(iter(cat["chooser"]))["handle"]
    return ROOT / "scripts/images/out" / APPROVED[handle]


def out_dir(slug: str) -> Path:
    d = HERE / "out" / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


# -- 1. hero image ------------------------------------------------------------------------
def hero(slug: str) -> None:
    cat = CATEGORIES[slug]
    scene = HERO_SCENES.get(slug) or f"Editorial lifestyle photograph of the ARDEA {cat['title'].lower()} from the reference image in use."
    prompt = (f"{scene}\n\nBrand look: {BRAND}\nThe product must look exactly like the reference image (same packaging, "
              f"lettering and colors). No other text, no watermark.")
    body = {
        "contents": [{"role": "user", "parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(ref_image(cat).read_bytes()).decode()}},
            {"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9", "imageSize": "2K"}},
    }
    t0 = time.time()
    res = post(f"{API}/models/gemini-3-pro-image:generateContent", body)
    part = next(p for p in res["candidates"][0]["content"]["parts"] if p.get("inlineData") or p.get("inline_data"))
    data = part.get("inlineData") or part.get("inline_data")
    path = out_dir(slug) / f"hero-{time.strftime('%H%M%S')}.jpg"
    path.write_bytes(base64.b64decode(data["data"]))
    u = res.get("usageMetadata", {})
    img = sum(d["tokenCount"] for d in u.get("candidatesTokensDetails", []) if d.get("modality") == "IMAGE")
    txt = u.get("candidatesTokenCount", 0) - img + u.get("thoughtsTokenCount", 0)
    cost = (u.get("promptTokenCount", 0) * 2 + txt * 12 + img * 120) / 1e6
    print(f"hero  -> {path.relative_to(ROOT)} in {time.time()-t0:.0f}s, cost ≈ ${cost:.3f}")


# -- 2. video clip (Gemini Omni via the Interactions API) ----------------------------------
def find_video(node):
    """The Interactions response nests the video; accept inline base64 or a files/ URI wherever it is."""
    if isinstance(node, dict):
        if node.get("type") == "video" and (node.get("data") or node.get("uri")):
            return node
        if "output_video" in node and isinstance(node["output_video"], dict):
            return node["output_video"]
        for v in node.values():
            found = find_video(v)
            if found:
                return found
    elif isinstance(node, list):
        for v in node:
            found = find_video(v)
            if found:
                return found
    return None


def clip(slug: str, resolution: str = "1080p") -> None:
    cat = CATEGORIES[slug]
    v = cat["video"]
    prompt = (
        f"A calm, premium skincare how-to video for {BRAND}\n\nShots:\n{v['shots']}\n\n"
        "The serum bottle must look exactly like the product in the reference image. Consistent warm lighting across "
        "shots, gentle slow camera moves, elegant and unhurried. Audio: no dialogue, no voiceover, no singing; soft "
        "ambient room tone and a gentle, calm acoustic background track. Do not add any on-screen text, captions, "
        "subtitles or logos other than the ARDEA lettering on the product."
    )
    body = {
        "model": "gemini-omni-1.2-flash",
        "input": [
            {"type": "image", "data": base64.b64encode(ref_image(cat).read_bytes()).decode(), "mime_type": "image/jpeg"},
            {"type": "text", "text": prompt},
        ],
        "response_format": {"type": "video", "aspect_ratio": "16:9", "resolution": resolution, "duration": "15s", "delivery": "uri"},
    }
    t0 = time.time()
    res = post(f"{API}/interactions", body, timeout=900)
    # keep the response for debugging, without the (possibly huge) base64 payload
    redacted = json.loads(json.dumps(res))
    def strip(node):
        if isinstance(node, dict):
            for k in list(node):
                if k == "data" and isinstance(node[k], str) and len(node[k]) > 200:
                    node[k] = f"<{len(node[k])} base64 chars>"
                else:
                    strip(node[k])
        elif isinstance(node, list):
            for x in node:
                strip(x)
    strip(redacted)
    (out_dir(slug) / "clip-response.json").write_text(json.dumps(redacted, indent=1), encoding="utf-8")
    video = find_video(res)
    if not video:
        raise SystemExit(f"No video in response: {json.dumps(res)[:800]}")
    path = out_dir(slug) / f"clip-{time.strftime('%H%M%S')}.mp4"
    if video.get("data"):
        path.write_bytes(base64.b64decode(video["data"]))
    else:
        # uri comes as ".../v1beta/files/<id>:download?alt=media" (or "files/<id>")
        file_id = re.search(r"files/([^:/?]+)", video["uri"]).group(1)
        for _ in range(120):  # wait until the file is ACTIVE
            meta = json.loads(urllib.request.urlopen(urllib.request.Request(f"{API}/files/{file_id}", headers={"x-goog-api-key": key()}), timeout=30).read())
            if meta.get("state") == "ACTIVE":
                break
            if meta.get("state") == "FAILED":
                raise SystemExit(f"Video file FAILED: {meta}")
            time.sleep(5)
        req = urllib.request.Request(f"{API}/files/{file_id}:download?alt=media", headers={"x-goog-api-key": key()})
        with urllib.request.urlopen(req, timeout=300) as r:
            path.write_bytes(r.read())
    print(f"clip  -> {path.relative_to(ROOT)} ({path.stat().st_size//1024} KB) in {time.time()-t0:.0f}s, "
          f"cost ≈ ${15 * OMNI_PER_SECOND.get(resolution, 0.104):.2f}")


# -- 3. narration (Gemini TTS) --------------------------------------------------------------
def voice(slug: str, voice_name: str = "Aoede") -> None:
    # One clip per caption so each line can start exactly when its shot and caption appear
    # (a single narration front-loaded all four lines into the first 7 s of a 15 s video).
    for i, c in enumerate(CATEGORIES[slug]["video"]["captions"]):
        tts_line(slug, c["say"], out_dir(slug) / f"voice{i}.wav", voice_name)


def tts_line(slug: str, text: str, path: Path, voice_name: str) -> None:
    body = {
        # Text only: gemini-3.8-flash-tts reads ANY style prefix out loud ("Say warmly and calmly, start on…"),
        # verified 2026-11-20 by transcribing the output with Gemini. Voice choice sets the tone instead.
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}}},
    }
    res = post(f"{API}/models/gemini-3.8-flash-tts:generateContent", body)
    part = res["candidates"][0]["content"]["parts"][0]
    data = part.get("inlineData") or part.get("inline_data")
    raw, mime = base64.b64decode(data["data"]), data.get("mimeType") or data.get("mime_type", "")
    if "wav" in mime or raw[:4] == b"RIFF":
        path.write_bytes(raw)  # 3.8 TTS already returns a WAV container (2.5 returned bare PCM)
    else:
        rate = int(m.group(1)) if (m := re.search(r"rate=(\d+)", mime)) else 24000
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(raw)
    before = media_seconds(path)
    # TTS pads each line with ~1-2 s of silence; trim both ends so lines fit their caption windows
    trimmed = path.with_suffix(".trim.wav")
    subprocess.run([ffmpeg(), "-y", "-i", str(path), "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse",
                    str(trimmed)], capture_output=True, check=True)
    trimmed.replace(path)
    print(f"voice -> {path.name}: {media_seconds(path):.1f}s (was {before:.1f}s with padding) '{text}'")


# -- 4. assemble with ffmpeg ------------------------------------------------------------------
def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def media_seconds(path: Path) -> float:
    out = subprocess.run([ffmpeg(), "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def assemble(slug: str) -> None:
    d = out_dir(slug)
    clips = sorted(d.glob("clip-*.mp4"))
    caps = CATEGORIES[slug]["video"]["captions"]
    voices = [d / f"voice{i}.wav" for i in range(len(caps))]
    if not clips or not all(v.exists() for v in voices):
        raise SystemExit("Need a clip and voice0..N.wav first (run clip and voice)")
    src = clips[-1]
    clip_len = media_seconds(src)
    for c, v in zip(caps, voices):  # a line longer than its caption window would bleed into the next shot
        if media_seconds(v) > (c["to"] - c["from"]) + 0.4:
            print(f"  warning: '{c['say']}' is {media_seconds(v):.1f}s for a {c['to'] - c['from']:.1f}s window")

    # captions: one textfile per line (avoids drawtext escaping), fade in/out, bottom-left on a soft box
    filters, fonts = [], (HERE / "fonts/Inter.ttf").as_posix().replace(":", r"\:")
    for i, c in enumerate(CATEGORIES[slug]["video"]["captions"]):
        tf = d / f"caption{i}.txt"
        tf.write_text(c["text"], encoding="utf-8")
        a, b = c["from"], c["to"]
        alpha = f"if(lt(t\\,{a}+0.35)\\,(t-{a})/0.35\\,if(gt(t\\,{b}-0.35)\\,({b}-t)/0.35\\,1))"
        filters.append(
            f"drawtext=fontfile='{fonts}':textfile='{tf.as_posix().replace(':', chr(92)+':')}':fontsize=h*0.042:fontcolor=0xfbf8f3:"
            f"box=1:boxcolor=0x2f2a24@0.55:boxborderw=26:x=w*0.06:y=h*0.82:enable='between(t,{a},{b})':alpha='{alpha}'")
    vf = ",".join(["scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"] + filters)
    # music bed from the clip, lowered; each voice line delayed to its caption's start (+0.2 s)
    delays = "".join(f"[{i+1}:a]adelay={int((c['from'] + 0.2) * 1000)}:all=1,volume=1.15[v{i}];" for i, c in enumerate(caps))
    mix_in = "[bg]" + "".join(f"[v{i}]" for i in range(len(caps)))
    af = (f"[0:a]volume=0.30[bg];{delays}"
          f"{mix_in}amix=inputs={len(caps) + 1}:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]")
    final = d / f"{slug}-howto.mp4"
    inputs = ["-i", str(src)] + [arg for v in voices for arg in ("-i", str(v))]
    cmd = [ffmpeg(), "-y", *inputs, "-filter_complex", f"[0:v]{vf}[v];{af}",
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", str(final)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-1500:])
    poster = d / f"{slug}-howto-poster.jpg"
    subprocess.run([ffmpeg(), "-y", "-ss", str(max(0, clip_len - 1.5)), "-i", str(src), "-frames:v", "1", "-q:v", "3", str(poster)],
                   capture_output=True)
    print(f"final -> {final.relative_to(ROOT)} ({final.stat().st_size//1024} KB, {media_seconds(final):.1f}s); poster -> {poster.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", choices=sorted(CATEGORIES))
    ap.add_argument("step", choices=["hero", "clip", "voice", "assemble", "all"])
    ap.add_argument("--resolution", default="1080p", choices=["720p", "1080p"])
    a = ap.parse_args()
    steps = ["hero", "clip", "voice", "assemble"] if a.step == "all" else [a.step]
    for s in steps:
        {"hero": lambda: hero(a.slug), "clip": lambda: clip(a.slug, a.resolution),
         "voice": lambda: voice(a.slug), "assemble": lambda: assemble(a.slug)}[s]()


if __name__ == "__main__":
    main()
