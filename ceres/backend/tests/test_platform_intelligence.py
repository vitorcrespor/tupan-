from __future__ import annotations

import asyncio
import unittest

from backend.services.platform_intelligence import PlatformIntelligenceService, _as_avm_training_record


class _EmptyObservationRepository:
    async def start(self):
        return None

    async def close(self):
        return None

    async def valuation_observations(self, *, target_kind: str):
        return []


class PlatformIntelligenceTests(unittest.TestCase):
    def test_global_avm_training_uses_observed_sale_price_not_existing_estimate(self):
        record = _as_avm_training_record(
            {
                "property_type": "apartment",
                "city": "Sao Paulo",
                "area": "Pinheiros",
                "rooms": 2,
                "bathrooms": 2,
                "parking_spaces": 1,
                "area_m2": 70,
                "age_years": 8,
                "days_on_market": 32,
                "exclusive": True,
                "attributes": {"four_metric": {"luxury": 0.3, "leisure": 0.2, "location_": 0.8, "leverage": 0.4}},
                "last_sale_price": 825_000,
                "estimated_price": 999_999,
            }
        )

        self.assertEqual(record.predictions.suggested_price, 825_000)
        self.assertEqual(record.location.city, "Sao Paulo")
        self.assertEqual(record.real_estate_metrics.square_metrage, 70)

    def test_transaction_candidate_is_explicitly_not_ready_without_observations(self):
        result = asyncio.run(
            PlatformIntelligenceService(_EmptyObservationRepository()).train_transaction_avm()
        )
        self.assertEqual(result["promotion_status"], "not_ready")
        self.assertEqual(result["reason"], "no_eligible_transaction_observations")
        self.assertTrue(result["candidate_only"])


if __name__ == "__main__":
    unittest.main()
