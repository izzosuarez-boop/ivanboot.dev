"""Replay and fuzzing harness for `packets.PacketManager`.

Goal: validate locally that frame reassembly survives bursts, fragmentation
and garbage without breaking the framing or losing valid packets.

Levels:

  1. Offline parser replay: takes a list of frames, serializes them with their
     terminator, slices the stream in different ways and checks the round-trip
     (reassembled packets, re-serialized, rebuild the original stream).

  2. Invariant fuzzing: cuts at any position, split terminators, duplicated
     bursts, an unterminated frame exceeding `max_frame`, garbage.

  3. Online replay (optional): connects to the proxy's login, follows the
     redirect and re-injects the client frames through the proxy, stressing
     the whole chain (client -> proxy -> mock server).

Fragmentation modes: whole, fixed, byte, random, terminator.

Usage:
    python replay.py
    python replay.py --online --host 127.0.0.1 --login-port 4430
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys

import packets as pkt

MODES = ("whole", "fixed", "byte", "random", "terminator")


def terminator_of(direction: str) -> bytes:
    return b"\n\x00" if direction == pkt.CLIENT else b"\x00"


def _to_bytes(frame) -> bytes:
    return bytes(frame) if isinstance(frame, (bytes, bytearray)) else frame.encode("latin-1")


def encode(frames, direction: str, terminator: bytes | None = None) -> bytes:
    """Concatenates frames with their terminator (the stream as it travels)."""
    term = terminator if terminator is not None else terminator_of(direction)
    return b"".join(_to_bytes(f) + term for f in frames)


def fragment(stream: bytes, mode: str, size: int = 7, rng: random.Random | None = None):
    """Slices `stream` according to `mode`. Yields byte chunks."""
    if mode in ("whole", "coalesced"):
        yield stream
        return
    if mode == "fixed":
        for i in range(0, len(stream), size):
            yield stream[i:i + size]
        return
    if mode == "byte":
        for i in range(len(stream)):
            yield stream[i:i + 1]
        return
    if mode == "random":
        rng = rng or random.Random(1234)
        i = 0
        while i < len(stream):
            n = rng.randint(1, max(1, size))
            yield stream[i:i + n]
            i += n
        return
    if mode == "terminator":
        # leaves the last byte of each terminator for the next chunk, to force
        # the case of a 2-byte terminator split in half (b"\n\x00").
        i = 0
        while i < len(stream):
            j = stream.find(b"\x00", i)
            if j == -1:
                yield stream[i:]
                return
            yield stream[i:j]
            yield stream[j:j + 1]
            i = j + 1
        return
    raise ValueError(f"unknown fragmentation mode: {mode!r}")


def replay_parser(frames, direction: str, mode: str = "random",
                  size: int = 7, rng: random.Random | None = None) -> list[pkt.Packet]:
    """Re-injects the fragmented frames and returns the reassembled packets."""
    stream = encode(frames, direction)
    mgr = pkt.PacketManager(direction)
    out: list[pkt.Packet] = []
    for chunk in fragment(stream, mode, size, rng):
        out.extend(mgr.feed(chunk))
    return out


def verify_modes(frames, direction: str, size: int = 7) -> dict[str, bool]:
    """Tries every mode plus a cut at every position. True = OK."""
    stream = encode(frames, direction)
    expected = [_to_bytes(f).decode("latin-1") for f in frames]
    result: dict[str, bool] = {}

    for mode in MODES:
        rng = random.Random(20261007)
        packets = replay_parser(frames, direction, mode, size, rng)
        rebuilt = b"".join(p.serialize() for p in packets)
        result[mode] = (rebuilt == stream
                        and [p.text() for p in packets] == expected)

    # A cut at every possible position (exhaustive fragmentation sweep).
    ok = True
    for pos in range(len(stream) + 1):
        m = pkt.PacketManager(direction)
        out = m.feed(stream[:pos]) + m.feed(stream[pos:])
        if b"".join(p.serialize() for p in out) != stream:
            ok = False
            break
    result["boundary"] = ok
    return result


def fuzz_invariants(frames, direction: str) -> dict[str, bool]:
    """Robustness invariants. Returns {name: True/False}."""
    stream = encode(frames, direction)
    term = terminator_of(direction)
    checks: dict[str, bool] = {}

    # 1. Cutting the stream at any length never breaks or loses data
    #    inconsistently: what is parsed is a prefix of the stream.
    ok = True
    for L in range(len(stream) + 1):
        m = pkt.PacketManager(direction)
        out = m.feed(stream[:L])
        rebuilt = b"".join(p.serialize() for p in out)
        if not stream.startswith(rebuilt) or len(rebuilt) > L:
            ok = False
            break
    checks["cut_at_any_position"] = ok

    # 2. Duplicating the stream yields exactly twice the packets.
    m = pkt.PacketManager(direction)
    doubles = m.feed(stream + stream)
    checks["duplicated_burst"] = len(doubles) == 2 * len(frames)

    # 3. A terminator with an empty frame parses without error.
    m = pkt.PacketManager(direction)
    empties = m.feed(term)
    checks["empty_frame"] = len(empties) == 1 and empties[0].raw == b""

    # 4. Controlled overflow: an unterminated frame beyond max_frame raises
    #    PacketError, purges the buffer, and the parser stays usable.
    m = pkt.PacketManager(direction, max_frame=8)
    detected = False
    try:
        m.feed(b"X" * 32)
    except pkt.PacketError:
        detected = True
    first = b"HG" + term
    first_txt = "HG"
    usable = [p.text() for p in m.feed(first)] == [first_txt]
    checks["overflow_detected_and_purged"] = detected and usable

    # 5. Idempotence: feeding the whole stream at once == feeding it 1 byte at a time.
    a = [p.serialize() for p in pkt.PacketManager(direction).feed(stream)]
    m = pkt.PacketManager(direction)
    b = []
    for i in range(len(stream)):
        b += [p.serialize() for p in m.feed(stream[i:i + 1])]
    checks["idempotent_byte_by_byte"] = a == b

    return checks


def sample_frames(direction: str) -> list[str]:
    if direction == pkt.SERVER:
        return [
            "HCmockkey",
            "HG",
            "GDM|7411|1700000000|mapkey01",
            "GDF|dM;0;0|dN;4;10|d6;1;0|eS;0;0",
            "GTL|1;Hero;50;1200;6;3;0|2;Enemy;50;1100;6;3;1",
            "GM|+1000;dM;3",
            "GM|-1000",
            "GA1;1;7;dM;3",
            "GA501;1;3;dM",
            "GKE1|1",
            "BD1791349780",
            "qping",
        ]
    return [
        "AT40961",
        "GA0013dM",
        "GA500dM;3",
        "GKK1",
        "BD0",
        "ping",
    ]


def report(direction: str) -> bool:
    frames = sample_frames(direction)
    print("=" * 68)
    print(f"Replay/fuzzing  direction={direction}  ({len(frames)} frames)")
    print("=" * 68)
    all_ok = True
    for mode, ok in verify_modes(frames, direction).items():
        print(("  OK   " if ok else "  FAIL ") + f"  mode {mode}")
        all_ok &= ok
    for name, ok in fuzz_invariants(frames, direction).items():
        print(("  OK   " if ok else "  FAIL ") + f"  fuzz {name}")
        all_ok &= ok
    return all_ok


async def replay_online(host: str, login_port: int, frames, interval: float = 0.05):
    """Re-injects client `frames` through a running proxy."""
    import protocol as proto
    from mock_client import Reader

    r, w = await asyncio.open_connection(host, login_port)
    reader = Reader(r, pkt.SERVER)
    await asyncio.wait_for(reader.next_packet(), 3)          # HC
    red = await asyncio.wait_for(reader.next_packet(), 3)    # AXK/AYK
    info = proto.parse_redirect(red.text())
    if info is None:
        raise RuntimeError(f"unrecognized redirect: {red.text()!r}")
    game_host, game_port, ticket = info

    rg, wg = await asyncio.open_connection(game_host, game_port)
    game_reader = Reader(rg, pkt.SERVER)
    await asyncio.wait_for(game_reader.next_packet(), 3)      # HG
    wg.write(proto.client_bytes("AT" + ticket))
    await wg.drain()

    # AT is sent separately with the real ticket; don't duplicate it.
    frame_list = [f for f in frames if not _to_bytes(f).startswith(b"AT")]

    received: list[str] = []
    for f in frame_list:
        wg.write(proto.client_bytes(f))
        await wg.drain()
        await asyncio.sleep(interval)
        received += [p.text() for p in await game_reader.drain(interval)]
    wg.close()
    w.close()
    return received


def main(argv=None):
    ap = argparse.ArgumentParser(description="Replay + fuzzing for PacketManager.")
    ap.add_argument("--online", action="store_true",
                    help="also re-inject against a running proxy")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--login-port", type=int, default=4430)
    args = ap.parse_args(argv)

    all_ok = True
    for direction in (pkt.SERVER, pkt.CLIENT):
        all_ok &= report(direction)

    if args.online:
        print("-" * 68)
        print(f"Online replay against {args.host}:{args.login_port}")
        received = asyncio.run(replay_online(args.host, args.login_port,
                                             sample_frames(pkt.CLIENT)))
        print(f"  server replies: {received}")

    print("-" * 68)
    print("ALL OK" if all_ok else "FAILURES FOUND")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
