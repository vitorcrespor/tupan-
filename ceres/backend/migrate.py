"""Explicit, atomic migrations; never imported/run by the API or desktop.

Preview: python -m backend.migrate
Apply:   python -m backend.migrate --apply
Use an administrative DATABASE_URL, or the local DATABASE_API_URL fallback.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv


MIGRATIONS = Path(__file__).with_name("migrations")
LEDGER = "tupan_internal.schema_migrations"


def migration_files() -> list[tuple[str, str, str]]:
    return [
        (path.name, hashlib.sha256(path.read_bytes()).hexdigest(), path.read_text(encoding="utf-8"))
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))
    ]


async def migrate(*, apply: bool) -> None:
    load_dotenv(MIGRATIONS.parent.parent / ".env", override=False)
    database_url = (os.getenv("DATABASE_URL") or os.getenv("DATABASE_API_URL", "")).strip()
    if not database_url:
        raise RuntimeError("missing_database_url")
    connection = await asyncpg.connect(database_url, timeout=12, command_timeout=120)
    current = "preflight"
    try:
        async with connection.transaction():
            await connection.execute("SET LOCAL lock_timeout = '10s'")
            await connection.execute("SET LOCAL statement_timeout = '120s'")
            # A single session/transaction owns the entire migration sequence.
            await connection.execute("SELECT pg_advisory_xact_lock(84621, 1)")
            exists = await connection.fetchval("SELECT to_regclass($1) IS NOT NULL", LEDGER)
            applied = {
                row["name"]: row["sha256"]
                for row in (await connection.fetch(f"SELECT name, sha256 FROM {LEDGER}") if exists else [])
            }
            files = migration_files()
            local_hashes = {name: digest for name, digest, _ in files}
            if any(local_hashes.get(name) != digest for name, digest in applied.items()):
                raise RuntimeError("migration_history_mismatch")
            if not exists and await connection.fetchval("SELECT to_regclass('public.organizations') IS NOT NULL"):
                raise RuntimeError("existing_schema_requires_explicit_baseline_review")
            pending = [item for item in files if item[0] not in applied]
            print(json.dumps({"mode": "apply" if apply else "check", "pending": [item[0] for item in pending]}), flush=True)
            if not apply or not pending:
                return
            await connection.execute("CREATE SCHEMA IF NOT EXISTS tupan_internal")
            await connection.execute("REVOKE ALL ON SCHEMA tupan_internal FROM PUBLIC")
            await connection.execute(f"""CREATE TABLE IF NOT EXISTS {LEDGER} (
                name TEXT PRIMARY KEY, sha256 TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )""")
            await connection.execute(f"REVOKE ALL ON TABLE {LEDGER} FROM PUBLIC")
            for role in ("anon", "authenticated"):
                if await connection.fetchval("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=$1)", role):
                    await connection.execute(f"REVOKE ALL ON SCHEMA tupan_internal FROM {role}")
                    await connection.execute(f"REVOKE ALL ON TABLE {LEDGER} FROM {role}")
            for current, digest, sql in pending:
                await connection.execute(sql)
                await connection.execute(f"INSERT INTO {LEDGER} (name, sha256) VALUES ($1, $2)", current, digest)
                print(json.dumps({"migration": current, "status": "staged"}), flush=True)
        print(json.dumps({"status": "committed", "count": len(pending)}), flush=True)
    except Exception:
        print(json.dumps({"status": "rolled_back", "operation": current}), flush=True)
        raise
    finally:
        await connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply pending migrations atomically (default: check only).")
    args = parser.parse_args()
    try:
        asyncio.run(migrate(apply=args.apply))
    except Exception as error:
        # Never emit a DSN or raw driver exception containing credentials.
        print(json.dumps({"error_type": type(error).__name__, "sqlstate": getattr(error, "sqlstate", None)}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
