# -*- coding: utf-8 -*-
"""
Measures, on Tron's TESTNET (Nile), what each escrow design REALLY costs — to decide between
A (one address per order) and B (a single contract) with numbers instead of intuition.

Touches NO real money: Nile is a test network and its TRX comes free from a faucet.
Touches NOTHING else: this directory is independent from any backend.

WHAT IT MEASURES
    1. One-time deployments (factory and single contract)
    2. Option A: settle one order                      -> 1 transaction
    3. Option A: refund the buyer                      -> the exception path
    4. Option B: register + release one order          -> 2 transactions
    5. Option B: release N orders in a batch           -> B's real advantage
    Energy is converted to TRX at the network's REAL published price, not an invented one.

It also VERIFIES something that can't be assumed: that the address `addressOf()` computes
matches where CREATE2 actually deploys on the TVM. Tron uses prefix 0x41 where Ethereum uses
0xff; if that failed, option A collapses entirely. Better to find out here than after writing
the backend.

USAGE
    1. Create a throwaway test account and get free TRX: https://nileex.io/join/getJoinPage
    2. python scripts/compile.py
    3. export NILE_KEY=<hex private key of that TEST account>
       python scripts/measure_costs.py
"""
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from eth_abi import encode as abi_encode
    from tronpy import Tron
    from tronpy.contract import Contract
    from tronpy.keys import PrivateKey, to_base58check_address, to_hex_address
    from tronpy.providers import HTTPProvider
except ImportError as e:
    print(f"Missing dependency ({e}).  pip install tronpy eth_abi")
    sys.exit(1)

DIR = os.path.dirname(os.path.abspath(__file__))
NETWORK = "https://nile.trongrid.io"
FEE_BPS = 1000           # 10% — a realistic marketplace fee
DECIMALS = 6
BATCH = 5                # how many orders to group when measuring `releaseMany`

# Nile's official test USDT (distributed by the nileex.io faucet). Used instead of a mock
# because real USDT is a much heavier contract: measuring with a toy token would UNDERESTIMATE
# each transfer's cost — which is exactly what we want to know.
USDT_NILE = os.getenv("USDT_NILE", "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf").strip()

# Which option to measure. The faucet gives 1000 TRX per round and deploying a contract is the
# most expensive step, so measuring A and B in one run can run dry halfway.
#   ONLY=A  -> option A only (one address per order) — the decisive one, start here
#   ONLY=B  -> option B only (single contract)
#   unset   -> both
ONLY = os.getenv("ONLY", "").strip().upper()

measurements = []        # [(label, energy)]


# ── helpers ──────────────────────────────────────────────────────────────────────────────────
def hex20(address: str) -> str:
    """Tron base58 -> the 20 bytes the ABI expects (without the 41 prefix)."""
    return "0x" + to_hex_address(address)[2:]


def constructor_args(abi: list, values: list) -> str:
    """Tron has NO field for constructor arguments: they are CONCATENATED to the bytecode."""
    ctor = next((x for x in abi if x.get("type") == "constructor"), None)
    if not ctor or not values:
        return ""
    types = [i["type"] for i in ctor["inputs"]]
    vals = [hex20(v) if t == "address" and isinstance(v, str) else v
            for t, v in zip(types, values)]
    return abi_encode(types, vals).hex()


def wait_for(client, txid: str, label) -> dict:
    """Waits for the receipt and records consumption. Warns (without aborting) on revert."""
    info = {}
    for _ in range(30):
        time.sleep(2)
        try:
            info = client.get_transaction_info(txid)
        except Exception:
            continue
        if info:
            break
    if not info:
        print(f"   [!] {label or txid[:10]}: no receipt after 60 s")
        return {}

    receipt = info.get("receipt", {})
    result = receipt.get("result", "")
    if result not in ("SUCCESS", ""):
        raw = info.get("resMessage", "")
        try:
            msg = bytes.fromhex(raw).decode(errors="replace")
        except (ValueError, TypeError):
            msg = str(raw)            # sometimes it's already plain text, not hex
        print(f"   [!] FAILURE ({result}) in {label or txid[:10]}: {msg}")
        print(f"       energy used={receipt.get('energy_usage_total')} "
              f"net={receipt.get('net_usage')}")
        return info

    energy = receipt.get("energy_usage_total", 0)
    if label:
        measurements.append((label, energy))
        print(f"   {label:<46} {energy:>10,} energy")
    return info


