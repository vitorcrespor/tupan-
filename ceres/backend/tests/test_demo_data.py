from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from backend.seed_demo_portfolio import demo_estates
from backend.services.analysis_orchestrator import AnalysisOrchestrator
from train.academic_itbi import read_transactions, transaction_cells


def sample_row(index=0):
    return {"transaction_id": str(index), "property_id": str(index), "address_key": f"street-{index}",
            "street": "RUA EXEMPLO", "number": str(index + 1), "district": "CENTRO",
            "price_brl": 500000, "date": "2025-06-01", "source_row": index + 2,
            "geocode": {"latitude": -23.09, "longitude": -47.21, "city": "Indaiatuba", "state": "SP", "precision": "ROOFTOP"}}


class DemoDataTests(unittest.TestCase):
    def test_ingestion_excludes_partial_transfers_auctions_and_duplicate_transactions(self):
        base = {"cadastro": "one", "data_emissao": "2025-01-01", "natureza_transacao": "VENDA E COMPRA",
                "porcentagem": 100, "endereco_imovel": "RUA TESTE", "numero_imovel": "00012",
                "bairro": "CENTRO", "valor_instrumento": 500000}
        frame = pd.DataFrame([base, base, {**base, "porcentagem": 50},
                              {**base, "natureza_transacao": "VENDA E COMPRA COM ARREMATAÇÃO"},
                              {**base, "numero_imovel": None}])
        with patch("train.academic_itbi.pd.read_excel", return_value=frame):
            rows, report = read_transactions(Path("unused.xlsx"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["number"], "12")
        self.assertEqual(report["exclusions"]["duplicate_transaction"], 1)
        self.assertEqual(sum(report["exclusions"].values()), 4)

    def test_demo_facts_are_explicit_and_never_claim_a_real_sale_or_avm_estimate(self):
        estates = demo_estates([sample_row(i) for i in range(15)], "portfolio")
        self.assertEqual(len(estates), 12)
        for estate in estates:
            self.assertTrue(estate["attributes"]["is_demo"])
            self.assertFalse(estate["attributes"]["training_allowed"])
            self.assertIsNone(estate["last_sale_price"])
            self.assertIsNone(estate["estimated_price"])
            self.assertEqual(estate["price_per_m2"], round(estate["asking_price"] / estate["area_m2"], 2))

    def test_map_uses_real_transaction_units_and_does_not_publish_addresses(self):
        rows = [sample_row(), {**sample_row(1), "price_brl": 700000}]
        cells = transaction_cells(rows, version="test", source_rows=100)
        self.assertEqual(len(cells), 1)
        metrics = cells[0]["metrics"]
        self.assertEqual(metrics["transaction_count"], 2)
        self.assertEqual(metrics["average_transaction_price"], 600000)
        self.assertNotIn("inventory", metrics)
        self.assertNotIn("average_asking_price", metrics)
        self.assertNotIn("street", str(cells))
        self.assertTrue(metrics["partial_coverage"])
        cell = AnalysisOrchestrator._heatmap_cell({**cells[0], "scope": "platform", "calculated_at": "2026-09-13T12:00:00Z"})
        self.assertIsNone(cell.indicators["market_heat"])
        self.assertEqual(cell.metrics["units"]["average_transaction_price"], "BRL")


if __name__ == "__main__":
    unittest.main()
