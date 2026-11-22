"""People shots for the portfolio explainer videos (Gemini Omni 1.2 Flash).

    python scripts/media/explainer_video.py ai-agents couch     # one shot, ~$0.10 per second at 1080p
    python scripts/media/explainer_video.py ai-agents --list

Phone screens are NEVER generated: a model can't render readable UI text, so every shot keeps the phone's
screen facing away from the camera and the real screen recordings are cut in as close-ups. Outputs go to
scripts/media/out/portfolio-<video>/ (gitignored) and are reviewed before anything is assembled.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import generate_category_media as g

LOOK = ("Cinematic, photorealistic, natural skin texture, shallow depth of field, gentle slow camera move, "
        "consistent warm night-time color grading with soft amber lamp light and a subtle cool teal ambient glow. "
        "ONE continuous shot from one camera — no cuts, no split screen.")
PHONE_RULE = ("The smartphone's screen always faces the person, never the camera: we only ever see the back of "
              "the phone or its edge. No readable screen.")
CLEAN = ("No on-screen text, captions, subtitles, logos or brand names anywhere. Audio: only quiet natural room "
         "tone; no music, no dialogue, no voiceover.")

SHOTS = {
    "ai-agents": {
        "couch": {
            "seconds": 7,
            "prompt": "A relaxed woman in her late twenties sits curled up on a comfortable sofa in a cozy, modern "
                      "living room in the evening, a soft knit throw over her legs and a warm table lamp beside her. "
                      "She holds a smartphone in both hands and types a short message with her thumbs, then pauses "
                      "and reads with a curious, interested half-smile. The camera slowly dollies in from a medium "
                      "shot toward her. Calm, comfortable, everyday moment.",
        },
        "office": {
            "seconds": 7,
            "prompt": "A confident businessman in his early forties, short dark hair, open-collar navy shirt under a "
                      "charcoal blazer, sits at a sleek walnut desk in a modern private office in the evening; a large "
                      "window behind him shows soft out-of-focus city lights. A desktop monitor stands on the desk, "
                      "seen from its side so its screen is not visible. He picks up his smartphone from the desk, "
                      "leans back slightly in his leather chair and starts typing a message with his thumb, focused "
                      "and relaxed. The camera slowly pushes in from a medium shot.",
        },
        "closing": {
            "seconds": 6,
            "reference": "office",   # same man and office: a frame of the approved office shot is passed as reference
            "prompt": "The same businessman from the reference image, in the same office and clothes. He reads his "
                      "smartphone, gives a small satisfied smile and a slight nod, then sets the phone face down on "
                      "the desk and leans back in his chair, relaxed, looking toward the window. The camera slowly "
                      "pulls back to a medium-wide shot.",
        },
    },
    # section overview: "will you get into the AI race, or stay out?" (approved 2026-11-22)
    "ai-agents-overview": {
        "coding": {
            "seconds": 6,
            "reference": "coding-still.png",   # the approved still of Iván at his desk (made with --still)
            "prompt": "Animate the reference image exactly as it is: the same man, the same office, the same desk, "
                      "monitors and lamp, the same framing. He is focused, working: he types fluidly on the keyboard "
                      "with both hands, glances from the main center monitor to the LEFT monitor and back (his head never moves toward the right monitor), and gives a tiny "
                      "nod as if something just worked. LOCKED-OFF STATIC CAMERA on a tripod: no camera movement, "
                      "no zoom, no pan. The monitors stay exactly where they are, their screens steady and evenly "
                      "lit. Only the man moves.",
        },
    },
}

# Stills that start a shot: made with the image model from Iván's real photo + the approved hub scene, so he
# and his office look the same as on the home page. Reviewed before any video is generated.
STILLS = {
    "ai-agents-overview": {
        "coding": {
            "refs": ["C:/Users/Trollo/Desktop/ivan.jpeg", "apps/web/public/portfolio/scene.webp"],
            "prompt": (
                "Reference 1 is the identity reference: the man in the new image is this exact same real person and "
                "must stay instantly recognizable: same face, skin tone, short dark hair, thin dark metal rectangular "
                "glasses, light beard stubble. Reference 2 is his home office: keep the same room, the same dark "
                "walnut desk, the same three slim monitors on arms in a gentle arc, the same black ergonomic chair, "
                "the same amber desk lamp, small potted plant and compact PC tower, and the same light beige "
                "button-up shirt.\n\n"
                "Create ONE single continuous cinematic photograph, 16:9, not a collage. Now he is working: he sits "
                "facing the monitors with both hands on the keyboard, typing, focused, seen in profile from his "
                "right side. Camera: positioned behind him and to his right, slightly above eye level, a 35mm lens, "
                "so we see his right profile (glasses, ear, jaw), his shoulder and arms, and all three monitors "
                "FULLY VISIBLE and UNOBSTRUCTED to the left of and beyond his head: no part of any monitor screen is "
                "hidden behind him. He sits in the left third of the frame; the monitors fill the center and right. "
                "Each screen is a clean, sharp, evenly lit rectangle with clearly visible corners and thin black "
                "bezels. The main center monitor shows a dark code editor with colorful syntax-highlighted lines; the "
                "left monitor shows another dark code file; the right monitor shows a dark chat interface with "
                "message bubbles.\n\n"
                "Lighting: the monitors cast a cool teal-cyan glow on his face and hands; the warm amber lamp adds a "
                "golden rim light. The room falls off into deep near-black darkness at the edges. Photorealistic, "
                "natural skin texture, sharp focus on his face and the screens. "
                "No readable words, no logos, no brand names, no watermark, no other people."),
        },
    },
}


def still(video: str, name: str) -> None:
    """One still image for a shot (Gemini 3 Pro Image, 2K 16:9). Saved as <name>-still-<time>.png for review."""
    import base64
    import mimetypes
    from pathlib import Path
    sys.path.insert(0, str(g.ROOT / "scripts/images"))
    from generate_product_image import cost_usd
    s = STILLS[video][name]
    parts = []
    for r in s["refs"]:
        p = Path(r) if Path(r).is_absolute() else g.ROOT / r
        mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(p.read_bytes()).decode()}})
    parts.append({"text": s["prompt"]})
    model = "gemini-3-pro-image"
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9", "imageSize": "2K"}}}
    t0 = time.time()
    res = g.post(f"{g.API}/models/{model}:generateContent", body, timeout=300)
    for part in res.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        data = part.get("inlineData") or part.get("inline_data")
        if data:
            path = g.out_dir(f"portfolio-{video}") / f"{name}-still-{time.strftime('%H%M%S')}.png"
            path.write_bytes(base64.b64decode(data["data"]))
            cost = cost_usd(model, res.get("usageMetadata", {})) or 0
            print(f"{name} still -> {path.relative_to(g.ROOT)} in {time.time() - t0:.0f}s, cost ≈ ${cost:.3f}")
            return
    raise SystemExit(f"No image in response: {json.dumps(res)[:600]}")


def shot(video: str, name: str, resolution: str = "1080p") -> None:
    s = SHOTS[video][name]
    prompt = f"{s['prompt']}\n\n{LOOK}\n{PHONE_RULE}\n{CLEAN}"
    inputs = [{"type": "text", "text": prompt}]
    if s.get("reference"):
        r = s["reference"]
        ref = g.out_dir(f"portfolio-{video}") / (r if "." in r else f"{r}-ref.jpg")
        if not ref.exists():
            raise SystemExit(f"Missing {ref.name}: export a frame of the approved shot / copy the approved still first")
        import base64
        mime = "image/png" if ref.suffix == ".png" else "image/jpeg"
        inputs.insert(0, {"type": "image", "data": base64.b64encode(ref.read_bytes()).decode(), "mime_type": mime})
    body = {
        "model": "gemini-omni-1.2-flash",
        "input": inputs,
        "response_format": {"type": "video", "aspect_ratio": "16:9", "resolution": resolution,
                            "duration": f"{s['seconds']}s", "delivery": "uri"},
    }
    out = g.out_dir(f"portfolio-{video}")
    t0 = time.time()
    res = g.post(f"{g.API}/interactions", body, timeout=900)
    (out / f"{name}-response.json").write_text(
        json.dumps({k: v for k, v in res.items() if k not in ("steps", "outputs")}, indent=1, default=str), encoding="utf-8")
    vid = g.find_video(res)
    if not vid:
        raise SystemExit(f"No video in response: {json.dumps(res)[:800]}")
    path = out / f"{name}-{time.strftime('%H%M%S')}.mp4"
    g.download_video(vid, path)
    print(f"{name} -> {path.relative_to(g.ROOT)} ({path.stat().st_size // 1024} KB) in {time.time() - t0:.0f}s, "
          f"cost ≈ ${s['seconds'] * g.OMNI_PER_SECOND[resolution]:.2f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", choices=SHOTS)
    ap.add_argument("shot", nargs="?")
    ap.add_argument("--resolution", default="1080p", choices=["720p", "1080p"])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--still", action="store_true", help="make the shot's starting still instead of the video")
    a = ap.parse_args()
    if a.still:
        return still(a.video, a.shot)
    if a.list or not a.shot:
        for k, v in SHOTS[a.video].items():
            print(f"{k} ({v['seconds']} s): {v['prompt'][:100]}…")
        return
    shot(a.video, a.shot, a.resolution)


if __name__ == "__main__":
    sys.exit(main())