def deploy(client, account, build, name, values=None) -> str:
    me = account.public_key.to_base58check_address()
    data = build[name]
    contract = Contract(
        name=name,
        bytecode=data["bytecode"] + constructor_args(data["abi"], values or []),
        abi=data["abi"],
    )
    tx = (client.trx.deploy_contract(me, contract)
          .fee_limit(3_000_000_000).build().sign(account))
    info = wait_for(client, tx.broadcast()["txid"], f"deploy {name}")
    address = info.get("contract_address")
    if not address:
        print(f"   [!] could not deploy {name} — fee_limit or balance too low?")
        sys.exit(1)
    b58 = to_base58check_address(address)
    print(f"      -> {name} at {b58}")
    return b58


def call(client, account, contract, fn, *args, label=None):
    me = account.public_key.to_base58check_address()
    tx = (contract.functions[fn](*args)
          .with_owner(me).fee_limit(1_500_000_000).build().sign(account))
    return wait_for(client, tx.broadcast()["txid"], label)


def energy_of(*fragments) -> int:
    return sum(e for lbl, e in measurements if any(f in lbl for f in fragments))


# ── the experiment ───────────────────────────────────────────────────────────────────────────
def measure_option_a(client, account, build, token, usdt, me, amount, buyer, seller):
    """Option A: one address per order, derived with CREATE2."""
    factory_addr = deploy(client, account, build, "EscrowFactory", [usdt, me, FEE_BPS])
    factory = client.get_contract(factory_addr)

    print()
    print("=" * 80)
    print("OPTION A — one address per order")
    print("=" * 80)
    order = os.urandom(32)
    pay_to = factory.functions.addressOf(order, buyer, seller)
    print(f"   computed address (nothing deployed yet, zero cost): {pay_to}")

    call(client, account, token, "transfer", pay_to, amount)        # the buyer pays
    call(client, account, factory, "settle", order, buyer, seller, True,
         label="A: settle one order (deploy + split)")

    expected = amount - amount * FEE_BPS // 10000
    received = token.functions.balanceOf(seller)
    ok = received == expected
    print()
    print(f"   CREATE2-ON-TVM VERIFICATION: {'OK' if ok else '*** FAILED ***'}")
    print(f"      seller received {received / 10**DECIMALS} USDT "
          f"(expected {expected / 10**DECIMALS})")
    if not ok:
        print("      [!] The computed address is NOT where the money landed. Check the 0x41")
        print("          prefix in addressOf(). WITHOUT THIS, OPTION A IS NOT VIABLE.")

    print()
    print("   — exception path: refund the buyer —")
    order2 = os.urandom(32)
    call(client, account, token, "transfer",
         factory.functions.addressOf(order2, buyer, seller), amount)
    call(client, account, factory, "settle", order2, buyer, seller, False,
         label="A: refund the buyer")
    return ok


def measure_option_b(client, account, build, token, usdt, me, amount, buyer, seller):
    """Option B: a single contract for all orders."""
    single_addr = deploy(client, account, build, "SingleEscrow", [usdt, me, FEE_BPS])
    single = client.get_contract(single_addr)

    print()
    print("=" * 80)
    print("OPTION B — a single contract for all orders")
    print("=" * 80)
    order = os.urandom(32)
    call(client, account, token, "transfer", single_addr, amount)
    call(client, account, single, "registerDeposit", order, buyer, seller, amount,
         label="B: registerDeposit")
    call(client, account, single, "release", order, label="B: release")

    print()
    print(f"   — batch of {BATCH} (B's real advantage) —")
    ids = []
    for _ in range(BATCH):
        oid = os.urandom(32)
        ids.append(oid)
        call(client, account, token, "transfer", single_addr, amount)
        call(client, account, single, "registerDeposit", oid, buyer, seller, amount)
    call(client, account, single, "releaseMany", ids,
         label=f"B: releaseMany ({BATCH} at once)")


