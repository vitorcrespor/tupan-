from __future__ import annotations

import unittest
import asyncio
from datetime import date
from uuid import uuid4

from pydantic import ValidationError

from backend.api.schemas.estate import JobCreateRequest
from backend.repositories.job_queue import ClaimedJob
from backend.services.heatmap_precompute import _aggregate_sources
from backend.worker import BackgroundWorker, WorkerSettings, _portfolio_snapshot_handler


class FakeQueue:
    def __init__(self) -> None:
        self.failures = []
        self.heartbeats = []
        self.successes = []

    async def retry_or_fail(self, context, job, *, error, retryable) -> None:
        self.failures.append((context, job, error, retryable))

    async def heartbeat(self, context, job) -> bool:
        self.heartbeats.append((context, job))
        return True

    async def mark_succeeded(self, context, job, result) -> str:
        self.successes.append((context, job, result))
        return "SUCCEEDED"


class SnapshotQueue(FakeQueue):
    def __init__(self) -> None:
        super().__init__()
        self.progress = []
        self.captures = []

    async def set_progress(self, context, job, progress) -> bool:
        self.progress.append((context, job, progress))
        return True

    async def capture_portfolio_snapshot(self, context, *, portfolio_id):
        self.captures.append((context, portfolio_id))
        return {"portfolio_id": portfolio_id, "observed_on": "2026-09-16", "active_estate_count": 2}


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
            payload={}, input_version=None, attempt_count=1, max_attempts=3, execution_token="attempt-a",
        )

        await worker._execute(job)

        self.assertEqual(len(queue.failures), 1)
        context, _, error, retryable = queue.failures[0]
        self.assertEqual(context.organization_id, "organization-a")
        self.assertEqual(error["code"], "unsupported_job_type")
        self.assertFalse(retryable)

    async def test_portfolio_snapshot_handler_uses_database_observation_date(self) -> None:
        queue = SnapshotQueue()
        portfolio_id = str(uuid4())
        job = ClaimedJob(
            job_id="job-snapshot", organization_id="organization-a", user_id=None, job_type="portfolio_snapshot",
            payload={"portfolio_id": portfolio_id, "observed_on": "2026-09-15"},
            input_version="portfolio-snapshot-v1", attempt_count=1, max_attempts=3,
            execution_token="attempt-snapshot",
        )
        context = type("Context", (), {"organization_id": "organization-a", "user_id": "worker", "role": "background-worker"})()

        result = await _portfolio_snapshot_handler(queue, context, job)

        self.assertEqual(queue.captures[0][0], context)
        self.assertEqual(queue.captures[0][1], portfolio_id)
        self.assertEqual([item[2] for item in queue.progress], [25, 85])
        self.assertEqual(result.result_reference, f"portfolio_metric_snapshots:{portfolio_id}:2026-09-16")

    async def test_registered_handler_refreshes_its_lease(self) -> None:
        queue = FakeQueue()
        worker = BackgroundWorker(
            queue,  # type: ignore[arg-type]
            settings=WorkerSettings(heartbeat_seconds=0.01, max_execution_seconds=1),
        )

        async def handler(_queue, _context, _job):
            await asyncio.sleep(0.035)
            return type("Result", (), {"result": {}, "result_reference": None})()

        worker.register_handler("slow", handler)
        job = ClaimedJob(
            job_id="job-slow", organization_id="organization-a", user_id=None, job_type="slow",
            payload={}, input_version=None, attempt_count=1, max_attempts=3, execution_token="attempt-slow",
        )

        await worker._execute(job)

        self.assertGreaterEqual(len(queue.heartbeats), 2)
        self.assertEqual(len(queue.successes), 1)
