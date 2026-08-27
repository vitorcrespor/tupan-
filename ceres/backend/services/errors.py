from __future__ import annotations

from typing import Any


class ServiceError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details


class NotFoundError(ServiceError):
    status_code = 404
    code = "not_found"


class ConflictError(ServiceError):
    status_code = 409
    code = "conflict"


class UnavailableError(ServiceError):
    status_code = 503
    code = "dependency_unavailable"


class InsufficientDataError(ServiceError):
    status_code = 424
    code = "insufficient_data"


class DomainValidationError(ServiceError):
    status_code = 422
    code = "domain_validation_error"
