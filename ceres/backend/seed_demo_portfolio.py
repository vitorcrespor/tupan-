"""Operator-only demo seed plus publication of real academic ITBI map evidence.

Uses DATABASE_API_URL from the backend environment. The target tenant is
resolved by existing membership, never accepted as a command-line org id.
Synthetic portfolio facts never enter the public map or AVM training input.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from dotenv import load_dotenv

from backend.api.schemas.estate import EstateCreateRequest
from backend.repositories.tenant_data import TenantContext, TenantDataRepository
from backend.services.control_plane import ControlPlaneService
from train.academic_itbi import ROOT, SOURCE_ID, enrich, read_transactions, transaction_cells

DEMO_SOURCE = "ceres_demo_academic_v1"
DEMO_NAME = "Demonstração Ceres · Indaiatuba"


def demo_estates(rows: list[dict], portfolio_id: str, limit: int = 12) -> list[dict]:
    selected, seen = [], set()
    for row in sorted(rows, key=lambda item: (item["date"], item["transaction_id"]), reverse=True):
        if row["address_key"] in seen:
            continue
        seen.add(row["address_key"])
        selected.append(row)
        if len(selected) == limit:
            break
    results = []
    for index, row in enumerate(selected):
        geo = row["geocode"]
        area = (62, 85, 110, 140, 185, 220)[index % 6]
        asking = round(row["price_brl"] * (1 + (index % 5 - 2) * 0.025), 2)
        values = EstateCreateRequest(
            portfolio_id=portfolio_id, external_id=f"demo-{row['transaction_id']}", source_name=DEMO_SOURCE,
            title=f"Demo {index + 1:02d} · {row['street'].title()}, {row['number']}",
            summary="Imóvel de demonstração. Endereço e transação de referência vêm da planilha acadêmica; área, quartos, anúncio e DOM são simulados.",
            status="active", property_type="apartment" if index % 3 else "house", asking_price=asking,
            area_m2=area, price_per_m2=round(asking / area, 2), rooms=2 + index % 3,
            bathrooms=1 + index % 3, parking_spaces=1 + index % 2, days_on_market=18 + index * 9,
            address=f"{row['street'].title()}, {row['number']}", city=geo["city"], area=row["district"],
            state=geo["state"], postal_code=geo.get("postal_code"), latitude=geo["latitude"], longitude=geo["longitude"],
            attributes={"is_demo": True, "training_allowed": False, "source_name": SOURCE_ID,
                        "source_row": row["source_row"], "reference_transaction_date": row["date"],
                        "reference_transaction_price_brl": row["price_brl"], "geocoding_precision": geo["precision"],
                        "synthetic_fields": ["property_type", "asking_price", "area_m2", "rooms", "bathrooms", "parking_spaces", "days_on_market"]},
        ).model_dump()
        results.append(values)
    return results


async def persist(email: str, rows: list[dict], cells: list[dict]) -> dict:
    service = ControlPlaneService()
    repository = TenantDataRepository(service)
    try:
        pool = await service._database()
        memberships = await pool.fetch(
            """SELECT u.id, m.organization_id, m.role FROM cloud_users u
               JOIN organization_memberships m ON m.user_id = u.id WHERE lower(u.email)=lower($1)""", email)
        if len(memberships) != 1:
            raise ValueError("Target account must have exactly one unambiguous existing membership")
        context = TenantContext.from_principal(dict(memberships[0]))
        portfolio_id = str(uuid5(NAMESPACE_URL, f"{context.organization_id}:{DEMO_SOURCE}"))
        estates = demo_estates(rows, portfolio_id)
        if len(estates) < 6:
            raise ValueError("At least six verified addresses are required for this demo")
        inserted = 0
        async with repository.transaction(context) as connection:
            # Serialize repeated runs for this account and retain all user edits.
            await connection.execute("SELECT pg_advisory_xact_lock(hashtext($1))", f"{context.organization_id}:{DEMO_SOURCE}")
            await connection.execute(
                """INSERT INTO portfolios(id,organization_id,name,description,created_by_user_id)
                   VALUES($1,$2,$3,$4,$5) ON CONFLICT(id) DO NOTHING""", portfolio_id, context.organization_id,
                DEMO_NAME, "Carteira mock para testar Ceres. Características e anúncios simulados; sem uso para treinamento.", context.user_id)
            for estate in estates:
                estate_id = str(uuid5(NAMESPACE_URL, f"{context.organization_id}:{estate['external_id']}"))
                result = await connection.execute(
                    """INSERT INTO estates(id,organization_id,portfolio_id,external_id,source_name,status,title,summary,
                       property_type,asking_price,area_m2,price_per_m2,rooms,bathrooms,parking_spaces,days_on_market,
                       address,city,area,state,postal_code,location,attributes)
                       VALUES($1,$2,$3,$4,$5,'active',$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,
                              ST_SetSRID(ST_MakePoint($21,$22),4326)::geography,$23::jsonb)
                       ON CONFLICT(id) DO NOTHING""",
                    estate_id, context.organization_id, portfolio_id, estate["external_id"], DEMO_SOURCE,
                    *[estate[k] for k in ("title","summary","property_type","asking_price","area_m2","price_per_m2",
                                          "rooms","bathrooms","parking_spaces","days_on_market","address","city","area","state","postal_code")],
                    estate["longitude"], estate["latitude"], json.dumps(estate["attributes"]))
                inserted += result == "INSERT 0 1"
            # Public aggregates are built only from the input workbook, with no
            # tenant estate read and no identifiers or exact addresses published.
            for cell in cells:
                cell_id = str(uuid5(NAMESPACE_URL, f"{cell['input_version']}:{cell['h3_index']}"))
                await connection.execute(
                    """INSERT INTO heatmap_aggregates(id,organization_id,scope,h3_index,h3_resolution,
                       period_start,period_end,city,area,boundary,center,metrics,input_version)
                       VALUES($1,NULL,'platform',$2,$3,$4,$5,$6,$7,
                         ST_SetSRID(ST_GeomFromGeoJSON($8),4326)::geography,
                         ST_SetSRID(ST_GeomFromGeoJSON($9),4326)::geography,$10::jsonb,$11)
                       ON CONFLICT(id) DO NOTHING""", cell_id, cell["h3_index"], cell["h3_resolution"],
                    date.fromisoformat(cell["period_start"]), date.fromisoformat(cell["period_end"]), cell["city"], cell["area"],
                    json.dumps(cell["boundary"]), json.dumps(cell["center"]), json.dumps(cell["metrics"]), cell["input_version"])
        return {"portfolio_id": portfolio_id, "portfolio_name": DEMO_NAME, "inserted_estates": inserted,
                "demo_estate_count": len(estates), "published_cells": len(cells), "tenant_verified": True}
    finally:
        await service.close()


def train_candidate(rows: list[dict], source_version: str) -> dict:
    from train.transaction_avm import train_transaction_avm
    from train.valuation_data import ValuationRecord
    # One observation per cadastral property prevents repeat sales crossing
    # chronological windows. Exact issue dates are retained (not sale dates).
    latest = {}
    for row in sorted(rows, key=lambda row: row["date"]):
        latest[row["property_id"]] = row
    records = []
    for row in latest.values():
        event = datetime.fromisoformat(row["date"]).replace(tzinfo=timezone.utc)
        geo = row["geocode"]
        records.append(ValuationRecord(property_id=row["property_id"], transaction_id=row["transaction_id"],
            listing_cluster_id=row["address_key"], valuation_time=event, available_at=event, feature_as_of=event,
            source_id=SOURCE_ID, source_version=source_version, price_brl=row["price_brl"], target_kind="transaction",
            transaction_nature=None, features={"latitude":geo["latitude"],"longitude":geo["longitude"],
                                               "city":geo["city"],"state":geo["state"]}))
    artifact = ROOT / "ceres/train/artifacts/academic_address_candidate.json"
    result = train_transaction_avm(records, n_estimators=400, model_path=artifact)
    result["research_limitations"] = [
        "Geocoding is current and has not been verified historically; retrospective research only.",
        "Issue date is used; the workbook does not certify the actual sale date or arm-length status.",
        "No area, rooms or certified property type. Frequent-address sampling is biased.",
        "Price segment 100k-3m BRL, full transfers only. Not representative of the entire city.",
    ]
    result["production_eligible"] = False
    result["source_version"] = source_version
    Path(result["metadata_path"]).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return {key: result[key] for key in ("model_path", "promotion_status", "production_eligible", "training_rows",
                                        "calibration_rows", "test_rows", "out_of_time_metrics", "uncertainty", "research_limitations")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--city", required=True)
    parser.add_argument("--email")
    parser.add_argument("--max-geocodes", type=int, default=128)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--train", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_geocodes <= 256:
        parser.error("--max-geocodes must be between 1 and 256")
    if args.apply and not args.email:
        parser.error("--email is required for --apply")
    load_dotenv(ROOT / "ceres/.env")
    rows, report = read_transactions(args.source)
    enriched, coverage = enrich(rows, city=args.city, cache_path=ROOT / "data/enrichment/academic_address_geocodes.json",
                                max_requests=args.max_geocodes)
    version = SOURCE_ID + ":" + hashlib.sha256(args.source.read_bytes()).hexdigest()[:12] + f":n{args.max_geocodes}"
    report.update(coverage)
    cells = transaction_cells(enriched, version=version, source_rows=report["source_rows"])
    report["prepared_cells"] = len(cells)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if args.apply:
        report["database"] = asyncio.run(persist(args.email, enriched, cells))
        print(json.dumps(report["database"], ensure_ascii=False), flush=True)
    if args.train:
        report["training"] = train_candidate(enriched, version)
        print(json.dumps(report["training"], ensure_ascii=False), flush=True)
    destination = ROOT / "data/enrichment/academic_preparation_report.json"
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
