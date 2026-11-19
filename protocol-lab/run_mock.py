"""Local end-to-end test: mock login + mock game + proxy + client.

Starts both simulated servers, puts the proxy in front of them, launches the
simulated client, and additionally performs an injection in both directions
using the proxy's API (`Session.to_client` / `Session.to_server`).

What it actually exercises:

  * `packets.PacketManager`: frame segmentation in all 4 directions
    (login S->C, login C>S, game S->C, game C->S).
  * `Hooks`: rewriting `GDM` (server) and dropping `Ow` (client).
  * Asynchronous injection: a message to the client (GDF) and one to the
    server (GA500), verifying each endpoint receives it.

Usage:
    python run_mock.py
    python run_mock.py --proxy-login-port 4430 --proxy-game-port 5555
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile

import protocol as p
from mock_client import MockClient
from mock_server import MockGame, MockLogin
from proxy import Hooks, Proxy


class DemoHooks(Hooks):
    """Example hooks: rewrites GDM and drops Ow, to see the engine in action."""

    def server(self, session, msg):
        if msg.startswith("GDM"):
            parts = msg.split("|")
            if len(parts) == 4:
                parts[3] = "hookkey"           # the hook rewrites the key
                return "|".join(parts)
        return msg

    def client(self, session, msg):
        if msg == "Ow":
            print("[HOOKS] dropped C>S: Ow")
            return None
        return msg


def _cell(cell_id: int) -> str:
    return p.cell_to_hash(cell_id)


async def run(args) -> int:
    log_dir = args.log_dir or tempfile.mkdtemp(prefix="proxy_logs_")

    game = MockGame("127.0.0.1", args.mock_game_port, echo=True)
    await game.start()
    login = MockLogin("127.0.0.1", args.mock_login_port, "127.0.0.1", game.port, echo=True)
    await login.start()

    proxy = Proxy("127.0.0.1", login.port, "127.0.0.1",
                  args.proxy_login_port, args.proxy_game_port, log_dir,
                  hooks=DemoHooks(), echo=True)
    await proxy.start()

    print("-" * 68)
    print(f"mock login : 127.0.0.1:{login.port}")
    print(f"mock game  : 127.0.0.1:{game.port}")
    print(f"proxy login: 127.0.0.1:{proxy.local_login_port}")
    print(f"proxy game : 127.0.0.1:{proxy.local_game_port}")
    print("-" * 68)

    if args.serve:
        print("--serve mode: leaves everything up. Ctrl+C to quit.")
        print("config.py -> LOGIN_HOST='127.0.0.1'  LOGIN_PORT=%d" % login.port)
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await proxy.close()
            await login.close()
            await game.close()
        return 0

    client = MockClient("127.0.0.1", proxy.local_login_port, proxy.local_game_port,
                        echo=True)
    task = asyncio.create_task(client.play())

    await asyncio.wait_for(client.ready.wait(), 5)
    session = proxy.last_game_session
    assert session is not None, "no game session on the proxy"

    # --- Asynchronous injection in both directions ------------------------
    injected_client = "GDF|" + _cell(400) + ";5;0"
    injected_server = "GA500" + _cell(400) + ";9"
    print(f"[INJ] S>C {injected_client}")
    print(f"[INJ] C>S {injected_server}")
    session.to_client(injected_client)
    session.to_server(injected_server)

    result = await asyncio.wait_for(task, 10)

    await proxy.close()
    await login.close()
    await game.close()

    # --- Checks ------------------------------------------------------------
    errors = []

    def check(cond, text):
        print(("  OK   " if cond else "  FAIL ") + "  " + text)
        if not cond:
            errors.append(text)

    red_host, red_port, ticket = result["redirect"]
    check(red_host == "127.0.0.1" and red_port == proxy.local_game_port,
          "the AXK redirect points at the proxy (not at the mock server)")

    check(result["login"][0].startswith("HC"),
          "login: HC<key> received")

    check("HG" == result["hg"],
          "game: HG received")
    check("GDM" in result["initial_headers"],
          "game: GDM received after AT")
    check("GDF" in result["initial_headers"],
          "game: GDF received (interactive objects)")

    check(any(m.startswith("GDM|") and m.endswith("hookkey")
              for m in result["initial"]),
          "server hook rewrote the GDM key")

    check(any(m.startswith("GA1;") for m in result["replies"]),
          "movement GA001 -> reply GA1")
    check(any(m.startswith("GA501;") for m in result["replies"]),
          "gathering GA500 -> reply GA501")
    check("GKE" in result["reply_headers"],
          "end of action GKK -> reply GKE")
    check("BD" in result["reply_headers"],
          "date BD -> reply BD")
    check("qping" in result["replies"],
          "ping -> qping")

    check(injected_client in result["replies"],
          "injection to the CLIENT received (GDF)")
    check(any(m.startswith("GA500") and m.endswith(";9") for m in game.received),
          "injection to the SERVER received by the mock game (GA500;9)")
    check("Ow" not in game.received,
          "client hook dropped Ow (never reached the server)")

    print("-" * 68)
    print("session logs at:", os.path.abspath(log_dir))
    if errors:
        print(f"FAILURES ({len(errors)}):")
        for e in errors:
            print("  -", e)
        return 1
    print("ALL OK")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Local end-to-end proxy test.")
    ap.add_argument("--mock-login-port", type=int, default=0)
    ap.add_argument("--mock-game-port", type=int, default=0)
    ap.add_argument("--proxy-login-port", type=int, default=0,
                    help="0 = free port; use 4430 for a real client")
    ap.add_argument("--proxy-game-port", type=int, default=0,
                    help="0 = free port; use 5555 for a real client")
    ap.add_argument("--log-dir", default=None)
    ap.add_argument("--serve", action="store_true",
                    help="don't launch the simulated client; leave mock+proxy up")
    args = ap.parse_args(argv)
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
