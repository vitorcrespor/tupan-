"""Opt-in checks against migrated PostgreSQL; all test data/roles roll back.

Run explicitly with TUPAN_RUN_DATABASE_TESTS=1 using an administrative database
connection. No OpenAI calls, Supabase Auth users, or durable test accounts.
"""
from __future__ import annotations

import os
import secrets
import unittest
from contextlib import asynccontextmanager
from uuid import uuid4

import asyncpg
import httpx
from dotenv import load_dotenv


class _TransactionPool:
    """Bind real services to one outer rollback-only database transaction."""

    def __init__(self, connection):
        self.connection = connection

    @asynccontextmanager
    async def acquire(self):
        yield self.connection

    async def execute(self, query, *args):
        return await self.connection.execute(query, *args)

    async def fetchrow(self, query, *args):
        return await self.connection.fetchrow(query, *args)


@unittest.skipUnless(os.getenv("TUPAN_RUN_DATABASE_TESTS") == "1", "Requires explicit live database opt-in")
class MigratedDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        load_dotenv(override=False)
        self.connection = await asyncpg.connect(
            os.getenv("DATABASE_URL") or os.environ["DATABASE_API_URL"], timeout=12, command_timeout=20,
        )
        self.addAsyncCleanup(self.connection.close)
        self.transaction = self.connection.transaction()
        await self.transaction.start()
        self.addAsyncCleanup(self._rollback)

    async def _rollback(self):
        # asyncpg decorates rollback; unittest cannot always recognize the
        # decorated method as async. Await it explicitly before closing.
        await self.transaction.rollback()

    async def test_real_auth_http_contract_without_persisting_accounts(self):
        from backend.api.dependencies import get_control_plane_service
        from backend.api.main import create_app
        from backend.services.control_plane import ControlPlaneService

        service = ControlPlaneService()
        service._pool = _TransactionPool(self.connection)
        app = create_app()
        app.dependency_overrides[get_control_plane_service] = lambda: service
        account = {
            "email": f"migration-check-{uuid4().hex}@invalid.example",
            "password": secrets.token_urlsafe(32),
            "full_name": "Rollback-only migration check",
            "organization_name": "Rollback-only migration check",
        }
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            registered = await client.post("/api/v1/auth/register", json=account)
            self.assertEqual(registered.status_code, 201)
            self.assertIn("httponly", registered.headers["set-cookie"].lower())
            self.assertNotIn("token", registered.json())
            user = registered.json()["user"]
            self.assertIsInstance(user["id"], str)
            self.assertNotIn("password_hash", user)
            session = await client.get("/api/v1/auth/session")
            self.assertEqual(session.status_code, 200)
            self.assertEqual(session.json()["user"], user)
            duplicate = await client.post("/api/v1/auth/register", json=account)
            self.assertEqual(duplicate.status_code, 409)
            logout = await client.post("/api/v1/auth/logout")
            self.assertEqual(logout.status_code, 200)
            self.assertEqual((await client.get("/api/v1/auth/session")).status_code, 401)
            credentials = {key: account[key] for key in ("email", "password")}
            login = await client.post("/api/v1/auth/login", json=credentials)
            self.assertEqual(login.status_code, 200)
            self.assertEqual(login.json()["user"]["id"], user["id"])
            wrong = await client.post("/api/v1/auth/login", json={**credentials, "password": "wrong-password"})
            self.assertEqual(wrong.status_code, 401)
            self.assertEqual(wrong.json()["code"], "authentication_required")

    async def test_browser_roles_cannot_access_tupan_tables_or_privileged_jobs(self):
        from backend.migrate import migration_files

        applied = await self.connection.fetch("SELECT name, sha256 FROM tupan_internal.schema_migrations")
        self.assertEqual({row["name"]: row["sha256"] for row in applied}, {name: digest for name, digest, _ in migration_files()})
        for role in ("anon", "authenticated"):
            if not await self.connection.fetchval("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=$1)", role):
                continue
            for table in (
                "organizations", "cloud_users", "organization_memberships", "auth_sessions",
                "saved_searches", "property_notes", "district_boundaries", "portfolios",
                "estates", "market_observations", "heatmap_aggregates", "analysis_results",
                "notifications", "jobs", "conversations", "conversation_messages", "semantic_embeddings",
            ):
                allowed = await self.connection.fetchval(
                    "SELECT has_table_privilege($1, $2, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') "
                    "OR has_any_column_privilege($1, $2, 'SELECT,INSERT,UPDATE,REFERENCES')", role, f"public.{table}",
                )
                self.assertFalse(allowed, f"Direct client access to {table}")
            for function in ("public.claim_next_background_job()", "public.recover_stale_background_jobs(integer)"):
                self.assertFalse(await self.connection.fetchval("SELECT has_function_privilege($1,$2,'EXECUTE')", role, function))

    async def test_rls_and_foreign_keys_block_cross_tenant_estate_access(self):
        connection = self.connection
        tenant_a, tenant_b, portfolio_a, portfolio_b, estate_a, estate_b = [uuid4() for _ in range(6)]
        for tenant, portfolio, estate in ((tenant_a, portfolio_a, estate_a), (tenant_b, portfolio_b, estate_b)):
            await connection.execute("INSERT INTO organizations(id,name) VALUES($1,'Rollback-only isolation check')", tenant)
            await connection.execute("INSERT INTO portfolios(id,organization_id,name) VALUES($1,$2,'Test')", portfolio, tenant)
            await connection.execute("INSERT INTO estates(id,organization_id,portfolio_id) VALUES($1,$2,$3)", estate, tenant, portfolio)
        # Test real RLS as an unprivileged role, not the administrative pool user.
        role = f"tupan_test_{uuid4().hex}"
        await connection.execute(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOBYPASSRLS")
        await connection.execute(f"GRANT {role} TO CURRENT_USER")
        await connection.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
        await connection.execute(f"GRANT SELECT, INSERT ON estates, portfolios TO {role}")
        await connection.execute(f"SET LOCAL ROLE {role}")
        for tenant, expected in ((tenant_a, estate_a), (tenant_b, estate_b)):
            await connection.execute("SELECT set_config('app.organization_id',$1,true)", str(tenant))
            visible = await connection.fetch("SELECT id FROM estates")
            self.assertEqual([row["id"] for row in visible], [expected])
        with self.assertRaises(asyncpg.InsufficientPrivilegeError):
            async with connection.transaction():
                await connection.execute("INSERT INTO estates(id,organization_id) VALUES($1,$2)", uuid4(), tenant_a)
        with self.assertRaises(asyncpg.ForeignKeyViolationError):
            async with connection.transaction():
                await connection.execute(
                    "INSERT INTO estates(id,organization_id,portfolio_id) VALUES($1,$2,$3)", uuid4(), tenant_b, portfolio_a,
                )
        await connection.execute("RESET ROLE")


if __name__ == "__main__":
    unittest.main()
