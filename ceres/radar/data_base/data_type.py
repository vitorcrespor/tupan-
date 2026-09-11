from __future__ import annotations

from datetime import date
from enum import Enum
import os
import pydantic as pyda

try:
    from h3 import latlng_to_cell as latlong_to_cell
except ImportError:
    from h3 import latlong_to_cell


class MarketContext(pyda.BaseModel):
    reference_date: date
    city: str | None = None
    state: str | None = None

    selic_rate: float
    real_interest_rate: float
    mortgage_rate: float

    mortgage_credit_yoy: float
    mortgage_concessions_yoy: float
    mortgage_delinquency_rate: float

    ipca_yoy: float
    real_income: float
    unemployment_rate: float
    ibc_br_index: float
    sinapi_cost_m2: float

    fipezap_index: float




class MapPoint(pyda.BaseModel):
    latitude: float
    longitude: float


class NeighborPoint(pyda.BaseModel):
    map_point: MapPoint
    impact_score: float


class Location(pyda.BaseModel):
    city: str | None = None
    area: str | None = None
    address: str | None = None
    map_point: MapPoint | None = None

    @pyda.computed_field
    @property
    def h3_index(self) -> str | None:
        if self.map_point is None:
            return None

        return latlong_to_cell(
            self.map_point.latitude,
            self.map_point.longitude,
            9
        )


class PricePoint(pyda.BaseModel):
    date: date
    price: float


class Transaction(pyda.BaseModel):
    date: date
    price: float


class RealEstateMetrics(pyda.BaseModel):
    number_of_rooms: int | None = None
    number_of_bathrooms: int | None = None
    number_of_suites: int | None = None
    number_of_parking_spaces: int | None = None
    area_m2: float | None = None
    price_m2: float | None = None


class RePriceMetrics(pyda.BaseModel):
    asking_price: float | None = None
    listed_prices: list[PricePoint] = pyda.Field(default_factory=list)

    avm_price: float | None = None
    similarity_price: float | None = None
    neighboring_price: float | None = None
    suggested_price: float | None = None


class Predictions(pyda.BaseModel):
    expected_growth: float | None = None
    expected_dom: float | None = None


class FourMetric(pyda.BaseModel):
    luxury: float = pyda.Field(ge=0, le=5)
    leisure: float = pyda.Field(ge=0, le=5)
    location_: float = pyda.Field(ge=0, le=5)
    leverage: float = pyda.Field(ge=0, le=5)

class Kind(str, Enum):
    STREET_HOUSE = "casa de rua"
    CONDO_HOUSE = "casa de condomínio"
    APARTMENT = "apartamento"
    STUDIO = "studio"
    PENTHOUSE = "cobertura"
    SOBRADO = "sobrado"
    FARMHOUSE = "chácara"
    SITIO = "sítio"

class RealEstate(pyda.BaseModel):
    market_context: MarketContext | None = None
    exclusive: bool | None = None
    dom: float | None = None
    summary: str | None = None
    age: int | None = None
    on_sale_since: date | None = None
    last_sale: Transaction | None = None

    neighbor_points: list[NeighborPoint] = pyda.Field(default_factory=list)

    predictions: Predictions | None = pyda.Field(
        default=None,
        validation_alias=pyda.AliasChoices("predictions", "predictions")
    )

    four_metric: FourMetric | None = None
    re_price_metrics: RePriceMetrics | None = None
    kind: Kind | None = None
    location: Location | None = None
    real_estate_metrics: RealEstateMetrics | None = None

    @property
    def predictions_(self) -> Predictions | None:
        return self.predictions

    def get_neighboring_estates(self) -> list[RealEstate] | None:
        if not self.neighbor_points:
            return None

        from radar.support.support_functions import populate_real_estate_neighbors_gmaps

        return populate_real_estate_neighbors_gmaps(
            [self],
            api_key=os.getenv("GOOGLE_API_KEY")
        )
    

class SoldEstate(RealEstate):
    sale: Transaction
    practiced_commission: float | None = None


class Averages(pyda.BaseModel):
    average_dom: float | None = None
    average_discount: float | None = None
    average_price: float | None = None
    average_area_m2: float | None = None
    average_rooms: float | None = None
    average_bathrooms: float | None = None
    average_parking_spaces: float | None = None
    average_price_m2: float | None = None


class City(pyda.BaseModel):
    diversity_score: float | None = None
    name: str | None = None
    population: int | None = None
    available_estates: list[RealEstate] = pyda.Field(default_factory=list)
    averages: Averages | None = None


class Area(pyda.BaseModel):
    diversity_score: float | None = None
    name: str | None = None
    available_estates: list[RealEstate] = pyda.Field(default_factory=list)
    averages: Averages | None = None


class Portfolio(pyda.BaseModel):
    target_commission: float | None = None
    estates: list[RealEstate] = pyda.Field(default_factory=list)
    sold_estates: list[SoldEstate] = pyda.Field(default_factory=list)