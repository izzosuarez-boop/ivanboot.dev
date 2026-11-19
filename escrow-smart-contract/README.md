# On-chain escrow test bench — TRON / USDT TRC-20 (ported & verified on BSC)

> A measurement-driven design study for a **non-custodial escrow** on a digital-goods
> marketplace I built and operate. It answers one question with **measured numbers**:
> *what does each escrow design actually cost per order, and is it worth it?*

**TL;DR of what this demonstrates:**

- A non-custodial escrow in Solidity with a **legal constraint encoded as an invariant**
- A **CREATE2 one-address-per-order** design where the salt makes fund diversion impossible
- A real, **measured finding**: USDT's `transfer` returns `false` even when the money moves —
  the standard OpenZeppelin pattern reverts with it
- A decision made from **gas measured on two chains**, not from intuition: TRON made every
  sale lose money; the same contract on BSC costs 1% of the fee

---

## Why it exists

The marketplace's payment flow moved money in two custodial hops:

```
buyer → payment processor → platform → exchange → seller
```

Three production incidents in a single week all happened **inside that corridor**: a stuck
payment the processor never reported, an exchange silently deducting its withdrawal fee from a
seller's payout (22 requested → 20.5 received), and payouts blocked by exchange minimums.

An on-chain escrow reduces the flow to `buyer → contract → seller`, with the money never
touching a platform account. The question was never *does it work* — it was **what does it
cost per order**.

## The rule that cannot be broken

A constraint set by legal counsel, encoded as a contract invariant: **a buyer's money can only
end up at the seller or back at the buyer.** The fee goes to a wallet fixed at deployment
(`immutable`). There is no general withdrawal function.

## The two designs compared

### A — one address per order (`EscrowFactory`)

The backend **computes** each order's payment address with `CREATE2` without deploying
anything (zero cost). The buyer pays USDT there from anywhere — including an exchange. To
settle, an **ephemeral** contract is deployed at that address; it splits the funds inside its
own constructor and leaves no code behind (63 bytes of runtime code per order vs 2,964 for the
one-time factory).

**The key design decision is the salt:**

```solidity
salt = keccak256(abi.encode(orderId, buyer, seller))
```

Because the address derives from the salt, and the salt commits to the buyer and the seller,
**the backend cannot divert the funds**: settling with any other recipient would change the
inputs, and `CREATE2` would deploy at a *different* address — where there isn't a cent. The
only freedom left to the operator key is one boolean — seller or buyer — which are exactly the
two allowed outcomes. Anyone can recompute the address from public data and verify it.

*Without that binding, a factory with an admin key could send the money anywhere, and the
whole "guarantee" would be theater.*

### B — a single contract (`SingleEscrow`)

Everyone pays the same address. A contract can't read chain logs, so it can't know whose
deposit is whose — the backend has to register them. The contract still guarantees that no
more money can be committed than it holds (`totalCommitted <= balance`) and that funds only
ever reach the three allowed destinations. Its real advantage: `releaseMany()` settles N
orders in one transaction. Its real problem: with a shared address, only the exact amount
distinguishes orders — and amounts *don't arrive exact* (exchanges deduct withdrawal fees on
the way out). One address per order makes that a non-issue.

## Measured results (Tron testnet "Nile", 2026-09-06)

| Option | Energy/order | TRX | **USD/order** |
|---|---|---|---|
| A — one address per order | 181,314 | 18.13 | **6.01** |
| B — single contract, one by one | 165,101 | 16.51 | **5.47** |
| B — single contract, batches of 5 | 150,088 | 15.01 | **4.97** |

With a typical order of ~$22 and a 10% fee ($2.20), gas at ~$6/order means **every sale loses
money**. Staking TRX for free energy doesn't save it either: covering 100 orders/day requires
immobilizing ~$627k in TRX (measured: 1 staked TRX yields 9.58 energy/day). Verdict on TRON:
not viable below ~$60 per order.

## The same contract on BSC: 883× cheaper — full cycle verified on testnet

The problem was never the design; it was TRON's energy pricing. The full purchase cycle was
deployed and executed on BSC testnet:

| Step | Gas | USD (mainnet prices) |
|---|---|---|
| Deploy factory (one-time) | 863,588 | 0.0324 |
| Create order | 543,046 | 0.0204 |
| Release | 86,967 | 0.0033 |
| **Total per order** | **630,013** | **$0.0236** |

Gas becomes **1.07% of the fee** instead of ~950%. The on-chain payment verification detected
the deposit (amount, block, tx hash), and the RPC failover was exercised by a real failure:
BSC's own testnet RPC rejects `eth_getLogs`, and the query fell through to the second
endpoint — without failover, the first real test would have failed.

### Findings that apply beyond this project

1. **USDT lies in `transfer`'s return value.** On TRON it returns 32 zero bytes (`false`)
   while moving the money correctly. The standard pattern —
   `require(ok && (data.length == 0 || abi.decode(data, (bool))))` — **reverts**. Measured,
   not theorized. The fix in `SafeTransfer`: verify the recipient's **balance before and
   after**. Two extra reads; works with any token, including ones that lie.
2. **CREATE2 on Tron's TVM uses prefix `0x41`** (Ethereum uses `0xff`). Verified against the
   chain: the computed address matches where funds actually land.
3. **TVM doesn't support `PUSH0`**: compile with solc 0.8.19 / `evmVersion: istanbul`.
   0.8.20+ breaks deployment.
4. **A lab mock must misbehave like the real token.** The first `FakeUSDT` didn't emit
   `Transfer`, so log-based verification reported "no payment" with the payment on-chain —
   a test that validates against a well-behaved mock validates nothing.
5. **EVM cross-chain address risk:** a `0x…` address exists on every EVM chain at once. A
   buyer withdrawing on the wrong network sends real money to a contract-less address on
   another chain. (On TRON this is impossible — `T…` addresses are TRON-only.) Must be guarded
   in the UI.

## Running it

```bash
pip install py-solc-x tronpy

python scripts/compile.py        # compiles and reports each contract's on-chain size

# Create a TESTNET account with free TRX: https://nileex.io/join/getJoinPage
export NILE_KEY=<hex private key of that throwaway account>
python scripts/measure_costs.py
```

`measure_costs.py` runs against Nile (Tron's testnet). No real money is involved. It measures
every operation's energy at the network's **live** energy price, verifies the CREATE2 address
derivation against the chain, and prints cost-per-order for both designs.

## Design notes & open questions (kept honest)

- **Template versioning:** changing `OrderPayout`'s bytecode changes every future address.
  Orders with an already-announced address must keep the old template.
- **Late payments** (after settlement) are recoverable by redeploying on the same address —
  it has happened in production (a deposit arrived 2h43m late) and needs explicit handling.
- **The operator key** can't steal funds (the contract forbids it) but can break orders;
  it deserves isolation from regular backend credentials.
- **Audit pending** — few lines, but they move real money.
