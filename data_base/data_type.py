from __future__ import annotations

from datetime import date
from enum import Enum
import pydantic as pyda
from h3 import latlong_to_cell
from typing import Optional

class kind(str, Enum):
    STREET_HOUSE = "casa de rua"
    CONDO_HOUSE = "casa de condomínio"
    APARTMENT = "apartamento"
    STUDIO = "studio"
    PENTHOUSE = "cobertura"
    SOBRADO = "sobrado"
    FARMHOUSE = "chácara"
    SITE = "sítio"
    
class map_point(pyda.BaseModel):
    def __init__(self, latitude: float, longitude: float, impact_score: float):
        self.latitude= latitude
        self.longitude= longitude
        self.impact_score= impact_score

class predictions(pyda.BaseModel):
    suggested_price: float | None = None
    expected_growth: float | None = None
    expected_dom: float | None = None

class location(pyda.BaseModel):
    city: str | None = None
    area: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    @pyda.computed_field
    def h3_index(self) -> str | None:
        if self.latitude is not None and self.longitude is not None:
            return latlong_to_cell(self.latitude, self.longitude, 9)
        return None
    
class PricePoint(pyda.BaseModel):
    date: date
    price: float
class real_estate_metrics(pyda.BaseModel):
    number_of_rooms: int | None = None
    number_of_bathrooms: int | None = None
    number_of_parking_spaces: int | None = None
    square_metrage: float | None = None
    square_meter_price: float | None = None
    
class re_price_metrics(pyda.BaseModel):
    price: float | None = None
    listed_prices: list[PricePoint] | None = None
    last_sale_price: float | None = None
    sale_price: float | None = None
    
class four_metric(pyda.BaseModel):
    luxury: float= pyda.Field(gt=0, lt=5)
    leisure: float= pyda.Field(gt=0, lt=5)
    location_: float= pyda.Field(gt=0, lt=5)
    leverage: float= pyda.Field(gt=0, lt=5)

    
class real_estate(pyda.BaseModel):
    exclusive: bool | None = None
    dom: float | None = None
    summary: str | None = None
    age: int | None = None
    last_sale_date: date | None = None
    on_sale_since: date | None = None
    
    neighboors: list[map_point] | None = None
    
    four_metric: four_metric | None = None
    re_price_metrics: re_price_metrics | None = None
    kind: kind | None = None
    location: location | None = None
    real_estate_metrics: real_estate_metrics | None = None

        
class sold_estate(real_estate):
   sold_price: float | None = None
   sale_date: date | None = None
   practiced_comission: float | None = None
    
class city(pyda.BaseModel):
        diversity_score: float | None = None
        name: str | None = None
        population: int | None = None
        available_estates: list[real_estate] | None = None
        averages: averages | None = None

class area(pyda.BaseModel):
        diversity_score: float | None = None
        name: str | None = None
        averages: averages | None = None


class averages(pyda.BaseModel):
    average_dom: float | None = None
    average_discount: float | None = None
    average_price: float | None = None
    average_area: float | None = None
    average_rooms: float | None = None
    average_bathrooms: float | None = None
    average_parking_spaces: float | None = None
    available_estates: list[real_estate] | None = None
    average_square_meter_price: float | None = None
    
    
class portfolio(pyda.BaseModel):
    tgt_comission: float | None = None
    real_estates: list[real_estate] | None = None
    sold_estates: list[sold_estate] | None = None
    estates: list[real_estate] | None = None