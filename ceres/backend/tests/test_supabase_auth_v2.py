from __future__ import annotations

from datetime import datetime, timezone
import unittest

from fastapi.testclient import TestClient
import httpx

from backend.api.dependencies import get_control_plane_service, get_supabase_control_plane_service
from backend.api.main import create_app
from backend.services.control_plane import AuthenticationError, ControlPlaneService
from backend.services.supabase_control_plane import SupabaseAuthSettings, SupabaseControlPlaneService


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Acquire:
    def __init__(self, connection: "_SupabaseConnection") -> None:
        self.connection = connection

    async def __aenter__(self) -> "_SupabaseConnection":
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback) -> bool:
        return False


class _SupabaseConnection:
    def __init__(self) -> None:
        self.user: dict | None = None
        self.sessions: list[tuple] = []

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def execute(self, query: str, *args):
        if "INSERT INTO cloud_users" in query:
            self.user = {
                "id": args[0],
                "email": args[1],
                "full_name": args[2],
                "password_hash": None,
                "supabase_user_id": args[3],
                "organization_id": None,
                "role": "admin",
                "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            }
        elif "INSERT INTO organization_memberships" in query and self.user:
            self.user["organization_id"] = args[0]
        elif query.startswith("UPDATE cloud_users") and self.user and self.user["id"] == args[0]:
            self.user["supabase_user_id"] = args[1]
            return "UPDATE 1"
        elif "INSERT INTO auth_sessions" in query:
            self.sessions.append(args)
        return "OK"

    async def fetchval(self, query: str, *args):
        if "FROM cloud_users" in query and self.user and self.user["email"] == args[0]:
            return 1
        return None

    async def fetchrow(self, query: str, *args):
        if "FROM cloud_users WHERE email" in query:
            if self.user and self.user["email"] == args[0]:
                return self.user
            return None
        if "WHERE u.supabase_user_id" in query:
            if self.user and self.user["supabase_user_id"] == args[0]:
                return self.user
            return None
        if "WHERE u.id = $1" in query:
            return self.user
        if "FROM auth_sessions" in query:
            return self.user if self.sessions else None
        return None


class _SupabasePool:
    def __init__(self, connection: _SupabaseConnection) -> None:
        self.connection = connection

    def acquire(self) -> _Acquire:
        return _Acquire(self.connection)

    async def fetchrow(self, query: str, *args):
        return await self.connection.fetchrow(query, *args)

    async def execute(self, query: str, *args):
        return await self.connection.execute(query, *args)


class _TestableSupabaseControlPlane(SupabaseControlPlaneService):
    def __init__(self, pool: _SupabasePool, client: httpx.AsyncClient) -> None:
        super().__init__(
            settings=SupabaseAuthSettings(url="https://project.supabase.co", anon_key="test-anon-key"),
            client=client,
        )
        self._test_pool = pool

    async def _database(self):
        return self._test_pool


class SupabaseControlPlaneV2Tests(unittest.IsolatedAsyncioTestCase):
    provider_id = "6d654d03-5211-4d4f-93d0-e510c252d084"

    async def asyncSetUp(self) -> None:
        self.requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if request.url.path == "/auth/v1/signup":
                return httpx.Response(200, json={"user": {"id": self.provider_id}})
            if request.url.path == "/auth/v1/token":
                return httpx.Response(200, json={"user": {"id": self.provider_id}, "access_token": "provider-token"})
            if request.url.path == "/auth/v1/settings":
                return httpx.Response(200, json={})
            return httpx.Response(404)

        self.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://project.supabase.co")
        self.connection = _SupabaseConnection()
        self.service = _TestableSupabaseControlPlane(_SupabasePool(self.connection), self.client)

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_register_and_login_delegate_credentials_to_supabase_and_keep_tupan_session_opaque(self) -> None:
        registered = await self.service.register(
            email="Agent@Example.com",
            password="correct-password",
            full_name="Tupan Agent",
            organization_name="Tupan",
        )
        user, opaque_session = await self.service.login(email="agent@example.com", password="correct-password")

        self.assertEqual(registered["id"], self.provider_id)
        self.assertEqual(user["id"], self.provider_id)
        self.assertNotEqual(opaque_session, "provider-token")
        self.assertIsNone(self.connection.user["password_hash"])
        self.assertEqual(self.connection.user["supabase_user_id"], self.provider_id)
        self.assertEqual([request.url.path for request in self.requests], ["/auth/v1/signup", "/auth/v1/token", "/auth/v1/token"])
        self.assertTrue(all(request.headers["apikey"] == "test-anon-key" for request in self.requests))

    async def test_existing_legacy_hash_is_linked_without_breaking_v1_during_validation(self) -> None:
        legacy = {
            "id": "65af3d41-3aa1-4214-bb2e-cebe46a43fea",
            "email": "legacy@example.com",
            "full_name": "Legacy User",
            "password_hash": ControlPlaneService._hash_password("correct-password"),
            "supabase_user_id": None,
            "organization_id": "f0d72476-7737-4ab8-ae66-2fa113278cdb",
            "role": "admin",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
        self.connection.user = legacy

        user, _ = await self.service.login(email="legacy@example.com", password="correct-password")

        self.assertEqual(user["id"], legacy["id"])
        self.assertEqual(self.connection.user["supabase_user_id"], self.provider_id)
        self.assertIsNotNone(self.connection.user["password_hash"])
        self.assertTrue(ControlPlaneService._verify_password("correct-password", self.connection.user["password_hash"]))
        self.assertEqual([request.url.path for request in self.requests], ["/auth/v1/token"])


class _V2RouteServiceStub:
    user = {
        "id": "6d654d03-5211-4d4f-93d0-e510c252d084",
        "email": "agent@example.com",
        "full_name": "Tupan Agent",
        "organization_id": "f0d72476-7737-4ab8-ae66-2fa113278cdb",
        "role": "admin",
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    async def register(self, **_: object) -> dict:
        return dict(self.user)

    async def register_and_login(self, **_: object) -> tuple[dict, str]:
        return dict(self.user), "v2-opaque-token"

    async def login(self, **_: object) -> tuple[dict, str]:
        return dict(self.user), "v2-opaque-token"

    async def principal(self, token: str | None) -> dict:
        if token != "v2-opaque-token":
            raise AuthenticationError("The session has expired. Sign in again.")
        return dict(self.user)

    async def logout(self, token: str | None) -> None:
        self.logged_out_token = token

    async def readiness(self) -> None:
        return None

    async def close(self) -> None:
        pass


class SupabaseV2HttpContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.service = _V2RouteServiceStub()
        self.app.dependency_overrides[get_supabase_control_plane_service] = lambda: self.service
        self.app.dependency_overrides[get_control_plane_service] = lambda: _V2RouteServiceStub()

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_v2_register_and_session_preserve_the_auth_response_shape_with_a_separate_cookie(self) -> None:
        with TestClient(self.app) as client:
            register = client.post(
                "/api/v2/auth/register",
                json={
                    "email": "agent@example.com",
                    "password": "correct-password",
                    "full_name": "Tupan Agent",
                    "organization_name": "Tupan",
                },
            )
            session = client.get("/api/v2/auth/session")

        self.assertEqual(register.status_code, 201)
        self.assertEqual(session.status_code, 200)
        self.assertEqual(register.json(), session.json())
        cookie = register.headers["set-cookie"].lower()
        self.assertIn("tupan_session_supabase_v2=v2-opaque-token", cookie)
        self.assertIn("httponly", cookie)
        self.assertIn("path=/api/v2", cookie)

    def test_v2_ready_reports_both_the_database_and_supabase_auth_dependencies(self) -> None:
        with TestClient(self.app) as client:
            response = client.get("/api/v2/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready", "checks": {"database": "ok", "supabase_auth": "ok"}})


if __name__ == "__main__":
    unittest.main()
