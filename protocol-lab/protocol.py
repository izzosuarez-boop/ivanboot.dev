"""Wire-format primitives of a reverse-engineered legacy client-server text protocol.

Server -> client: each message ends in \\x00.
Client -> server: each message ends in \\n\\x00.

Message IDs and encodings were recovered from passive traffic captures.
"""

HASH = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"


class Framer:
    """Reassembles complete messages from the chunks TCP delivers."""

    def __init__(self):
        self._buf = b""

    def feed(self, data: bytes) -> list[bytes]:
        """Returns the complete messages (without the trailing \\x00)."""
        self._buf += data
        *messages, self._buf = self._buf.split(b"\x00")
        return messages


def to_text(raw: bytes) -> str:
    return raw.decode("utf-8", "replace").rstrip("\n")


def server_bytes(msg: str) -> bytes:
    """A message as the server sends it (towards the client)."""
    return msg.encode("utf-8") + b"\x00"


def client_bytes(msg: str) -> bytes:
    """A message as the client sends it (towards the server)."""
    return msg.encode("utf-8") + b"\n\x00"


# --- Login -> game-server redirect -------------------------------------------

def decode_ip(s: str) -> str:
    return ".".join(str((ord(s[i]) - 48) * 16 + (ord(s[i + 1]) - 48)) for i in range(0, 8, 2))


def encode_ip(ip: str) -> str:
    return "".join(chr(int(o) // 16 + 48) + chr(int(o) % 16 + 48) for o in ip.split("."))


def decode_port(s: str) -> int:
    return HASH.index(s[0]) * 4096 + HASH.index(s[1]) * 64 + HASH.index(s[2])


def encode_port(port: int) -> str:
    return HASH[port // 4096] + HASH[(port // 64) % 64] + HASH[port % 64]


def parse_redirect(msg: str):
    """If msg is the redirect to the game server, returns (host, port, ticket); else None."""
    if msg.startswith("AXK") and len(msg) >= 14:
        return decode_ip(msg[3:11]), decode_port(msg[11:14]), msg[14:]
    if msg.startswith("AYK"):
        target, _, ticket = msg[3:].partition(";")
        host, _, port = target.partition(":")
        return host, int(port), ticket
    return None


def build_redirect(original: str, host: str, port: int, ticket: str) -> str:
    """Rebuilds the redirect in the same format (AXK/AYK) as the original."""
    if original.startswith("AXK"):
        return "AXK" + encode_ip(host) + encode_port(port) + ticket
    return f"AYK{host}:{port};{ticket}"


# --- Grid cells ----------------------------------------------------------------

def cell_to_hash(cell: int) -> str:
    return HASH[cell // 64] + HASH[cell % 64]


def hash_to_cell(s: str) -> int:
    return HASH.index(s[0]) * 64 + HASH.index(s[1])
