from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import httpx

from backend.services.control_plane import AuthenticationError, ControlPlaneService
from backend.services.errors import ConflictError, DomainValidationError, UnavailableError


@dataclass(frozen=True)
class SupabaseAuthSettings:
    """Backend-only configuration for Supabase Auth's GoTrue HTTP API."""

    url: str
    anon_key: str
    timeout_seconds: float = 10.0

    @classmethod
    def from_environment(cls) -> "SupabaseAuthSettings":
        url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
        if not url or not anon_key:
            raise UnavailableError(
                "Supabase Auth is not configured.",
                details={"reason": "supabase_auth_not_configured"},
            )
        try:
            timeout_seconds = float(os.getenv("SUPABASE_AUTH_TIMEOUT_SECONDS", "10"))
        except ValueError:
            timeout_seconds = 10.0
        return cls(url=url, anon_key=anon_key, timeout_seconds=max(1.0, timeout_seconds))


class SupabaseControlPlaneService(ControlPlaneService):
    """Supabase Auth v2 adapter with Tupan's existing tenant/session contract.

    Supabase owns credentials and password verification. During the v2 validation window, Tupan retains legacy hashes only so v1 remains usable; the final cutover removes them. Tupan retains the
    authorization profile, organization memberships, and opaque server-side
    session because those records are needed by the existing API and RLS
    repositories. The inherited ``principal`` and workspace operations are
    intentionally reused: their observable response shape stays unchanged.
    """

    def __init__(
        self,
        *,
        settings: SupabaseAuthSettings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._client = client
        self._owns_client = client is None

    def _auth_settings(self) -> SupabaseAuthSettings:
        if self._settings is None:
            self._settings = SupabaseAuthSettings.from_environment()
        return self._settings

    async def _http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            settings = self._auth_settings()
            self._client = httpx.AsyncClient(base_url=settings.url, timeout=settings.timeout_seconds)
        return self._client

    async def close(self) -> None:
        await super().close()
        if self._client is not None and self._owns_client:
            await self._client.aclose()
        self._client = None

    async def readiness(self) -> None:
        """A v2 instance is ready only when both its DB and Auth are reachable."""
        await super().readiness()
        response = await self._request("GET", "/auth/v1/settings")
        if response.status_code >= 400:
            raise UnavailableError(
                "Supabase Auth could not be reached.",
                details={"reason": "supabase_auth_unavailable"},
            )

    async def _request(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> httpx.Response:
        settings = self._auth_settings()
        client = await self._http_client()
        try:
            return await client.request(
                method,
                path,
                headers={"apikey": settings.anon_key},
                json=json,
            )
        except httpx.RequestError as exc:
            raise UnavailableError(
                "Supabase Auth could not be reached.",
                details={"reason": "supabase_auth_unavailable"},
            ) from exc

    @staticmethod
    def _provider_user_id(response: httpx.Response) -> str | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        user = payload.get("user") if isinstance(payload, dict) else None
        candidate = user.get("id") if isinstance(user, dict) else None
        try:
            return str(UUID(str(candidate)))
        except (TypeError, ValueError):
            return None

    async def _sign_up(self, *, email: str, password: str, full_name: str | None) -> str:
        response = await self._request(
            "POST",
            "/auth/v1/signup",
            json={
                "email": email,
                "password": password,
                "data": {"full_name": full_name} if full_name else {},
            },
        )
        if response.status_code >= 500:
            raise UnavailableError(
                "Supabase Auth is temporarily unavailable.",
                details={"reason": "supabase_auth_server_error"},
            )
        provider_id = self._provider_user_id(response)
        if response.status_code >= 400 or provider_id is None:
            raise ConflictError("An account already exists for this email address.")
        return provider_id

    async def _password_grant(self, *, email: str, password: str) -> str | None:
        response = await self._request(
            "POST",
            "/auth/v1/token?grant_type=password",
            json={"email": email, "password": password},
        )
        if response.status_code >= 500:
            raise UnavailableError(
                "Supabase Auth is temporarily unavailable.",
                details={"reason": "supabase_auth_server_error"},
            )
        if response.status_code >= 400:
            return None
        return self._provider_user_id(response)

    async def _user_by_email(self, email: str) -> dict[str, Any] | None:
        pool = await self._database()
        row = await pool.fetchrow(
            """SELECT id, email, full_name, password_hash, supabase_user_id
               FROM cloud_users WHERE email = $1""",
            email,
        )
        return self._record(row) if row else None

    async def _user_by_provider_id(self, provider_id: str) -> dict[str, Any] | None:
        pool = await self._database()
        row = await pool.fetchrow(
            """SELECT u.id, u.email, u.full_name, m.organization_id, m.role, u.created_at
               FROM cloud_users u
               JOIN organization_memberships m ON m.user_id = u.id
               WHERE u.supabase_user_id = $1
               ORDER BY CASE WHEN m.role = 'admin' THEN 0 ELSE 1 END, m.created_at
               LIMIT 1""",
            provider_id,
        )
        return self._record(row) if row else None

    async def _link_legacy_user(self, *, user_id: str, provider_id: str) -> None:
        pool = await self._database()
        outcome = await pool.execute(
            """UPDATE cloud_users
               SET supabase_user_id = $2
               WHERE id = $1 AND supabase_user_id IS NULL""",
            user_id,
            provider_id,
        )
        if outcome.endswith("0"):
            raise AuthenticationError("Invalid email or password.")

    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None,
        organization_name: str | None,
    ) -> dict[str, Any]:
        self._require_password(password)
        normalized_email = email.strip().casefold()
        if not normalized_email or "@" not in normalized_email:
            raise DomainValidationError("A valid email address is required.")

        existing = await self._user_by_email(normalized_email)
        if existing:
            raise ConflictError("An account already exists for this email address.")

        provider_id = await self._sign_up(email=normalized_email, password=password, full_name=full_name)
        verified_provider_id = await self._password_grant(email=normalized_email, password=password)
        if verified_provider_id != provider_id:
            raise DomainValidationError(
                "The Supabase account must be able to sign in before its Tupan profile is created."
            )
        organization_id = str(uuid4())
        pool = await self._database()
        try:
            async with pool.acquire() as connection:
                async with connection.transaction():
                    duplicate = await connection.fetchval("SELECT 1 FROM cloud_users WHERE email = $1", normalized_email)
                    if duplicate:
                        raise ConflictError("An account already exists for this email address.")
                    await connection.execute(
                        "INSERT INTO organizations (id, name) VALUES ($1, $2)",
                        organization_id,
                        (organization_name or normalized_email.split("@", 1)[0]).strip()[:160],
                    )
                    await connection.execute(
                        """INSERT INTO cloud_users (id, email, full_name, password_hash, supabase_user_id)
                           VALUES ($1, $2, $3, NULL, $4)""",
                        provider_id,
                        normalized_email,
                        (full_name or "").strip() or None,
                        provider_id,
                    )
                    await connection.execute(
                        """INSERT INTO organization_memberships (organization_id, user_id, role)
                           VALUES ($1, $2, 'admin')""",
                        organization_id,
                        provider_id,
                    )
                    user = await connection.fetchrow(
                        """SELECT u.id, u.email, u.full_name, m.organization_id, m.role, u.created_at
                           FROM cloud_users u
                           JOIN organization_memberships m ON m.user_id = u.id
                           WHERE u.id = $1 AND m.organization_id = $2""",
                        provider_id,
                        organization_id,
                    )
        except ConflictError:
            raise
        except Exception as exc:
            raise UnavailableError(
                "Tupan profile storage could not be updated after Supabase registration.",
                details={"reason": "supabase_profile_write_failed"},
            ) from exc
        return self._record(user)

    async def register_and_login(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None,
        organization_name: str | None,
    ) -> tuple[dict[str, Any], str]:
        user = await self.register(
            email=email,
            password=password,
            full_name=full_name,
            organization_name=organization_name,
        )
        return await self._create_application_session(user)

    async def login(self, *, email: str, password: str) -> tuple[dict[str, Any], str]:
        normalized_email = email.strip().casefold()
        provider_id = await self._password_grant(email=normalized_email, password=password)
        if provider_id:
            user = await self._user_by_provider_id(provider_id)
            if user:
                return await self._create_application_session(user)

            # A Supabase account without a Tupan profile must not gain tenant
            # access merely because its email exists in the identity provider.
            legacy_user = await self._user_by_email(normalized_email)
            if legacy_user and self._verify_password(password, legacy_user.get("password_hash")):
                await self._link_legacy_user(user_id=legacy_user["id"], provider_id=provider_id)
                user = await self._user_by_provider_id(provider_id)
                if user:
                    return await self._create_application_session(user)
            raise AuthenticationError("Invalid email or password.")

        # One-time migration for a legacy locally-hashed account. This is an
        # active data-migration path, not a fallback authentication provider:
        # after a successful link, the final cutover can remove the legacy hash safely.
        legacy_user = await self._user_by_email(normalized_email)
        if not legacy_user or not self._verify_password(password, legacy_user.get("password_hash")):
            raise AuthenticationError("Invalid email or password.")
        provider_id = await self._sign_up(
            email=normalized_email,
            password=password,
            full_name=legacy_user.get("full_name"),
        )
        await self._link_legacy_user(user_id=legacy_user["id"], provider_id=provider_id)
        user = await self._user_by_provider_id(provider_id)
        if not user:
            raise UnavailableError(
                "Tupan profile storage could not be linked to Supabase Auth.",
                details={"reason": "supabase_profile_link_missing"},
            )
        return await self._create_application_session(user)

    async def _create_application_session(self, user: dict[str, Any]) -> tuple[dict[str, Any], str]:
        pool = await self._database()
        token = __import__("secrets").token_urlsafe(48)
        from datetime import datetime, timedelta, timezone

        await pool.execute(
            """INSERT INTO auth_sessions (id, user_id, organization_id, token_hash, expires_at)
               VALUES ($1, $2, $3, $4, $5)""",
            str(uuid4()),
            user["id"],
            user["organization_id"],
            self._session_digest(token),
            datetime.now(timezone.utc) + timedelta(days=7),
        )
        return user, token
