from enum import Enum
import pydantic as pyda
class kind(str, Enum):
    STREET_HOUSE = "casa de rua"
    CONDO_HOUSE = "casa de condomínio"
    APARTMENT = "apartamento"
    STUDIO = "studio"
    PENTHOUSE = "cobertura"
    SOBRADO = "sobrado"
    FARMHOUSE = "chácara"
    SITE = "sítio"
    

class predictions(pyda.BaseModel):
    suggested_price: float | None = None
    expected_growth: float | None = None
    expected_dom: float | None = None

class location(pyda.BaseModel):
    h3_index: str | None = None
    city: str | None = None
    area: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    

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
    location: float= pyda.Field(gt=0, lt=5)
    leverage: float= pyda.Field(gt=0, lt=5)

    
class real_estate(pyda.BaseModel):
    summary: str | None = None
    
    four_metric: four_metric
    re_price_metrics: re_price_metrics
    kind: kind
    location: location
    real_estate_metrics: real_estate_metrics
    
    age: int | None = None
    last_sale_date: str | None = None
    
class city(pyda.BaseModel):
    name: str | None = None
    population: int | None = None
    averages: averages
class area(pyda.BaseModel):
    name: str | None = None
    averages: averages
    
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
    
    

    