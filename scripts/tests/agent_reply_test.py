"""Regression test: the store agent never returns an empty reply (real API, ~$0.006 for 6 runs).

    python scripts/tests/agent_reply_test.py [runs]

Bug found 2026-11-22: when the model wrote its recommendation in the same response as a tool call and only
the suggestions line afterwards, the reply came back empty (the visitor saw product cards in an empty bubble).
It also ignored tool calls in responses marked end_turn. Each run asks the question that triggered it.
"""
import asyncio
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$", line)
    if m:
        os.environ.setdefault(m.group(1), m.group(2).strip("'\""))
os.environ["SUPABASE_URL"] = ""  # test turns are not logged
sys.path.insert(0, str(ROOT / "apps/api"))
sys.stdout.reconfigure(encoding="utf-8")
from app import agent  # noqa: E402


async def main() -> int:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    ok = 0
    for i in range(runs):
        conv = agent.Conversation(id=f"00000000-0000-0000-0000-0000000000{i:02d}", visitor="test")
        out = await agent.chat(conv, "What would work for my oily skin?", None, None)
        good = len(out["reply"]) > 80 and "<<SUGGEST" not in out["reply"] and len(out["suggestions"]) == 2
        ok += good
        print(("✅" if good else "❌"), f"run {i}: {len(out['reply'])} chars, {len(out['suggestions'])} suggestions, "
              f"actions {[a['type'] for a in out['actions']]}")
    print(f"{ok}/{runs}")
    return 0 if ok == runs else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
