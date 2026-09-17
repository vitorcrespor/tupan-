"""HTTP cutover characterization: Supabase sessions authorize existing data routes."""
from __future__ import annotations

import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx

from backend.api.dependencies import get_control_plane_service, get_tenant_data_repository
from backend.api.main import create_app
from backend.services.errors import NotFoundError
from backend.tests.test_supabase_auth_v2 import (
    _SupabaseConnection, _SupabasePool, _TestableSupabaseControlPlane,
)


class _ProfileConnection(_SupabaseConnection):
    async def fetchrow(self, query, *args):
        row = await super().fetchrow(query, *args)
        if row and "JOIN" in query:
            return {key: value for key, value in row.items()
                    if key not in {"password_hash", "supabase_user_id"}}
        return row


class SupabaseDataRouteContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_supabase_login_cookie_reaches_tenant_data_and_rejects_foreign_id(self):
        identity = str(uuid4())
        provider = httpx.AsyncClient(
            base_url="https://project.supabase.co",
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
                "user": {"id": identity, "email": "cutover@example.com",
                         "email_confirmed_at": "2026-01-01T00:00:00Z"},
                "access_token": "never-expose-provider-token",
            })),
        )
        self.addAsyncCleanup(provider.aclose)
        connection = _ProfileConnection()
        service = _TestableSupabaseControlPlane(_SupabasePool(connection), provider)
        repository = AsyncMock()
        repository.list_portfolios.return_value = []
        repository.get_portfolio.side_effect = NotFoundError("Portfolio not found.")
        app = create_app()
        app.dependency_overrides[get_control_plane_service] = lambda: service
        app.dependency_overrides[get_tenant_data_repository] = lambda: repository

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver",
        ) as client:
            denied = await client.get("/api/v1/portfolios")
            self.assertEqual(denied.status_code, 401)
            registered = await client.post("/api/v1/auth/register", json={
                "email": "cutover@example.com", "password": "correct-password",
            })
            self.assertEqual(registered.status_code, 201, registered.text)
            self.assertNotIn("never-expose-provider-token", registered.text)
            self.assertIn("HttpOnly", registered.headers["set-cookie"])
            principal = registered.json()["user"]
            portfolios = await client.get("/api/v1/portfolios", params={"organization_id": str(uuid4())})
            self.assertEqual(portfolios.status_code, 200, portfolios.text)
            context = repository.list_portfolios.call_args.args[0]
            self.assertEqual(context.organization_id, principal["organization_id"])
            self.assertEqual(context.user_id, principal["id"])
            foreign = await client.get(f"/api/v1/portfolios/{uuid4()}")
            self.assertEqual(foreign.status_code, 404)
            repository.get_portfolio.assert_awaited_once()
            self.assertEqual(
                repository.get_portfolio.call_args.args[0].organization_id,
                principal["organization_id"],
            )
