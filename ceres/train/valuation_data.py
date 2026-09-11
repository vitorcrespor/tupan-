"""Point-in-time, provenance-aware inputs for the production AVM.

The legacy AVM accepts domain objects because it predates a transaction data
contract.  This module is the stricter boundary used by the research-aligned
training path.  It intentionally refuses to guess whether an asking price or
an old ``suggested_price`` is a market-sale label.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from types import MappingProxyType
from typing import Any, Iterable, Literal, Mapping


TargetKind = Literal["transaction", "asking"]

# The model receives granular facts, never a raw address, owner, identifier or
# a score that could contain the target price.  This list is deliberately
# conservative; new features are added through a versioned experiment.
FEATURE_COLUMNS = (
    "usable_area_m2",
    "built_area_m2",
    "lot_area_m2",
    "latitude",
    "longitude",
    "property_type",
    "subtype",
    "city",
    "state",
    "rooms",
    "suites",
    "bathrooms",
    "parking_spaces",
    "floor",
    "building_floors",
    "year_built",
    "renovation_year",
    "condition",
    "elevator",
    "condo_fee_brl",
    "h3_r7",
    "h3_r8",
    "h3_r9",
)
CATEGORICAL_FEATURES = (
    "property_type",
    "subtype",
    "city",
    "state",
    "condition",
    "h3_r7",
    "h3_r8",
    "h3_r9",
)
CRITICAL_FEATURES = ("usable_area_m2", "property_type", "city", "latitude", "longitude")
_NUMERIC_FEATURES = tuple(name for name in FEATURE_COLUMNS if name not in CATEGORICAL_FEATURES)
_EXCLUDED_FEATURES = {
    "address", "owner", "owner_name", "organization_id", "portfolio_id", "property_id",
    "transaction_id", "asking_price_brl", "sale_price_brl", "last_sale_price",
    "suggested_price", "estimated_price", "price_per_m2", "leverage", "location_score",
    "luxury_score", "leisure_score", "avm_output", "target", "raw_address",
}


class ValuationDataError(ValueError):
    """Base error for an invalid valuation observation."""


class ObservationExcluded(ValuationDataError):
    """Raised internally when a record is intentionally not trainable."""


class FrozenFeatureMap(dict[str, Any]):
    """A dict-shaped immutable mapping that remains friendly to ``asdict``."""

    def _blocked(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("valuation features are immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _blocked

    def __deepcopy__(self, memo: dict[int, Any]) -> dict[str, Any]:
        return dict(self)


def _utc(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValuationDataError(f"{field} must be an ISO-8601 timestamp") from exc
    else:
        raise ValuationDataError(f"{field} is required")
    if result.tzinfo is None:
        raise ValuationDataError(f"{field} must include a timezone")
    return result.astimezone(timezone.utc)


def _positive_price(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValuationDataError(f"{field} must be a positive number") from exc
    if not isfinite(number) or number <= 0:
        raise ValuationDataError(f"{field} must be a positive number")
    return number


def _lineage(value: Any, field: str) -> tuple[datetime, str, str]:
    if not isinstance(value, Mapping):
        raise ValuationDataError(f"feature_lineage[{field}] is required")
    return (
        _utc(value.get("available_at"), f"feature_lineage[{field}].available_at"),
        _required_text(value.get("source_id"), f"feature_lineage[{field}].source_id"),
        _required_text(value.get("source_version"), f"feature_lineage[{field}].source_version"),
    )


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValuationDataError(f"{field} is required")
    return value.strip()


@dataclass(frozen=True, slots=True)
class ValuationRecord:
    """One eligible observation with all dates needed for point-in-time joins."""

    property_id: str
    transaction_id: str
    listing_cluster_id: str | None
    valuation_time: datetime
    available_at: datetime
    feature_as_of: datetime
    source_id: str
    source_version: str
    price_brl: float
    target_kind: TargetKind
    transaction_nature: str | None
    features: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.available_at < self.valuation_time and self.target_kind == "transaction":
            # Labels can arrive after an event; silently making them available
            # before the sale would leak future information into training.
            raise ValuationDataError("transaction label available_at cannot precede valuation_time")
        if self.feature_as_of > self.valuation_time:
            raise ValuationDataError("feature_as_of cannot be after valuation_time")


def _derived_h3(features: dict[str, Any]) -> None:
    if not all(isinstance(features.get(name), (int, float)) and isfinite(float(features[name])) for name in ("latitude", "longitude")):
        return
    try:
        import h3

        for resolution, name in ((7, "h3_r7"), (8, "h3_r8"), (9, "h3_r9")):
            features.setdefault(name, h3.latlng_to_cell(float(features["latitude"]), float(features["longitude"]), resolution))
    except (ImportError, AttributeError, ValueError):
        # H3 is an optional enrichment; coordinates remain valid features.
        return


def _normalize_features(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValuationDataError("features must be an object")
    unknown = set(raw) - set(FEATURE_COLUMNS) - _EXCLUDED_FEATURES
    if unknown:
        raise ValuationDataError(f"unsupported valuation features: {sorted(unknown)}")
    values = {name: raw.get(name) for name in FEATURE_COLUMNS if name in raw}
    # None means unknown.  Zero remains a real observation.
    for name in _NUMERIC_FEATURES:
        if values.get(name) is None:
            continue
        try:
            number = float(values[name])
        except (TypeError, ValueError) as exc:
            raise ValuationDataError(f"features.{name} must be numeric or null") from exc
        if not isfinite(number):
            raise ValuationDataError(f"features.{name} must be finite or null")
        values[name] = number
    _derived_h3(values)
    return values


def parse_records(
    payloads: Iterable[Mapping[str, Any]],
    *,
    target_kind: TargetKind = "transaction",
) -> tuple[list[ValuationRecord], dict[str, int]]:
    """Parse only explicit, verified observations and return exclusion counts.

    ``sale_price_brl`` and ``asking_price_brl`` are intentionally separate.
    Legacy fields such as ``suggested_price`` and ``last_sale_price`` are not
    accepted as labels by this contract.
    """
    if target_kind not in ("transaction", "asking"):
        raise ValueError("target_kind must be transaction or asking")
    accepted: list[ValuationRecord] = []
    excluded: dict[str, int] = {}
    for index, payload in enumerate(payloads):
        try:
            if not isinstance(payload, Mapping):
                raise ObservationExcluded("record is not an object")
            if payload.get("verified") is not True or payload.get("training_allowed") is not True:
                raise ObservationExcluded("record is not verified for training")
            property_id = _required_text(payload.get("property_id"), "property_id")
            transaction_id = _required_text(payload.get("transaction_id"), "transaction_id")
            valuation_time = _utc(payload.get("valuation_time", payload.get("event_time")), "valuation_time")
            available_at = _utc(payload.get("available_at"), "available_at")
            feature_as_of = _utc(payload.get("feature_as_of", valuation_time), "feature_as_of")
            if feature_as_of > valuation_time:
                raise ObservationExcluded("features are newer than the valuation event")
            features = _normalize_features(payload.get("features"))
            lineage = payload.get("feature_lineage")
            if not isinstance(lineage, Mapping):
                raise ObservationExcluded("feature lineage is missing")
            for name in features:
                source_lineage = lineage.get(name)
                # H3 cells are deterministic derivatives of the coordinates;
                # inherit their source lineage while retaining the derived
                # feature as an explicit field in the feature graph.
                if source_lineage is None and name in {"h3_r7", "h3_r8", "h3_r9"}:
                    source_lineage = lineage.get("latitude") or lineage.get("longitude")
                available, source_id, source_version = _lineage(source_lineage, name)
                if available > valuation_time:
                    raise ObservationExcluded(f"feature {name} was unavailable at valuation time")
                if available > feature_as_of:
                    raise ObservationExcluded(f"feature {name} is newer than feature_as_of")
                if not source_id or not source_version:
                    raise ObservationExcluded(f"feature {name} has incomplete provenance")
            if target_kind == "transaction":
                if payload.get("transaction_nature") != "arm_length":
                    raise ObservationExcluded("transaction is not explicitly arm's-length")
                if "sale_price_brl" not in payload:
                    raise ObservationExcluded("sale_price_brl is required for transaction targets")
                price = _positive_price(payload.get("sale_price_brl"), "sale_price_brl")
            else:
                if "asking_price_brl" not in payload:
                    raise ObservationExcluded("asking_price_brl is required for asking targets")
                price = _positive_price(payload.get("asking_price_brl"), "asking_price_brl")
            source_id = _required_text(payload.get("source_id"), "source_id")
            source_version = _required_text(payload.get("source_version"), "source_version")
            accepted.append(ValuationRecord(
                property_id=property_id,
                transaction_id=transaction_id,
                listing_cluster_id=payload.get("listing_cluster_id"),
                valuation_time=valuation_time,
                available_at=available_at,
                feature_as_of=feature_as_of,
                source_id=source_id,
                source_version=source_version,
                price_brl=price,
                target_kind=target_kind,
                transaction_nature=payload.get("transaction_nature"),
                features=MappingProxyType(features),
            ))
        except ObservationExcluded as exc:
            key = str(exc)
            excluded[key] = excluded.get(key, 0) + 1
        except ValuationDataError as exc:
            key = f"invalid:{exc}"
            excluded[key] = excluded.get(key, 0) + 1
        except Exception as exc:
            excluded[f"record_{index}:{type(exc).__name__}"] = excluded.get(f"record_{index}:{type(exc).__name__}", 0) + 1
    return accepted, excluded


def feature_values(record: ValuationRecord) -> dict[str, Any]:
    """Return the model feature vector without identifiers or target fields."""
    return {name: record.features.get(name) for name in FEATURE_COLUMNS}
