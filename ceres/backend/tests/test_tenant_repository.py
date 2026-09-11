from __future__ import annotations

import unittest
from uuid import uuid4

from pydantic import ValidationError

from backend.api.schemas.estate import EstateCreateRequest
from backend.repositories.tenant_data import TenantContext, TenantDataRepository, _record
from backend.services.errors import NotFoundError


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Connection:
    def __init__(self):
        self.calls = []

    def transaction(self):
        return _Transaction()

    async def execute(self, query, *args):
        self.calls.append(("execute", query, args))
        if query.startswith("UPDATE estates"):
            return "UPDATE 1" if args[1] == "tenant-a" else "UPDATE 0"
        return "OK"

    async def fetchrow(self, query, *args):
        self.calls.append(("fetchrow", query, args))
        if "FROM estates" in query and args[1] == "tenant-a":
            return {"id": args[0], "organization_id": args[1]}
        return None

    async def fetchval(self, query, *args):
        self.calls.append(("fetchval", query, args))
        return 1 if args[1] == "tenant-a" else None


class _Acquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Pool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return _Acquire(self.connection)


class _ControlPlane:
    def __init__(self, pool):
        self.pool = pool

    async def _database(self):
        return self.pool


class TenantRepositoryIsolationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.connection = _Connection()
        self.repository = TenantDataRepository(_ControlPlane(_Pool(self.connection)))
        self.a = TenantContext(organization_id="tenant-a", user_id="user-a", role="admin")
        self.b = TenantContext(organization_id="tenant-b", user_id="user-b", role="admin")

    def test_record_adapter_serializes_uuid(self):
        record_id = uuid4()
        self.assertEqual(_record({"id": record_id})["id"], str(record_id))
    def test_client_cannot_submit_organization_scope(self):
        with self.assertRaises(ValidationError):
            EstateCreateRequest.model_validate({"title": "Scoped estate", "organization_id": "tenant-b"})
    async def test_same_estate_id_cannot_cross_tenant_boundary(self):
        estate = await self.repository.get_estate(self.a, "estate-shared-id")
        self.assertEqual(estate["organization_id"], "tenant-a")

        with self.assertRaises(NotFoundError):
            await self.repository.get_estate(self.b, "estate-shared-id")

        reads = [call for call in self.connection.calls if call[0] == "fetchrow"]
        self.assertEqual(reads[0][2], ("estate-shared-id", "tenant-a"))
        self.assertEqual(reads[1][2], ("estate-shared-id", "tenant-b"))

    async def test_estate_creation_rejects_cross_tenant_portfolio(self):
        with self.assertRaises(NotFoundError):
            await self.repository.create_estate(self.b, {"title": "Estate", "portfolio_id": "portfolio-1"})
        checks = [call for call in self.connection.calls if call[0] == "fetchval"]
        self.assertEqual(checks[-1][2], ("portfolio-1", "tenant-b"))
    async def test_portfolio_move_requires_portfolio_in_same_tenant(self):
        await self.repository.move_estate_to_portfolio(self.a, "estate-1", "portfolio-1")
        with self.assertRaises(NotFoundError):
            await self.repository.move_estate_to_portfolio(self.b, "estate-1", "portfolio-1")

        portfolio_checks = [call for call in self.connection.calls if call[0] == "fetchval"]
        self.assertEqual(portfolio_checks[0][2], ("portfolio-1", "tenant-a"))
        self.assertEqual(portfolio_checks[1][2], ("portfolio-1", "tenant-b"))

    async def test_rls_context_is_set_for_each_tenant_transaction(self):
        await self.repository.get_estate(self.a, "estate-1")
        with self.assertRaises(NotFoundError):
            await self.repository.get_estate(self.b, "estate-1")

        contexts = [call[2][0] for call in self.connection.calls if call[0] == "execute" and "set_config" in call[1]]
        self.assertEqual(contexts, ["tenant-a", "tenant-b"])


if __name__ == "__main__":
    unittest.main()