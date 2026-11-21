"""Generate a realistic 3-month sales history in the Shopify store (demo data for the owner bot).

    python scripts/shopify/seed_orders.py --plan      # build the plan and print its stats (no API writes)
    python scripts/shopify/seed_orders.py --sample    # create only the first order, for review
    python scripts/shopify/seed_orders.py --all       # create the rest (resumable; ~5 orders/min on dev stores)
    python scripts/shopify/seed_orders.py --delete    # remove every order tagged demo-seed

Shape of the data (deterministic, seed 9): ~45 fictitious customers with @example.com emails (a reserved domain:
nothing is ever delivered), a few loyal buyers and many one-off ones, demand growing over the quarter, busier
weekends and a mid-October campaign spike, product popularity that matches the store's story.
Orders are tagged `demo-seed`, bypass inventory, send no receipts, and the API ignores them for Telegram alerts.
Needs scopes write_orders + write_customers.
"""
from __future__ import annotations

import json
import random
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from shopify_admin import ShopifyAdmin, ShopifyError, raise_user_errors

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).parent / "out"
PLAN, DONE = OUT / "seed_plan.json", OUT / "seed_done.json"
TAG, DAYS, SEED = "demo-seed", 90, 9

FIRST = ["Lucía", "Hannah", "Sofia", "James", "Camila", "Noah", "Amélie", "Diego", "Emma", "Mateo", "Olivia", "Lukas",
         "Valentina", "Ethan", "Chloé", "Marco", "Isabella", "Liam", "Nora", "Pablo", "Mia", "Oscar", "Elena", "Theo",
         "Aisha", "Julian", "Freya", "Tomás", "Grace", "Leo", "Ines", "Samuel", "Zoe", "Hugo", "Maya", "Daniel",
         "Clara", "Felix", "Ana", "Arthur", "Lea", "Rafael", "Sara", "Victor", "Jade"]
LAST = ["Fernández", "Becker", "Rossi", "Carter", "Torres", "Williams", "Laurent", "Morales", "Johansson", "Silva",
        "Brown", "Schmidt", "Ruiz", "Miller", "Dubois", "Bianchi", "García", "Murphy", "Lindqvist", "Navarro",
        "Fischer", "Nilsson", "Romero", "Martin", "Khan", "Weber", "Hansen", "Ortega", "Taylor", "Moreau", "Costa",
        "Cohen", "Evans", "Lefebvre", "Patel", "Wright", "Hoffmann", "Vargas", "Castro", "Bennett", "Roux", "Mendes",
        "Ali", "Duarte", "Kim"]

# handle -> (weight, {variant title: weight})
POPULARITY = {
    "centella-calming-serum": (22, {"30 ml": 1}),
    "niacinamide-zinc-serum": (18, {"30 ml": 1}),
    "hyaluronic-hydration-serum": (16, {"30 ml": 0.65, "60 ml": 0.35}),
    "gentle-cream-cleanser": (13, {"150 ml": 1}),
    "relaxing-sheet-masks": (12, {"1 mask": 0.3, "5 masks": 0.45, "10 masks": 0.25}),
    "vitamin-c-brightening-serum": (11, {"30 ml": 1}),
    "retinal-night-serum": (7, {"30 ml": 1}),
    "clarifying-gel-cleanser": (4, {"150 ml": 1}),
}
FREE_SHIPPING_FROM, SHIPPING = 50.0, 5.95
MAX_ORDERS_PER_CUSTOMER = 10


def variants(s: ShopifyAdmin) -> dict[tuple[str, str], dict]:
    data = s.gql("""{ products(first: 50) { nodes { handle variants(first: 10) { nodes { id title price } } } } }""")
    return {(p["handle"], v["title"]): {"id": v["id"], "price": float(v["price"])}
            for p in data["products"]["nodes"] for v in p["variants"]["nodes"] if p["handle"] in POPULARITY}


