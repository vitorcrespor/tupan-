from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from backend.services.errors import ConflictError, DomainValidationError, NotFoundError, ServiceError, UnavailableError


class AuthenticationError(ServiceError):
    status_code = 401
    code = "authentication_required"


class AuthorizationError(ServiceError):
    status_code = 403
    code = "authorization_denied"


class ControlPlaneService:
    """Tenant-scoped identity and workspace persistence.

    This deliberately owns credentials, sessions, memberships, user workspace
    records, and authorization. It is a control-plane adapter only: real-estate
    analytics remain in the existing domain services.
    """

    _scrypt_n = 2**14
    _scrypt_r = 8
    _scrypt_p = 1

    def __init__(self) -> None:
        self._pool: Any | None = None
        self._pool_lock: Any | None = None

    async def _database(self):
        if self._pool is not None:
            return self._pool
        database_url = (os.getenv("DATABASE_API_URL") or os.getenv("DATABASE_URL", "")).strip()
        if not database_url:
            raise UnavailableError(
                "Cloud control-plane storage is not configured.",
                details={"reason": "database_url_missing"},
            )
        try:
            import asyncpg
            import asyncio
        except ImportError as exc:
            raise UnavailableError(
                "Cloud control-plane dependencies are unavailable.",
                details={"reason": "asyncpg_missing"},
            ) from exc
        if self._pool_lock is None:
            self._pool_lock = asyncio.Lock()
        async with self._pool_lock:
            if self._pool is None:
                try:
                    self._pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
                except Exception as exc:
                    raise UnavailableError(
                        "Cloud control-plane storage could not be reached.",
                        details={"reason": "database_unavailable"},
                    ) from exc
        return self._pool

    async def readiness(self) -> None:
        """Verify the authoritative PostgreSQL connection without exposing details."""
        pool = await self._database()
        try:
            await pool.fetchval("SELECT 1")
        except Exception as exc:
            raise UnavailableError(
                "Cloud control-plane storage could not be reached.",
                details={"reason": "database_unavailable"},
            ) from exc
    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @staticmethod
    def _require_password(password: str) -> None:
        if len(password) < 10:
            raise DomainValidationError("Passwords must contain at least 10 characters.")

    @classmethod
    def _hash_password(cls, password: str) -> str:
        cls._require_password(password)
        salt = os.urandom(16)
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=cls._scrypt_n, r=cls._scrypt_r, p=cls._scrypt_p
        )
        encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii")
        return f"scrypt${cls._scrypt_n}${cls._scrypt_r}${cls._scrypt_p}${encode(salt)}${encode(digest)}"

    @classmethod
    def _verify_password(cls, password: str, encoded: str | None) -> bool:
        try:
            scheme, n, r, p, salt, digest = (encoded or "").split("$")
            if scheme != "scrypt":
                return False
            expected = base64.urlsafe_b64decode(digest.encode("ascii"))
            calculated = hashlib.scrypt(
                password.encode("utf-8"),
                salt=base64.urlsafe_b64decode(salt.encode("ascii")),
                n=int(n), r=int(r), p=int(p),
            )
            return hmac.compare_digest(calculated, expected)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _session_digest(token: str) -> bytes:
        return hashlib.sha256(token.encode("utf-8")).digest()

    @staticmethod
    def _record(record: Any) -> dict[str, Any]:
        """Adapt database records at the service/API boundary.

        asyncpg returns PostgreSQL UUID columns as ``uuid.UUID`` objects, while
        the API contract exposes opaque identifiers as strings. Keep timestamps
        and other domain values intact; only normalize the transport-incompatible
        UUID values here.
        """
        if record is None:
            return {}
        return {
            key: str(value) if isinstance(value, UUID) else value
            for key, value in dict(record).items()
        }

    async def register(self, *, email: str, password: str, full_name: str | None, organization_name: str | None) -> dict[str, Any]:
        pool = await self._database()
        normalized_email = email.strip().casefold()
        if not normalized_email or "@" not in normalized_email:
            raise DomainValidationError("A valid email address is required.")
        password_hash = self._hash_password(password)
        organization_id = str(uuid4())
        user_id = str(uuid4())
        async with pool.acquire() as connection:
            async with connection.transaction():
                duplicate = await connection.fetchval("SELECT 1 FROM cloud_users WHERE email = $1", normalized_email)
                if duplicate:
                    raise ConflictError("An account already exists for this email address.")
                await connection.execute(
                    """INSERT INTO organizations (id, name) VALUES ($1, $2)""",
                    organization_id,
                    (organization_name or normalized_email.split("@", 1)[0]).strip()[:160],
                )
                await connection.execute(
                    """INSERT INTO cloud_users (id, email, full_name, password_hash)
                       VALUES ($1, $2, $3, $4)""",
                    user_id, normalized_email, (full_name or "").strip() or None, password_hash,
                )
                await connection.execute(
                    """INSERT INTO organization_memberships (organization_id, user_id, role)
                       VALUES ($1, $2, 'admin')""",
                    organization_id, user_id,
                )
                user = await connection.fetchrow(
                    """SELECT u.id, u.email, u.full_name, m.organization_id, m.role, u.created_at
                       FROM cloud_users u
                       JOIN organization_memberships m ON m.user_id = u.id
                       WHERE u.id = $1 AND m.organization_id = $2""",
                    user_id, organization_id,
                )
        return self._record(user)

    async def login(self, *, email: str, password: str) -> tuple[dict[str, Any], str]:
        pool = await self._database()
        normalized_email = email.strip().casefold()
        async with pool.acquire() as connection:
            user = await connection.fetchrow(
                """SELECT u.id, u.email, u.full_name, u.password_hash, m.organization_id, m.role, u.created_at
                   FROM cloud_users u
                   JOIN organization_memberships m ON m.user_id = u.id
                   WHERE u.email = $1
                   ORDER BY CASE WHEN m.role = 'admin' THEN 0 ELSE 1 END, m.created_at
                   LIMIT 1""",
                normalized_email,
            )
            if not user or not self._verify_password(password, user["password_hash"]):
                raise AuthenticationError("Invalid email or password.")
            token = secrets.token_urlsafe(48)
            await connection.execute(
                """INSERT INTO auth_sessions (id, user_id, organization_id, token_hash, expires_at)
                   VALUES ($1, $2, $3, $4, $5)""",
                str(uuid4()), user["id"], user["organization_id"], self._session_digest(token),
                datetime.now(timezone.utc) + timedelta(days=7),
            )
        user_data = self._record(user)
        user_data.pop("password_hash", None)
        return user_data, token

    async def logout(self, token: str | None) -> None:
        if not token:
            return
        pool = await self._database()
        await pool.execute("DELETE FROM auth_sessions WHERE token_hash = $1", self._session_digest(token))

    async def principal(self, token: str | None) -> dict[str, Any]:
        if not token:
            raise AuthenticationError("Sign in is required to use this resource.")
        pool = await self._database()
        row = await pool.fetchrow(
            """SELECT u.id, u.email, u.full_name, s.organization_id, m.role, u.created_at
               FROM auth_sessions s
               JOIN cloud_users u ON u.id = s.user_id
               JOIN organization_memberships m
                 ON m.user_id = s.user_id AND m.organization_id = s.organization_id
               WHERE s.token_hash = $1 AND s.expires_at > now()""",
            self._session_digest(token),
        )
        if not row:
            raise AuthenticationError("The session has expired. Sign in again.")
        return self._record(row)

    @staticmethod
    def require_admin(principal: dict[str, Any]) -> None:
        if principal.get("role") != "admin":
            raise AuthorizationError("Administrator access is required for this action.")

    async def list_members(self, principal: dict[str, Any]) -> list[dict[str, Any]]:
        pool = await self._database()
        records = await pool.fetch(
            """SELECT u.id, u.email, u.full_name, m.role, u.created_at
               FROM organization_memberships m
               JOIN cloud_users u ON u.id = m.user_id
               WHERE m.organization_id = $1
               ORDER BY u.created_at""",
            principal["organization_id"],
        )
        return [self._record(row) for row in records]

    async def change_member_role(self, principal: dict[str, Any], member_id: str, role: str) -> dict[str, Any]:
        self.require_admin(principal)
        if role not in {"admin", "user"}:
            raise DomainValidationError("Member role must be 'admin' or 'user'.")
        if member_id == principal["id"]:
            raise DomainValidationError("Your own administrator role cannot be changed here.")
        pool = await self._database()
        row = await pool.fetchrow(
            """UPDATE organization_memberships m SET role = $3
               FROM cloud_users u
               WHERE m.organization_id = $1 AND m.user_id = $2 AND u.id = m.user_id
               RETURNING u.id, u.email, u.full_name, m.role, u.created_at""",
            principal["organization_id"], member_id, role,
        )
        if not row:
            raise NotFoundError("Team member not found.")
        return self._record(row)

    async def remove_member(self, principal: dict[str, Any], member_id: str) -> None:
        self.require_admin(principal)
        if member_id == principal["id"]:
            raise DomainValidationError("Your own membership cannot be removed here.")
        pool = await self._database()
        outcome = await pool.execute(
            "DELETE FROM organization_memberships WHERE organization_id = $1 AND user_id = $2",
            principal["organization_id"], member_id,
        )
        if outcome.endswith("0"):
            raise NotFoundError("Team member not found.")

    async def list_saved_searches(self, principal: dict[str, Any]) -> list[dict[str, Any]]:
        pool = await self._database()
        rows = await pool.fetch(
            """SELECT id, name, filters, created_at FROM saved_searches
               WHERE organization_id = $1 AND user_id = $2 ORDER BY created_at DESC""",
            principal["organization_id"], principal["id"],
        )
        return [self._record(row) for row in rows]

    async def create_saved_search(self, principal: dict[str, Any], *, name: str, filters: dict[str, Any]) -> dict[str, Any]:
        if not name.strip():
            raise DomainValidationError("A saved search name is required.")
        pool = await self._database()
        row = await pool.fetchrow(
            """INSERT INTO saved_searches (id, organization_id, user_id, name, filters)
               VALUES ($1, $2, $3, $4, $5::jsonb)
               RETURNING id, name, filters, created_at""",
            str(uuid4()), principal["organization_id"], principal["id"], name.strip()[:160], __import__("json").dumps(filters),
        )
        return self._record(row)

    async def delete_saved_search(self, principal: dict[str, Any], saved_search_id: str) -> None:
        pool = await self._database()
        outcome = await pool.execute(
            """DELETE FROM saved_searches
               WHERE id = $1 AND organization_id = $2 AND user_id = $3""",
            saved_search_id, principal["organization_id"], principal["id"],
        )
        if outcome.endswith("0"):
            raise NotFoundError("Saved search not found.")

    async def list_notes(self, principal: dict[str, Any], property_id: str) -> list[dict[str, Any]]:
        pool = await self._database()
        rows = await pool.fetch(
            """SELECT id, property_id, note, created_at, user_id
               FROM property_notes
               WHERE organization_id = $1 AND property_id = $2 ORDER BY created_at DESC""",
            principal["organization_id"], property_id,
        )
        return [self._record(row) for row in rows]

    async def create_note(self, principal: dict[str, Any], *, property_id: str, note: str) -> dict[str, Any]:
        if not note.strip():
            raise DomainValidationError("A note cannot be empty.")
        pool = await self._database()
        row = await pool.fetchrow(
            """INSERT INTO property_notes (id, organization_id, property_id, user_id, note)
               VALUES ($1, $2, $3, $4, $5)
               RETURNING id, property_id, note, user_id, created_at""",
            str(uuid4()), principal["organization_id"], property_id, principal["id"], note.strip(),
        )
        return self._record(row)

    async def list_boundaries(self, principal: dict[str, Any]) -> list[dict[str, Any]]:
        pool = await self._database()
        rows = await pool.fetch(
            """SELECT id, name, geojson, created_at FROM district_boundaries
               WHERE organization_id = $1 ORDER BY name""",
            principal["organization_id"],
        )
        return [self._record(row) for row in rows]