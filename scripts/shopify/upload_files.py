"""Upload category media (hero image, how-to video, poster) to Shopify Files and record the CDN URLs.

    python upload_files.py serums --hero ../media/out/serums/hero-165339.jpg \
        --video ../media/out/serums/serums-howto.mp4 --poster ../media/out/serums/serums-howto-poster.jpg

Writes apps/web/src/content/category-media.json (slug -> urls), which the category page reads.
Flow: stagedUploadsCreate (IMAGE|VIDEO) -> multipart POST -> fileCreate -> poll until READY -> read CDN url.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from shopify_admin import ShopifyAdmin, ShopifyError, raise_user_errors
from upload_images import multipart_post

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
MEDIA_JSON = ROOT / "apps/web/src/content/category-media.json"


def upload(s: ShopifyAdmin, path: Path, kind: str, alt: str) -> dict:
    data = path.read_bytes()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "mp4": "video/mp4"}[path.suffix.lower().lstrip(".")]
    staged = s.gql("""mutation($i:[StagedUploadInput!]!){ stagedUploadsCreate(input:$i){
                        stagedTargets { url resourceUrl parameters { name value } } userErrors { field message } } }""",
                   {"i": [{"resource": kind, "filename": path.name, "mimeType": mime, "httpMethod": "POST", "fileSize": str(len(data))}]})["stagedUploadsCreate"]
    raise_user_errors(staged, f"stage {path.name}")
    t = staged["stagedTargets"][0]
    # videos are several MB: a 120 s write timeout failed on a slow uplink (2026-11-20); retry once
    for attempt in range(2):
        try:
            multipart_post(t["url"], [(p["name"], p["value"]) for p in t["parameters"]], path.name, data, mime,
                           timeout=900 if kind == "VIDEO" else 180)
            break
        except OSError as e:
            if attempt:
                raise ShopifyError(f"upload of {path.name} failed twice: {e}") from None
            print(f"  retrying {path.name} after: {e}")

    created = s.gql("""mutation($f:[FileCreateInput!]!){ fileCreate(files:$f){ files { id fileStatus } userErrors { field message } } }""",
                    {"f": [{"originalSource": t["resourceUrl"], "contentType": kind, "alt": alt}]})["fileCreate"]
    raise_user_errors(created, f"fileCreate {path.name}")
    fid = created["files"][0]["id"]

    q = """query($id:ID!){ node(id:$id){ ... on MediaImage { fileStatus image { url width height } }
                                          ... on Video { fileStatus duration sources { url mimeType width height } }
                                          ... on GenericFile { fileStatus url } } }"""
    for _ in range(90):  # videos take a while to transcode
        n = s.gql(q, {"id": fid})["node"]
        if n["fileStatus"] == "READY":
            break
        if n["fileStatus"] == "FAILED":
            raise ShopifyError(f"{path.name}: processing FAILED")
        time.sleep(4)
    else:
        raise ShopifyError(f"{path.name}: still processing after 6 min")

    if kind == "IMAGE":
        return {"id": fid, "url": n["image"]["url"], "width": n["image"]["width"], "height": n["image"]["height"], "alt": alt}
    if kind == "FILE":
        return {"id": fid, "url": n["url"]}
    mp4 = sorted((x for x in n["sources"] if x["mimeType"] == "video/mp4"), key=lambda x: x["height"], reverse=True)
    return {"id": fid, "duration_ms": n.get("duration"),
            "sources": [{"url": x["url"], "height": x["height"], "width": x["width"]} for x in mp4]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--hero", type=Path)
    ap.add_argument("--video", type=Path)
    ap.add_argument("--poster", type=Path)
    ap.add_argument("--raw-video", type=Path, nargs="+", metavar="MP4",
                    help="upload our own encodes as generic files (served byte-for-byte; Shopify's video "
                         "transcodes were 2-3x larger, measured 2026-11-20). Name them <name>-<height>.mp4")
    a = ap.parse_args()
    media = json.loads(MEDIA_JSON.read_text(encoding="utf-8")) if MEDIA_JSON.exists() else {}
    entry = media.get(a.slug, {})
    s = ShopifyAdmin()
    media[a.slug] = entry

    def save():  # after every file: a failed video upload once orphaned the hero + poster that had succeeded
        MEDIA_JSON.write_text(json.dumps(media, indent=2) + "\n", encoding="utf-8", newline="\n")

    if a.hero:
        entry["hero"] = upload(s, a.hero, "IMAGE", f"Ardea Skin {a.slug} in use")
        save()
        print("hero  ->", entry["hero"]["url"][:90])
    if a.poster:
        entry["poster"] = upload(s, a.poster, "IMAGE", f"Ardea Skin {a.slug} how-to video")
        save()
        print("poster->", entry["poster"]["url"][:90])
    if a.video:
        entry["video"] = upload(s, a.video, "VIDEO", f"How to use Ardea Skin {a.slug}")
        save()
        print("video ->", [(x["height"], x["url"][:70]) for x in entry["video"]["sources"]])
    if a.raw_video:
        sources = []
        for p in a.raw_video:
            f = upload(s, p, "FILE", f"Ardea Skin {a.slug} video")
            height = int(p.stem.rsplit("-", 1)[-1])
            sources.append({"url": f["url"], "height": height, "width": round(height * 16 / 9), "id": f["id"]})
        entry["video"] = {"sources": sorted(sources, key=lambda x: -x["height"])}
        save()
        print("raw   ->", [(x["height"], x["url"][:70]) for x in entry["video"]["sources"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
