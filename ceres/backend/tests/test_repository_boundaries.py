"""Regression tests for values crossing the PostgreSQL/application boundary."""

from __future__ import annotations

import json
import unittest
from decimal import Decimal

from backend.repositories.job_queue import JobQueueRepository
from backend.repositories.tenant_data import _record
from backend.services.serialization import json_safe


class RepositoryBoundaryTests(unittest.TestCase):
    def test_tenant_record_decodes_declared_json_objects(self) -> None:
        record = _record(
            {
                "market_metrics": '{"market_heat": 72}',
                "result": '{"count": 2}',
                "error": '{"code": "failed"}',
            }
        )

        self.assertEqual(record["market_metrics"], {"market_heat": 72})
        self.assertEqual(record["result"], {"count": 2})
        self.assertEqual(record["error"], {"code": "failed"})

    def test_claimed_job_accepts_asyncpg_json_text(self) -> None:
        job = JobQueueRepository._claimed_job(
            {
                "job_id": "job-a",
                "organization_id": "organization-a",
                "user_id": None,
                "job_type": "portfolio_snapshot",
                "payload": '{"portfolio_id": "portfolio-a"}',
                "input_version": "portfolio-snapshot-v1",
                "attempt_count": 1,
                "max_attempts": 3,
                "created_at": None,
                "execution_token": "5969bf01-48f9-49b9-9055-0f6afbee00bb",
            }
        )

        self.assertEqual(job.payload, {"portfolio_id": "portfolio-a"})

    def test_decimal_results_remain_json_numbers(self) -> None:
        payload = json_safe({"portfolio_value": Decimal("1200000.50")})

        self.assertEqual(json.loads(json.dumps(payload)), {"portfolio_value": 1200000.5})


if __name__ == "__main__":
    unittest.main()
