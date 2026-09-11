from __future__ import annotations

from datetime import datetime, timezone
import unittest

from fastapi.testclient import TestClient

from backend.api.dependencies import get_control_plane_service
from backend.api.main import create_app
from backend.services.control_plane import AuthenticationError


class _LegacyControlPlaneStub:
    """Observable legacy auth behavior used to protect the HTTP contract."""

    _user = {
        "id": "user-1",
        "email": "agent@example.com",
        "full_name": "Tupan Agent",
        "organization_id": "organization-1",
        "role": "admin",
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    async def register(self, **_: object) -> dict[str, object]:
        return dict(self._user)

    async def login(self, *, email: str, password: str) -> tuple[dict[str, object], str]:
        if email != self._user["email"] or password != "correct-password":
            raise AuthenticationError("Invalid email or password.")
        return dict(self._user), "opaque-session-token"

    async def principal(self, token: str | None) -> dict[str, object]:
        if token != "opaque-session-token":
            raise AuthenticationError("The session has expired. Sign in again.")
        return dict(self._user)

    async def logout(self, token: str | None) -> None:
        self.logged_out_token = token

    async def close(self) -> None:
        pass


class LegacyAuthHttpContractTests(unittest.TestCase):
    """Retained characterization tests for the existing desktop auth contract.

    These tests intentionally exercise the public FastAPI seam. They establish
    the response and opaque-cookie behavior that the Supabase-backed adapter
    must preserve when it replaces the legacy password implementation.
    """

    def setUp(self) -> None:
        self.service = _LegacyControlPlaneStub()
        self.app = create_app()
        self.app.dependency_overrides[get_control_plane_service] = lambda: self.service

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_register_creates_an_opaque_http_only_session_without_exposing_a_token(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "agent@example.com",
                    "password": "correct-password",
                    "full_name": "Tupan Agent",
                    "organization_name": "Tupan",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"]["id"], "user-1")
        self.assertNotIn("token", response.json())
        set_cookie = response.headers["set-cookie"].lower()
        self.assertIn("tupan_session=opaque-session-token", set_cookie)
        self.assertIn("httponly", set_cookie)
        self.assertIn("path=/api/v1", set_cookie)

    def test_login_cookie_authenticates_the_existing_session_endpoint(self) -> None:
        with TestClient(self.app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": "agent@example.com", "password": "correct-password"},
            )
            session = client.get("/api/v1/auth/session")

        self.assertEqual(login.status_code, 200)
        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["user"], login.json()["user"])

    def test_invalid_login_has_the_existing_authentication_error_shape(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "agent@example.com", "password": "wrong-password"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "authentication_required")
        self.assertEqual(response.json()["message"], "Invalid email or password.")
        self.assertIn("request_id", response.json())


if __name__ == "__main__":
    unittest.main()