def build_plan(var: dict) -> list[dict]:
    rnd = random.Random(SEED)
    customers = [{"first": f, "last": l, "email": f"{f}.{l}".lower().translate(str.maketrans("áéíóúñ", "aeioun")) + "@example.com"}
                 for f, l in zip(FIRST, LAST)]
    loyalty = [1 / (i + 1) ** 0.55 for i in range(len(customers))]  # Zipf-like: a few loyal buyers, a long tail
    handles = list(POPULARITY)
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=DAYS - 1)
    plan, counts = [], {}
    for d in range(DAYS - 1):  # up to yesterday
        day = start + timedelta(days=d)
        rate = 1.5 + 1.3 * d / DAYS                              # demand grows over the quarter
        rate *= 1.3 if day.weekday() >= 5 else 1.0               # busier weekends
        rate *= 2.2 if date(day.year, 10, 14) <= day <= date(day.year, 10, 16) else 1.0  # autumn campaign
        n = sum(1 for _ in range(12) if rnd.random() < rate / 12)  # ~Poisson(rate)
        for _ in range(n):
            c = rnd.choices(range(len(customers)), weights=loyalty)[0]
            while counts.get(c, 0) >= MAX_ORDERS_PER_CUSTOMER:  # even loyal buyers order every ~9 days at most
                c = rnd.choices(range(len(customers)), weights=loyalty)[0]
            counts[c] = counts.get(c, 0) + 1
            k = rnd.choices([1, 2, 3], weights=[0.55, 0.33, 0.12])[0]
            pool, picks = handles[:], []
            while len(picks) < k:  # weighted sampling without replacement
                h = rnd.choices(pool, weights=[POPULARITY[x][0] for x in pool])[0]
                picks.append(h)
                pool.remove(h)
            lines = []
            for h in picks:
                opts = POPULARITY[h][1]
                vt = rnd.choices(list(opts), weights=list(opts.values()))[0]
                lines.append({"handle": h, "variant": vt, "qty": 2 if rnd.random() < 0.12 else 1,
                              "price": var[(h, vt)]["price"]})
            subtotal = sum(ln["price"] * ln["qty"] for ln in lines)
            hour, minute = rnd.choices(range(24), weights=[1, 1, 1, 1, 1, 1, 2, 3, 4, 5, 5, 6, 7, 6, 5, 5, 6, 7, 8, 9, 9, 7, 4, 2])[0], rnd.randrange(60)
            plan.append({"customer": customers[c], "lines": lines,
                         "processed_at": datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc).isoformat(),
                         "shipping": 0.0 if subtotal >= FREE_SHIPPING_FROM else SHIPPING,
                         "subtotal": round(subtotal, 2)})
    plan.sort(key=lambda o: o["processed_at"])
    for i, o in enumerate(plan, 1):
        o["key"] = f"seed-{i:04d}"
    return plan


def stats(plan: list[dict]) -> None:
    revenue = sum(o["subtotal"] + o["shipping"] for o in plan)
    by_cust, by_prod = {}, {}
    for o in plan:
        name = f'{o["customer"]["first"]} {o["customer"]["last"]}'
        by_cust[name] = by_cust.get(name, 0) + o["subtotal"] + o["shipping"]
        for ln in o["lines"]:
            by_prod[ln["handle"]] = by_prod.get(ln["handle"], 0) + ln["qty"]
    print(f"  {len(plan)} orders · {len(by_cust)} customers · revenue ${revenue:,.2f} · "
          f"avg ${revenue / len(plan):.2f} · {plan[0]['processed_at'][:10]} → {plan[-1]['processed_at'][:10]}")
    print("  units by product:", ", ".join(f"{k} {v}" for k, v in sorted(by_prod.items(), key=lambda kv: -kv[1])))
    print("  top 5 customers:", ", ".join(f"{k} ${v:,.0f}" for k, v in sorted(by_cust.items(), key=lambda kv: -kv[1])[:5]))


