from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, TypeAlias


JsonObject: TypeAlias = Mapping[str, Any]
PropertyPayload: TypeAlias = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class SourceInfo:
    kind: Literal["LIVE", "MOCK", "UNAVAILABLE"]
    label: str
    detail: str | None = None
    calculated_at: str | None = None

    @classmethod
    def from_json(cls, value: JsonObject) -> "SourceInfo":
        return cls(
            kind=value["kind"],
            label=value["label"],
            detail=value.get("detail"),
            calculated_at=value.get("calculated_at"),
        )


@dataclass(frozen=True, slots=True)
class PageMeta:
    limit: int
    offset: int
    total: int

    @classmethod
    def from_json(cls, value: JsonObject) -> "PageMeta":
        return cls(limit=int(value["limit"]), offset=int(value["offset"]), total=int(value["total"]))


@dataclass(frozen=True, slots=True)
class PricePoint:
    date: str
    price: float

    @classmethod
    def from_json(cls, value: JsonObject) -> "PricePoint":
        return cls(date=str(value["date"]), price=float(value["price"]))


@dataclass(frozen=True, slots=True)
class PropertyLocation:
    city: str | None
    area: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    h3_index: str | None

    @classmethod
    def from_json(cls, value: JsonObject) -> "PropertyLocation":
        return cls(**{key: value.get(key) for key in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class PropertyMetrics:
    rooms: int | None
    bathrooms: int | None
    parking_spaces: int | None
    area_m2: float | None
    price_per_m2: float | None

    @classmethod
    def from_json(cls, value: JsonObject) -> "PropertyMetrics":
        return cls(**{key: value.get(key) for key in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class PropertyPricing:
    asking_price: float | None
    last_sale_price: float | None
    sale_price: float | None
    listed_prices: list[PricePoint]

    @classmethod
    def from_json(cls, value: JsonObject) -> "PropertyPricing":
        return cls(
            asking_price=value.get("asking_price"),
            last_sale_price=value.get("last_sale_price"),
            sale_price=value.get("sale_price"),
            listed_prices=[PricePoint.from_json(point) for point in value.get("listed_prices", [])],
        )


@dataclass(frozen=True, slots=True)
class PropertyPrediction:
    suggested_price: float | None
    expected_growth: float | None
    expected_dom_days: float | None

    @classmethod
    def from_json(cls, value: JsonObject) -> "PropertyPrediction":
        return cls(**{key: value.get(key) for key in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class FourMetric:
    luxury: float | None
    leisure: float | None
    location_: float | None
    leverage: float | None

    @classmethod
    def from_json(cls, value: JsonObject) -> "FourMetric":
        return cls(**{key: value.get(key) for key in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class Property:
    id: str
    kind: str | None
    exclusive: bool | None
    dom_days: float | None
    age: int | None
    last_sale_date: str | None
    on_sale_since: str | None
    summary: str | None
    location: PropertyLocation | None
    metrics: PropertyMetrics | None
    pricing: PropertyPricing | None
    predictions: PropertyPrediction | None
    profile: FourMetric | None

    @classmethod
    def from_json(cls, value: JsonObject) -> "Property":
        return cls(
            id=str(value["id"]),
            kind=value.get("kind"),
            exclusive=value.get("exclusive"),
            dom_days=value.get("dom_days"),
            age=value.get("age"),
            last_sale_date=value.get("last_sale_date"),
            on_sale_since=value.get("on_sale_since"),
            summary=value.get("summary"),
            location=PropertyLocation.from_json(value["location"]) if value.get("location") else None,
            metrics=PropertyMetrics.from_json(value["metrics"]) if value.get("metrics") else None,
            pricing=PropertyPricing.from_json(value["pricing"]) if value.get("pricing") else None,
            predictions=PropertyPrediction.from_json(value["predictions"]) if value.get("predictions") else None,
            profile=FourMetric.from_json(value["profile"]) if value.get("profile") else None,
        )


@dataclass(frozen=True, slots=True)
class PropertyPage:
    items: list[Property]
    page: PageMeta

    @classmethod
    def from_json(cls, value: JsonObject) -> "PropertyPage":
        return cls(
            items=[Property.from_json(item) for item in value["items"]],
            page=PageMeta.from_json(value["page"]),
        )


@dataclass(frozen=True, slots=True)
class PropertySearchResult:
    id: str | None
    property: Property | None
    metadata: dict[str, Any]
    document: str | None
    distance: float | None

    @classmethod
    def from_json(cls, value: JsonObject) -> "PropertySearchResult":
        return cls(
            id=value.get("id"),
            property=Property.from_json(value["property"]) if value.get("property") else None,
            metadata=dict(value.get("metadata") or {}),
            document=value.get("document"),
            distance=value.get("distance"),
        )


@dataclass(frozen=True, slots=True)
class PropertySearchPage:
    items: list[PropertySearchResult]
    page: PageMeta

    @classmethod
    def from_json(cls, value: JsonObject) -> "PropertySearchPage":
        return cls(
            items=[PropertySearchResult.from_json(item) for item in value["items"]],
            page=PageMeta.from_json(value["page"]),
        )


@dataclass(frozen=True, slots=True)
class PropertyValuation:
    property_id: str
    current_price: float
    suggested_price: float
    deviation: float | None
    model_available: bool

    @classmethod
    def from_json(cls, value: JsonObject) -> "PropertyValuation":
        return cls(**value)


@dataclass(frozen=True, slots=True)
class H3Cell:
    h3_index: str
    h3_resolution: int
    city: str | None
    neighborhood: str | None
    center: tuple[float, float] | None
    boundary: list[tuple[float, float]]
    market_heat: float | None
    demand_score: float | None
    average_price_m2: float | None
    price_growth: float | None
    inventory: int
    average_dom_days: float | None
    sales_velocity: float | None
    calculation: Literal["EXISTING_MODEL", "UNAVAILABLE"]
    source: Literal["LIVE", "MOCK"]

    @classmethod
    def from_json(cls, value: JsonObject) -> "H3Cell":
        return cls(
            **{
                **{key: value.get(key) for key in cls.__dataclass_fields__ if key not in {"center", "boundary"}},
                "center": tuple(value["center"]) if value.get("center") else None,
                "boundary": [tuple(point) for point in value.get("boundary", [])],
            }
        )


@dataclass(frozen=True, slots=True)
class MarketCells:
    source: SourceInfo
    filters: dict[str, Any]
    cells: list[H3Cell]

    @classmethod
    def from_json(cls, value: JsonObject) -> "MarketCells":
        return cls(
            source=SourceInfo.from_json(value["source"]),
            filters=dict(value["filters"]),
            cells=[H3Cell.from_json(cell) for cell in value["cells"]],
        )


@dataclass(frozen=True, slots=True)
class MarketOverview:
    source: SourceInfo
    metrics: list[dict[str, str]]
    trends: dict[str, Any]
    exposure: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    brief: dict[str, str]

    @classmethod
    def from_json(cls, value: JsonObject) -> "MarketOverview":
        return cls(source=SourceInfo.from_json(value["source"]), **{key: value.get(key, {} if key in {"trends", "brief"} else []) for key in cls.__dataclass_fields__ if key != "source"})


@dataclass(frozen=True, slots=True)
class MarketRegion:
    cell: H3Cell
    source: SourceInfo

    @classmethod
    def from_json(cls, value: JsonObject) -> "MarketRegion":
        return cls(cell=H3Cell.from_json(value["cell"]), source=SourceInfo.from_json(value["source"]))


@dataclass(frozen=True, slots=True)
class MarketIntelligence:
    source: SourceInfo
    controls: dict[str, str]
    available_geographies: list[str]
    metric: dict[str, str]
    metrics: list[dict[str, str]]
    chart: dict[str, Any]
    summary_statistics: dict[str, Any]

    @classmethod
    def from_json(cls, value: JsonObject) -> "MarketIntelligence":
        values = dict(value)
        values["source"] = SourceInfo.from_json(values["source"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class MetricCatalogItem:
    key: str
    label: str
    group: str
    source: Literal["DATA", "MODEL"]

    @classmethod
    def from_json(cls, value: JsonObject) -> "MetricCatalogItem":
        return cls(**value)


@dataclass(frozen=True, slots=True)
class MetricSeries:
    metric: str
    unit: str
    aggregation: str
    points: list[dict[str, Any]]
    source: SourceInfo

    @classmethod
    def from_json(cls, value: JsonObject) -> "MetricSeries":
        values = dict(value)
        values["source"] = SourceInfo.from_json(values["source"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class PortfolioAnalytics:
    lsp: float | None
    active_listing_months: float | None
    average_dom_days: float | None
    stagnation_rate: float | None
    exclusive_retention: float | None
    commission_retention: float | None
    gci_per_sqm: float | None
    hhi: float | None
    clustering_coefficient: float | None
    source: SourceInfo

    @classmethod
    def from_json(cls, value: JsonObject) -> "PortfolioAnalytics":
        values = dict(value)
        values["source"] = SourceInfo.from_json(values["source"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class Forecast:
    property_id: str | None
    time_span_days: int
    expected_growth_pct: float
    interval: list[float]

    @classmethod
    def from_json(cls, value: JsonObject) -> "Forecast":
        return cls(**value)


@dataclass(frozen=True, slots=True)
class PropertyImportResult:
    successful_records: list[dict[str, Any]]
    invalid_records: list[dict[str, Any]]
    duplicates: list[dict[str, Any]]
    errors: list[dict[str, Any]]

    @classmethod
    def from_json(cls, value: JsonObject) -> "PropertyImportResult":
        return cls(**value)


@dataclass(frozen=True, slots=True)
class AgentMessage:
    session_id: str
    content: str
    sources: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    actions: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_json(cls, value: JsonObject) -> "AgentMessage":
        message = value["message"]
        return cls(
            session_id=value["session_id"],
            content=message["content"],
            sources=list(value.get("sources") or []),
            warnings=list(value.get("warnings") or []),
            actions=list(value.get("actions") or []),
        )


@dataclass(frozen=True, slots=True)
class AgentTrace:
    session_id: str
    events: list[dict[str, Any]]

    @classmethod
    def from_json(cls, value: JsonObject) -> "AgentTrace":
        return cls(session_id=value["session_id"], events=list(value.get("events") or []))
