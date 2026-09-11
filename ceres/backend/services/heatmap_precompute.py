"""Background H3 aggregation over tenant-authorized estate source data."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import fmean
from typing import Any

from backend.repositories.job_queue import ClaimedJob, JobQueueRepository, JobResult
from backend.repositories.tenant_data import TenantContext
from backend.services.errors import DomainValidationError


class HeatmapPrecomputer:
    """Compute only common base aggregates; request-time reads remain fast."""

    async def run(self, queue: JobQueueRepository, context: TenantContext, job: ClaimedJob) -> JobResult:
        payload = job.payload
        resolution = int(payload.get("h3_resolution", 9))
        if not 0 <= resolution <= 15:
            raise DomainValidationError("h3_resolution must be between 0 and 15.")
        city = payload.get("city")
        area = payload.get("area")
        period_start = _date_value(payload.get("period_start"), default=date.today())
        period_end = _date_value(payload.get("period_end"), default=date.today())
        if period_end < period_start:
            raise DomainValidationError("Heatmap period_end cannot precede period_start.")
        input_version = str(payload.get("input_version") or "estate-base-v1")

        await queue.set_progress(context, job.job_id, 10)
        sources = await queue.heatmap_source_estates(context, city=city, area=area)
        await queue.set_progress(context, job.job_id, 35)
        aggregates = _aggregate_sources(
            sources,
            resolution=resolution,
            period_start=period_start,
            period_end=period_end,
            input_version=input_version,
        )
        await queue.set_progress(context, job.job_id, 75)
        await queue.upsert_heatmap_aggregates(context, aggregates)
        reference = f"heatmap:{context.organization_id}:{resolution}:{period_start.isoformat()}:{period_end.isoformat()}:{input_version}"
        return JobResult(
            result_reference=reference,
            result={"aggregate_count": len(aggregates), "source_estate_count": len(sources), "h3_resolution": resolution},
        )


def _aggregate_sources(
    sources: list[dict[str, Any]],
    *,
    resolution: int,
    period_start: date,
    period_end: date,
    input_version: str,
) -> list[dict[str, Any]]:
    try:
        import h3
    except ImportError as exc:
        raise RuntimeError("The H3 dependency is unavailable to the worker.") from exc

    grouped: dict[tuple[str, str | None, str | None], list[dict[str, Any]]] = defaultdict(list)
    for source in sources:
        latitude, longitude = source.get("latitude"), source.get("longitude")
        if latitude is None or longitude is None:
            continue
        cell = _latlng_to_cell(h3, float(latitude), float(longitude), resolution)
        grouped[(cell, source.get("city"), source.get("area"))].append(source)

    aggregates: list[dict[str, Any]] = []
    for (cell, city, area), rows in grouped.items():
        boundary = _boundary_geojson(h3, cell)
        center_lat, center_lng = _cell_center(h3, cell)
        aggregates.append(
            {
                "h3_index": cell,
                "h3_resolution": resolution,
                "city": city,
                "area": area,
                "period_start": period_start,
                "period_end": period_end,
                "boundary": boundary,
                "center": {"type": "Point", "coordinates": [center_lng, center_lat]},
                "metrics": {
                    "inventory": len(rows),
                    "average_asking_price": _mean(rows, "asking_price"),
                    "average_price_m2": _mean(rows, "price_per_m2"),
                    "average_dom_days": _mean(rows, "days_on_market"),
                },
                "input_version": input_version,
            }
        )
    return aggregates


def _latlng_to_cell(h3_module: Any, latitude: float, longitude: float, resolution: int) -> str:
    if hasattr(h3_module, "latlng_to_cell"):
        return str(h3_module.latlng_to_cell(latitude, longitude, resolution))
    return str(h3_module.geo_to_h3(latitude, longitude, resolution))


def _cell_center(h3_module: Any, cell: str) -> tuple[float, float]:
    if hasattr(h3_module, "cell_to_latlng"):
        latitude, longitude = h3_module.cell_to_latlng(cell)
    else:
        latitude, longitude = h3_module.h3_to_geo(cell)
    return float(latitude), float(longitude)


def _boundary_geojson(h3_module: Any, cell: str) -> dict[str, Any]:
    if hasattr(h3_module, "cell_to_boundary"):
        boundary = h3_module.cell_to_boundary(cell)
    else:
        boundary = h3_module.h3_to_geo_boundary(cell)
    coordinates = [[float(longitude), float(latitude)] for latitude, longitude in boundary]
    coordinates.append(coordinates[0])
    return {"type": "Polygon", "coordinates": [coordinates]}


def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
    values = []
    for row in rows:
        try:
            value = float(row.get(key))
        except (TypeError, ValueError):
            continue
        values.append(value)
    return float(fmean(values)) if values else None


def _date_value(value: Any, *, default: date) -> date:
    if value is None:
        return default
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
