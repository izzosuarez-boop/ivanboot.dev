# Portfolio — Iván

Four self-contained pieces of work, each extracted and sanitized from production systems I
built and operate solo. Each folder is a standalone repo with its own README.

| Project | What it shows | Language / stack |
|---|---|---|
| **escrow-smart-contract** | A non-custodial escrow in Solidity with a legal constraint encoded as an invariant, a CREATE2 one-address-per-order design, and a gas study measured on two chains | Solidity, Python, TRON/EVM |
| **protocol-lab** | A reverse-engineered TCP protocol test bench: framer, MITM proxy with hooks, mock servers/client, replay + fuzzing harness — all passing | Python (asyncio, stdlib only) |
| **linux-fleet-guide** | A field guide to operating a fleet of 9 headless Linux workers: systemd, per-machine proxy egress, self-healing supervisor, and a catalog of real failures | Linux, systemd, networking |
| **llm-production-case-study** | Three production LLM integrations (DeepSeek + Anthropic) designed around cost budgets, latency budgets and code-level verification | Python, LLM APIs |

### How I work

The thread through all four: **I measure before I conclude, and I write down why.** Comments
carry the date and the number that motivated a decision; every fix is tested so it also
*fails* with the wrong input; conclusions later found false are struck through in place rather
than quietly deleted, because the evidence trail is the point.

Each repo runs on its own — `protocol-lab` and `escrow-smart-contract` include runnable tests
and measurement scripts.
