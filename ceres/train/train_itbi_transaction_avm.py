"""Build the first transaction-AVM candidate from the curated ITBI workbook.

The workbook contains annual market transactions, not property coordinates.
This command therefore keeps the first candidate honest: it uses observed
transaction prices and structural facts that are present in the source and
does not invent coordinates or Google-neighbor features. A later geocoded
source can add those features through the versioned valuation contract.

Usage (from ``ceres``):
    python -m train.train_itbi_transaction_avm --n-estimators 600
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from train.itbi_campinas_data import (
    DEFAULT_GEOCODE_CACHE,
    DEFAULT_SOURCE,
    RESIDENTIAL_TYPES,
    _text,
    build_observations,
    load_geocode_cache,
)
from train.transaction_avm import train_transaction_avm
from train.valuation_data import parse_records

DEFAULT_ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "avm_transaction_v2.json"


def geocode_neighborhoods(
    neighborhoods: set[str],
    *,
    api_key: str,
    cache_path: Path,
    request_delay_seconds: float = 0.05,
    timeout_seconds: float = 15,
    max_requests: int | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    """Geocode neighborhood centroids once, with a durable cache.

    ITBI has no street address or property coordinates.  This deliberately
    enriches only the normalized neighborhood centroid; it never presents the
    result as the exact location of an individual transaction.
    """
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is required for --enrich-google")
    cache = load_geocode_cache(cache_path)
    cache_hits = sum(name in cache for name in neighborhoods)
    pending = sorted(name for name in neighborhoods if name and name not in cache)
    if max_requests is not None:
        pending = pending[:max(0, max_requests)]
    requested = 0
    succeeded = 0
    failed = 0
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    for name in pending:
        params = urllib.parse.urlencode({
            "address": f"{name}, Campinas, SP, Brazil",
            "key": api_key,
        })
        url = f"https://maps.googleapis.com/maps/api/geocode/json?{params}"
        entry: dict[str, Any] = {"status": "error", "query": name}
        requested += 1
        try:
            with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            results = payload.get("results") or []
            location = (results[0].get("geometry") or {}).get("location") if results else None
            if payload.get("status") == "OK" and location:
                entry = {
                    "status": "ok",
                    "query": name,
                    "latitude": float(location["lat"]),
                    "longitude": float(location["lng"]),
                    "formatted_address": results[0].get("formatted_address"),
                    "provider": "google_geocoding",
                }
                succeeded += 1
            else:
                entry["provider_status"] = payload.get("status")
                failed += 1
        except Exception as exc:  # keep one transient failure from losing the batch
            entry["error_type"] = type(exc).__name__
            failed += 1
        cache[name] = entry
        cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
        if request_delay_seconds > 0:
            time.sleep(request_delay_seconds)
    return cache, {
        "requested": requested,
        "succeeded": succeeded,
        "failed": failed,
        "cache_hits": cache_hits,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the first ITBI transaction AVM candidate.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--n-estimators", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--metadata-path", type=Path, default=None)
    parser.add_argument("--enrich-google", action="store_true", help="Geocode normalized Campinas neighborhoods before training")
    parser.add_argument("--geocode-cache", type=Path, default=DEFAULT_GEOCODE_CACHE)
    parser.add_argument("--max-geocodes", type=int, default=None, help="Optional cap for first-run/API quota control")
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    frame = pd.read_excel(args.source, sheet_name="Dados Limpos")
    geocodes: dict[str, dict[str, Any]] = {}
    enrichment_stats = {"requested": 0, "succeeded": 0, "failed": 0, "cache_hits": 0}
    if args.enrich_google:
        candidate_names = {
            _text(value)
            for value in frame.loc[
                frame["tipo_imovel"].isin(RESIDENTIAL_TYPES)
                & frame["transacao_onerosa_valida"].fillna(False).astype(bool),
                "bairro_final",
            ].tolist()
        }
        geocodes, enrichment_stats = geocode_neighborhoods(
            candidate_names,
            api_key=os.getenv("GOOGLE_API_KEY", ""),
            cache_path=args.geocode_cache,
            max_requests=args.max_geocodes,
        )
    payloads, counts = build_observations(frame, geocodes=geocodes)
    records, exclusions = parse_records(payloads, target_kind="transaction")
    if len(records) < 12:
        raise RuntimeError(f"Not enough eligible observations for a candidate: {len(records)}")

    result = train_transaction_avm(
        records,
        seed=args.seed,
        n_estimators=args.n_estimators,
        model_path=args.model_path,
        metadata_path=args.metadata_path,
    )
    report = {
        "source": str(args.source),
        "source_rows": counts["source_rows"],
        "mapped_rows": counts["mapped_rows"],
        "eligible_rows": len(records),
        "excluded_observations": exclusions,
        "candidate_only": True,
        "promotion_status": "candidate",
        "transaction_nature_mapping": {
            "value": "arm_length",
            "basis": "transacao_onerosa_valida=true is documented as a valid onerous purchase/sale",
            "limitation": "the workbook has no related-party field; review this assumption before promotion",
        },
        "google_neighbors": {
            "status": "not_applied",
            "reason": "ITBI workbook has no property coordinates or addresses; Google enrichment is neighborhood centroid only",
        },
        "google_geocoding": enrichment_stats,
        "enrichment_cache": str(args.geocode_cache) if args.enrich_google else None,
        "artifact": result,
    }
    report_path = args.model_path.with_suffix(".training-report.json")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "model_path": result["model_path"],
        "metadata_path": result["metadata_path"],
        "training_report": str(report_path),
        "source_rows": counts["source_rows"],
        "mapped_rows": counts["mapped_rows"],
        "eligible_rows": len(records),
        "promotion_status": "candidate",
        "google_neighbors": "not_applied_missing_coordinates",
        "google_geocoding": enrichment_stats,
        "geocoded_rows": counts.get("geocoded_rows", 0),
        "missing_geocodes": counts.get("missing_geocodes", 0),
        "out_of_time_metrics": result["out_of_time_metrics"],
        "uncertainty": result["uncertainty"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
