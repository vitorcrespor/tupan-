from __future__ import annotations

import json
import math
from hashlib import sha256
from typing import Any

from backend.api.schemas.property import (
    AreaCreateRequest,
    AreaResponse,
    CityCreateRequest,
    CityResponse,
    PropertyCreateRequest,
    PropertyCreateResponse,
    PropertyImportResponse,
    PropertyPredictionResponse,
    PropertyPricingResponse,
    PropertyResponse,
    PropertySearchRequest,
    PropertySearchResult,
    PropertyValuationResponse,
)
from backend.services.errors import ConflictError, DomainValidationError, NotFoundError, UnavailableError
from backend.services.serialization import json_safe, model_payload


class PropertyService:
    """Adapter around existing Pydantic, Chroma ingestion, and pricing functions."""

    def _modules(self):
        try:
            from radar import config
            from radar.data_base import data_type as data
        except Exception as exc:
            raise UnavailableError("The property backend could not be initialized.") from exc
        if not hasattr(config, "collection"):
            raise UnavailableError("The configured backend does not expose a Chroma collection.")
        return config, data

    @staticmethod
    def _ingestion_module():
        """Legacy import used only by endpoints that still depend on it."""
        try:
            from radar.data_base import ingestion
        except Exception as exc:
            raise UnavailableError("The property ingestion backend could not be initialized.") from exc
        return ingestion

    def _properties_with_ids(self) -> list[tuple[str, Any]]:
        config, data = self._modules()
        try:
            result = config.collection.get(where={"record_type": "property"}, include=["documents"])
        except Exception as exc:
            raise UnavailableError("The property collection could not be queried.") from exc

        records: list[tuple[str, Any]] = []
        for record_id, document in zip(result.get("ids", []) or [], result.get("documents", []) or []):
            property_ = self._property_from_document(document, data)
            if property_ is not None:
                records.append((str(record_id), property_))
        return records

    @staticmethod
    def _property_from_document(document: Any, data: Any):
        try:
            payload = json.loads(str(document).rsplit("\n\n", 1)[-1])
            if "preictions" in payload and "predictions" not in payload:
                payload["predictions"] = payload["preictions"]
            return data.real_estate.model_validate(payload)
        except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def list(self, *, city: str | None, area: str | None, kind: str | None, limit: int, offset: int) -> tuple[list[PropertyResponse], int]:
        records = self._properties_with_ids()
        filtered = [
            (record_id, property_)
            for record_id, property_ in records
            if self._matches(property_, city=city, area=area, kind=kind)
        ]
        return [self.to_response(record_id, property_) for record_id, property_ in filtered[offset : offset + limit]], len(filtered)

    def get_domain(self, property_id: str):
        for record_id, property_ in self._properties_with_ids():
            if record_id == property_id:
                return property_
        raise NotFoundError("Property not found.", details={"property_id": property_id})

    def get(self, property_id: str) -> PropertyResponse:
        return self.to_response(property_id, self.get_domain(property_id))

    def create(self, request: PropertyCreateRequest) -> PropertyCreateResponse:
        config, data = self._modules()
        if request.normalize_address:
            raise UnavailableError("Address normalization is unavailable in the current ingestion runtime.")
        try:
            payload = model_payload(request)
            payload.pop("normalize_address", None)
            if "predictions" in payload:
                payload["preictions"] = payload["predictions"]
            property_ = data.real_estate.model_validate(payload)
        except ValueError as exc:
            raise DomainValidationError("The property is invalid for the existing domain model.", details={"reason": str(exc)}) from exc
        record_id = self._record_id(property_)
        try:
            existing = config.collection.get(ids=[record_id], include=[])
            if existing.get("ids"):
                raise ConflictError("A property with this address already exists.", details={"property_id": record_id})
            config.collection.add(
                ids=[record_id],
                documents=[self._property_document(property_)],
                metadatas=[self._property_metadata(property_)],
            )
        except ConflictError:
            raise
        except Exception as exc:
            raise UnavailableError("The property could not be persisted.") from exc
        return PropertyCreateResponse(id=record_id, property=self.to_response(record_id, property_), duplicate=False)

    def search(self, request: PropertySearchRequest) -> list[PropertySearchResult]:
        config, data = self._modules()
        filters = {key: value for key, value in {"city": request.city, "area": request.area, "kind": request.kind}.items() if value is not None}
        try:
            results = config.collection.query(
                query_texts=[request.query],
                n_results=request.limit,
                where=self._chroma_where({"record_type": "property", **filters}),
                include=["documents", "metadatas", "distances"],
            )
        except ValueError as exc:
            raise DomainValidationError(str(exc)) from exc
        except Exception as exc:
            raise UnavailableError("The semantic search dependency is unavailable.") from exc

        response: list[PropertySearchResult] = []
        ids = (results.get("ids") or [[]])[0]
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]
        for record_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            property_ = self._property_from_document(document, data)
            metadata = json_safe(metadata or {})
            response.append(
                PropertySearchResult(
                    id=str(record_id),
                    property=self.to_response(str(record_id), property_) if property_ else None,
                    metadata=metadata,
                    document=document,
                    distance=float(distance) if distance is not None else None,
                )
            )
        return response

    @staticmethod
    def _record_id(property_: Any) -> str:
        """Stable Chroma identity based on the persisted real-estate address."""
        location = getattr(property_, "location", None)
        address = getattr(location, "address", None)
        if not address:
            raise ValueError("A property address is required for persistence.")
        return f"property-{sha256(str(address).strip().lower().encode('utf-8')).hexdigest()}"

    @staticmethod
    def _property_document(property_: Any) -> str:
        location = getattr(property_, "location", None)
        address = getattr(location, "address", None) or "Imóvel sem endereço"
        summary = getattr(property_, "summary", None) or address
        payload = property_.model_dump(mode="json", exclude_none=True, exclude_computed_fields=True)
        return f"{summary}\n\n{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"

    @staticmethod
    def _property_metadata(property_: Any) -> dict[str, str | int | float | bool]:
        location = getattr(property_, "location", None)
        kind = getattr(property_, "kind", None)
        metadata: dict[str, str | int | float | bool] = {"record_type": "property"}
        for key, value in {
            "city": getattr(location, "city", None),
            "area": getattr(location, "area", None),
            "kind": getattr(kind, "value", kind),
            "address": getattr(location, "address", None),
        }.items():
            if value is not None:
                metadata[key] = str(value)
        return metadata

    @staticmethod
    def _chroma_where(filters: dict[str, str]) -> dict[str, object]:
        clauses = [{key: value} for key, value in filters.items()]
        return clauses[0] if len(clauses) == 1 else {"$and": clauses}

    def import_workbook(self, path: str, *, normalize_addresses: bool) -> PropertyImportResponse:
        _, data = self._modules()
        try:
            from radar.data_base import ingestion
        except Exception as exc:
            raise UnavailableError("The property workbook importer is unavailable.") from exc
        if not hasattr(ingestion, "import_excel"):
            raise UnavailableError("The configured ingestion backend does not support workbook import.")
        try:
            outcome = ingestion.import_excel(path, data.real_estate, normalize_addresses=normalize_addresses)
        except (ValueError, FileNotFoundError) as exc:
            raise DomainValidationError("The workbook could not be validated.", details={"reason": str(exc)}) from exc
        except Exception as exc:
            raise UnavailableError("The workbook import backend is unavailable.") from exc
        return PropertyImportResponse(
            successful_records=json_safe(outcome.successful_records),
            invalid_records=json_safe(outcome.invalid_records),
            duplicates=json_safe(outcome.duplicates),
            errors=json_safe(outcome.errors),
        )

    def valuation(self, property_id: str) -> PropertyValuationResponse:
        property_ = self.get_domain(property_id)
        try:
            from train import analytics
            from train.avm import (
                FeaturePreparationError,
                ModelArtifactIncompatibleError,
                ModelArtifactMissingError,
            )

            current_price = self._current_price(property_)
            suggested = float(analytics.price_suggestion(property_))
        except ModelArtifactMissingError as exc:
            raise UnavailableError(
                "No trained AVM artifact is available for property valuation.",
                details={"reason": "model_artifact_missing"},
            ) from exc
        except ModelArtifactIncompatibleError as exc:
            raise UnavailableError(
                "The deployed AVM artifact is incompatible with the valuation service.",
                details={"reason": "model_artifact_incompatible"},
            ) from exc
        except FeaturePreparationError as exc:
            raise DomainValidationError(
                "This property has incomplete or incompatible AVM features.",
                details={"reason": str(exc)},
            ) from exc
        except ValueError as exc:
            raise DomainValidationError(
                "This property has incomplete pricing data for valuation.",
                details={"reason": str(exc)},
            ) from exc
        except Exception as exc:
            raise UnavailableError("The valuation service is unavailable.") from exc

        area_m2 = self._area_m2(property_)
        difference = current_price - suggested
        return PropertyValuationResponse(
            property_id=property_id,
            current_price=current_price,
            suggested_price=suggested,
            deviation=difference / suggested,
            listed_price=current_price,
            estimated_price=suggested,
            difference=difference,
            difference_percent=(difference / suggested) * 100,
            price_per_m2=current_price / area_m2 if area_m2 is not None else None,
            estimated_price_per_m2=suggested / area_m2 if area_m2 is not None else None,
            model_available=True,
        )

    @staticmethod
    def _current_price(property_: Any) -> float:
        """Extract the persisted asking price without duplicating AVM logic."""
        pricing = getattr(property_, "re_price_metrics", None)
        if pricing is None:
            raise ValueError("The property needs price metrics for valuation.")
        asking_price = getattr(pricing, "price", None)
        if asking_price is not None:
            return PropertyService._positive_price(asking_price)
        listed_prices = getattr(pricing, "listed_prices", None) or []
        if listed_prices:
            last_listed = getattr(listed_prices[-1], "price", None)
            if last_listed is not None:
                return PropertyService._positive_price(last_listed)
        last_sale_price = getattr(pricing, "last_sale_price", None)
        if last_sale_price is not None:
            return PropertyService._positive_price(last_sale_price)
        raise ValueError("The property needs re_price_metrics.price or a listed price.")

    @staticmethod
    def _positive_price(value: Any) -> float:
        price = float(value)
        if not math.isfinite(price) or price <= 0:
            raise ValueError("The property price must be a finite positive number.")
        return price

    @staticmethod
    def _area_m2(property_: Any) -> float | None:
        metrics = getattr(property_, "real_estate_metrics", None)
        area = getattr(metrics, "square_metrage", None)
        try:
            area_m2 = float(area)
        except (TypeError, ValueError):
            return None
        return area_m2 if math.isfinite(area_m2) and area_m2 > 0 else None

    def create_city(self, request: CityCreateRequest) -> CityResponse:
        config, data = self._modules()
        try:
            city = data.city.model_validate(model_payload(request))
            record_id = self._persist_named_entity(config, "city", city)
        except ConflictError:
            raise
        except ValueError as exc:
            raise DomainValidationError("The city is invalid.", details={"reason": str(exc)}) from exc
        except Exception as exc:
            raise UnavailableError("The city could not be persisted.") from exc
        return CityResponse(id=record_id, **request.model_dump())

    def create_area(self, request: AreaCreateRequest) -> AreaResponse:
        config, data = self._modules()
        try:
            area = data.area.model_validate(model_payload(request))
            record_id = self._persist_named_entity(config, "area", area)
        except ConflictError:
            raise
        except ValueError as exc:
            raise DomainValidationError("The area is invalid.", details={"reason": str(exc)}) from exc
        except Exception as exc:
            raise UnavailableError("The area could not be persisted.") from exc
        return AreaResponse(id=record_id, **request.model_dump())

    @staticmethod
    def _persist_named_entity(config: Any, record_type: str, entity: Any) -> str:
        """Persist a city or area through the configured Chroma collection.

        The former LlamaIndex ingestion module is incompatible with the
        current domain models and cannot initialize.  Cities and areas need
        only durable identity records here, so use the same existing Chroma
        store as property persistence instead of recreating an ingestion or
        analytics implementation.
        """
        name = str(getattr(entity, "name", "") or "").strip()
        if not name:
            raise ValueError(f"A {record_type} name is required for persistence.")
        record_id = f"{record_type}-{sha256(name.casefold().encode('utf-8')).hexdigest()}"
        try:
            existing = config.collection.get(ids=[record_id], include=[])
            if existing.get("ids"):
                raise ConflictError(
                    f"A {record_type} with this name already exists.",
                    details={f"{record_type}_id": record_id},
                )
            payload = entity.model_dump(mode="json", exclude_none=True)
            config.collection.add(
                ids=[record_id],
                documents=[f"{name}\n\n{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"],
                metadatas=[{"record_type": record_type, "name": name}],
            )
        except ConflictError:
            raise
        except Exception as exc:
            raise UnavailableError(f"The {record_type} could not be persisted.") from exc
        return record_id

    @staticmethod
    def _matches(property_: Any, *, city: str | None, area: str | None, kind: str | None) -> bool:
        location = getattr(property_, "location", None)
        property_kind = getattr(property_, "kind", None)
        kind_value = getattr(property_kind, "value", property_kind)
        return (
            (city is None or getattr(location, "city", None) == city)
            and (area is None or getattr(location, "area", None) == area)
            and (kind is None or kind_value == kind)
        )

    @staticmethod
    def to_response(record_id: str, property_: Any) -> PropertyResponse:
        location = getattr(property_, "location", None)
        metrics = getattr(property_, "real_estate_metrics", None)
        pricing = getattr(property_, "re_price_metrics", None)
        predictions = getattr(property_, "predictions", None)
        if predictions is None:  # preserve legacy persisted typo while keeping it out of API JSON
            predictions = getattr(property_, "preictions", None)
        kind = getattr(property_, "kind", None)
        listed_prices = [
            {"date": point.date, "price": float(point.price)}
            for point in (getattr(pricing, "listed_prices", None) or [])
        ]
        return PropertyResponse(
            id=record_id,
            kind=getattr(kind, "value", kind),
            exclusive=getattr(property_, "exclusive", None),
            dom_days=getattr(property_, "dom", None),
            age=getattr(property_, "age", None),
            last_sale_date=getattr(property_, "last_sale_date", None),
            on_sale_since=getattr(property_, "on_sale_since", None),
            summary=getattr(property_, "summary", None),
            location=(
                {
                    "city": getattr(location, "city", None),
                    "area": getattr(location, "area", None),
                    "address": getattr(location, "address", None),
                    "latitude": getattr(location, "latitude", None),
                    "longitude": getattr(location, "longitude", None),
                    "h3_index": getattr(location, "h3_index", None),
                }
                if location else None
            ),
            metrics=(
                {
                    "rooms": getattr(metrics, "number_of_rooms", None),
                    "bathrooms": getattr(metrics, "number_of_bathrooms", None),
                    "parking_spaces": getattr(metrics, "number_of_parking_spaces", None),
                    "area_m2": getattr(metrics, "square_metrage", None),
                    "price_per_m2": getattr(metrics, "square_meter_price", None),
                }
                if metrics else None
            ),
            pricing=(
                PropertyPricingResponse(
                    asking_price=getattr(pricing, "price", None),
                    last_sale_price=getattr(pricing, "last_sale_price", None),
                    sale_price=getattr(pricing, "sale_price", None),
                    listed_prices=listed_prices,
                ) if pricing else None
            ),
            predictions=(
                PropertyPredictionResponse(
                    suggested_price=getattr(predictions, "suggested_price", None),
                    expected_growth=getattr(predictions, "expected_growth", None),
                    expected_dom_days=getattr(predictions, "expected_dom", None),
                ) if predictions else None
            ),
            profile=json_safe(getattr(property_, "four_metric", None)) if getattr(property_, "four_metric", None) else None,
        )
