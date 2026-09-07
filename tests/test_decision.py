"""Unit tests for deterministic affordability decision engine."""

from __future__ import annotations

import unittest
from src.decision import evaluate_affordability, rank_and_recommend


class TestDecision(unittest.TestCase):
    """Test suite for affordability and recommendation logic."""

    def test_evaluate_affordability_below_threshold(self):
        """EMI below 30% of income should be marked affordable."""
        # Income = 50,000, 30% threshold = 15,000, EMI = 10,746 -> Affordable
        result = evaluate_affordability(monthly_emi=10746.0, monthly_income=50000.0, threshold=0.30)
        self.assertTrue(result["is_affordable"])
        self.assertEqual(result["max_preferred_emi"], 15000.0)
        self.assertEqual(result["status"], "Affordable")

    def test_evaluate_affordability_above_threshold(self):
        """EMI above 30% of income should be marked unaffordable."""
        # Income = 50,000, 30% threshold = 15,000, EMI = 16,134 -> Unaffordable
        result = evaluate_affordability(monthly_emi=16134.0, monthly_income=50000.0, threshold=0.30)
        self.assertFalse(result["is_affordable"])
        self.assertEqual(result["max_preferred_emi"], 15000.0)
        self.assertEqual(result["status"], "Above Preferred Threshold")

    def test_evaluate_affordability_missing_or_invalid_income(self):
        """Missing or non-positive income must raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_affordability(monthly_emi=10000.0, monthly_income=None)
        with self.assertRaises(ValueError):
            evaluate_affordability(monthly_emi=10000.0, monthly_income=0)
        with self.assertRaises(ValueError):
            evaluate_affordability(monthly_emi=10000.0, monthly_income=-50000)

    def test_rank_and_recommend_chooses_affordable_option(self):
        """Should select the affordable option with lowest EMI."""
        options = [
            {"name": "Option A (3 Years)", "monthly_emi": 16134.0, "months": 36},
            {"name": "Option B (5 Years)", "monthly_emi": 10746.0, "months": 60},
        ]
        # Monthly income = 50,000 (cap = 15,000). Option B is affordable, Option A is not.
        rec = rank_and_recommend(options, monthly_income=50000.0, threshold=0.30)
        self.assertTrue(rec["is_recommended_affordable"])
    def test_evaluate_affordability_with_existing_obligations(self):
        """Existing obligations reduce effective disposable income for affordability cap."""
        # Income = 60,000, obligations = 10,000 -> effective income = 50,000 -> 30% cap = 15,000
        result = evaluate_affordability(
            monthly_emi=14000.0,
            monthly_income=60000.0,
            threshold=0.30,
            existing_obligations=10000.0,
        )
        self.assertTrue(result["is_affordable"])
        self.assertEqual(result["effective_income"], 50000.0)
        self.assertEqual(result["max_preferred_emi"], 15000.0)

        # EMI = 16,000 exceeds 15,000 cap
        result_unaffordable = evaluate_affordability(
            monthly_emi=16000.0,
            monthly_income=60000.0,
            threshold=0.30,
            existing_obligations=10000.0,
        )
        self.assertFalse(result_unaffordable["is_affordable"])


if __name__ == "__main__":
    unittest.main()
