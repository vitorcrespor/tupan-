from __future__ import annotations

from datetime import date

from pydantic import Field

from backend.api.schemas.common import ApiSchema


class PricePoint(ApiSchema):
    date: date
    price: float


class LocationInput(ApiSchema):
    city: str | None = None
    area: str | None = None
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class PropertyMetricsInput(ApiSchema):
    number_of_rooms: int | None = Field(default=None, ge=0)
    number_of_bathrooms: int | None = Field(default=None, ge=0)
    number_of_parking_spaces: int | None = Field(default=None, ge=0)
    square_metrage: float | None = Field(default=None, gt=0)
    square_meter_price: float | None = Field(default=None, gt=0)


class RePriceMetricsInput(ApiSchema):
    price: float | None = Field(default=None, ge=0)
    listed_prices: list[PricePoint] = Field(default_factory=list)
    last_sale_price: float | None = Field(default=None, ge=0)
    sale_price: float | None = Field(default=None, ge=0)


class PredictionsInput(ApiSchema):
    suggested_price: float | None = Field(default=None, ge=0)
    expected_growth: float | None = None
    expected_dom: float | None = Field(default=None, ge=0)


class FourMetricInput(ApiSchema):
    luxury: float | None = Field(default=None, ge=0, le=5)
    leisure: float | None = Field(default=None, ge=0, le=5)
    location_: float | None = Field(default=None, ge=0, le=5)
    leverage: float | None = Field(default=None, ge=0, le=5)


class PropertyInput(ApiSchema):
    exclusive: bool | None = None
    dom: float | None = Field(default=None, ge=0)
    summary: str | None = None
    age: int | None = Field(default=None, ge=0)
    last_sale_date: date | None = None
    on_sale_since: date | None = None
    kind: str | None = None
    location: LocationInput | None = None
    real_estate_metrics: PropertyMetricsInput | None = None
    re_price_metrics: RePriceMetricsInput | None = None
    predictions: PredictionsInput | None = None
    four_metric: FourMetricInput | None = None


class PropertyCreateRequest(PropertyInput):
    normalize_address: bool = False


class PropertyLocationResponse(LocationInput):
    h3_index: str | None = None


class PropertyMetricsResponse(ApiSchema):
    rooms: int | None = None
    bathrooms: int | None = None
    parking_spaces: int | None = None
    area_m2: float | None = None
    price_per_m2: float | None = None


class PropertyPricingResponse(ApiSchema):
    asking_price: float | None = None
    last_sale_price: float | None = None
    sale_price: float | None = None
    listed_prices: list[PricePoint] = Field(default_factory=list)


class PropertyPredictionResponse(ApiSchema):
    suggested_price: float | None = None
    expected_growth: float | None = None
    expected_dom_days: float | None = None


class PropertyResponse(ApiSchema):
    id: str
    kind: str | None = None
    exclusive: bool | None = None
    dom_days: float | None = None
    age: int | None = None
    last_sale_date: date | None = None
    on_sale_since: date | None = None
    summary: str | None = None
    location: PropertyLocationResponse | None = None
    metrics: PropertyMetricsResponse | None = None
    pricing: PropertyPricingResponse | None = None
    predictions: PropertyPredictionResponse | None = None
    profile: FourMetricInput | None = None


class PropertySearchRequest(ApiSchema):
    query: str = Field(min_length=1, max_length=2_000)
    city: str | None = None
    area: str | None = None
    kind: str | None = None
    limit: int = Field(default=10, ge=1, le=100)


class PropertySearchResult(ApiSchema):
    id: str | None = None
    property: PropertyResponse | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
    document: str | None = None
    distance: float | None = None


class PropertyCreateResponse(ApiSchema):
    id: str
    property: PropertyResponse
    duplicate: bool = False


class PropertyImportResponse(ApiSchema):
    successful_records: list[dict] = Field(default_factory=list)
    invalid_records: list[dict] = Field(default_factory=list)
    duplicates: list[dict] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)


class PropertyValuationResponse(ApiSchema):
    property_id: str
    # Legacy names retained for existing frontend consumers.
    current_price: float = Field(gt=0)
    suggested_price: float = Field(gt=0)
    deviation: float | None = None
    # Explicit transport names for new consumers. The AVM only produces a
    # point estimate, so no confidence or interval is represented here.
    listed_price: float = Field(gt=0)
    estimated_price: float = Field(gt=0)
    difference: float
    difference_percent: float | None = None
    price_per_m2: float | None = Field(default=None, gt=0)
    estimated_price_per_m2: float | None = Field(default=None, gt=0)
    model_available: bool


class CityCreateRequest(ApiSchema):
    name: str = Field(min_length=1, max_length=200)
    population: int | None = Field(default=None, ge=0)
    diversity_score: float | None = None


class CityResponse(CityCreateRequest):
    id: str


class AreaCreateRequest(ApiSchema):
    name: str = Field(min_length=1, max_length=200)
    diversity_score: float | None = None


class AreaResponse(AreaCreateRequest):
    id: str
