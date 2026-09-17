from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from train.valuation_data import ValuationDataError, feature_values, parse_records
from train.valuation_uncertainty import assess_data_quality, conformal_interval, fit_conformal, local_residual_correction
from train.valuation_validation import regression_metrics, spatial_holdout, temporal_partitions
from train.transaction_avm import predict_transaction_price
from backend.services.avm_runtime import AvmRuntime


UTC = timezone.utc


def _payload(day: int, *, property_id: str = "p1", transaction_id: str | None = None, price: float = 800_000, verified: bool = True) -> dict:
    event = datetime(2026, 1, day, tzinfo=UTC)
    fields = {
        "usable_area_m2": 70,
        "latitude": -23.56,
        "longitude": -46.67,
        "property_type": "apartment",
        "city": "Sao Paulo",
        "rooms": 2,
        "bathrooms": 2,
        "parking_spaces": 1,
        "h3_r8": "cell-a" if property_id.endswith("1") else "cell-b",
    }
    lineage = {key: {"available_at": event.isoformat(), "source_id": "itbi", "source_version": "2026-01"} for key in fields}
    return {
        "property_id": property_id,
        "transaction_id": transaction_id or f"tx-{property_id}-{day}",
        "valuation_time": event.isoformat(),
        "available_at": (event + timedelta(days=3)).isoformat(),
        "feature_as_of": event.isoformat(),
        "source_id": "itbi",
        "source_version": "2026-01",
        "sale_price_brl": price,
        "transaction_nature": "arm_length",
        "verified": verified,
        "training_allowed": True,
        "features": fields,
        "feature_lineage": lineage,
    }


