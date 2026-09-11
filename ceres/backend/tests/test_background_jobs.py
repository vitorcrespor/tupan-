from __future__ import annotations

import unittest
from datetime import date

from pydantic import ValidationError

from backend.api.schemas.estate import JobCreateRequest
from backend.repositories.job_queue import ClaimedJob
from backend.services.heatmap_precompute import _aggregate_sources
from backend.worker import BackgroundWorker


class FakeQueue:
    def __init__(self) -> None:
        self.failures = []

    async def retry_or_fail(self, context, job, *, error, retryable) -> None:
        self.failures.append((context, job, error, retryable))


class BackgroundJobTests(unittest.IsolatedAsyncioTestCase):
    def test_heatmap_aggregation_groups_by_h3_and_has_base_metrics(self) -> None:
        rows = _aggregate_sources(
            [
                {"latitude": -23.56, "longitude": -46.68, "asking_price": 1_000_000, "price_per_m2": 10_000, "days_on_market": 30, "city": "São Paulo", "area": "Pinheiros"},
                {"latitude": -23.5601, "longitude": -46.6801, "asking_price": 1_200_000, "price_per_m2": 12_000, "days_on_market": 50, "city": "São Paulo", "area": "Pinheiros"},
            ],
            resolution=9,
            period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 1),
            input_version="estate-base-v1",
        )

        self.assertEqual(sum(row["metrics"]["inventory"] for row in rows), 2)
        self.assertTrue(all(row["boundary"]["type"] == "Polygon" for row in rows))
        self.assertTrue(all(row["metrics"]["average_price_m2"] is not None for row in rows))

    def test_background_job_submission_requires_an_idempotency_key(self) -> None:
        with self.assertRaises(ValidationError):
            JobCreateRequest(job_type="heatmap_precompute")

    async def test_unknown_job_type_fails_once_without_retry(self) -> None:
        queue = FakeQueue()
        worker = BackgroundWorker(queue)  # type: ignore[arg-type]
        job = ClaimedJob(
            job_id="job-a", organization_id="organization-a", user_id="user-a", job_type="not-supported",
            payload={}, input_version=None, attempt_count=1, max_attempts=3,
        )

        await worker._execute(job)

        self.assertEqual(len(queue.failures), 1)
        context, _, error, retryable = queue.failures[0]
        self.assertEqual(context.organization_id, "organization-a")
        self.assertEqual(error["code"], "unsupported_job_type")
        self.assertFalse(retryable)
