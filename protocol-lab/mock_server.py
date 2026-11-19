"""Simulated login and game servers for fully-local protocol testing.

  * MockLogin : on connect it sends `HC<key>` and the redirect
    `AXK<ip><port><ticket>` towards the simulated game server.
  * MockGame  : sends `HG`, validates `AT<ticket>` and replies to movement
    (`GA001...`), gathering (`GA500...`), end-of-action (`GKK`), date (`BD`)
    and `ping` with plausible server frames.

All framing (terminator segmentation plus header/body split) goes through
`packets.PacketManager` — the same parser the proxy uses — so the test
validates the real parser, not a shortcut.

Formats used (as recovered from captures; adjust if your server differs):

    S->C login : HC<key>              ; AXK<ip 8><port 3><ticket> | AYK<ip>:<port>;<ticket>
    S->C game  : HG                   ; GDM|<mapId>|<date>|<key>
                 GDF|<cell>;<state>;<interactive>|<...>
                 GA<actor>;<action>;<...>
    C->S game  : AT<ticket>           ; GA001<dir+cell>  ; GA500<cell>;<skill>
                 GKK<id>              ; BD<date>         ; ping

Usage:
    python mock_server.py --login-port 14430 --game-port 15555
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import itertools

import packets as pkt
import protocol as p

LOGIN = "MOCK-LOGIN"
GAME = "MOCK-GAME"


def _cell(cell_id: int) -> str:
    return p.cell_to_hash(cell_id)


class _BaseServer:
    def __init__(self, host: str, port: int, echo: bool = True):
        self.host = host
        self.port = port
        self.echo = echo
        self.server = None
        self._counter = itertools.count(1)

    async def start(self) -> int:
        # Port 0 -> the OS picks a free one; keep the real port.
        self.server = await asyncio.start_server(self._serve, self.host, self.port)
        self.port = self.server.sockets[0].getsockname()[1]
        return self.port

    async def close(self) -> None:
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()

    def log(self, label: str, direction: str, msg) -> None:
        if self.echo:
            print(f"[{label}#{getattr(self, '_n', 0)}] {direction} {msg}")

    async def _send(self, w: asyncio.StreamWriter, msg: str) -> None:
        self.log(type(self).__name__, "S>C", msg)
        w.write(p.server_bytes(msg))
        await w.drain()

    async def _serve(self, r, w):  # pragma: no cover - overridden
        raise NotImplementedError


class MockLogin(_BaseServer):
    """Simulated login: greets and redirects to the game server."""

    def __init__(self, host: str, port: int, game_host: str, game_port: int,
                 key: bytes = b"mockkey", ayk_format: bool = False, echo: bool = True):
        super().__init__(host, port, echo)
        self.game_host = game_host
        self.game_port = game_port
        self.key = key
        self.ayk_format = ayk_format
        self.last_ticket = None

    def _redirect(self, ticket: str) -> str:
        if self.ayk_format:
            return f"AYK{self.game_host}:{self.game_port};{ticket}"
        return ("AXK" + p.encode_ip(self.game_host)
                + p.encode_port(self.game_port) + ticket)

    async def _serve(self, r, w):
        self._n = next(self._counter)
        self.log(LOGIN, "---", f"client connected ({self.host}:{self.port})")
        self.last_ticket = "%d" % (0xA000 + self._n)
        await self._send(w, "HC" + self.key.decode("latin-1"))
        await self._send(w, self._redirect(self.last_ticket))
        mgr = pkt.PacketManager(pkt.CLIENT)
        try:
            while data := await r.read(4096):
                for pa in mgr.feed(data):
                    self.log(LOGIN, "C>S", pa.text())
        except (ConnectionError, OSError, pkt.PacketError):
            pass
        finally:
            self.log(LOGIN, "---", "client disconnected")
            w.close()


class MockGame(_BaseServer):
    """Simulated game server with a plausible response script."""

    def __init__(self, host: str, port: int, map_id: int = 7411,
                 map_date: int = 1_700_000_000, map_key: bytes = b"mapkey01",
                 ticket: str = "0xA001", burst: int = 12, echo: bool = True):
        super().__init__(host, port, echo)
        self.map_id = map_id
        self.map_date = map_date
        self.map_key = map_key
        self.ticket = ticket
        self.burst = burst
        self.received: list[str] = []
        self.received_event: dict[str, asyncio.Event] = {}

    def expect(self, msg: str) -> asyncio.Event:
        ev = self.received_event.get(msg)
        if ev is None:
            ev = asyncio.Event()
            self.received_event[msg] = ev
        return ev

    def _mark(self, msg: str) -> None:
        self.received.append(msg)
        for key, ev in self.received_event.items():
            if msg.startswith(key):
                ev.set()

    def _initial_script(self) -> list[str]:
        """Initial burst on entering the map.

        Includes GDM (map data), GDF (interactive objects), GTL (combat data
        initialization) and a burst of entities (GM/GA). The point is to force
        coalescing and a realistic frame volume.
        """
        frames = [
            f"GDM|{self.map_id}|{self.map_date}|{self.map_key.decode('latin-1')}",
            "GDF|" + "|".join([
                f"{_cell(230)};0;0", f"{_cell(231)};4;10",
                f"{_cell(250)};1;0", f"{_cell(300)};0;0",
            ]),
            # Representative structure of the fighters/turns list.
            # Replace with the exact shape once a real GTL is captured.
            "GTL|" + "|".join([
                "1;Hero;50;1200;6;3;0",
                "2;Enemy;50;1100;6;3;1",
            ]),
        ]
        frames.extend(self.entity_burst(self.burst))
        return frames

    def entity_burst(self, n: int) -> list[str]:
        """Generates `n` map-entity frames (GM) plus some actions (GA)."""
        out = []
        for i in range(n):
            fid = 1000 + i
            if i % 5 == 4:
                out.append(f"GM|-{fid}")                      # entity leaves
            else:
                out.append(f"GM|+{fid};{_cell(200 + i)};{i % 8}")
            if i % 3 == 0:
                out.append(f"GA1;{fid};7;{_cell(200 + i)};{i % 8}")  # action
        return out

    def _reply(self, pa: pkt.Packet) -> list[str]:
        header, body = pa.header, pa.body.decode("latin-1")
        if header == "AT":
            self.log(GAME, "---", f"ticket {body!r} accepted")
            return self._initial_script()
        if header == "GA":
            # body like "0013ab" (movement) or "500ab;3" (gathering).
            if body.startswith("001"):
                cell = body[4:6] or "aa"
                return [f"GA1;1;7;{cell};3"]       # actor;type;sprite;cell;dir
            if body.startswith("500"):
                fields = body.split(";")
                cell = fields[0][3:] or "aa"
                skill = fields[1] if len(fields) > 1 else "0"
                return [f"GA501;1;{skill};{cell}"]
            return [f"GA1;1;7;aa;0"]
        if header == "GKK":
            return [f"GKE{body}|1"]                # end of action (status 1)
        if header == "BD":
            now = int(datetime.datetime.now().timestamp())
            return [f"BD{now}"]
        if header == "ping":
            return ["qping"]
        if header == "DIAG":
            # Latency probe (telemetry): the peer echoes the same nonce.
            parts = [x.decode("latin-1") for x in pa.params()]
            if parts and parts[0] == "probe":
                nonce = parts[1] if len(parts) > 1 else ""
                return [f"DIAG|pong|{nonce}"]
        return []

    async def _serve(self, r, w):
        self._n = next(self._counter)
        self.log(GAME, "---", f"client connected ({self.host}:{self.port})")
        await self._send(w, "HG")
        mgr = pkt.PacketManager(pkt.CLIENT)
        authenticated = False
        try:
            while data := await r.read(4096):
                for pa in mgr.feed(data):
                    self.log(GAME, "C>S", pa.text())
                    if pa.header == "AT":
                        authenticated = True
                    if not authenticated and pa.header != "AT":
                        continue
                    self._mark(pa.text())
                    for reply in self._reply(pa):
                        await self._send(w, reply)
        except (ConnectionError, OSError, pkt.PacketError):
            pass
        finally:
            self.log(GAME, "---", "client disconnected")
            w.close()


async def _demo(args):
    game = MockGame("127.0.0.1", args.game_port, burst=args.burst, echo=True)
    await game.start()
    login = MockLogin("127.0.0.1", args.login_port, "127.0.0.1", game.port, echo=True)
    await login.start()
    print(f"Mock listening: login 127.0.0.1:{login.port}  game 127.0.0.1:{game.port}")
    print("Point the proxy at those ports, or use run_mock.py")
    await asyncio.Event().wait()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Local mock servers for the legacy protocol.")
    ap.add_argument("--login-port", type=int, default=14430)
    ap.add_argument("--game-port", type=int, default=15555)
    ap.add_argument("--burst", type=int, default=12,
                    help="number of entities in the initial burst")
    args = ap.parse_args(argv)
    try:
        asyncio.run(_demo(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
