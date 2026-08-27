from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any


class Pagination(BaseModel):
    limit: Optional[int] = Field(100, ge=1, le=1000)


class PropertyIn(BaseModel):
    id: Optional[str]
    title: Optional[str]
    address: Optional[str]
    city: Optional[str]
    neighborhood: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    price: Optional[int]
    price_per_m2: Optional[int]


class PropertyOut(PropertyIn):
    created_date: Optional[Any]
    updated_date: Optional[Any]


class BulkItems(BaseModel):
    items: List[PropertyIn]


class FilterRequest(BaseModel):
    query: Optional[dict] = {}
    limit: Optional[int] = 100


class MarketRegionIn(BaseModel):
    id: Optional[str]
    name: Optional[str]
    city: Optional[str]
    average_price_per_m2: Optional[int]
    market_heat: Optional[int]
    demand_score: Optional[int]
    liquidity_score: Optional[int]


class MarketRegionOut(MarketRegionIn):
    created_date: Optional[Any]


class UserIn(BaseModel):
    id: Optional[str]
    full_name: Optional[str]
    email: EmailStr
    password: Optional[str]
    role: Optional[str] = 'user'


class UserOut(BaseModel):
    id: str
    full_name: Optional[str]
    email: EmailStr
    role: Optional[str]
    created_date: Optional[Any]


class SavedSearchIn(BaseModel):
    id: Optional[str]
    user_id: Optional[str]
    name: Optional[str]
    filters: Optional[dict]


class SavedSearchOut(SavedSearchIn):
    created_date: Optional[Any]


class PropertyNoteIn(BaseModel):
    id: Optional[str]
    property_id: Optional[str]
    user_id: Optional[str]
    note: Optional[str]


class PropertyNoteOut(PropertyNoteIn):
    created_date: Optional[Any]


class DistrictBoundaryIn(BaseModel):
    id: Optional[str]
    name: Optional[str]
    geojson: Optional[dict]


class DistrictBoundaryOut(DistrictBoundaryIn):
    created_date: Optional[Any]


class EmbeddingIn(BaseModel):
    entity_type: Optional[str]
    entity_id: Optional[str]
    vector: List[float]
    text: Optional[str]


class EmbeddingSearchIn(BaseModel):
    vector: List[float]
    top_k: Optional[int] = Field(10, ge=1, le=100)