def create(s: ShopifyAdmin, var: dict, o: dict) -> dict:
    total = round(o["subtotal"] + o["shipping"], 2)
    usd = lambda v: {"shopMoney": {"amount": f"{v:.2f}", "currencyCode": "USD"}}  # noqa: E731
    old = datetime.fromisoformat(o["processed_at"]).date() < datetime.now(timezone.utc).date() - timedelta(days=4)
    order = {
        "email": o["customer"]["email"], "currency": "USD", "processedAt": o["processed_at"],
        "customer": {"toUpsert": {"email": o["customer"]["email"], "firstName": o["customer"]["first"],
                                  "lastName": o["customer"]["last"]}},
        "lineItems": [{"variantId": var[(ln["handle"], ln["variant"])]["id"], "quantity": ln["qty"],
                       "priceSet": usd(ln["price"])} for ln in o["lines"]],
        "shippingLines": [{"title": "Free shipping" if not o["shipping"] else "Standard shipping",
                           "priceSet": usd(o["shipping"])}],
        "financialStatus": "PAID",
        "transactions": [{"kind": "SALE", "status": "SUCCESS", "gateway": "manual", "amountSet": usd(total),
                          "processedAt": o["processed_at"]}],
        "tags": [TAG], "sourceName": "web", "sourceIdentifier": o["key"],
    }
    if old:
        order["fulfillmentStatus"] = "FULFILLED"
    res = s.gql("""mutation($order: OrderCreateOrderInput!, $options: OrderCreateOptionsInput) {
        orderCreate(order: $order, options: $options) { order { id name processedAt totalPriceSet { shopMoney { amount } } }
          userErrors { field message } } }""",
                {"order": order, "options": {"inventoryBehaviour": "BYPASS", "sendReceipt": False,
                                             "sendFulfillmentReceipt": False}})["orderCreate"]
    raise_user_errors(res, f"orderCreate {o['key']}")
    return res["order"]


def main() -> int:
    OUT.mkdir(exist_ok=True)
    s = ShopifyAdmin()
    if "--delete" in sys.argv:
        n = 0
        while True:
            ids = [o["id"] for o in s.gql(f'{{ orders(first: 50, query: "tag:{TAG}") {{ nodes {{ id }} }} }}')["orders"]["nodes"]]
            if not ids:
                break
            for oid in ids:
                raise_user_errors(s.gql("mutation($id: ID!) { orderDelete(orderId: $id) { userErrors { field message } } }",
                                        {"id": oid})["orderDelete"], "orderDelete")
                n += 1
        DONE.unlink(missing_ok=True)
        print(f"  deleted {n} demo orders")
        return 0

    var = variants(s)
    if PLAN.exists() and "--replan" not in sys.argv:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
    else:
        plan = build_plan(var)
        PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    stats(plan)
    if "--plan" in sys.argv:
        return 0
    for need in ("write_orders", "write_customers"):
        if not s.has_scope(need):
            raise SystemExit(f"Missing scope {need}: add it in the Dev Dashboard app version and release it.")

    done = json.loads(DONE.read_text(encoding="utf-8")) if DONE.exists() else {}
    todo = [o for o in plan if o["key"] not in done][: 1 if "--sample" in sys.argv else None]
    delay = 12.5  # dev stores accept about 5 new orders per minute through the API
    for i, o in enumerate(todo, 1):
        for attempt in range(6):
            try:
                made = create(s, var, o)
                break
            except ShopifyError as e:
                msg = str(e)
                if attempt < 5 and ("Too many" in msg or "throttl" in msg.lower() or "429" in msg or "limit" in msg.lower()):
                    time.sleep(60)
                    continue
                raise
        done[o["key"]] = made["id"]
        DONE.write_text(json.dumps(done, indent=1), encoding="utf-8")
        print(f"  [{i}/{len(todo)}] {made['name']} {made['processedAt'][:10]} ${float(made['totalPriceSet']['shopMoney']['amount']):.2f}"
              f" · {o['customer']['first']} {o['customer']['last']} · " + ", ".join(f"{ln['qty']}× {ln['handle']} {ln['variant']}" for ln in o["lines"]),
              flush=True)
        if i < len(todo):
            time.sleep(delay)
    print(f"  done: {len(done)}/{len(plan)} orders created")
    return 0


if __name__ == "__main__":
    sys.exit(main())
