"""Adapt authorized estate facts to the existing quality policy, not confidence."""
from datetime import datetime, timezone
from typing import Any, Mapping

from train.valuation_uncertainty import assess_data_quality


def estate_data_quality(estate: Mapping[str, Any]) -> dict[str, Any]:
    attributes = estate.get('attributes') or {}
    lineage = attributes.get('feature_lineage') or {}
    if not isinstance(lineage, dict):
        lineage = {}
    features = {key: estate.get(key) for key in
                ('property_type', 'city', 'latitude', 'longitude', 'rooms', 'bathrooms', 'parking_spaces')}
    features['usable_area_m2'] = estate.get('area_m2')
    features['condition'] = attributes.get('condition')
    return assess_data_quality(features, lineage, datetime.now(timezone.utc))
