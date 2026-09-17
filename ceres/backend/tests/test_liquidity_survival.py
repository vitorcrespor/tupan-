from __future__ import annotations

import unittest
from datetime import date

from backend.services.liquidity_survival import (
    H3_MODEL_VERSION,
    MODEL_VERSION,
    attach_h3_liquidity,
    score_listing_liquidity,
    summarize_portfolio_liquidity,
    train_liquidity_survival_model,
)


def _record(*, status: str, days: int, city: str = "São Paulo", area: str = "Pinheiros", property_type: str = "apartment") -> dict:
    return {
        "status": status,
        "days_on_market": days,
        "city": city,
        "area": area,
        "property_type": property_type,
    }


class LiquiditySurvivalTests(unittest.TestCase):
    def setUp(self) -> None:
        # Two sales and three active, right-censored listings.  At 10 days,
        # S=0.8; at 20 days, S=0.6.
        self.artifact = train_liquidity_survival_model(
            [
                _record(status="sold", days=10),
                _record(status="sold", days=20),
                _record(status="active", days=30),
                _record(status="active", days=30),
                _record(status="active", days=30),
            ],
            as_of=date(2026, 9, 15),
            min_observations=1,
            min_events=1,
        )

    def test_score_is_conditional_sale_probability_for_the_selected_horizon(self) -> None:
        result = score_listing_liquidity(
            self.artifact,
            _record(status="active", days=10),
            horizon_days=10,
        )

        # Conditional on surviving ten days: 1 - S(20)/S(10) = 25%.
        self.assertEqual(result.status, "available")
        self.assertEqual(result.horizon_days, 10)
        self.assertEqual(result.score, 25.0)
        self.assertEqual(result.model_version, MODEL_VERSION)

    def test_score_changes_with_the_horizon_from_the_existing_selector(self) -> None:
        short = score_listing_liquidity(self.artifact, _record(status="active", days=0), horizon_days=10)
        long = score_listing_liquidity(self.artifact, _record(status="active", days=0), horizon_days=20)

        self.assertEqual(short.score, 20.0)
        self.assertEqual(long.score, 40.0)
        self.assertLess(short.score, long.score)

    def test_active_listing_is_right_censored_and_sold_listing_is_an_event(self) -> None:
        global_curve = next(item for item in self.artifact["strata"] if item["key"] == ["global"])["curve"]

        self.assertEqual(global_curve, [[10.0, 0.8], [20.0, 0.6]])

    def test_missing_selected_horizon_never_falls_back_to_an_arbitrary_default(self) -> None:
        result = score_listing_liquidity(self.artifact, _record(status="active", days=10), horizon_days=None)

        self.assertIsNone(result.score)
        self.assertEqual(result.status, "horizon_not_selected")

    def test_missing_duration_and_non_active_estates_remain_unscored(self) -> None:
        missing_duration = score_listing_liquidity(
            self.artifact,
            {"status": "active", "city": "São Paulo", "area": "Pinheiros", "property_type": "apartment"},
            horizon_days=30,
        )
        sold = score_listing_liquidity(self.artifact, _record(status="sold", days=10), horizon_days=30)

        self.assertEqual(missing_duration.status, "missing_listing_duration")
        self.assertEqual(sold.status, "not_active")

    def test_portfolio_summary_uses_only_its_own_sales_and_listings(self) -> None:
        rows = [
            _record(status="sold", days=10, city="Ignored", property_type="ignored"),
            _record(status="sold", days=20, city="Ignored", property_type="ignored"),
            _record(status="sold", days=30, city="Ignored", property_type="ignored"),
            _record(status="active", days=5, city="Ignored", property_type="ignored"),
            _record(status="active", days=15, city="Ignored", property_type="ignored"),
        ]

        result = summarize_portfolio_liquidity(rows, horizon_days=20, min_observations=5, min_events=3)

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["active_estate_count"], 2)
        self.assertEqual(result["eligible_estate_count"], 2)
        self.assertEqual(result["sale_event_count"], 3)
        self.assertIsNotNone(result["score"])

    def test_h3_liquidity_uses_only_sales_and_censoring_in_the_exact_cell(self) -> None:
        import h3

        latitude, longitude = -23.56, -46.68
        cell = (h3.latlng_to_cell(latitude, longitude, 9)
                if hasattr(h3, "latlng_to_cell") else h3.geo_to_h3(latitude, longitude, 9))
        aggregate = {"h3_index": str(cell), "metrics": {"inventory": 3, "units": {}}}
        rows = [
            {**_record(status="sold", days=10), "latitude": latitude, "longitude": longitude},
            {**_record(status="sold", days=20), "latitude": latitude, "longitude": longitude},
            {**_record(status="active", days=30), "latitude": latitude, "longitude": longitude},
            {**_record(status="active", days=30), "latitude": latitude, "longitude": longitude},
            {**_record(status="active", days=30), "latitude": latitude, "longitude": longitude},
            # A sale in another H3 cell cannot affect this curve.
            {**_record(status="sold", days=1), "latitude": -22.90, "longitude": -47.06},
        ]

        published = attach_h3_liquidity(
            [aggregate], rows, h3_resolution=9, as_of=date(2026, 9, 15),
            horizons_days=[10, 20], min_observations=1, min_events=1,
        )[0]["metrics"]["liquidity_by_horizon"]

        self.assertEqual(published["10"]["score"], 20.0)
        self.assertEqual(published["20"]["score"], 40.0)
        self.assertEqual(published["20"]["observation_count"], 5)
        self.assertEqual(published["20"]["sale_event_count"], 2)
        self.assertEqual(published["20"]["model_version"], H3_MODEL_VERSION)

    def test_h3_liquidity_suppresses_small_cell_support(self) -> None:
        import h3

        latitude, longitude = -23.56, -46.68
        cell = (h3.latlng_to_cell(latitude, longitude, 9)
                if hasattr(h3, "latlng_to_cell") else h3.geo_to_h3(latitude, longitude, 9))
        result = attach_h3_liquidity(
            [{"h3_index": str(cell), "metrics": {}}],
            [{**_record(status="sold", days=10), "latitude": latitude, "longitude": longitude}],
            h3_resolution=9, as_of=date(2026, 9, 15), horizons_days=[30],
        )[0]["metrics"]["liquidity_by_horizon"]["30"]

        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["score"])
        self.assertIsNone(result["observation_count"])
        self.assertIsNone(result["sale_event_count"])


if __name__ == "__main__":
    unittest.main()
