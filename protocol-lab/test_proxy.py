"""Tests for the protocol primitives and the proxy.

Usage:  python test_proxy.py   (or: pytest test_proxy.py)
"""

import asyncio
import tempfile

import protocol as p
from proxy import Hooks, Proxy


def test_protocol():
    assert p.decode_ip(p.encode_ip("190.12.255.7")) == "190.12.255.7"
    for port in (443, 5555, 65535):
        assert p.decode_port(p.encode_port(port)) == port
    for cell in (0, 63, 64, 479):
        assert p.hash_to_cell(p.cell_to_hash(cell)) == cell
    f = p.Framer()
    assert f.feed(b"HCab") == []
    assert f.feed(b"cd\x00AT12\n\x00GD") == [b"HCabcd", b"AT12\n"]
    assert f.feed(b"M\x00") == [b"GDM"]
    assert p.parse_redirect("AYK1.2.3.4:5555;tk") == ("1.2.3.4", 5555, "tk")


class TestHooks(Hooks):
    def client(self, session, msg):
        if msg == "drop":
            return None
        if msg == "change":
            return "changed"
        return msg


async def read_n(reader, framer, n):
    messages = []
    while len(messages) < n:
        messages += [p.to_text(x) for x in framer.feed(await reader.read(1024))]
    return messages


async def run_proxy_test():
    game_received = []
    game_done = asyncio.Event()

    async def game(r, w):
        w.write(p.server_bytes("HG"))
        await w.drain()
        game_received.extend(await read_n(r, p.Framer(), 3))
        game_done.set()
        w.close()

    game_srv = await asyncio.start_server(game, "127.0.0.1", 0)
    game_port = game_srv.sockets[0].getsockname()[1]

    async def login(r, w):
        w.write(p.server_bytes("HCkey"))
        w.write(p.server_bytes("AXK" + p.encode_ip("127.0.0.1")
                               + p.encode_port(game_port) + "TICKET1"))
        await w.drain()
        await r.read(1024)
        w.close()

    login_srv = await asyncio.start_server(login, "127.0.0.1", 0)
    login_port = login_srv.sockets[0].getsockname()[1]

    proxy = Proxy("127.0.0.1", login_port, "127.0.0.1", 0, 0,
                  tempfile.mkdtemp(), hooks=TestHooks())
    await proxy.start()

    # Login through the proxy: the redirect must point at the proxy, not at the real server.
    r, w = await asyncio.open_connection("127.0.0.1", proxy.local_login_port)
    hc, axk = await read_n(r, p.Framer(), 2)
    assert hc == "HCkey"
    assert p.parse_redirect(axk) == ("127.0.0.1", proxy.local_game_port, "TICKET1"), axk
    w.write(p.client_bytes("Af"))
    w.close()

    # Game through the proxy: hooks + injection.
    r, w = await asyncio.open_connection("127.0.0.1", proxy.local_game_port)
    assert await read_n(r, p.Framer(), 1) == ["HG"]
    for msg in ("ATTICKET1", "drop", "change"):
        w.write(p.client_bytes(msg))
    await w.drain()
    await asyncio.sleep(0.1)
    proxy.last_game_session.to_server("BD")
    await asyncio.wait_for(game_done.wait(), 2)
    assert game_received == ["ATTICKET1", "changed", "BD"], game_received
    w.close()

    await proxy.close()
    game_srv.close()
    login_srv.close()


def test_proxy():
    asyncio.run(run_proxy_test())


if __name__ == "__main__":
    test_protocol()
    test_proxy()
    print("OK")
