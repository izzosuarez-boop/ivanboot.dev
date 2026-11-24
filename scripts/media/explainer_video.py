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
                      "nod as if something just worked. His face stays exactly as in the reference (same features, same "
                      "facial hair) and he never turns toward the camera. LOCKED-OFF STATIC CAMERA on a tripod: no camera movement, "
                      "no zoom, no pan. The monitors stay exactly where they are, their screens steady and evenly "
                      "lit. Only the man moves.",
        },
        "viewer": {
            "seconds": 7,
            "reference": "viewer-still.png",   # approved still: business owner, phone on a desk stand, black screen
            "prompt": "Animate the reference image exactly as it is: the same woman, office, desk, phone on its "
                      "stand and framing. For the first three seconds she sits still, watching the phone screen "
                      "attentively. Then she leans in slightly and brings her right hand up from the desk, from the "
                      "lower right, with only her index finger extended, and touches the GLASS of the screen with the "
                      "tip of that finger in the upper-right area of the screen, a little below its top edge: a "
                      "single short press on the screen itself, like pressing a button in an app; her hand stays "
                      "below the top edge of the phone and never grabs the phone or its edge. Then she pulls her hand "
                      "back to the desk and sits back with a small satisfied smile. The phone never moves in its stand and "
                      "its screen stays completely black. LOCKED-OFF STATIC CAMERA on a tripod: no camera movement, "
                      "no zoom, no pan.",
        },
        "requests": {
            "seconds": 10,
            "reference": "requests-still.png",   # approved still: over Iván's shoulder, main monitor in the middle
            "prompt": "Animate the reference image exactly as it is: the same man seen in profile from behind and "
                      "to his right, the same office, monitors and framing. His face stays exactly as in the "
                      "reference (same features, same facial hair); he keeps facing the center monitor in profile and "
                      "NEVER turns his head toward the camera. He reads the center monitor attentively, "
                      "scrolls a little with the mouse, leans slightly forward with interest, then nods slowly as if "
                      "he already knows how to solve it. Small, natural movements only. The monitors and their "
                      "screens stay perfectly still. LOCKED-OFF STATIC CAMERA on a tripod: no camera movement, no "
                      "zoom, no pan.",
        },
        "phone": {
            "seconds": 8,
            "reference": "phone-still.png",   # approved still: shop owner holding his phone, screen toward him
            "prompt": "Animate the reference image exactly as it is: the same man, the same shop, the same framing. "
                      "He types a short message on his smartphone with both thumbs for a couple of seconds, pauses "
                      "and reads, then reads again a moment later and a satisfied, relieved smile spreads across his "
                      "face; he gives a small nod and relaxes his shoulders. He keeps holding the phone in both hands "
                      "at the same height and place the whole time, its screen facing him, never the camera. "
                      "LOCKED-OFF STATIC CAMERA on a tripod: no camera movement, no zoom, no pan.",
        },
        "whiteboard": {
            "seconds": 10,
            "reference": "whiteboard-still.png",   # approved still: owner + whiteboard with blank sticky notes
            "prompt": "Animate the reference image exactly as it is: the same woman, the same office, the same "
                      "whiteboard with the same grid of blank sticky notes in the same places, the same framing. "
                      "She studies the board for a moment, then steps closer and, with the black marker, draws a "
                      "quick, loose circle around one sticky note, then around a second and a third note in other "
                      "places on the board, each circle drawn around the OUTSIDE edge of the note so the note itself "
                      "stays clean and uncovered. Then she steps back to where she started, caps the marker and "
                      "looks at the board with a decided, confident half-smile. She always stays on the left side "
                      "of the board and never stands in front of the notes for long. LOCKED-OFF STATIC CAMERA on a "
                      "tripod: no camera movement, no zoom, no pan. The sticky notes never move and stay blank: "
                      "no writing appears on them.",
        },
    },
    # Automation section: a client's game-currency sales automated end to end (approved 2026-11-23). The same man
    # in all three shots: first by hand at night, then relaxed on his couch while the bots work.
    "automation-overview": {
        "manual": {
            "seconds": 10,
            "reference": "manual-still.png",
            "prompt": "Animate the reference image exactly as it is: the same man, the same room, desk, monitor, lamp, "
                      "notebook and framing. Late at night he works by hand, tired: he looks at the monitor, then writes "
                      "a few numbers in the paper notebook with the pen, looks back at the monitor, writes again, then "
                      "pauses, rubs his eyes with one hand and lets out a tired sigh, and goes back to the monitor. "
                      "Small, natural movements. The monitor stays exactly where it is, its screen steady. LOCKED-OFF "
                      "STATIC CAMERA on a tripod: no camera movement, no zoom, no pan.",
        },
        "ask": {
            "seconds": 9,
            "reference": "couch-back-still.png",
            "prompt": "Animate the reference image exactly as it is: the same man seen from behind, the same sofa, "
                      "living room, TV and framing. For the first two seconds he watches the TV, relaxed. Then he turns "
                      "his head slightly to his right toward the smartphone lying face down on the sofa cushion beside "
                      "him, picks it up with his right hand and brings it up in front of his chest, holding it there "
                      "and looking down at it, the phone hidden in front of his body; he stays sitting. He then taps "
                      "it once with his thumb and nods slightly. He never turns his face toward the camera. The TV "
                      "shows the same calm, softly blurred image the whole time. LOCKED-OFF STATIC CAMERA on a "
                      "tripod: no camera movement, no zoom, no pan.",
        },
        "done": {
            "seconds": 10,
            "reference": "couch-profile-still.png",
            "prompt": "Animate the reference image exactly as it is: the same man in profile, the same sofa, room, "
                      "side table and framing. For the first two seconds he watches the TV, relaxed. Then he picks up "
                      "the smartphone lying face down on the side table with his right hand and holds it in front of "
                      "him at chest height, its screen facing him (we only see the back and edge of the phone), reads "
                      "it, and a calm, satisfied smile spreads across his face; he gives a small nod and leans back "
                      "into the sofa, still holding the phone. He never turns his face toward the camera. LOCKED-OFF "
                      "STATIC CAMERA on a tripod: no camera movement, no zoom, no pan.",
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
        "whiteboard": {
            "refs": ["apps/web/public/portfolio/scene.webp"],
            "prompt": (
                "The reference image only sets the look: the same night-time mood, warm amber lamp light and cool "
                "teal ambient glow, the same color grading. It is NOT the place and the man in it must NOT appear. "
                "Create ONE single continuous cinematic photograph, 16:9, not a collage. A small, modern business "
                "office in the evening. A woman in her late thirties, the owner of a small business, smart casual "
                "(dark green blouse, dark trousers), dark hair tied back, stands at the LEFT edge of a large "
                "wall-mounted whiteboard, turned three-quarters toward it, holding an uncapped black marker, "
                "thoughtful. The whiteboard fills the center and right of the frame, seen almost straight on, "
                "slightly from her side. On it: a neat grid of 12 square sticky notes, 4 columns by 3 rows, evenly "
                "spaced with generous gaps, alternating soft yellow and light mint green. Every sticky note is "
                "COMPLETELY BLANK: no writing, no drawings, no marks anywhere on the notes or on the board. She "
                "does not cover any note. "
                "Lighting: a warm amber desk lamp to the left, a cool teal glow from a laptop screen out of frame, "
                "the room falling off into darkness at the edges; the board is evenly lit so every note is clearly "
                "visible. Camera: eye level, 35mm, medium-wide, sharp focus on the board and on her. Photorealistic, "
                "natural skin texture. No readable text, no logos, no watermark, no other people."),
        },
        # v2 (user, 2026-11-22): facial hair like his real photo; 5a with a profile angle that keeps his likeness
        "coding-v2": {
            "refs": ["scripts/media/out/portfolio-ai-agents-overview/coding-still.png", "C:/Users/Trollo/Desktop/ivan.jpeg"],
            "prompt": (
                "Edit image 1. Keep EVERYTHING in it exactly the same: composition, framing, camera angle, room, "
                "desk, monitors and their screens, lamp, lighting, colors, his pose, hands, shirt, glasses, hair and "
                "face shape. Change ONLY his facial hair so it matches the man in image 2: the cheeks and the sides "
                "of the face are clean-shaven smooth skin with no stubble; keep a thin, neat mustache, a short beard "
                "on the chin, and a fine short line of beard along the lower edge of the jaw. Do NOT slim or reshape "
                "the face: keep exactly the same full cheeks, the same soft rounded jaw and the same face volume as "
                "in image 1. Same person, same identity. 16:9, photorealistic, no text."),
        },
        "requests-v2": {
            "refs": ["C:/Users/Trollo/Desktop/ivan.jpeg", "scripts/media/out/portfolio-ai-agents-overview/coding-v2-still.png"],
            "prompt": (
                "Image 1 is the identity reference: this exact real man must be instantly recognizable: same face "
                "shape, warm tan skin, short dark hair faded on the sides, thin dark metal rectangular glasses, a "
                "thin neat mustache and a short beard on the chin, cheeks clean-shaven. Image 2 shows him in his home "
                "office at night: keep the same room, desk, three monitors on arms, amber lamp, teal glow, the same "
                "light beige button-up shirt and the same face as in image 2. "
                "Create ONE single continuous cinematic photograph, 16:9, not a collage. The camera is behind him and "
                "to his right, a bit higher, so we see his RIGHT PROFILE clearly (glasses, nose, mustache, chin "
                "beard, ear), his right shoulder and arm in the lower right of the frame, and beyond him the CENTER "
                "monitor large, sharp and unobstructed in the middle of the frame, showing a calm dark messaging app "
                "as soft shapes; the other monitors partly visible at the edges. He is reading the center monitor, "
                "one hand on the mouse. Lighting: cool teal screen glow on his face, warm amber rim light. "
                "Photorealistic, 35mm, sharp focus on his profile and the screen. No readable words, no logos, no "
                "watermark, no other people."),
        },
        "requests": {
            "refs": ["C:/Users/Trollo/Desktop/ivan.jpeg", "scripts/media/out/portfolio-ai-agents-overview/coding-still.png"],
            "prompt": (
                "Reference 1 is the identity reference: this exact real man (short dark hair, thin dark metal "
                "rectangular glasses, light beige button-up shirt). Reference 2 is his home office at night: keep the "
                "same room, the same walnut desk, the same three slim monitors on arms, the same amber desk lamp and "
                "teal glow. Create ONE single continuous cinematic photograph, 16:9, not a collage, seen from BEHIND "
                "him and slightly to his right, over his right shoulder: the back and right side of his head with the "
                "right temple of his glasses, his right shoulder and arm, in the lower right of the frame, slightly "
                "soft. He sits facing the monitors, relaxed, one hand on the mouse, reading. In front of him the "
                "center monitor is large and sharp in the middle of the frame, a clean evenly lit rectangle with "
                "thin black bezels and visible corners, showing a calm dark messaging app with a list of "
                "conversations as soft shapes; the left and right monitors are partly visible at the edges. "
                "Lighting: cool teal-cyan screen glow on him, warm amber rim light from the lamp, the room falling off "
                "into darkness. Photorealistic, 35mm. No readable words, no logos, no watermark, no other people."),
        },
        "viewer": {
            "refs": ["apps/web/public/portfolio/scene.webp"],
            "prompt": (
                "The reference image only sets the look: night-time mood, warm amber lamp light, a cool teal ambient "
                "glow, the same color grading. Its place and its man must NOT appear. "
                "Create ONE single continuous cinematic photograph, 16:9, not a collage. A business owner, a woman in "
                "her early forties with shoulder-length dark hair and a navy blazer, sits at the desk of her modern "
                "office in the evening, city lights softly out of focus through the window. On the desk in front of "
                "her a smartphone stands in a small desk stand, in LANDSCAPE orientation, its screen facing her and "
                "angled so the camera sees the whole screen clearly. The screen is completely BLACK, off, a clean "
                "glossy black rectangle with thin bezels and visible corners; nothing on it. The camera is behind "
                "her and slightly to her right, at her shoulder height: her right shoulder and the side of her head "
                "are in the right foreground, softly out of focus, and the phone on its stand is sharp in the center "
                "of the frame, about a third of the frame wide, with nothing in front of it. A coffee cup and a "
                "notebook on the desk. Photorealistic, 35mm. No readable text, no logos, no watermark, no other people."),
        },
        "phone": {
            "refs": ["apps/web/public/portfolio/scene.webp"],
            "prompt": (
                "The reference image only sets the look: night-time mood, warm amber lamp light, a cool teal ambient "
                "glow, the same color grading. Its place and its man must NOT appear. "
                "Create ONE single continuous cinematic photograph, 16:9, not a collage. A small business owner, a "
                "man in his early thirties with a short dark beard and a casual dark green shirt, sits on a stool at "
                "the wooden counter of his own small shop after closing time: shelves with products and a few warm "
                "pendant lights glow softly out of focus behind him. He is in the right half of the frame, turned "
                "three-quarters toward the left of the frame, relaxed, holding his smartphone in both hands at "
                "chest height in front of him. We see the BACK of the phone: its screen faces him, never the camera. "
                "Above and to the left of the phone there is calm, dark, softly blurred shop background. "
                "Eye level, 50mm, medium shot from mid-thigh up, sharp focus on him and the phone, photorealistic, "
                "natural skin texture. No readable text, no logos, no watermark, no other people."),
        },
        "brain": {
            "refs": [],
            "aspect": "1:1",
            "prompt": (
                "A single glowing emblem of a human brain made of fine luminous circuit-board lines and small round "
                "nodes, like a neural network, seen from the side, elegant and symmetrical in its detail. Color: "
                "bright teal-cyan (#5eead4) glowing lines with a soft bloom, a few white-hot nodes. Centered, filling "
                "about 70% of the frame, on a PURE BLACK background (#000000) with nothing else: no text, no logo, "
                "no frame, no reflections, no floor. Crisp, high detail, vector-like but luminous."),
        },
        # v2 (user, 2026-11-22): no person; the circles are drawn in code, stroke by stroke, so they look natural
        "whiteboard-empty": {
            "refs": ["scripts/media/out/portfolio-ai-agents-overview/whiteboard-still.png"],
            "prompt": (
                "The reference image shows the office and the whiteboard. Create ONE single continuous cinematic "
                "photograph, 16:9, not a collage, of the SAME office and the SAME whiteboard on its stand, with the "
                "same night-time mood: warm amber desk lamp, cool teal ambient glow, dark room. NOBODY is in the "
                "frame: no person, no hands. The camera is closer and almost straight-on, a little to the left of "
                "center: the whiteboard fills most of the frame, with a glimpse of the dark office, the warm lamp "
                "and the desk at the left edge. On the board: the same neat grid of 15 square sticky notes, 5 "
                "columns by 3 rows, evenly spaced with generous gaps, alternating soft yellow and light mint green. "
                "Every sticky note is COMPLETELY BLANK: no writing, no marks anywhere on the notes or the board. A "
                "black whiteboard marker with its cap on lies on the tray at the bottom of the board. The board is "
                "evenly lit so every note is clearly visible. Eye level, 35mm, sharp focus on the board, "
                "photorealistic. No readable text, no logos, no watermark."),
        },
    },
    "automation-overview": {
        "manual": {
            "refs": ["apps/web/public/portfolio/scene.webp"],
            "prompt": (
                "The reference image only sets the look: night-time mood, warm amber lamp light, a cool teal ambient "
                "glow, the same color grading. Its place and its man must NOT appear. "
                "Create ONE single continuous cinematic photograph, 16:9, not a collage. A man in his early thirties, "
                "short dark curly hair, a short dark beard, a plain heather-grey hoodie, sits at a cluttered desk in a "
                "small apartment late at night, visibly tired, shoulders slumped. In front of him a single desktop "
                "monitor glows with a bright spreadsheet-like page of rows and columns as soft unreadable shapes; next "
                "to the keyboard an open paper notebook with handwritten columns of numbers, a pen in his right hand "
                "resting on the page, two empty coffee mugs and a crumpled energy-drink can. The camera is in front of "
                "him and to his left at eye level, three-quarter view: we see his tired face lit by the cool screen "
                "glow, the monitor from its side at the right edge of the frame (its screen angled away, partly "
                "visible), the notebook and his hands. A warm desk lamp on the left; the room falls off into darkness. "
                "Photorealistic, 35mm, natural skin texture. No readable text, no logos, no watermark, no other people."),
        },
        "couch-back": {
            "refs": ["scripts/media/out/portfolio-automation-overview/manual-still.png", "apps/web/public/portfolio/scene.webp"],
            "prompt": (
                "Image 1 is the identity reference: the same man (short dark curly hair, short dark beard, heather-grey "
                "hoodie). Image 2 only sets the look: night-time mood, warm amber lamp light, cool teal glow. "
                "Create ONE single continuous cinematic photograph, 16:9, not a collage. A cozy, modern living room in "
                "the evening. The man sits relaxed at the RIGHT END of a deep dark-green sofa, right next to its armrest, "
                "watching a large wall-mounted TV. The camera is BEHIND the sofa and slightly to his LEFT, a little "
                "above the sofa back: we see the back of his head, his left ear and a hint of his beard line, and his "
                "shoulders above the sofa back, in the center-right of the frame. On the wide sofa armrest right beside "
                "his right elbow, within easy reach of his right hand, a smartphone lies FACE DOWN: we only see its "
                "plain dark back, never its screen. The TV in the upper left shows a calm, softly out-of-focus nature "
                "scene of a misty green forest, no text, no logos. A warm floor lamp at the far right, the room "
                "otherwise dark. Above his right shoulder and above the phone there is calm, dark, empty wall "
                "space. Photorealistic, 35mm. No readable text, no logos, no watermark, no other people."),
        },
        "couch-profile": {
            "refs": ["scripts/media/out/portfolio-automation-overview/manual-still.png",
                     "scripts/media/out/portfolio-automation-overview/couch-back-still.png"],
            "prompt": (
                "Image 1 is the identity reference: this exact same man (same face, short dark curly hair, short dark "
                "beard, heather-grey hoodie). Image 2 is his living room: keep the same dark-green sofa, warm floor "
                "lamp, TV and night mood. Create ONE single continuous cinematic photograph, 16:9, not a collage. The "
                "man sits relaxed on the sofa in PROFILE, seen from his RIGHT side at eye level, facing the left of the "
                "frame toward the TV (the TV is out of frame or a soft glow at the left edge). He is in the center-left "
                "of the frame from the knees up, calm and content. Beside him on the RIGHT, closer to the camera, a "
                "small wooden side table with a smartphone lying FACE DOWN on it (we see its dark back). Above the side "
                "table and above his hands there is calm, dark, empty space. Warm lamp light on his face, a cool teal "
                "glow from the TV. Photorealistic, 50mm, natural skin texture. No readable text, no logos, no "
                "watermark, no other people."),
        },
        "robot": {
            "refs": [],
            "aspect": "1:1",
            "prompt": (
                "A single glowing emblem of a friendly robot head with two round eyes and a small antenna, made of fine "
                "luminous circuit-board lines and small round nodes, seen from the front, symmetrical and elegant. "
                "Color: bright teal-cyan (#5eead4) glowing lines with a soft bloom, a few white-hot nodes. Centered, "
                "filling about 65% of the frame, on a PURE BLACK background (#000000) with nothing else: no text, no "
                "logo, no frame, no reflections, no floor. Crisp, high detail, vector-like but luminous."),
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
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": s.get("aspect", "16:9"), "imageSize": "2K"}}}
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
