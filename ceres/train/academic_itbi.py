"""Read academic ITBI transactions and geocode a bounded, auditable sample.

No structural property facts are inferred from sale prices. Address coordinates
are current geocoding results; they are not certified historical snapshots.
"""
from __future__ import annotations

import hashlib
import json
import os
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ID = "academic_itbi_address_v1"


def normalize(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().upper().split())


def read_transactions(path: Path) -> tuple[list[dict], dict]:
    frame = pd.read_excel(path, dtype={"cadastro": str, "numero_imovel": str})
    required = {"cadastro", "data_emissao", "natureza_transacao", "porcentagem",
                "endereco_imovel", "numero_imovel", "bairro", "valor_instrumento"}
    if missing := required - set(frame.columns):
        raise ValueError(f"Missing source columns: {sorted(missing)}")
    excluded = Counter()
    transactions, seen = [], set()
    for index, raw in frame.iterrows():
        row = raw.to_dict()
        nature = normalize(row["natureza_transacao"])
        if "VENDA E COMPRA" not in nature or any(x in nature for x in ("ARREMAT", "LEIL", "CESSAO", "PERMUTA", "DOACAO")):
            excluded["non_standard_sale"] += 1
            continue
        if row["porcentagem"] != 100:
            excluded["partial_transfer"] += 1
            continue
        price = pd.to_numeric(row["valor_instrumento"], errors="coerce")
        if pd.isna(price) or not 100_000 <= price <= 3_000_000:
            excluded["outside_declared_price_segment"] += 1
            continue
        street, number, district = (normalize(row[k]) for k in ("endereco_imovel", "numero_imovel", "bairro"))
        if not street or not number.isdigit() or int(number) <= 0 or not district:
            excluded["incomplete_address"] += 1
            continue
        number = str(int(number))
        date = pd.to_datetime(row["data_emissao"], errors="coerce")
        if pd.isna(date) or not normalize(row["cadastro"]):
            excluded["invalid_identity_or_date"] += 1
            continue
        date = date.date().isoformat()
        key = "|".join((street, number, district))
        identity = "|".join((normalize(row["cadastro"]), date, str(float(price))))
        if identity in seen:
            excluded["duplicate_transaction"] += 1
            continue
        seen.add(identity)
        transactions.append({
            "transaction_id": hashlib.sha256(identity.encode()).hexdigest(),
            "property_id": hashlib.sha256(normalize(row["cadastro"]).encode()).hexdigest(),
            "address_key": key, "street": street, "number": number, "district": district,
            "complement": normalize(row.get("complemento")), "date": date, "price_brl": float(price),
            "source_row": int(index) + 2,
        })
    return transactions, {"source_rows": len(frame), "eligible_rows": len(transactions),
                          "exclusions": dict(excluded), "price_segment_brl": [100000, 3000000]}


def _geocode(row: dict, city: str, api_key: str) -> dict:
    params = urllib.parse.urlencode({"address": f"{row['street']}, {row['number']}, {city}, SP, Brasil",
                                    "components": "country:BR", "key": api_key})
    result = {"status": "unavailable", "retrieved_at": datetime.now(timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen("https://maps.googleapis.com/maps/api/geocode/json?" + params, timeout=15) as response:
            payload = json.load(response)
        result["provider_status"] = payload.get("status")
        for item in payload.get("results", []):
            components = {kind: part for part in item.get("address_components", []) for kind in part["types"]}
            geometry = item.get("geometry", {})
            matched_city = components.get("administrative_area_level_2", {}).get("long_name", "")
            matched_number = components.get("street_number", {}).get("long_name", "")
            if (normalize(matched_city) != normalize(city) or matched_number != row["number"]
                    or item.get("partial_match") or geometry.get("location_type") not in {"ROOFTOP", "RANGE_INTERPOLATED"}):
                continue
            result.update(status="ok", latitude=geometry["location"]["lat"], longitude=geometry["location"]["lng"],
                          city=matched_city, state=components.get("administrative_area_level_1", {}).get("short_name"),
                          postal_code=components.get("postal_code", {}).get("long_name"),
                          precision=geometry["location_type"], formatted_address=item.get("formatted_address"),
                          provider="google_geocoding")
            break
    except Exception as exc:
        # Never include a request URL or exception message containing the key.
        result["error_type"] = type(exc).__name__
    return result


def enrich(transactions: list[dict], *, city: str, cache_path: Path, max_requests: int = 128) -> tuple[list[dict], dict]:
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    counts = Counter(row["address_key"] for row in transactions)
    rows = {row["address_key"]: row for row in transactions}
    # Repeated addresses increase sample support per paid request. This sampling
    # bias is reported and must not be advertised as whole-city coverage.
    keys = sorted(rows, key=lambda key: (-counts[key], key))[:max_requests]
    pending = [key for key in keys if f"{city}|{key}" not in cache]
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
    if pending and not api_key:
        raise ValueError("Backend Google geocoding key is missing")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as executor:
        for key, result in zip(pending, executor.map(lambda key: _geocode(rows[key], city, api_key), pending)):
            cache[f"{city}|{key}"] = result
            cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    enriched = []
    for row in transactions:
        geo = cache.get(f"{city}|{row['address_key']}", {})
        if row["address_key"] in keys and geo.get("status") == "ok":
            enriched.append({**row, "geocode": geo})
    return enriched, {"requests": len(pending), "address_budget": max_requests,
                      "accepted_addresses": len({row['address_key'] for row in enriched}),
                      "geocoded_transactions": len(enriched), "city": city,
                      "sampling": "most_frequent_complete_addresses; partial_city_coverage"}


def transaction_cells(rows: list[dict], *, version: str, source_rows: int, resolution: int = 9) -> list[dict]:
    import h3
    from statistics import fmean, median
    from backend.services.heatmap_precompute import _boundary_geojson
    groups = defaultdict(list)
    for row in rows:
        geo = row["geocode"]
        groups[h3.latlng_to_cell(geo["latitude"], geo["longitude"], resolution)].append(row)
    cells = []
    for cell, records in groups.items():
        lat, lng = h3.cell_to_latlng(cell)
        prices = [row["price_brl"] for row in records]
        cells.append({"h3_index": cell, "h3_resolution": resolution,
                      "city": records[0]["geocode"]["city"], "area": Counter(r['district'] for r in records).most_common(1)[0][0],
                      "period_start": min(r["date"] for r in records), "period_end": max(r["date"] for r in records),
                      "boundary": _boundary_geojson(h3, cell), "center": {"type": "Point", "coordinates": [lng, lat]},
                      "input_version": version, "metrics": {
                          "dataset_kind": "transactions", "source_name": SOURCE_ID, "partial_coverage": True,
                          "source_row_count": source_rows, "geocoded_row_count": len(rows),
                          "transaction_count": len(records), "average_transaction_price": fmean(prices),
                          "median_transaction_price": median(prices),
                          "units": {"transaction_count": "count", "average_transaction_price": "BRL", "median_transaction_price": "BRL"},
                      }})
    return cells
