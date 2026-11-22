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
}


def shot(video: str, name: str, resolution: str = "1080p") -> None:
    s = SHOTS[video][name]
    prompt = f"{s['prompt']}\n\n{LOOK}\n{PHONE_RULE}\n{CLEAN}"
    inputs = [{"type": "text", "text": prompt}]
    if s.get("reference"):
        ref = g.out_dir(f"portfolio-{video}") / f"{s['reference']}-ref.jpg"
        if not ref.exists():
            raise SystemExit(f"Missing {ref.name}: export a frame of the approved {s['reference']} shot first")
        import base64
        inputs.insert(0, {"type": "image", "data": base64.b64encode(ref.read_bytes()).decode(), "mime_type": "image/jpeg"})
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
    a = ap.parse_args()
    if a.list or not a.shot:
        for k, v in SHOTS[a.video].items():
            print(f"{k} ({v['seconds']} s): {v['prompt'][:100]}…")
        return
    shot(a.video, a.shot, a.resolution)


if __name__ == "__main__":
    sys.exit(main())
