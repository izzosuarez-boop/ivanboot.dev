"""Simulated client that exercises the full chain through the proxy.

It connects to the proxy's login port, reads the `AXK`/`AYK` redirect (which
the proxy will have rewritten to its own game port), connects to the game
server through the proxy and plays a complete conversation with real frames
of the legacy protocol:

    login : HC -> AXK/AYK (redirected to the proxy)
    game  : HG -> AT<ticket> -> GDM/GDF
            GA001 (move) -> GA1
            GA500 (gather) -> GA501
            GKK -> GKE
            BD -> BD
            ping -> qping
            Ow (dropped by the hook -> no reply)

Exposes `ready` (Event), set once the initial sequence completes, so a runner
can inject packets exactly then and verify they arrive.

Usage:
    python mock_client.py --host 127.0.0.1 --login-port 4430 --game-port 5555
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import sys

import packets as pkt
import protocol as p


def _cell(cell_id: int) -> str:
    return p.cell_to_hash(cell_id)


class Reader:
    """PacketManager wrapper that never loses coalesced packets.

    `PacketManager.feed()` can return several messages from a single read;
    they go into a queue so `next_packet()` hands them out one by one.
    """

    def __init__(self, r: asyncio.StreamReader, direction: str, log=None):
        self.r = r
        self.mgr = pkt.PacketManager(direction)
        self.queue: collections.deque[pkt.Packet] = collections.deque()
        self.log = log

    async def _refill(self) -> None:
        data = await self.r.read(4096)
        if not data:
            raise ConnectionError("connection closed")
        self.queue.extend(self.mgr.feed(data))

    async def next_packet(self) -> pkt.Packet:
        while not self.queue:
            await self._refill()
        pa = self.queue.popleft()
        if self.log:
            self.log("S>C", pa.text())
        return pa

    async def drain(self, duration: float) -> list[pkt.Packet]:
        """Collects everything that arrives during `duration` seconds."""
        out: list[pkt.Packet] = []
        deadline = asyncio.get_running_loop().time() + duration
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                break
            try:
                out.append(await asyncio.wait_for(self.next_packet(), remaining))
            except asyncio.TimeoutError:
                break
        return out


class MockClient:
    def __init__(self, host: str, login_port: int, game_port: int,
                 game_host: str | None = None, echo: bool = True):
        self.host = host
        self.login_port = login_port
        self.game_port = game_port          # the proxy's game port
        self.game_host = game_host or host
        self.echo = echo
        self.ready = asyncio.Event()
        # Results
        self.login_msgs: list[str] = []
        self.redirect = None
        self.hg = ""
        self.initial: list[str] = []
        self.replies: list[str] = []

    def log(self, direction: str, msg: str) -> None:
        if self.echo:
            print(f"[MOCK-CLI] {direction} {msg}")

    async def _send(self, w: asyncio.StreamWriter, msg: str) -> None:
        self.log("C>S", msg)
        w.write(p.client_bytes(msg))
        await w.drain()

    async def play(self) -> dict:
        # --- login -------------------------------------------------------
        r, w_login = await asyncio.open_connection(self.host, self.login_port)
        reader = Reader(r, pkt.SERVER, self.log)
        hc = await asyncio.wait_for(reader.next_packet(), 3)
        red = await asyncio.wait_for(reader.next_packet(), 3)
        self.login_msgs = [hc.text(), red.text()]
        if hc.header != "HC":
            raise AssertionError(f"expected HC, got {hc.header!r}")
        self.redirect = p.parse_redirect(red.text())
        if self.redirect is None:
            raise AssertionError(f"unrecognized redirect: {red.text()!r}")
        host, port, ticket = self.redirect

        # --- game (through the proxy) ------------------------------------
        r, w = await asyncio.open_connection(host, port)
        reader = Reader(r, pkt.SERVER, self.log)
        hg = await asyncio.wait_for(reader.next_packet(), 3)
        if hg.header != "HG":
            raise AssertionError(f"expected HG, got {hg.header!r}")
        self.hg = hg.text()
        await self._send(w, "AT" + ticket)

        initial = await reader.drain(0.4)
        self.initial = [pa.text() for pa in initial]
        self.ready.set()

        # --- client actions ----------------------------------------------
        cell = 230
        await self._send(w, "GA001" + "3" + _cell(cell))   # move
        await self._send(w, "GA500" + _cell(cell) + ";3")  # gather
        await self._send(w, "GKK1")                        # end of action
        await self._send(w, "BD0")                         # date
        await self._send(w, "ping")                        # ping
        await self._send(w, "Ow")                          # dropped by the hook

        replies = await reader.drain(1.0)
        self.replies = [pa.text() for pa in replies]

        w.close()
        w_login.close()
        return {
            "login": self.login_msgs,
            "redirect": self.redirect,
            "hg": self.hg,
            "initial": self.initial,
            "replies": self.replies,
            "initial_headers": [pa.header for pa in initial],
            "reply_headers": [pa.header for pa in replies],
        }


async def _demo(args):
    client = MockClient(args.host, args.login_port, args.game_port)
    result = await client.play()
    print("\n--- result ---")
    for k, v in result.items():
        print(f"{k}: {v}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Simulated client for the legacy protocol.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--login-port", type=int, default=4430)
    ap.add_argument("--game-port", type=int, default=5555)
    args = ap.parse_args(argv)
    asyncio.run(_demo(args))


if __name__ == "__main__":
    sys.exit(main())
