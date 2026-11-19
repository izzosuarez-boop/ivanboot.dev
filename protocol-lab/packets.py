"""Frame segmentation and header/body parsing for a legacy text-over-TCP protocol.

This module replaces the simple `protocol.Framer` for serious packet work:

  TCP (stream)  --feed-->  [Packet, Packet, ...]  (already-complete messages)

Network problems it solves that the original `Framer` did not cover well:

  * Fragmentation: a message can arrive split across several `recv` reads;
    the residual buffer is kept between `feed()` calls.
  * Coalescing ("TCP stickiness"): several frames can arrive glued together in
    a single read; `feed()` returns every complete one.
  * Direction-specific terminators: server->client ends in ``\\x00`` and
    client->server in ``\\n\\x00``. The terminator is removed from the body,
    not dragged along (the old `Framer` left the ``\\n`` stuck to the message).
  * A terminator split across two reads (``\\n`` in one, ``\\x00`` in the
    next): handled because the whole buffer is searched.
  * An unterminated frame growing without bound (memory): capped by
    `max_frame` with `PacketError`, instead of accumulating bytes forever.

Each `Packet` carries the header (message ID: ``GA``, ``GDM``, ``HC``...)
already separated from the body — which is what higher-level logic needs to
attach its hooks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

# --- Traffic direction ---------------------------------------------------------

SERVER = "S>C"  # server -> client
CLIENT = "C>S"  # client -> server

# Terminators per direction, most specific first. For the client both
# '\n\x00' (as documented) and a bare '\x00' are accepted, because some server
# implementations omit the '\n'.
TERMINATORS = {
    SERVER: (b"\x00",),
    CLIENT: (b"\n\x00", b"\x00"),
}

# Maximum size of an unterminated frame before considering it corrupt.
MAX_FRAME = 1 << 20  # 1 MiB


class PacketError(Exception):
    """Invalid frame (exceeds `max_frame` or has no terminator)."""


# Known protocol headers (the LONGEST matching prefix wins, so that e.g.
# "AT<ticket>" is not confused with "ATTICKET"). Extensible by passing
# `headers=` to `PacketManager`. Recovered from traffic captures.
KNOWN_HEADERS: tuple[bytes, ...] = (
    # login / connection
    b"AXK", b"AYK", b"HC", b"HG", b"AT",
    # map & interactive objects
    b"GDM", b"GDF",
    # action / combat / entities
    b"GTL", b"GTS", b"GTF", b"GKK", b"GKE", b"GM", b"GA", b"GE",
    # misc
    b"JX", b"BD", b"Ow", b"As",
    b"ping", b"qping",
)

# Fallback when the message starts with no known header: take the alphabetic
# prefix (message IDs are short). Prevents swallowing the body when the body
# itself starts with letters (e.g. "ATTICKET1").
_RE_ALPHA = re.compile(rb"^[A-Za-z]{1,6}")


def split_header(raw: bytes, headers: Sequence[bytes] = KNOWN_HEADERS):
    """Returns (header, body) of a frame already stripped of its terminator.

    Prefers the LONGEST matching prefix in `headers`; if none matches, falls
    back to the generic alphabetic prefix. If the frame does not start with a
    letter, the header is empty and everything is body.
    """
    best = b""
    for h in headers:
        if len(h) > len(best) and raw.startswith(h):
            best = h
    if best:
        return best.decode("ascii"), raw[len(best):]
    m = _RE_ALPHA.match(raw)
    if m:
        return m.group(0).decode("ascii"), raw[len(m.group(0)):]
    return "", raw


@dataclass
class Packet:
    """A complete frame, with header and body separated."""

    direction: str
    raw: bytes              # message bytes WITHOUT the terminator
    terminator: bytes       # the terminator that closed it
    header: str             # e.g. "GA", "GDM", "HC" ("" if none applies)
    body: bytes             # the rest: "001;2", "10000|...|key", ...

    def text(self) -> str:
        """The message as text (equivalent to protocol.to_text on `raw`)."""
        return self.raw.decode("utf-8", "replace").rstrip("\n")

    def params(self, sep: bytes = b"|") -> list[bytes]:
        """The body split by a separator ('|' by default).

        If the body starts with the separator (common: "GDM|a|b|c"), the first
        empty field is dropped.
        """
        if not self.body:
            return []
        parts = self.body.split(sep)
        if parts and parts[0] == b"":
            parts = parts[1:]
        return parts

    def with_body(self, new_body: bytes) -> "Packet":
        """A copy with another body (rebuilds `raw`, keeping the header)."""
        raw = self.header.encode("ascii") + new_body
        return Packet(self.direction, raw, self.terminator, self.header, new_body)

    def serialize(self) -> bytes:
        """Bytes ready for the socket: body + original terminator."""
        return self.raw + self.terminator

    def __repr__(self) -> str:
        return f"Packet({self.direction!r}, header={self.header!r}, body={self.body!r})"


class PacketManager:
    """Reassembles the TCP stream into `Packet`s and splits header from body.

    Usage:
        mgr = PacketManager(CLIENT)
        for packet in mgr.feed(recv_data):
            print(packet.header, packet.body)

    One instance per connection and per direction; `feed()` is reentrant and
    keeps the incomplete residue between calls.
    """

    def __init__(self, direction: str, max_frame: int = MAX_FRAME,
                 headers: Sequence[bytes] = KNOWN_HEADERS):
        if direction not in TERMINATORS:
            raise ValueError(f"unknown direction: {direction!r}")
        self.direction = direction
        self.max_frame = max_frame
        self.headers = tuple(headers)
        self._terminators = TERMINATORS[direction]
        self._buf = bytearray()
        # Useful diagnostic counters.
        self.packets = 0
        self.discarded = 0

    @property
    def remainder(self) -> bytes:
        """Incomplete residue that has not yet closed a frame."""
        return bytes(self._buf)

    def _find_terminator(self):
        """(index, terminator) of the nearest terminator; None if absent.

        On an index tie the longer terminator wins, so a '\\n\\x00' is never
        split at its '\\x00'.
        """
        best = None
        for term in self._terminators:
            idx = self._buf.find(term)
            if idx == -1:
                continue
            if best is None or idx < best[0] or (idx == best[0] and len(term) > len(best[1])):
                best = (idx, term)
        return best

    def feed(self, data: bytes) -> list[Packet]:
        """Appends bytes to the buffer and returns the newly completed frames."""
        if data:
            self._buf += data

        out: list[Packet] = []
        while True:
            found = self._find_terminator()
            if found is None:
                break
            idx, term = found
            raw = bytes(self._buf[:idx])
            del self._buf[:idx + len(term)]
            if len(raw) > self.max_frame:
                self.discarded += 1
                raise PacketError(
                    f"frame of {len(raw)} bytes > max_frame={self.max_frame}")
            self.packets += 1
            out.append(self._parse(raw, term))

        if len(self._buf) > self.max_frame:
            self._buf.clear()
            self.discarded += 1
            raise PacketError(
                f"unterminated residue > max_frame={self.max_frame}; buffer purged")
        return out

    def _parse(self, raw: bytes, term: bytes) -> Packet:
        header, body = split_header(raw, self.headers)
        return Packet(self.direction, raw, term, header, body)


# Alias with the same behavior under another name.
PacketParser = PacketManager


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    # Fragmentation: one message split across two reads.
    mgr = PacketManager(SERVER)
    assert mgr.feed(b"HCke") == []
    pkts = mgr.feed(b"y1\x00HG\x00")
    assert [pk.header for pk in pkts] == ["HC", "HG"]
    assert [pk.body for pk in pkts] == [b"key1", b""]
    assert pkts[0].text() == "HCkey1"
    assert pkts[0].serialize() == b"HCkey1\x00"

    # Coalescing and the '\n\x00' terminator on the client side.
    mgr = PacketManager(CLIENT)
    pkts = mgr.feed(b"AT12\n\x00GA001;2\n\x00")
    assert [pk.header for pk in pkts] == ["AT", "GA"]
    assert [pk.text() for pk in pkts] == ["AT12", "GA001;2"]
    assert pkts[1].params(b";") == [b"001", b"2"]

    # Alphanumeric header: 'ATTICKET1' must yield 'AT' + 'TICKET1', not 'ATTICKET'.
    header, body = split_header(b"ATTICKET1")
    assert (header, body) == ("AT", b"TICKET1"), (header, body)

    # GDM with '|' separator, without confusing 'GD'/'GDM'.
    pkts = PacketManager(SERVER).feed(b"GDM|10000|date|key\x00")
    assert pkts[0].header == "GDM"
    assert pkts[0].params() == [b"10000", b"date", b"key"]

    # A terminator split across reads.
    mgr = PacketManager(CLIENT)
    assert mgr.feed(b"BD\n") == []
    pkts = mgr.feed(b"\x00")
    assert pkts and pkts[0].text() == "BD"

    # Controlled overflow.
    mgr = PacketManager(SERVER, max_frame=8)
    try:
        mgr.feed(b"X" * 10)
        raise AssertionError("PacketError expected")
    except PacketError:
        pass

    print("OK packets.py")
