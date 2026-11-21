"""Apply apps/api/migrations/*.sql to Supabase in order, once each (tracked in public.schema_migrations).

    python scripts/db/migrate.py          # apply pending
    python scripts/db/migrate.py --list   # show status
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import psycopg

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = sorted((ROOT / "apps/api/migrations").glob("*.sql"))


def db_url() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*SUPABASE_DB_URL\s*=\s*(.*?)\s*$", line)
        if m:
            return m.group(1).strip("'\"")
    raise SystemExit("SUPABASE_DB_URL missing in .env")


def main() -> int:
    with psycopg.connect(db_url(), connect_timeout=15, autocommit=False) as conn:
        conn.execute("create table if not exists public.schema_migrations (name text primary key, applied_at timestamptz default now())")
        conn.execute("alter table public.schema_migrations enable row level security")
        done = {r[0] for r in conn.execute("select name from public.schema_migrations")}
        if "--list" in sys.argv:
            for m in MIGRATIONS:
                print(f"  {'applied' if m.name in done else 'PENDING'}  {m.name}")
            return 0
        pending = [m for m in MIGRATIONS if m.name not in done]
        for m in pending:
            with conn.transaction():  # each migration is all-or-nothing
                conn.execute(m.read_text(encoding="utf-8"))
                conn.execute("insert into public.schema_migrations (name) values (%s)", (m.name,))
            print(f"  applied {m.name}")
        if not pending:
            print("  nothing to apply")
        tables = conn.execute("""select c.relname, c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace
                                 where n.nspname = 'public' and c.relkind = 'r' order by 1""").fetchall()
        print("  tables:", ", ".join(f"{t}{' (RLS)' if rls else ' (NO RLS!)'}" for t, rls in tables))
    return 0


if __name__ == "__main__":
    sys.exit(main())
