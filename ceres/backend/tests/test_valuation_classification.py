import unittest

from backend.services.valuation_classification import classify_asking_price


class ValuationClassificationTests(unittest.TestCase):
    def test_classifies_only_against_calibrated_bounds(self):
        self.assertEqual(classify_asking_price(89, 100, 90, 110, uncertainty_status="calibrated"), "BELOW_ESTIMATED_RANGE")
        self.assertEqual(classify_asking_price(90, 100, 90, 110, uncertainty_status="calibrated"), "WITHIN_ESTIMATED_RANGE")
        self.assertEqual(classify_asking_price(110, 100, 90, 110, uncertainty_status="calibrated"), "WITHIN_ESTIMATED_RANGE")
        self.assertEqual(classify_asking_price(111, 100, 90, 110, uncertainty_status="calibrated"), "ABOVE_ESTIMATED_RANGE")

    def test_uncalibrated_or_invalid_interval_is_insufficient_confidence(self):
        for status, low, high in (("not_calibrated", 90, 110), ("calibrated", None, None), ("calibrated", 105, 110)):
            with self.subTest(status=status, low=low, high=high):
                self.assertEqual(classify_asking_price(100, 100, low, high, uncertainty_status=status), "INSUFFICIENT_CONFIDENCE")

    def test_missing_price_has_no_classification(self):
        self.assertIsNone(classify_asking_price(None, 100, 90, 110, uncertainty_status="calibrated"))
        self.assertIsNone(classify_asking_price(100, None, 90, 110, uncertainty_status="calibrated"))


if __name__ == "__main__":
    unittest.main()
