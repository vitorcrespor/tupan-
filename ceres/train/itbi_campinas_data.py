"""Pure mapping of the curated Campinas ITBI workbook into AVM observations.

This module intentionally has no XGBoost or network dependency. It is shared
by the offline trainer and the controlled database importer so both enforce
the same source filters, temporal semantics and feature lineage.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd


UTC = timezone.utc
DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "data" / "ITBI_Campinas_2021_2026_LIMPO (1).xlsx"
DEFAULT_GEOCODE_CACHE = Path(__file__).resolve().parents[2] / "data" / "enrichment" / "itbi_campinas_google_geocodes.json"
RESIDENTIAL_TYPES = {
    "Residencial Vertical": ("apartment", "vertical"),
    "Residencial Horizontal": ("house", "horizontal"),
}


def _positive(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _lineage(
    available_at: datetime,
    source_version: str,
    *,
    source_id: str = "itbi_campinas",
) -> dict[str, str]:
    return {
        "available_at": available_at.isoformat(),
        "source_id": source_id,
        "source_version": source_version,
    }


def _text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().upper().split())


def load_geocode_cache(path: Path) -> dict[str, dict[str, Any]]:
    """Read a local cache only; no enrichment request is ever made here."""
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def build_observations(
    frame: pd.DataFrame,
    *,
    geocodes: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Map only curated, market-valid rows to the explicit AVM contract."""
    counts = {"source_rows": len(frame)}
    observations: list[dict[str, Any]] = []
    geocodes = geocodes or {}
    source_version = "ITBI_Campinas_2021_2026_LIMPO+GoogleGeocoding:v2" if geocodes else "ITBI_Campinas_2021_2026_LIMPO:v1"
    geocoded_rows = 0
    missing_geocodes = 0

    for row_number, row in frame.iterrows():
        kind = RESIDENTIAL_TYPES.get(str(row.get("tipo_imovel")))
        if kind is None:
            continue
        valid_transaction = row.get("transacao_onerosa_valida")
        if pd.isna(valid_transaction) or not bool(valid_transaction):
            continue
        price = _positive(row.get("vl_instrumento_reais"))
        built_area = _positive(row.get("area_total_const"))
        if price is None or built_area is None:
            continue
        outlier = row.get("outlier_preco_m2", False)
        if not pd.isna(outlier) and bool(outlier):
            continue
        try:
            year = int(row.get("ANO"))
        except (TypeError, ValueError):
            continue
        if not 2000 <= year <= 2100:
            continue

        event_time = datetime(year, 12, 31, tzinfo=UTC)
        available_at = event_time + timedelta(days=1)
        property_type, subtype = kind
        features: dict[str, Any] = {
            "built_area_m2": built_area,
            "property_type": property_type,
            "subtype": subtype,
            "city": "Campinas",
            "state": "SP",
        }
        neighborhood = _text(row.get("bairro_final")) or _text(row.get("bairro"))
        geocode = geocodes.get(neighborhood) or {}
        if geocode.get("status") == "ok":
            features["latitude"] = geocode.get("latitude")
            features["longitude"] = geocode.get("longitude")
            geocoded_rows += 1
        else:
            missing_geocodes += 1
        lot_area = _positive(row.get("area_terreno"))
        if lot_area is not None:
            features["lot_area_m2"] = lot_area
        lineage = {name: _lineage(event_time, source_version) for name in features}
        if geocode.get("status") == "ok":
            lineage["latitude"] = _lineage(
                event_time,
                "google-geocoding:v1",
                source_id="google_geocoding",
            )
            lineage["longitude"] = _lineage(
                event_time,
                "google-geocoding:v1",
                source_id="google_geocoding",
            )
        observations.append(
            {
                "property_id": f"itbi-campinas-{year}-{row_number}",
                "transaction_id": f"itbi-campinas-{year}-{row_number}",
                "valuation_time": event_time.isoformat(),
                "available_at": available_at.isoformat(),
                "feature_as_of": event_time.isoformat(),
                "source_id": "itbi_campinas",
                "source_version": source_version,
                "sale_price_brl": price,
                "transaction_nature": "arm_length",
                "verified": True,
                "training_allowed": True,
                "features": features,
                "feature_lineage": lineage,
            }
        )

    counts["mapped_rows"] = len(observations)
    counts["geocoded_rows"] = geocoded_rows
    counts["missing_geocodes"] = missing_geocodes
    return observations, counts
