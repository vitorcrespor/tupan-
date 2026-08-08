from __future__ import annotations

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
    

class real_estate_metrics(pyda.BaseModel):
    number_of_rooms: int | None = None
    number_of_bathrooms: int | None = None
    number_of_parking_spaces: int | None = None
    square_metrage: float | None = None
    square_meter_price: float | None = None
    
class re_price_metrics(pyda.BaseModel):
    price: float | None = None
    last_sale_price: float | None = None
    
class four_metric(pyda.BaseModel):
    luxury: float= pyda.Field(gt=0, lt=5)
    leisure: float= pyda.Field(gt=0, lt=5)
    location_: float= pyda.Field(gt=0, lt=5)
    leverage: float= pyda.Field(gt=0, lt=5)

    
class real_estate(pyda.BaseModel):
    def __init__(self, summary: str, neighboors: list[map_point], four_metric: four_metric,
                 re_price_metrics: re_price_metrics, kind: kind, location: location,
                 real_estate_metrics: real_estate_metrics, age: int, last_sale_date: str):
        self.summary= summary
        self.neighboors= neighboors
        self.four_metric= four_metric
        self.re_price_metrics= re_price_metrics
        self.kind= kind
        self.location= location
        self.real_estate_metrics= real_estate_metrics
        self.age= age
        self.last_sale_date= last_sale_date 
class city(pyda.BaseModel):
    def __init__(self, diversity_score: float, name: str, population: int, available_estates: list[real_estate],
                 averages: averages):
        self.diversity_score= diversity_score
        self.name= name
        self.population= population
        self.available_estates= available_estates        
        self.averages= averages         
class area(pyda.BaseModel):
    def __init__(self, diversity_score: float, name: str, averages: averages):
        self.diversity_score= diversity_score
        self.name= name        
        self.averages= averages
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
    
    

    