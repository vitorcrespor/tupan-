from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.dependencies import ApiSettings
from backend.api.main import create_app
from backend.security.rate_limit import SlidingWindowRateLimiter


class ProductionRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_sensitive_rate_limiter_bounds_requests(self) -> None:
        limiter = SlidingWindowRateLimiter(window_seconds=60)
        self.assertEqual(await limiter.allow(scope="auth", identifier="client-a", limit=2), (True, 0))
        self.assertEqual(await limiter.allow(scope="auth", identifier="client-a", limit=2), (True, 0))
        allowed, retry_after = await limiter.allow(scope="auth", identifier="client-a", limit=2)
        self.assertFalse(allowed)
        self.assertGreaterEqual(retry_after, 1)

    async def test_liveness_is_independent_but_readiness_requires_database(self) -> None:
        with TestClient(create_app()) as client:
            live = client.get("/health")
            ready = client.get("/ready")
        self.assertEqual(live.status_code, 200)
        self.assertEqual(live.json(), {"status": "ok"})
        self.assertIn("x-request-id", live.headers)
        self.assertEqual(live.headers["x-tupan-api-version"], "1.0.0")
        self.assertEqual(ready.status_code, 503)



class ProductionConfigurationTests(unittest.TestCase):
    def test_production_rejects_insecure_or_implicit_configuration(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TUPAN_ENV": "production",
                "API_CORS_ORIGINS": "https://desktop.example",
                "AUTH_COOKIE_SECURE": "false",
                "API_ALLOW_MOCK_DATA": "false",
                "API_ALLOW_LEGACY_GLOBAL_DATA": "false",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(ValueError, "AUTH_COOKIE_SECURE"):
                ApiSettings.from_environment()

    def test_production_accepts_explicit_secure_configuration(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TUPAN_ENV": "production",
                "API_CORS_ORIGINS": "https://desktop.example",
                "AUTH_COOKIE_SECURE": "true",
                "API_ALLOW_MOCK_DATA": "false",
                "API_ALLOW_LEGACY_GLOBAL_DATA": "false",
            },
            clear=False,
        ):
            self.assertEqual(ApiSettings.from_environment().cors_origins, ["https://desktop.example"])

if __name__ == "__main__":
    unittest.main()
