"""Man-in-the-middle TCP proxy for a legacy text protocol.

Usage:  python proxy.py

- Forwards everything as-is and logs every packet to logs/.
- Rewrites the login redirect (AXK/AYK) so the client also goes through the
  proxy when connecting to the game server.
- Console to inject messages into the latest game session:
    s <message>   send to the server (as if the client had sent it)
    c <message>   send to the client (as if the server had sent it)
"""

import asyncio
import datetime
import itertools
import os
import sys
import threading
from collections import deque

import config
import packets as pkt
import protocol as p


class Hooks:
    """Interception points.

    Each method receives an already-reassembled message and returns the
    message to forward (same or modified) or None to drop it.

    `observe()` is an observation-only point: it receives the full `Packet`
    (header and body already split) before forwarding, and may return
    diagnostic injections as (target, message) pairs, where target is
    "client" or "server".
    """

    def server(self, session, msg):
        return msg

    def client(self, session, msg):
        return msg

    def observe(self, session, packet):
        return ()


class Session:
    def __init__(self, kind, number, client_w, server_w, log_dir, echo):
        self.kind = kind
        self.client_w = client_w
        self.server_w = server_w
        self.echo = echo
        os.makedirs(log_dir, exist_ok=True)
        name = f"{datetime.datetime.now():%Y%m%d_%H%M%S}_{kind}_{number}.log"
        self._log = open(os.path.join(log_dir, name), "a", encoding="utf-8")

    def log(self, direction, msg):
        line = f"{datetime.datetime.now():%H:%M:%S.%f}"[:-3] + f" {direction} {msg}"
        self._log.write(line + "\n")
        self._log.flush()
        if self.echo:
            print(f"[{self.kind}] {line}")

    def to_server(self, msg):
        self.log("INJ>S", msg)
        self.server_w.write(p.client_bytes(msg))

    def to_client(self, msg):
        self.log("INJ>C", msg)
        self.client_w.write(p.server_bytes(msg))

    def close(self):
        self._log.close()


class Proxy:
    def __init__(self, login_host, login_port, local_host, local_login_port,
                 local_game_port, log_dir, hooks=None, echo=False):
        self.login_target = (login_host, login_port)
        self.local_host = local_host
        self.local_login_port = local_login_port
        self.local_game_port = local_game_port
        self.log_dir = log_dir
        self.hooks = hooks or Hooks()
        self.echo = echo
        self.game_targets = deque()    # redirects not yet consumed
        self.last_game_target = None
        self.last_game_session = None
        self._counter = itertools.count(1)
        self._servers = []

    async def start(self):
        login = await asyncio.start_server(self._new_login, self.local_host, self.local_login_port)
        game = await asyncio.start_server(self._new_game, self.local_host, self.local_game_port)
        # With port 0 the OS picks a free one; keep the real port.
        self.local_login_port = login.sockets[0].getsockname()[1]
        self.local_game_port = game.sockets[0].getsockname()[1]
        self._servers = [login, game]

    async def close(self):
        for s in self._servers:
            s.close()
            await s.wait_closed()

    async def _new_login(self, client_r, client_w):
        await self._connect("login", self.login_target, client_r, client_w)

    async def _new_game(self, client_r, client_w):
        target = self.game_targets.popleft() if self.game_targets else self.last_game_target
        if target is None:
            print("[game] connection without a prior login redirect; closing")
            client_w.close()
            return
        await self._connect("game", target, client_r, client_w)

    async def _connect(self, kind, target, client_r, client_w):
        try:
            server_r, server_w = await asyncio.open_connection(*target)
        except OSError as e:
            print(f"[{kind}] could not connect to {target}: {e}")
            client_w.close()
            return
        session = Session(kind, next(self._counter), client_w, server_w, self.log_dir, self.echo)
        session.log("---", f"connected to {target[0]}:{target[1]}")
        if kind == "game":
            self.last_game_session = session
        tasks = [
            asyncio.create_task(self._pump(session, server_r, client_w, True)),
            asyncio.create_task(self._pump(session, client_r, server_w, False)),
        ]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in tasks:
            t.cancel()
        for w in (client_w, server_w):
            w.close()
        session.log("---", "disconnected")
        session.close()

    async def _pump(self, session, reader, writer, from_server):
        direction = pkt.SERVER if from_server else pkt.CLIENT
        manager = pkt.PacketManager(direction)
        try:
            while data := await reader.read(65536):
                for packet in manager.feed(data):
                    self._observe(session, packet)
                    msg = packet.text()
                    session.log("S>C" if from_server else "C>S", msg)
                    new = self._process(session, msg, from_server)
                    if new is None:
                        continue
                    if new == msg:
                        writer.write(packet.serialize())   # unchanged: original bytes
                    elif from_server:
                        writer.write(p.server_bytes(new))
                    else:
                        writer.write(p.client_bytes(new))
                await writer.drain()
        except (ConnectionError, OSError, pkt.PacketError):
            pass

    def _observe(self, session, packet):
        """Fires the observation hook and applies any injections it returns.

        Independent from forwarding: it never alters the message in flight,
        it only allows emitting diagnostic packets (e.g. a latency probe).
        """
        for target, injected in self.hooks.observe(session, packet) or ():
            if target == "client":
                session.to_client(injected)
            elif target == "server":
                session.to_server(injected)

    def _process(self, session, msg, from_server):
        if from_server and session.kind == "login":
            redirect = p.parse_redirect(msg)
            if redirect:
                host, port, ticket = redirect
                self.game_targets.append((host, port))
                self.last_game_target = (host, port)
                msg = p.build_redirect(msg, self.local_host, self.local_game_port, ticket)
                session.log("---", f"redirect {host}:{port} rewritten to the proxy")
        if from_server:
            return self.hooks.server(session, msg)
        return self.hooks.client(session, msg)


def _console(proxy, loop):
    for line in sys.stdin:
        cmd, _, msg = line.rstrip("\n").partition(" ")
        session = proxy.last_game_session
        if not msg or cmd not in ("s", "c"):
            print("usage: s <message> | c <message>")
        elif session is None:
            print("no game session yet")
        elif cmd == "s":
            loop.call_soon_threadsafe(session.to_server, msg)
        else:
            loop.call_soon_threadsafe(session.to_client, msg)


async def main():
    if not config.LOGIN_HOST:
        sys.exit("LOGIN_HOST missing in config.py (upstream login server, or the mock's).")
    proxy = Proxy(config.LOGIN_HOST, config.LOGIN_PORT, config.LOCAL_HOST,
                  config.LOCAL_LOGIN_PORT, config.LOCAL_GAME_PORT, config.LOG_DIR,
                  echo=config.ECHO_TO_CONSOLE)
    await proxy.start()
    print(f"Proxy listening: login {config.LOCAL_HOST}:{proxy.local_login_port}, "
          f"game {config.LOCAL_HOST}:{proxy.local_game_port}")
    print(f"Forwarding login to {config.LOGIN_HOST}:{config.LOGIN_PORT}")
    threading.Thread(target=_console, args=(proxy, asyncio.get_running_loop()), daemon=True).start()
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
