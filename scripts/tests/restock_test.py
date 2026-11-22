"""Owner-bot restock flow against the real Shopify dev store (no Telegram messages are sent).

    python scripts/tests/restock_test.py

Touches only Clarifying Gel Cleanser: +1 then back to the original number. Telegram calls are replaced by
recorders, so the test checks exactly what the bot would send. Checks:
  - a proposal changes nothing until confirmed; confirm applies it and reads the result back
  - a confirm after the stock moved is rejected by Shopify's compare-and-swap (nothing overwritten)
  - another chat can't propose or confirm; an expired / replayed proposal can't be applied
  - the button handler edits the message and removes the buttons
  - the agent answers "add N units" with a proposal (buttons) and never claims the change happened
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$", line)
    if m:
        os.environ.setdefault(m.group(1), m.group(2).strip("'\""))
sys.path.insert(0, str(ROOT / "apps/api"))

from app import config, notify, owner_agent, restock, shopify_admin, webhooks  # noqa: E402

PRODUCT = "Clarifying Gel Cleanser - 150 ml"
SENT: list[tuple[str, str]] = []


async def _rec_edit(chat_id, message_id, text):
    SENT.append(("edit", text))
    return True


async def _rec_answer(callback_id, text=""):
    SENT.append(("toast", text))


notify.edit_message = _rec_edit
notify.answer_callback = _rec_answer


async def qty() -> int:
    v = next(v for v in await shopify_admin.variants_with_inventory() if v["name"] == PRODUCT)
    return v["qty"]


async def main() -> int:
    owner = config.TELEGRAM_OWNER_CHAT_ID
    c: dict[str, bool] = {}
    start = await qty()
    print(f"start: {PRODUCT} = {start}")

    # 1. propose → nothing changes yet
    res, pid = await restock.propose(owner, "clarifying gel", 1, "add")
    c["propuesta creada"] = bool(pid) and res["proposal"]["new_units"] == start + 1
    c["la propuesta no cambia Shopify"] = await qty() == start

    # 2. other chat can't confirm; owner confirm via the button handler applies it
    out, _ = await restock.confirm("123", pid)
    c["otro chat no puede confirmar"] = "expired" in out.lower() and await qty() == start
    SENT.clear()
    await webhooks._button({"id": "cb1", "data": f"rs:{pid}:y",
                            "message": {"chat": {"id": int(owner)}, "message_id": 1, "text": "Clarifying: 3 → 4. Confirm?"}})
    c["confirmar aplica el cambio"] = await qty() == start + 1
    c["mensaje editado con el resultado"] = any(k == "edit" and "Done" in t for k, t in SENT)
    out, _ = await restock.confirm(owner, pid)
    c["no se puede aplicar dos veces"] = "expired" in out.lower() and await qty() == start + 1

    # 3. compare-and-swap: stock moves after the proposal → confirm is rejected, nothing overwritten
    res, pid = await restock.propose(owner, PRODUCT, start, "set")
    p = restock._PENDING[pid]
    await shopify_admin.set_available(p.item_id, p.location_id, start + 2, start + 1, ref=f"gid://ardea-test/Move/{time.time_ns()}")  # unique: Shopify remembers idempotency keys
    out, toast = await restock.confirm(owner, pid)
    c["CAS: cambio rechazado si el stock se movió"] = toast == "Not applied" and await qty() == start + 2

    # 4. restore the original stock (also exercises 'set' mode)
    res, pid = await restock.propose(owner, PRODUCT, start, "set")
    out, toast = await restock.confirm(owner, pid)
    c["restaurado al valor original"] = toast == "Stock updated" and await qty() == start

    # 5. guard rails
    res, pid = await restock.propose("123", PRODUCT, 5)
    c["otro chat no puede proponer"] = pid is None
    res, pid = await restock.propose(owner, PRODUCT, 900)
    c["límite de 500 unidades"] = pid is None and "500" in res["error"]
    res, pid = await restock.propose(owner, "hyaluronic", 10)
    c["ambiguo: pide elegir variante"] = pid is None and len(res.get("candidates", [])) == 2
    res, pid = await restock.propose(owner, PRODUCT, 3)
    out = restock.cancel(owner, pid)
    c["cancelar no cambia nada"] = "nothing" in out and await qty() == start and pid not in restock._PENDING

    # 6. the agent: proposes with buttons, never claims the change happened (works whatever Vitamin C's stock is)
    vit_before = next(v for v in await shopify_admin.variants_with_inventory() if v["name"].startswith("Vitamin C"))["qty"]
    owner_agent.reset(owner)
    reply, photos, cost, proposal = await owner_agent.ask(owner, "Add 40 units of Vitamin C")
    print("agent reply:", reply.replace("\n", " | "), f"(${cost:.5f})")
    c["agente crea la propuesta"] = bool(proposal) and restock._PENDING[proposal].to_qty == restock._PENDING[proposal].from_qty + 40
    c["agente no dice que ya cambió"] = not re.search(r"\b(done|updated|added|restocked|listo|actualizado)\b", reply, re.I)
    restock.cancel(owner, proposal)
    owner_agent.reset("999")
    reply2, _, _, proposal2 = await owner_agent.ask("999", "add 40 units of Vitamin C")
    c["otro chat: el agente no tiene la herramienta"] = proposal2 is None
    c["Vitamin C sigue igual"] = next(v for v in await shopify_admin.variants_with_inventory()
                                      if v["name"].startswith("Vitamin C"))["qty"] == vit_before

    for k, v in c.items():
        print(("✅" if v else "❌"), k)
    ok = sum(c.values())
    print(f"{ok}/{len(c)} · final {PRODUCT} = {await qty()}")
    return 0 if ok == len(c) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
