"""Authoritative asking-price classification against calibrated AVM bounds."""

from __future__ import annotations

from typing import Literal


ValuationClass = Literal[
    "BELOW_ESTIMATED_RANGE",
    "WITHIN_ESTIMATED_RANGE",
    "ABOVE_ESTIMATED_RANGE",
    "INSUFFICIENT_CONFIDENCE",
]


def classify_asking_price(
    asking_price: float | None,
    estimated_price: float | None,
    lower_bound: float | None,
    upper_bound: float | None,
    *,
    uncertainty_status: str | None,
) -> ValuationClass | None:
    """Classify against model-calibrated bounds; never invent fixed margins.

    A missing asking price or central estimate means there is no price to
    classify. A valuation without a valid calibrated interval is explicitly
    low-confidence rather than being compared against an arbitrary percentage.
    """
    if not _positive(asking_price) or not _positive(estimated_price):
        return None
    if (
        uncertainty_status != "calibrated"
        or not _positive(lower_bound)
        or not _positive(upper_bound)
        or lower_bound > estimated_price
        or upper_bound < estimated_price
        or lower_bound > upper_bound
    ):
        return "INSUFFICIENT_CONFIDENCE"
    if asking_price < lower_bound:
        return "BELOW_ESTIMATED_RANGE"
    if asking_price > upper_bound:
        return "ABOVE_ESTIMATED_RANGE"
    return "WITHIN_ESTIMATED_RANGE"


def _positive(value: float | None) -> bool:
    return value is not None and value > 0
