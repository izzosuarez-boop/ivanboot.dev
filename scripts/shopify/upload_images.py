"""Upload the approved product images (scripts/images/approved.json) to Shopify.

    python upload_images.py            # products that have no image yet
    python upload_images.py --replace  # also replace existing product images

Flow per image: stagedUploadsCreate -> multipart POST of the file to the staged target ->
productUpdate(media: originalSource=resourceUrl) -> poll until Shopify finishes processing.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import uuid
from pathlib import Path

from shopify_admin import ShopifyAdmin, ShopifyError, raise_user_errors

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "scripts/images"
CATALOG = {p["handle"]: p for p in json.loads((ROOT / "scripts/shopify/catalog.json").read_text(encoding="utf-8"))["products"]}


def multipart_post(url: str, fields: list[tuple[str, str]], file_name: str, data: bytes, mime: str, timeout: int = 120) -> int:
    boundary = uuid.uuid4().hex
    body = bytearray()
    for name, value in fields:  # parameters must come before the file
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
             f"Content-Type: {mime}\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=bytes(body), method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def upload_one(s: ShopifyAdmin, handle: str, path: Path, replace: bool) -> str:
    prod = s.gql('query($h:String!){ productByIdentifier(identifier:{handle:$h}){ id title media(first:10){ nodes { id } } } }',
                 {"h": handle})["productByIdentifier"]
    if not prod:
        raise ShopifyError(f"{handle}: product not found")
    existing = [m["id"] for m in prod["media"]["nodes"]]
    if existing and not replace:
        return "skipped (already has an image)"

    data = path.read_bytes()
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    staged = s.gql("""mutation($i:[StagedUploadInput!]!){ stagedUploadsCreate(input:$i){
                        stagedTargets { url resourceUrl parameters { name value } } userErrors { field message } } }""",
                   {"i": [{"resource": "IMAGE", "filename": f"ardea-{handle}{path.suffix}", "mimeType": mime,
                           "httpMethod": "POST", "fileSize": str(len(data))}]})["stagedUploadsCreate"]
    raise_user_errors(staged, f"{handle} staged upload")
    target = staged["stagedTargets"][0]
    status = multipart_post(target["url"], [(p["name"], p["value"]) for p in target["parameters"]],
                            f"ardea-{handle}{path.suffix}", data, mime)
    if status not in (200, 201, 204):
        raise ShopifyError(f"{handle}: staged POST returned {status}")

    p = CATALOG[handle]
    alt = f"{p['title']} ({p['variants'][0]['size']}) by Ardea Skin"
    r = s.gql("""mutation($p:ProductUpdateInput!, $m:[CreateMediaInput!]){ productUpdate(product:$p, media:$m){
                   product { media(first:10){ nodes { id status } } } userErrors { field message } } }""",
              {"p": {"id": prod["id"]}, "m": [{"originalSource": target["resourceUrl"], "alt": alt, "mediaContentType": "IMAGE"}]})
    raise_user_errors(r["productUpdate"], f"{handle} attach media")
    new_ids = [m["id"] for m in r["productUpdate"]["product"]["media"]["nodes"] if m["id"] not in existing]

    # Shopify processes media asynchronously; wait until READY (or FAILED)
    for _ in range(30):
        nodes = s.gql('query($id:ID!){ product(id:$id){ media(first:10){ nodes { id status } } } }', {"id": prod["id"]})["product"]["media"]["nodes"]
        states = {n["id"]: n["status"] for n in nodes if n["id"] in new_ids}
        if states and all(v in ("READY", "FAILED") for v in states.values()):
            break
        time.sleep(2)
    if any(v == "FAILED" for v in states.values()):
        raise ShopifyError(f"{handle}: Shopify failed to process the image")

    if replace and existing:  # remove the old images only after the new one is live
        d = s.gql('mutation($ids:[ID!]!){ fileDelete(fileIds:$ids){ deletedFileIds userErrors { field message } } }', {"ids": existing})
        raise_user_errors(d["fileDelete"], f"{handle} delete old media")
    return f"uploaded {len(data)//1024} KB -> {', '.join(states.values())}" + (f" (replaced {len(existing)})" if replace and existing else "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()
    approved = json.loads((IMAGES / "approved.json").read_text(encoding="utf-8"))["images"]
    unknown = set(approved) - set(CATALOG)
    missing_files = [f for f in approved.values() if not (IMAGES / "out" / f).exists()]
    if unknown or missing_files:
        print(f"unknown handles: {sorted(unknown)} | missing files: {missing_files}")
        return 1
    s = ShopifyAdmin()
    for handle, fname in approved.items():
        try:
            print(f"  {handle:32} {upload_one(s, handle, IMAGES / 'out' / fname, a.replace)}")
        except ShopifyError as e:
            print(f"  {handle:32} ERROR {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
