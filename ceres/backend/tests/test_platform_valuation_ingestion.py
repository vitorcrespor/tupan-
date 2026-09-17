from __future__ import annotations

import asyncio
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from backend.services.platform_intelligence import PlatformIntelligenceService
from train.itbi_campinas_data import build_observations


UTC = timezone.utc


def _observation() -> dict:
    observed_at = datetime(2024, 12, 31, tzinfo=UTC).isoformat()
    available_at = datetime(2025, 1, 1, tzinfo=UTC).isoformat()
    features = {
        "built_area_m2": 82.0,
        "property_type": "apartment",
        "subtype": "vertical",
        "city": "Campinas",
        "state": "SP",
        "latitude": -22.90,
        "longitude": -47.06,
    }
    lineage = {key: {"available_at": observed_at, "source_id": "itbi_campinas", "source_version": "v2"} for key in features}
    return {
        "property_id": "itbi-campinas-2024-1",
        "transaction_id": "itbi-campinas-2024-1",
        "valuation_time": observed_at,
        "available_at": available_at,
        "feature_as_of": observed_at,
        "source_id": "itbi_campinas",
        "source_version": "v2",
        "sale_price_brl": 420_000,
        "transaction_nature": "arm_length",
        "verified": True,
        "training_allowed": True,
        "features": features,
        "feature_lineage": lineage,
    }


class FakeRepository:
    def __init__(self) -> None:
        self.started = False
        self.closed = False
        self.rows: list[dict] = []

    async def start(self) -> None:
        self.started = True

    async def close(self) -> None:
        self.closed = True

    async def upsert_valuation_observations(self, rows: list[dict], *, connection=None) -> int:
        self.rows = rows
        return len(rows)

    @asynccontextmanager
    async def transaction(self):
        yield object()


class PlatformValuationIngestionTests(unittest.TestCase):
    def test_shared_mapper_preserves_only_verified_source_features(self):
        frame = pd.DataFrame([{
            "tipo_imovel": "Residencial Vertical",
            "transacao_onerosa_valida": True,
            "vl_instrumento_reais": 420_000,
            "area_total_const": 82,
            "area_terreno": 0,
            "outlier_preco_m2": False,
            "ANO": 2024,
            "bairro_final": "CENTRO",
        }])
        observations, report = build_observations(frame, geocodes={
            "CENTRO": {"status": "ok", "latitude": -22.9, "longitude": -47.06},
        })
        self.assertEqual(report["mapped_rows"], 1)
        self.assertEqual(observations[0]["sale_price_brl"], 420_000)
        self.assertEqual(observations[0]["features"]["built_area_m2"], 82.0)
        self.assertNotIn("rooms", observations[0]["features"])
        self.assertEqual(observations[0]["transaction_nature"], "arm_length")

    def test_preview_never_starts_storage_or_writes(self):
        repository = FakeRepository()
        service = PlatformIntelligenceService(repository)
        with patch(
            "backend.services.platform_intelligence._preview_itbi_campinas_observations",
            return_value={"mapped_rows": 1, "preview_only": True},
        ) as prepare:
            report = asyncio.run(service.preview_itbi_campinas_observations(
                source=Path("source.xlsx"), geocode_cache=Path("cache.json"),
            ))
        self.assertEqual(report["mapped_rows"], 1)
        self.assertFalse(repository.started)
        self.assertEqual(repository.rows, [])
        prepare.assert_called_once()

    def test_import_uses_only_prepared_observations_and_does_not_promote(self):
        repository = FakeRepository()
        service = PlatformIntelligenceService(repository)
        with patch(
            "backend.services.platform_intelligence._preview_itbi_campinas_observations",
            return_value={"mapped_rows": 1, "preview_only": True},
        ), patch(
            "backend.services.platform_intelligence._iter_itbi_campinas_observation_batches",
            return_value=iter([[_observation()]]),
        ):
            result = asyncio.run(service.import_itbi_campinas_observations())
        self.assertTrue(repository.started)
        self.assertTrue(repository.closed)
        self.assertEqual(repository.rows, [_observation()])
        self.assertEqual(result["imported_observation_count"], 1)
        self.assertEqual(result["network_enrichment"], "not_called")
        self.assertEqual(result["promotion_status"], "unchanged")


if __name__ == "__main__":
    unittest.main()
