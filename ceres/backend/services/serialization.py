from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from enum import Enum
from typing import Any


def json_safe(value: Any) -> Any:
    """Convert internal Pydantic, NumPy, Pandas, and mapping values to JSON primitives."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return json_safe(value.value)
    if hasattr(value, "model_dump"):
        return json_safe(value.model_dump(mode="json", exclude_none=True))
    if hasattr(value, "item") and callable(value.item):
        try:
            return json_safe(value.item())
        except (TypeError, ValueError):
            pass
    if hasattr(value, "tolist") and callable(value.tolist):
        try:
            return json_safe(value.tolist())
        except (TypeError, ValueError):
            pass
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return json_safe(value.to_dict())
        except (TypeError, ValueError):
            pass
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return [json_safe(item) for item in value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [json_safe(item) for item in value]
    return str(value)


def model_payload(model: Any) -> dict[str, Any]:
    """Return JSON-compatible input accepted by the existing Pydantic domain model."""
    if hasattr(model, "model_dump"):
        return json_safe(model.model_dump(mode="json", exclude_none=True))
    if isinstance(model, Mapping):
        return json_safe(model)
    raise TypeError(f"Expected a Pydantic model or mapping, received {type(model).__name__}.")
