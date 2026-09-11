from enum import Enum
from ceres.radar.data_base.data_type import RealEstate
from typing import Literal
from pydantic import BaseModel
import pydantic as pyda

class Kind(str, Enum):
    STREET_HOUSE = "casa de rua"
    CONDO_HOUSE = "casa de condomínio"
    APARTMENT = "apartamento"
    STUDIO = "studio"
    PENTHOUSE = "cobertura"
    SOBRADO = "sobrado"
    FARMHOUSE = "chácara"
    SITIO = "sítio"

class House(RealEstate):
    lot_area: float | None = None
    floors: int | None = None
    frontage: float | None = None
    backyard_area: float | None = None
    garden_area: float | None = None

    pool: bool | None = None
    barbecue_area: bool | None = None
    service_area: bool | None = None
    service_room: bool | None = None
    gated: bool | None = None
    furnished: bool | None = None    

class CondominiumUnit(RealEstate):
    condominium_fee: float | None = None
    floor: int | None = None
    building_floors: int | None = None
    units_per_floor: int | None = None
    elevators: int | None = None
    balcony_area: float | None = None
    doorman: bool | None = None
    security_24h: bool | None = None
    gym: bool | None = None
    shared_pool: bool | None = None
    playground: bool | None = None
    party_room: bool | None = None
    furnished: bool | None = None
    
class RuralEstate(RealEstate):
    land_area: float | None = None
    cultivated_area: float | None = None
    preserved_area: float | None = None
    water_source: bool | None = None
    well: bool | None = None
    septic_system: bool | None = None
    main_house_area: float | None = None
    guest_house: bool | None = None
    caretaker_house: bool | None = None
    pool: bool | None = None
    internal_road: bool | None = None
    paved_access: bool | None = None
    internet_available: bool | None = None
    electricity_available: bool | None = None

class StreetHouse(House):
    kind: Literal[Kind.STREET_HOUSE] = Kind.STREET_HOUSE
    detached: bool | None = None
    corner_lot: bool | None = None
    street_frontage: float | None = None
    side_access: bool | None = None

    wall_or_fence: bool | None = None
    electric_gate: bool | None = None
    
class CondoHouse(House):
    kind: Literal[Kind.CONDO_HOUSE] = Kind.CONDO_HOUSE
    condominium_fee: float | None = None
    gated_community: bool | None = None
    security_24h: bool | None = None
    controlled_access: bool | None = None
    shared_pool: bool | None = None
    gym: bool | None = None
    sports_court: bool | None = None
    playground: bool | None = None
    party_room: bool | None = None
    condo_lot_area: float | None = None

class Apartment(CondominiumUnit):
    kind: Literal[Kind.APARTMENT] = Kind.APARTMENT
    service_elevator: bool | None = None
    private_elevator: bool | None = None
    
    
class Studio(CondominiumUnit):
    kind: Literal[Kind.STUDIO] = Kind.STUDIO
    integrated_layout: bool = True
    sleeping_area: float | None = None
    kitchenette: bool | None = None
    separate_bedroom: bool | None = None
    laundry_in_unit: bool | None = None
    coworking: bool | None = None
    shared_laundry: bool | None = None
    
class Penthouse(Apartment):
    kind: Literal[Kind.PENTHOUSE] = Kind.PENTHOUSE

    terrace_area: float | None = None
    rooftop_area: float | None = None
    private_pool: bool | None = None
    private_barbecue: bool | None = None
    duplex: bool | None = None
    triplex: bool | None = None
    private_elevator_access: bool | None = None
    panoramic_view: bool | None = None
    
    
class Farmhouse(RuralEstate):
    kind: Literal[Kind.FARMHOUSE] = Kind.FARMHOUSE

    leisure_area: float | None = None
    barbecue_area: bool | None = None
    sports_court: bool | None = None
    orchard: bool | None = None
    vegetable_garden: bool | None = None
    lake: bool | None = None
    event_area: bool | None = None
    distance_to_urban_center_km: float | None = None
    
class Sitio(RuralEstate):
    kind: Literal[Kind.SITIO] = Kind.SITIO

    productive_area: float | None = None
    pasture_area: float | None = None
    crops: list[str] = pyda.Field(default_factory=list)
    livestock_capacity: int | None = None
    barn_area: float | None = None
    stable_area: float | None = None
    machinery_shed_area: float | None = None
    river: bool | None = None
    lake: bool | None = None
    rural_registration: str | None = None
    distance_to_urban_center_km: float | None = None