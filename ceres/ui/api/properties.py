from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ui.api.client import ApiClient, get_api_client
from ui.api.types import (
    Property,
    PropertyImportResult,
    PropertyPage,
    PropertyPayload,
    PropertySearchPage,
    PropertyValuation,
)


def get_properties(
    *,
    city: str | None = None,
    area: str | None = None,
    kind: str | None = None,
    limit: int = 25,
    offset: int = 0,
    client: ApiClient | None = None,
) -> PropertyPage:
    response = (client or get_api_client()).get(
        "properties",
        query={"city": city, "area": area, "kind": kind, "limit": limit, "offset": offset},
    )
    return PropertyPage.from_json(response)


def get_property(property_id: str, *, client: ApiClient | None = None) -> Property:
    return Property.from_json((client or get_api_client()).get(f"properties/{property_id}"))


def search_properties(
    query: str,
    *,
    city: str | None = None,
    area: str | None = None,
    kind: str | None = None,
    limit: int = 10,
    client: ApiClient | None = None,
) -> PropertySearchPage:
    response = (client or get_api_client()).post(
        "properties/search",
        body={"query": query, "city": city, "area": area, "kind": kind, "limit": limit},
    )
    return PropertySearchPage.from_json(response)


def create_property(
    property_payload: PropertyPayload,
    *,
    normalize_address: bool = False,
    client: ApiClient | None = None,
) -> Property:
    response = (client or get_api_client()).post(
        "properties",
        body={**dict(property_payload), "normalize_address": normalize_address},
    )
    return Property.from_json(response["property"])


def import_properties(
    workbook_path: str | Path,
    *,
    normalize_addresses: bool = True,
    client: ApiClient | None = None,
) -> PropertyImportResult:
    response = (client or get_api_client()).post_file(
        "properties/import",
        file_path=workbook_path,
        query={"normalize_addresses": normalize_addresses},
    )
    return PropertyImportResult.from_json(response)


def get_property_valuation(property_id: str, *, client: ApiClient | None = None) -> PropertyValuation:
    return PropertyValuation.from_json((client or get_api_client()).post(f"properties/{property_id}/valuation"))
