from __future__ import annotations

import asyncio
import copy
import unittest
from datetime import date

from backend.services.heatmap_precompute import _aggregate_sources
from backend.services.market_heat import INPUT_VERSION, calculate_market_heat
from backend.services.published_metrics import published_cell_indicators
from backend.services.market_snapshot import market_snapshot_observations
from backend.services.platform_intelligence import PlatformIntelligenceService


LISTINGS = [
    {"latitude": -23.5600, "longitude": -46.6800, "asking_price": 1_000_000, "price_per_m2": 10_000, "days_on_market": 30, "city": "São Paulo", "area": "Pinheiros"},
    {"latitude": -23.5602, "longitude": -46.6802, "asking_price": 1_100_000, "price_per_m2": 11_000, "days_on_market": 35, "city": "São Paulo", "area": "Pinheiros"},
]
SALES = [
    *[{"latitude": -23.5600, "longitude": -46.6800, "last_sale_date": day, "last_sale_price": price}
      for day, price in (("2026-08-20", 130_000), ("2026-08-28", 132_000), ("2026-09-05", 135_000))],
    *[{"latitude": -23.5600, "longitude": -46.6800, "last_sale_date": day, "last_sale_price": price}
      for day, price in (("2025-08-20", 100_000), ("2025-08-28", 101_000), ("2025-09-05", 102_000))],
]


def aggregates(resolution: int):
    return _aggregate_sources(
        LISTINGS, resolution=resolution, period_start=date(2026, 9, 14), period_end=date(2026, 9, 14),
        input_version=INPUT_VERSION,
    )


class MarketHeatTests(unittest.TestCase):
    def test_market_heat_remains_the_normalized_0_to_100_cell_indicator(self):
        indicators = published_cell_indicators({
            "market_heat": 0.62,
            "units": {"market_heat": "score_0_1"},
        })

        self.assertEqual(indicators["market_heat"], 62.0)

    def test_cell_indicators_do_not_publish_the_removed_demand_alias(self):
        indicators = published_cell_indicators({
            "market_heat": 75,
            "units": {"market_heat": "score_0_100"},
        })

        self.assertNotIn("demand_score", indicators)
        self.assertEqual(indicators["market_heat"], 75.0)

    def test_cell_indicator_selects_only_the_requested_liquidity_horizon(self):
        metrics = {
            "units": {"liquidity": "score_0_100"},
            "liquidity_by_horizon": {
                "30": {"score": 20.0, "status": "available", "horizon_days": 30},
                "90": {"score": 55.0, "status": "available", "horizon_days": 90},
            },
        }

        self.assertIsNone(published_cell_indicators(metrics)["liquidity"])
        self.assertEqual(
            published_cell_indicators(metrics, liquidity_horizon_days=90)["liquidity"],
            55.0,
        )

    def test_observed_heat_is_resolution_specific_and_does_not_mutate_base_aggregates(self):
        base = aggregates(9)
        original = copy.deepcopy(base)
        published = calculate_market_heat(base, SALES, h3_resolution=9, as_of=date(2026, 9, 14))

        self.assertEqual(base, original)
        self.assertEqual({row["h3_resolution"] for row in published}, {9})
        # Resolution 9 separates the two nearby listings into different
        # cells. Evidence belongs only to the first one, so the other must
        # remain unavailable rather than borrowing or fabricating support.
        available = [row for row in published if row["metrics"]["market_heat"] is not None]
        self.assertTrue(available)
        self.assertTrue(all(0 <= row["metrics"]["market_heat"] <= 100 for row in available))
        self.assertTrue(all(row["metrics"]["market_heat_status"] == "available" for row in available))
        self.assertTrue(all(row["metrics"]["units"]["market_heat"] == "score_0_100" for row in published))
        self.assertTrue(all(row["metrics"]["units"]["sales_velocity"] == "sales/day" for row in published))

    def test_insufficient_sale_support_remains_unavailable_not_zero(self):
        published = calculate_market_heat(aggregates(8), SALES[:2], h3_resolution=8, as_of=date(2026, 9, 14))

        self.assertEqual({row["h3_resolution"] for row in published}, {8})
        self.assertTrue(all(row["metrics"]["market_heat"] is None for row in published))
        self.assertTrue(all(row["metrics"]["market_heat_status"] == "insufficient_observed_sale_support" for row in published))

    def test_one_h3_cell_is_not_duplicated_when_source_labels_differ(self):
        rows = _aggregate_sources(
            [
                {**LISTINGS[0], "area": "Pinheiros"},
                {**LISTINGS[0], "area": "Jardins"},
            ],
            resolution=9, period_start=date(2026, 9, 14), period_end=date(2026, 9, 14),
            input_version=INPUT_VERSION,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["metrics"]["inventory"], 2)
        self.assertEqual(rows[0]["city"], "São Paulo")
        self.assertIsNone(rows[0]["area"])

    def test_snapshot_projection_keeps_units_and_omits_unavailable_heat(self):
        row = {
            "h3_index": "8928308280fffff", "city": "São Paulo", "area": "Pinheiros",
            "metrics": {
                "inventory": 2, "average_price_m2": 10_000, "average_asking_price": 1_000_000,
                "average_dom_days": 30, "market_heat": None, "price_growth": None,
                "sales_velocity": 0.05, "heat_recent_sales": 3,
            },
        }
        observations = market_snapshot_observations(
            [row], observed_on=date(2026, 9, 14), source_reference="heatmap:test",
        )
        city_rows = [item for item in observations if item["city"] == "São Paulo" and item["area"] is None]
        values = {item["metric"]: item for item in city_rows}

        self.assertEqual(values["active_listings"]["value"], 2)
        self.assertEqual(values["price_m2"]["unit"], "BRL/m²")
        self.assertEqual(values["sales_velocity"]["unit"], "sales/day")
        self.assertNotIn("market_heat", values)

    def test_snapshot_projection_preserves_observed_price_decline(self):
        row = {
            "h3_index": "8928308280fffff",
            "city": "São Paulo",
            "area": "Pinheiros",
            "metrics": {
                "inventory": 2,
                "price_growth": -8.5,
                "heat_recent_sales": 4,
            },
        }

        observations = market_snapshot_observations(
            [row], observed_on=date(2026, 9, 14), source_reference="heatmap:test",
        )
        city_rows = [item for item in observations if item["city"] == "São Paulo" and item["area"] is None]
        price_growth = next(item for item in city_rows if item["metric"] == "price_growth")

        self.assertEqual(price_growth["value"], -8.5)
        self.assertEqual(price_growth["unit"], "percent")


