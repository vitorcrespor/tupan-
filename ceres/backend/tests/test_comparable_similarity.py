from __future__ import annotations

import unittest

from backend.services.comparable_similarity import (
    FEATURE_VERSION,
    cosine_similarity,
    rank_comparables,
)


def estate(id_: str, *, area=100, rooms=3, bathrooms=2, parking=1, distance=100):
    return {
        "id": id_, "area_m2": area, "rooms": rooms, "bathrooms": bathrooms,
        "parking_spaces": parking, "distance_meters": distance,
    }


class ComparableSimilarityTests(unittest.TestCase):
    def test_identical_structural_vectors_have_unit_cosine(self):
        self.assertEqual(cosine_similarity(estate("a"), estate("b")), 1.0)

    def test_ranking_uses_cosine_before_distance_and_is_deterministic(self):
        target = estate("target")
        candidates = [
            estate("far-identical", distance=900),
            estate("near-different", area=250, rooms=1, bathrooms=1, parking=0, distance=10),
        ]

        ranked, metadata = rank_comparables(target, candidates, limit=2)

        self.assertEqual([item["id"] for item in ranked], ["far-identical", "near-different"])
        self.assertEqual(ranked[0]["similarity_score"], 1.0)
        self.assertEqual(ranked[0]["similarity_feature_version"], FEATURE_VERSION)
        self.assertEqual(metadata["scored_count"], 2)

    def test_missing_features_are_not_treated_as_zero(self):
        target = estate("target")
        candidate = estate("candidate")
        candidate["bathrooms"] = None

        ranked, metadata = rank_comparables(target, [candidate], limit=1)

        self.assertIsNone(ranked[0]["similarity_score"])
        self.assertEqual(ranked[0]["similarity_status"], "candidate_incomplete_features")
        self.assertEqual(metadata["scored_count"], 0)

    def test_similarity_is_symmetric(self):
        left = estate("left", area=80, rooms=2, bathrooms=1, parking=0)
        right = estate("right", area=160, rooms=4, bathrooms=3, parking=2)
        self.assertEqual(cosine_similarity(left, right), cosine_similarity(right, left))


if __name__ == "__main__":
    unittest.main()
