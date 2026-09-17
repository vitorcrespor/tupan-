"""Deterministic valuation presentation values, independent of model inference."""
from __future__ import annotations


def valuation_metrics(listed_price: float | None, estimated_price: float, area_m2: float | None) -> dict:
    """Signed gap uses estimated value as denominator; percentages are 0–100 units.

    Callers decide whether a price is a usable observation. This function never
    infers confidence, fills missing prices with zero, or changes model output.
    """
    difference = listed_price - estimated_price if listed_price is not None else None
    return {
        "difference": difference,
        "difference_percent": difference / estimated_price * 100 if difference is not None and estimated_price > 0 else None,
        "price_per_m2": listed_price / area_m2 if listed_price is not None and area_m2 else None,
        "estimated_price_per_m2": estimated_price / area_m2 if area_m2 else None,
    }