def main() -> int:
    key = os.getenv("NILE_KEY", "").strip()
    if not key:
        print(__doc__)
        print("Missing NILE_KEY — the hex private key of a TEST account holding Nile TRX.")
        print("Free at https://nileex.io/join/getJoinPage (never use a real account).")
        return 1

    build_path = os.path.join(DIR, "build.json")
    if not os.path.exists(build_path):
        print("Missing build.json — run first:  python scripts/compile.py")
        return 1
    build = json.load(open(build_path, encoding="utf-8"))

    client = Tron(HTTPProvider(NETWORK), network="nile")
    account = PrivateKey(bytes.fromhex(key))
    me = account.public_key.to_base58check_address()
    balance = client.get_account_balance(me)

    print("Network: Nile (TESTNET — no real money involved)")
    print(f"Account: {me}")
    print(f"Balance: {balance} TRX")
    if balance < 900:
        print("[!] Low balance. The faucet gives 1000 TRX per round and deploying a contract is")
        print("    the most expensive step. If it runs dry: get another round and rerun with")
        print("    ONLY=A or ONLY=B.")

    price = next((p["value"] for p in client.get_chain_parameters()
                  if p["key"] == "getEnergyFee"), 420)
    print(f"Energy : {price} SUN per unit (the network's real parameter)")
    print()

    # ── The token: prefer Nile's test USDT ──
    print("=" * 80)
    print("SETUP")
    print("=" * 80)
    usdt = USDT_NILE
    try:
        usdt_balance = client.get_contract(usdt).functions.balanceOf(me)
        print(f"   Nile test USDT : {usdt}")
        print(f"   your balance   : {usdt_balance / 10**DECIMALS:,.2f}")
        if usdt_balance < 200 * 10**DECIMALS:
            print("   [!] Low test USDT: request more from the faucet (3rd form) or the")
            print("       experiment will run out of funds halfway.")
    except Exception as e:
        print(f"   [!] Could not use Nile's USDT ({e.__class__.__name__}): {e}")
        print("       Deploying an own token. NOTE: a mock consumes LESS energy than real")
        print("       USDT, so figures will come out OPTIMISTIC. For the true number, use the")
        print("       faucet USDT (or pass the right address in USDT_NILE).")
        usdt = deploy(client, account, build, "FakeUSDT", [10**13])

    token = client.get_contract(usdt)
    buyer = PrivateKey.random().public_key.to_base58check_address()
    seller = PrivateKey.random().public_key.to_base58check_address()
    amount = 22 * 10**DECIMALS      # a typical order price

    do_a = ONLY in ("", "A")
    do_b = ONLY in ("", "B")
    if ONLY:
        print(f"   (ONLY={ONLY}: measuring that option alone, to avoid running out of TRX)")

    if do_a:
        measure_option_a(client, account, build, token, usdt, me, amount, buyer, seller)
    if do_b:
        measure_option_b(client, account, build, token, usdt, me, amount, buyer, seller)

    # ── report ───────────────────────────────────────────────────────────────────────────────
    def trx(e):
        return e * price / 1e6

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"{'operation':<48} {'energy':>10} {'TRX':>10}")
    print("-" * 80)
    for label, e in measurements:
        print(f"{label:<48} {e:>10,} {trx(e):>10.4f}")

    a = energy_of("A: settle")
    b_reg = energy_of("B: registerDeposit")
    b_rel = sum(e for lbl, e in measurements if lbl == "B: release")   # exact: not releaseMany
    b_batch = energy_of("releaseMany")

    print()
    print("── COST PER ORDER (the number that decides) ──")
    rows = []
    if do_a:
        rows.append(("A — one address per order", a))
    if do_b:
        rows.append(("B — single contract, one by one", b_reg + b_rel))
        rows.append((f"B — single contract, batches of {BATCH}", b_reg + b_batch / BATCH))
    for label, e in rows:
        print(f"   {label:<40} {e:>10,.0f} energy   {trx(e):>8.4f} TRX")

    if rows:
        print()
        print("   Multiply TRX by the TRX/USD price for the real cost per order.")
        print("   At 100 orders/day:")
        for label, e in rows:
            print(f"      {label:<40} {trx(e) * 100:>10,.1f} TRX/day")

    print()
    print("   NOTE: this is the WORST case, burning TRX on every operation. Staking TRX yields")
    print("   free renewable daily energy, which at volume can bring marginal cost near zero")
    print("   (you immobilize TRX instead of spending it).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
