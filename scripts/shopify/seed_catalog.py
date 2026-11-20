"""Seed the Ardea Skin demo catalog into the Shopify dev store.

    python seed_catalog.py --dry-run   # validate data + check scopes, no writes
    python seed_catalog.py             # create/update everything, then verify via Storefront API

Idempotent: products and collections are upserted by handle. Stock is only set when a
product is CREATED, so re-running never overwrites stock that changed through demo orders.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

from shopify_admin import ShopifyAdmin, ShopifyError, load_env, raise_user_errors

sys.stdout.reconfigure(encoding="utf-8")
CATALOG = json.loads((Path(__file__).parent / "catalog.json").read_text(encoding="utf-8"))
NS = CATALOG["metafield_namespace"]
REQUIRED_SCOPES = ["write_products", "write_inventory", "read_locations", "write_publications"]

# key -> (type, name, validations)
METAFIELDS = {
    "skin_types": ("list.single_line_text_field", "Skin types", [("choices", CATALOG["allowed"]["skin_types"])]),
    "concerns": ("list.single_line_text_field", "Skin concerns", [("choices", CATALOG["allowed"]["concerns"])]),
    "key_ingredients": ("list.single_line_text_field", "Key ingredients", []),
    "how_to_use": ("multi_line_text_field", "How to use", []),
    "cautions": ("multi_line_text_field", "Cautions", []),
    "routine_step": ("number_integer", "Routine step (1 cleanse ... 5 protect, 6 weekly mask)", [("min", "1"), ("max", "6")]),
    "usage_time": ("single_line_text_field", "When to use", [("choices", ["AM", "PM", "AM & PM"])]),
    "texture": ("single_line_text_field", "Texture", []),
    "fragrance_free": ("boolean", "Fragrance free", []),
}


# -- validation (runs before any write) -----------------------------------------
def validate() -> list[str]:
    problems, handles, skus = [], set(), set()
    allowed = CATALOG["allowed"]
    for p in CATALOG["products"]:
        h = p["handle"]
        if h in handles:
            problems.append(f"duplicate handle {h}")
        handles.add(h)
        for st in p["skin_types"]:
            if st not in allowed["skin_types"]:
                problems.append(f"{h}: unknown skin type {st}")
        for c in p["concerns"]:
            if c not in allowed["concerns"]:
                problems.append(f"{h}: unknown concern {c}")
        if not p.get("retired") and not 1 <= p["routine_step"] <= 3:
            problems.append(f"{h}: routine_step out of range")
        if p["usage_time"] not in ("AM", "PM", "AM & PM"):
            problems.append(f"{h}: bad usage_time")
        for v in p["variants"]:
            if v["sku"] in skus:
                problems.append(f"duplicate sku {v['sku']}")
            skus.add(v["sku"])
            if "compare_at" in v and float(v["compare_at"]) <= float(v["price"]):
                problems.append(f"{v['sku']}: compare_at must be above price")
        if set(p["es"]) != {"title", "summary", "benefits", "how_to_use", "cautions"}:
            problems.append(f"{h}: incomplete Spanish copy")
    return problems


# -- builders ----------------------------------------------------------------------
def description_html(p: dict) -> str:
    items = "".join(f"<li>{b}</li>" for b in p["benefits"])
    return f"<p>{p['summary']}</p><ul>{items}</ul>"


def tags(p: dict) -> list[str]:
    t = [f"skin-{s}" for s in p["skin_types"]] + [f"concern-{c}" for c in p["concerns"]]
    t.append(f"step-{p['routine_step']}")
    t += {"AM": ["time-am"], "PM": ["time-pm"], "AM & PM": ["time-am", "time-pm"]}[p["usage_time"]]
    return t


def metafields(p: dict) -> list[dict]:
    raw = {
        "skin_types": json.dumps(p["skin_types"]),
        "concerns": json.dumps(p["concerns"]),
        "key_ingredients": json.dumps(p["key_ingredients"]),
        "how_to_use": p["how_to_use"],
        "cautions": p["cautions"],
        "routine_step": str(p["routine_step"]),
        "usage_time": p["usage_time"],
        "texture": p["texture"],
        "fragrance_free": "true" if p["fragrance_free"] else "false",
    }
    return [{"namespace": NS, "key": k, "type": METAFIELDS[k][0], "value": v} for k, v in raw.items()]


def product_input(p: dict, location_id: str | None) -> dict:
    option = p.get("option_name", "Size")  # e.g. "Pack" for the sheet masks
    variants = []
    for v in p["variants"]:
        vi = {
            "optionValues": [{"optionName": option, "name": v["size"]}],
            "price": v["price"],
            "sku": v["sku"],
            "inventoryPolicy": "DENY",
            "inventoryItem": {"tracked": True},
        }
        if "compare_at" in v:
            vi["compareAtPrice"] = v["compare_at"]
        if location_id is not None:
            vi["inventoryQuantities"] = [{"locationId": location_id, "name": "available", "quantity": v["stock"]}]
        variants.append(vi)
    return {
        "handle": p["handle"],
        "title": p["title"],
        "vendor": CATALOG["brand"],
        "productType": p["type"],
        "status": "ACTIVE",
        "descriptionHtml": description_html(p),
        "tags": tags(p),
        "seo": {"title": f"{p['title']} | {CATALOG['brand']}", "description": p["summary"][:160]},
        "productOptions": [{"name": option, "position": 1, "values": [{"name": v["size"]} for v in p["variants"]]}],
        "variants": variants,
        "metafields": metafields(p),
    }


# -- steps -------------------------------------------------------------------------
def ensure_metafield_definitions(s: ShopifyAdmin) -> None:
    d = s.gql('query($ns:String!){ metafieldDefinitions(first:50, ownerType:PRODUCT, namespace:$ns){ nodes { key } } }', {"ns": NS})
    existing = {n["key"] for n in d["metafieldDefinitions"]["nodes"]}
    for key, (mtype, name, validations) in METAFIELDS.items():
        if key in existing:
            print(f"  = definition {NS}.{key}")
            continue
        definition = {
            "namespace": NS, "key": key, "name": name, "type": mtype, "ownerType": "PRODUCT",
            "access": {"storefront": "PUBLIC_READ"},
            "validations": [{"name": n, "value": json.dumps(v) if isinstance(v, list) else v} for n, v in validations],
        }
        r = s.gql('mutation($d:MetafieldDefinitionInput!){ metafieldDefinitionCreate(definition:$d){ createdDefinition { key } userErrors { field message } } }', {"d": definition})
        raise_user_errors(r["metafieldDefinitionCreate"], f"definition {key}")
        print(f"  + definition {NS}.{key}")


def primary_location(s: ShopifyAdmin) -> str:
    d = s.gql("{ locations(first:10){ nodes { id name isActive } } }")
    active = [n for n in d["locations"]["nodes"] if n["isActive"]]
    if not active:
        raise ShopifyError("No active location found")
    print(f"  location: {active[0]['name']}")
    return active[0]["id"]


def upsert_products(s: ShopifyAdmin, location_id: str) -> list[tuple[str, bool]]:
    ids = []  # (gid, retired)
    for p in CATALOG["products"]:
        exists = s.gql('query($h:String!){ productByIdentifier(identifier:{handle:$h}){ id } }', {"h": p["handle"]})["productByIdentifier"]
        r = s.gql(
            """mutation($id:ProductSetIdentifiers, $input:ProductSetInput!){
                 productSet(identifier:$id, input:$input, synchronous:true){
                   product { id handle variants(first:10){ nodes { sku inventoryQuantity } } }
                   userErrors { field message code } } }""",
            {"id": {"handle": p["handle"]}, "input": product_input(p, None if exists else location_id)})
        raise_user_errors(r["productSet"], p["handle"])
        prod = r["productSet"]["product"]
        ids.append((prod["id"], bool(p.get("retired"))))
        stock = ", ".join(f"{v['sku']}={v['inventoryQuantity']}" for v in prod["variants"]["nodes"])
        print(f"  {'~' if exists else '+'} {p['handle']}  [{stock}]{'  (retired)' if p.get('retired') else ''}")
    return ids


def upsert_collections(s: ShopifyAdmin) -> list[tuple[str, bool]]:
    ids = []  # (gid, retired)
    for c in CATALOG["collections"]:
        column, *conditions = c["rule"]
        coll = {
            "handle": c["handle"], "title": c["title"],
            "ruleSet": {"appliedDisjunctively": len(conditions) > 1,
                        "rules": [{"column": column, "relation": "EQUALS", "condition": cond} for cond in conditions]},
        }
        found = s.gql('query($h:String!){ collectionByIdentifier(identifier:{handle:$h}){ id } }', {"h": c["handle"]})["collectionByIdentifier"]
        if found:
            coll["id"] = found["id"]
            r = s.gql('mutation($c:CollectionInput!){ collectionUpdate(input:$c){ collection { id } userErrors { field message } } }', {"c": coll})
            raise_user_errors(r["collectionUpdate"], c["handle"])
            ids.append((r["collectionUpdate"]["collection"]["id"], bool(c.get("retired"))))
            print(f"  ~ collection {c['handle']}{'  (retired)' if c.get('retired') else ''}")
        else:
            r = s.gql('mutation($c:CollectionInput!){ collectionCreate(input:$c){ collection { id } userErrors { field message } } }', {"c": coll})
            raise_user_errors(r["collectionCreate"], c["handle"])
            ids.append((r["collectionCreate"]["collection"]["id"], bool(c.get("retired"))))
            print(f"  + collection {c['handle']}")
    return ids


def publish(s: ShopifyAdmin, items: list[tuple[str, bool]]) -> None:
    """Active items are published to the Headless channel; retired ones are unpublished (kept in Shopify)."""
    pubs = s.gql("{ publications(first:20){ nodes { id name } } }")["publications"]["nodes"]
    targets = [p for p in pubs if "headless" in p["name"].lower()]
    if not targets:
        raise ShopifyError(f"No Headless publication found among: {[p['name'] for p in pubs]}")
    for pub in targets:
        for gid, retired in items:
            op = "publishableUnpublish" if retired else "publishablePublish"
            r = s.gql(f'mutation($id:ID!, $p:[PublicationInput!]!){{ {op}(id:$id, input:$p){{ userErrors {{ field message }} }} }}',
                      {"id": gid, "p": [{"publicationId": pub["id"]}]})
            raise_user_errors(r[op], f"{op} {gid}")
        n_off = sum(1 for _, r_ in items if r_)
        print(f"  '{pub['name']}': published {len(items) - n_off}, unpublished {n_off} (retired)")


def verify_storefront() -> None:
    env = load_env()
    token = env.get("SHOPIFY_STOREFRONT_PUBLIC_TOKEN")
    if not token:
        print("  (no public Storefront token, skipping)")
        return
    q = """{ products(first:50){ nodes { handle availableForSale
              skin: metafield(namespace:"%s", key:"skin_types"){ value } } }
             collections(first:50){ nodes { handle products(first:50){ nodes { handle } } } } }""" % NS
    req = urllib.request.Request(
        f"https://{env['SHOPIFY_SHOP']}.myshopify.com/api/{env.get('SHOPIFY_API_VERSION') or '2026-10'}/graphql.json",
        data=json.dumps({"query": q}).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Shopify-Storefront-Access-Token": token})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())["data"]
    prods = data["products"]["nodes"]
    expected = {p["handle"] for p in CATALOG["products"] if not p.get("retired")}
    retired = {p["handle"] for p in CATALOG["products"] if p.get("retired")}
    visible = {p["handle"] for p in prods}
    print(f"  storefront sees {len(visible & expected)}/{len(expected)} active products"
          + (f"  MISSING: {sorted(expected - visible)}" if expected - visible else "")
          + (f"  RETIRED BUT VISIBLE: {sorted(visible & retired)}" if visible & retired else "  (no retired product visible)"))
    no_mf = [p["handle"] for p in prods if p["handle"] in expected and not p["skin"]]
    print(f"  metafields readable: {'yes' if not no_mf else 'NO for ' + ', '.join(no_mf)}")
    sold_out = [p["handle"] for p in prods if not p["availableForSale"]]
    print(f"  sold out: {sold_out}")
    for c in data["collections"]["nodes"]:
        print(f"    collection {c['handle']}: {len(c['products']['nodes'])} products")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    problems = validate()
    if problems:
        print("Catalog data problems:\n  " + "\n  ".join(problems))
        return 1
    print(f"catalog OK: {len(CATALOG['products'])} products, "
          f"{sum(len(p['variants']) for p in CATALOG['products'])} variants, {len(CATALOG['collections'])} collections")

    s = ShopifyAdmin()
    missing = [sc for sc in REQUIRED_SCOPES if not s.has_scope(sc)]
    if missing:
        print(f"missing scopes: {', '.join(missing)} -> release a new app version with them and approve it on the store")
        return 2
    print("scopes OK")
    if args.dry_run:
        print("dry run: no changes made")
        return 0

    print("metafield definitions:"); ensure_metafield_definitions(s)
    print("inventory:"); loc = primary_location(s)
    print("products:"); product_ids = upsert_products(s, loc)
    print("collections:"); collection_ids = upsert_collections(s)
    print("publishing:"); publish(s, product_ids + collection_ids)
    print("verify (Storefront API, public token):"); verify_storefront()
    return 0


if __name__ == "__main__":
    sys.exit(main())