class ValuationContractTests(unittest.TestCase):
    def test_transaction_requires_explicit_verified_sale_and_does_not_accept_suggestion(self):
        valid, excluded = parse_records([_payload(1), {**_payload(2), "suggested_price": 900_000, "sale_price_brl": None}])
        self.assertEqual(len(valid), 1)
        self.assertTrue(any("positive" in reason for reason in excluded))
        self.assertEqual(feature_values(valid[0])["usable_area_m2"], 70.0)

    def test_future_feature_and_non_arm_length_are_excluded(self):
        future = _payload(1)
        future["feature_lineage"]["rooms"]["available_at"] = (datetime(2026, 2, 1, tzinfo=UTC)).isoformat()
        non_market = {**_payload(2), "transaction_nature": "related_party"}
        records, excluded = parse_records([future, non_market])
        self.assertEqual(records, [])
        self.assertEqual(sum(excluded.values()), 2)

    def test_zero_is_observed_but_unknown_is_not(self):
        quality = assess_data_quality(
            {"usable_area_m2": 70, "property_type": "apartment", "city": "Sao Paulo", "latitude": -23.5, "longitude": -46.6, "parking_spaces": 0},
            {field: {"available_at": datetime(2026, 1, 1, tzinfo=UTC), "source_id": "s", "source_version": "1"} for field in ("usable_area_m2", "property_type", "city", "latitude", "longitude", "parking_spaces")},
            datetime(2026, 1, 2, tzinfo=UTC),
        )
        self.assertNotIn("parking_spaces", quality["missing_fields"])
        self.assertIn("rooms", quality["missing_fields"])

    def test_temporal_partition_keeps_same_property_together(self):
        payloads = []
        for day in range(1, 13):
            payload = _payload(day, property_id=f"p{day % 4}")
            payload["listing_cluster_id"] = f"cluster-{day % 2}"
            payloads.append(payload)
        records, _ = parse_records(payloads)
        partitions = temporal_partitions(records)
        memberships = {}
        for name, rows in partitions.items():
            for row in rows:
                memberships.setdefault(row.property_id, set()).add(name)
        self.assertTrue(all(len(buckets) == 1 for buckets in memberships.values()))

    def test_metrics_and_spatial_holdout(self):
        records, _ = parse_records([_payload(day, property_id=f"p{day}") for day in range(1, 5)])
        self.assertAlmostEqual(regression_metrics([100, 100], [110, 90])["within_10"], 1.0)
        self.assertRaises(ValuationDataError, spatial_holdout, records, {"missing-cell"})

    def test_conformal_interval_and_local_support(self):
        calibration = fit_conformal([10, 11, 12], [9, 10, 11], [11, 12, 13], level=0.8)
        low, high = conformal_interval(10, 12, calibration)
        self.assertLessEqual(low, 10)
        self.assertGreaterEqual(high, 12)
        result = local_residual_correction({"property_id": "subject", "latitude": -23.5, "longitude": -46.6, "area_m2": 70, "property_type": "apartment", "city": "Sao Paulo"}, [], valuation_time=datetime(2026, 1, 1, tzinfo=UTC))
        self.assertEqual(result["lambda"], 0.0)

    def test_promoted_transaction_avm_returns_calibrated_interval(self):
        features = {
            "usable_area_m2": 70,
            "property_type": "apartment",
            "city": "Sao Paulo",
        }
        categories = {name: ["__MISSING__"] for name in (
            "property_type", "subtype", "city", "state", "condition", "h3_r7", "h3_r8", "h3_r9"
        )}
        categories["property_type"].append("apartment")
        categories["city"].append("Sao Paulo")
        metadata = {
            "schema_version": 2,
            "model_type": "xgboost.XGBRegressor",
            "target": "sale_price_brl",
            "feature_columns": [
                "usable_area_m2", "built_area_m2", "lot_area_m2", "latitude", "longitude",
                "property_type", "subtype", "city", "state", "rooms", "suites", "bathrooms",
                "parking_spaces", "floor", "building_floors", "year_built", "renovation_year",
                "condition", "elevator", "condo_fee_brl", "h3_r7", "h3_r8", "h3_r9",
            ],
            "categories": categories,
            "uncertainty": {
                "method": "split_conformal_point_residual",
                "calibration": {"level": 0.8, "sample_count": 10, "nonconformity_quantile": 0.1},
                "out_of_time_coverage": 0.75,
            },
            "promotion_status": "production",
            "model_version": "transaction-avm-v2",
        }

        class FakeRegressor:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def load_model(self, path):
                self.path = path

            def predict(self, frame):
                return [12.0]

        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.json"
            metadata_path = Path(directory) / "model.metadata.json"
            model_path.write_text("model", encoding="utf-8")
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            with patch("train.transaction_avm.XGBRegressor", FakeRegressor):
                result = predict_transaction_price(features, model_path=model_path, metadata_path=metadata_path)
                with patch.dict(os.environ, {
                    "AVM_TRANSACTION_MODEL_PATH": str(model_path),
                    "AVM_TRANSACTION_METADATA_PATH": str(metadata_path),
                }, clear=False):
                    runtime_result = AvmRuntime._predict_sync({
                        "area_m2": 70,
                        "property_type": "apartment",
                        "city": "Sao Paulo",
                        "attributes": {},
                    })

        self.assertEqual(result["interval_level"], 0.8)
        self.assertEqual(result["calibration_sample_count"], 10)
        self.assertEqual(result["out_of_time_coverage"], 0.75)
        self.assertLess(result["lower_bound"], result["estimated_price"])
        self.assertLess(result["estimated_price"], result["upper_bound"])
        self.assertEqual(runtime_result.uncertainty_status, "calibrated")
        self.assertEqual(runtime_result.calibration_sample_count, 10)

    def test_candidate_transaction_artifact_is_not_served(self):
        metadata = {"promotion_status": "candidate"}
        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.json"
            metadata_path = Path(directory) / "model.metadata.json"
            model_path.write_text("model", encoding="utf-8")
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            with patch("train.transaction_avm.XGBRegressor") as regressor:
                with self.assertRaises(RuntimeError):
                    predict_transaction_price({}, model_path=model_path, metadata_path=metadata_path)
                regressor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
