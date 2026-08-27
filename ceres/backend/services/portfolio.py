from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from statistics import fmean, median
from typing import Any

from backend.api.schemas.common import SourceInfo
from backend.api.schemas.portfolio import (
    PortfolioAnalysisRequest,
    PortfolioAnalyticsResponse,
    PortfolioConcentrationItem,
    PortfolioRegionalPerformanceItem,
    PortfolioTypeMixItem,
    PortfolioValuationItem,
)
from backend.services.errors import DomainValidationError, InsufficientDataError, UnavailableError
from backend.services.property import PropertyService
from backend.services.serialization import model_payload


class PortfolioService:
    """Presentation adapter over the existing ``portfolio`` and ``real_estate`` domain models.

    The legacy composite ``portfolio_analysis_scores`` function is deliberately
    left untouched. It currently cannot return a serializable score mapping, so
    this service exposes only deterministic aggregates that can be evidenced by
    the persisted domain records and the existing HHI primitive.
    """

    def __init__(self, properties: PropertyService) -> None:
        self.properties = properties

    def current_collection(self) -> PortfolioAnalyticsResponse:
        records = self.properties._properties_with_ids()
        if not records:
            raise InsufficientDataError("No persisted properties are available for portfolio analysis.")
        return self._analyse(records, [], None, source_kind="LIVE")

    def analyse_request(self, request: PortfolioAnalysisRequest) -> PortfolioAnalyticsResponse:
        try:
            from radar.data_base import data_type as data

            properties = [data.real_estate.model_validate(model_payload(property_)) for property_ in request.properties]
            sold = [data.sold_estate.model_validate(model_payload(property_)) for property_ in request.sold_properties]
        except ValueError as exc:
            raise DomainValidationError("The portfolio is invalid for the existing domain model.", details={"reason": str(exc)}) from exc
        except Exception as exc:
            raise UnavailableError("The portfolio domain model is unavailable.") from exc
        if not properties and not sold:
            raise InsufficientDataError("A portfolio requires at least one active or sold property.")
        records = [(f"request-property-{index}", property_) for index, property_ in enumerate(properties, start=1)]
        return self._analyse(records, sold, request.target_commission, source_kind="LIVE")

    @classmethod
    def _analyse(
        cls,
        records: list[tuple[str, Any]],
        sold: list[Any],
        target_commission: float | None,
        *,
        source_kind: str,
    ) -> PortfolioAnalyticsResponse:
        portfolio = cls._portfolio_domain([property_ for _, property_ in records], sold, target_commission)
        active_rows = [cls._property_row(record_id, property_) for record_id, property_ in records]
        asking_prices = [row["asking_price"] for row in active_rows if row["asking_price"] is not None]
        price_per_m2 = [row["price_per_m2"] for row in active_rows if row["price_per_m2"] is not None]
        dom_days = [row["dom_days"] for row in active_rows if row["dom_days"] is not None]
        listing_age = [row["listing_age_days"] for row in active_rows if row["listing_age_days"] is not None]
        price_gaps = [row["price_gap"] for row in active_rows if row["price_gap"] is not None]
        expected_growth = [row["expected_growth"] for row in active_rows if row["expected_growth"] is not None]

        regional_concentration = cls._regional_concentration(active_rows, sum(asking_prices))
        property_type_mix = cls._property_type_mix(active_rows, sum(asking_prices))
        regional_performance = cls._regional_performance(active_rows)
        valuation_rows = [row for row in active_rows if row["price_gap"] is not None]
        above_estimate = [cls._valuation_item(row) for row in sorted(valuation_rows, key=lambda row: row["price_gap"], reverse=True) if row["price_gap"] > 0]
        below_estimate = [cls._valuation_item(row) for row in sorted(valuation_rows, key=lambda row: row["price_gap"]) if row["price_gap"] < 0]

        return PortfolioAnalyticsResponse(
            active_listing_count=len(active_rows),
            sold_listing_count=len(sold),
            portfolio_value=sum(asking_prices),
            average_asking_price=cls._mean_or_none(asking_prices),
            median_asking_price=float(median(asking_prices)) if asking_prices else None,
            average_price_per_m2=cls._mean_or_none(price_per_m2),
            average_price_gap=cls._mean_or_none(price_gaps),
            average_expected_growth=cls._mean_or_none(expected_growth),
            average_listing_age_days=cls._mean_or_none(listing_age),
            # Existing score names retained for the established API contract.
            average_dom_days=cls._mean_or_none(dom_days),
            stagnation_rate=(sum(day > 90 for day in dom_days) / len(dom_days)) if dom_days else None,
            hhi=cls._existing_hhi(portfolio),
            regional_concentration=regional_concentration,
            property_type_mix=property_type_mix,
            regional_performance=regional_performance,
            above_estimate=above_estimate,
            below_estimate=below_estimate,
            source=SourceInfo(
                kind=source_kind,
                label="DATA · PORTFOLIO ANALYTICS",
                detail="Deterministic aggregates over persisted real_estate records",
            ),
        )

    @staticmethod
    def _portfolio_domain(properties: list[Any], sold: list[Any], target_commission: float | None) -> Any:
        try:
            from radar.data_base import data_type as data

            return data.portfolio(
                tgt_comission=target_commission,
                real_estates=properties,
                sold_estates=sold,
                estates=properties,
            )
        except ValueError as exc:
            raise DomainValidationError("The portfolio cannot be represented by the existing domain model.", details={"reason": str(exc)}) from exc
        except Exception as exc:
            raise UnavailableError("The portfolio domain model is unavailable.") from exc

    @classmethod
    def _property_row(cls, record_id: str, property_: Any) -> dict[str, Any]:
        location = getattr(property_, "location", None)
        metrics = getattr(property_, "real_estate_metrics", None)
        pricing = getattr(property_, "re_price_metrics", None)
        predictions = getattr(property_, "predictions", None) or getattr(property_, "preictions", None)
        asking_price = cls._asking_price(property_)
        estimated_price = cls._number_or_none(getattr(predictions, "suggested_price", None))
        if estimated_price is None:
            estimated_price = cls._number_or_none(getattr(pricing, "avm_price", None))
        price_gap = (asking_price - estimated_price) / estimated_price if asking_price is not None and estimated_price not in (None, 0) else None
        area_m2 = cls._number_or_none(getattr(metrics, "square_metrage", None))
        price_per_m2 = cls._number_or_none(getattr(metrics, "square_meter_price", None))
        if price_per_m2 is None and asking_price is not None and area_m2 not in (None, 0):
            price_per_m2 = asking_price / area_m2
        kind = getattr(property_, "kind", None)
        kind_value = getattr(kind, "value", kind)
        area = getattr(location, "area", None)
        city = getattr(location, "city", None)
        region = area or city or "Sem região"
        title = getattr(location, "address", None) or getattr(property_, "summary", None) or f"Imóvel {record_id}"
        dom_days = cls._number_or_none(getattr(property_, "dom", None))
        on_sale_since = getattr(property_, "on_sale_since", None)
        listing_age_days = None
        if isinstance(on_sale_since, date):
            listing_age_days = float(max((date.today() - on_sale_since).days, 0))
        elif dom_days is not None:
            listing_age_days = dom_days
        return {
            "property_id": record_id,
            "title": str(title),
            "region": str(region),
            "kind": str(kind_value) if kind_value is not None else "Sem tipo",
            "asking_price": asking_price,
            "estimated_price": estimated_price,
            "price_gap": price_gap,
            "price_per_m2": price_per_m2,
            "dom_days": dom_days,
            "listing_age_days": listing_age_days,
            "expected_growth": cls._number_or_none(getattr(predictions, "expected_growth", None)),
        }

    @staticmethod
    def _asking_price(property_: Any) -> float | None:
        try:
            return PortfolioService._number_or_none(PropertyService._current_price(property_))
        except ValueError:
            return None

    @staticmethod
    def _number_or_none(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) and number >= 0 else None

    @staticmethod
    def _mean_or_none(values: list[float]) -> float | None:
        return float(fmean(values)) if values else None

    @staticmethod
    def _existing_hhi(portfolio: Any) -> float | None:
        try:
            from radar.data_base.metrics import calculate_portfolio_hhi

            return float(calculate_portfolio_hhi(portfolio.real_estates or []))
        except Exception:
            return None

    @classmethod
    def _regional_concentration(cls, rows: list[dict[str, Any]], portfolio_value: float) -> list[PortfolioConcentrationItem]:
        buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "value": 0.0})
        for row in rows:
            bucket = buckets[row["region"]]
            bucket["count"] += 1
            bucket["value"] += row["asking_price"] or 0.0
        return [
            PortfolioConcentrationItem(
                region=region,
                property_count=int(values["count"]),
                portfolio_value=values["value"],
                share=values["value"] / portfolio_value if portfolio_value else 0.0,
            )
            for region, values in sorted(buckets.items(), key=lambda item: item[1]["value"], reverse=True)
        ]

    @classmethod
    def _property_type_mix(cls, rows: list[dict[str, Any]], portfolio_value: float) -> list[PortfolioTypeMixItem]:
        buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "value": 0.0})
        for row in rows:
            bucket = buckets[row["kind"]]
            bucket["count"] += 1
            bucket["value"] += row["asking_price"] or 0.0
        return [
            PortfolioTypeMixItem(
                kind=kind,
                property_count=int(values["count"]),
                portfolio_value=values["value"],
                share=values["value"] / portfolio_value if portfolio_value else 0.0,
            )
            for kind, values in sorted(buckets.items(), key=lambda item: item[1]["count"], reverse=True)
        ]

    @classmethod
    def _regional_performance(cls, rows: list[dict[str, Any]]) -> list[PortfolioRegionalPerformanceItem]:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            buckets[row["region"]].append(row)
        performance = []
        for region, region_rows in buckets.items():
            growth = [row["expected_growth"] for row in region_rows if row["expected_growth"] is not None]
            price_per_m2 = [row["price_per_m2"] for row in region_rows if row["price_per_m2"] is not None]
            dom_days = [row["dom_days"] for row in region_rows if row["dom_days"] is not None]
            performance.append(
                PortfolioRegionalPerformanceItem(
                    region=region,
                    property_count=len(region_rows),
                    average_expected_growth=cls._mean_or_none(growth),
                    average_price_per_m2=cls._mean_or_none(price_per_m2),
                    average_dom_days=cls._mean_or_none(dom_days),
                )
            )
        return sorted(
            performance,
            key=lambda item: item.average_expected_growth if item.average_expected_growth is not None else float("-inf"),
            reverse=True,
        )

    @staticmethod
    def _valuation_item(row: dict[str, Any]) -> PortfolioValuationItem:
        return PortfolioValuationItem(
            property_id=row["property_id"],
            title=row["title"],
            region=None if row["region"] == "Sem região" else row["region"],
            kind=None if row["kind"] == "Sem tipo" else row["kind"],
            asking_price=row["asking_price"],
            estimated_price=row["estimated_price"],
            price_gap=row["price_gap"],
            dom_days=row["dom_days"],
            expected_growth=row["expected_growth"],
        )
