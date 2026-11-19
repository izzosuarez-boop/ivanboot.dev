# protocol-lab — reverse-engineered TCP protocol test bench

A self-contained laboratory for working with a **legacy client-server text protocol over
TCP** that I reverse-engineered from passive traffic captures. It contains the full chain
needed to study, intercept and test such a protocol **without touching any production
system**: a framer, a MITM proxy with hooks, simulated servers and client, a replay/fuzzing
harness, and tests.

Everything runs locally with zero dependencies beyond the standard library.

```
python run_mock.py        # full end-to-end: mocks + proxy + client + injections + checks
python replay.py          # fragmentation/fuzzing sweep of the frame parser
python test_proxy.py      # protocol + proxy tests (also runs under pytest)
python packets.py         # parser self-test
```

## What's in it

| File | Role |
|---|---|
| `protocol.py` | Wire primitives: terminators, redirect encode/decode (IP and port packed into a base-64 alphabet), grid-cell encoding |
| `packets.py` | `PacketManager`: stream → complete frames, with header/body split. Handles fragmentation, coalescing, split terminators, and caps unterminated frames (`max_frame`) instead of growing forever |
| `proxy.py` | asyncio MITM proxy: logs everything, rewrites the login→game redirect so the client stays behind the proxy, `Hooks` API (modify / drop / observe+inject), live console injection |
| `mock_server.py` | Simulated login + game servers that speak plausible protocol, built on the same parser the proxy uses — so tests validate the real parser, not a shortcut |
| `mock_client.py` | Simulated client that plays a full session through the proxy |
| `replay.py` | Replay + fuzzing: 5 fragmentation modes, an exhaustive cut-at-every-position sweep, and robustness invariants |
| `run_mock.py` | End-to-end runner with assertions: 4 traffic directions, hook rewrite/drop, bidirectional injection |
| `test_proxy.py` | Tests for the primitives and the proxy against real sockets |

## Why it's built this way

**The mock must use the real parser.** Every simulated endpoint frames its traffic through
the same `PacketManager` the proxy uses. A test bench that takes shortcuts validates
something that doesn't exist — the same principle as a token mock that behaves better than
the real token.

**A verification that passes with the wrong answer verifies nothing.** The fuzzing harness
doesn't just check happy paths: it asserts that parsing a stream cut at *every* position
reconstructs a strict prefix, that an oversized unterminated frame raises *and leaves the
parser usable*, and that byte-by-byte feeding is identical to feeding the whole stream.

**Observation is separated from interference.** The proxy's `observe()` hook can emit
diagnostic packets (e.g. latency probes) without touching the messages in flight — capture
stays read-only unless a hook explicitly rewrites.

## Protocol notes (recovered from captures)

- Server→client frames end in `\x00`; client→server in `\n\x00` — and the parser also
  accepts a bare `\x00` from clients, because real implementations differ.
- The login's redirect message packs the game server's IP and port into a 64-character
  alphabet; the proxy decodes it, stores the real target, and rewrites the message so the
  client transparently reconnects through the proxy.
- Message IDs are short alphabetic prefixes; the longest-known-prefix rule avoids
  misparsing bodies that start with letters (`AT` + `TICKET1`, not `ATTICKET` + `1`).