class _RecordingRepository:
    def __init__(self):
        self.replacements = []
        self.observation_publications = []

    async def start(self):
        return None

    async def close(self):
        return None

    async def heatmap_sources(self):
        return LISTINGS

    async def heatmap_sale_sources(self):
        return SALES

    async def h3_liquidity_training_sources(self):
        return []

    async def replace_platform_heatmap(self, rows, *, allow_empty, h3_resolution, input_version, market_observations):
        self.replacements.append((rows, allow_empty, h3_resolution, input_version))
        self.observation_publications.append(market_observations)
        return len(rows)


class PlatformHeatPublicationTests(unittest.TestCase):
    def test_multiple_resolutions_are_published_independently_from_one_global_read(self):
        repository = _RecordingRepository()
        results = asyncio.run(
            PlatformIntelligenceService(repository).refresh_heatmaps(h3_resolutions=[8, 9, 8])
        )

        self.assertEqual([result.h3_resolution for result in results], [8, 9])
        self.assertEqual([resolution for _, _, resolution, _ in repository.replacements], [8, 9])
        self.assertTrue(all(version == INPUT_VERSION for *_, version in repository.replacements))
        self.assertTrue(all(result.heat_cell_count > 0 for result in results))

    def test_market_history_publishes_canonical_city_scope_and_every_h3_scope(self):
        repository = _RecordingRepository()
        asyncio.run(PlatformIntelligenceService(repository).refresh_heatmaps(h3_resolutions=[8, 9]))

        resolution_8, resolution_9 = repository.observation_publications
        self.assertTrue(resolution_8)
        self.assertTrue(resolution_9)
        self.assertTrue(all(row["h3_index"] is not None for row in resolution_8))
        self.assertTrue(any(row["h3_index"] is None and row["city"] is None for row in resolution_9))
        self.assertTrue(any(row["h3_index"] is None and row["city"] is not None for row in resolution_9))
        self.assertTrue(all(row["source_reference"].endswith("h3-8") for row in resolution_8))
        self.assertTrue(all(row["source_reference"].endswith("h3-9") for row in resolution_9))


if __name__ == "__main__":
    unittest.main()
