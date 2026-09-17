"""Lineage transport and client trust boundary; no external database required."""
import json
import unittest
from datetime import datetime, timezone

from pydantic import ValidationError
from backend.api.schemas.estate import EstateCreateRequest, EstateUpdateRequest, EstateResponse
from backend.api.schemas.analysis import ComparableEstate, PortfolioPricePosition
from backend.repositories.tenant_data import _record


class EstimateProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.lineage = dict(source="recorded", recorded_at="2026-09-15T12:00:00Z",
                            model_version=None, input_version="estate-input-v1:abc",
                            status="inputs_changed")

    def test_desktop_cannot_claim_model_lineage(self):
        for schema in (EstateCreateRequest, EstateUpdateRequest):
            with self.subTest(schema=schema.__name__), self.assertRaises(ValidationError):
                schema.model_validate(dict(estimated_price=900000, estimate_provenance=self.lineage))

    def test_json_transport_preserves_stale_lineage_across_consumers(self):
        record = _record(dict(estimate_provenance=json.dumps(self.lineage)))
        now = datetime.now(timezone.utc)
        consumers = [
            EstateResponse(id="estate", created_at=now, updated_at=now, **record),
            ComparableEstate(id="estate", **record),
            PortfolioPricePosition(property_id="estate", **record),
        ]
        for consumer in consumers:
            self.assertEqual(consumer.estimate_provenance.status, "inputs_changed")
            self.assertIsNone(consumer.estimate_provenance.model_version)
            self.assertEqual(consumer.estimate_provenance.input_version, "estate-input-v1:abc")

    def test_legacy_estimate_does_not_acquire_invented_lineage(self):
        now = datetime.now(timezone.utc)
        estate = EstateResponse(id="estate", created_at=now, updated_at=now, estimated_price=900000)
        self.assertIsNone(estate.estimate_provenance)
