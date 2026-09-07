"""Unit tests for deterministic financial calculation tools."""

from __future__ import annotations

import unittest
from src.tools import compute_emi, compare_options


class TestTools(unittest.TestCase):
    """Test suite for compute_emi and compare_options tools."""

    def test_compute_emi_standard_loan(self):
        """Verify reducing balance EMI calculation for 5 Lakh at 10% for 36 months."""
        result = compute_emi(amount=500000, rate=10.0, months=36)
        self.assertEqual(result["loan_amount"], 500000.0)
        self.assertEqual(result["annual_rate"], 10.0)
        self.assertEqual(result["months"], 36)
        # Expected EMI: 500000 * 0.008333 * (1.008333)^36 / ((1.008333)^36 - 1) ≈ 16133.60
        self.assertAlmostEqual(result["monthly_emi"], 16133.60, delta=1.5)
        self.assertGreater(result["total_payment"], 500000.0)
        self.assertAlmostEqual(
            result["total_interest"], result["total_payment"] - 500000.0, places=2
        )

    def test_compute_emi_zero_interest(self):
        """Verify zero-interest loan calculates simple division."""
        result = compute_emi(amount=120000, rate=0.0, months=12)
        self.assertEqual(result["monthly_emi"], 10000.0)
        self.assertEqual(result["total_payment"], 120000.0)
        self.assertEqual(result["total_interest"], 0.0)

    def test_compute_emi_invalid_inputs(self):
        """Verify proper validation errors for invalid amounts, rates, or months."""
        # Non-positive amount
        with self.assertRaises(ValueError):
            compute_emi(amount=0, rate=10.0, months=12)
        with self.assertRaises(ValueError):
            compute_emi(amount=-50000, rate=10.0, months=12)

        # Negative interest rate
        with self.assertRaises(ValueError):
            compute_emi(amount=100000, rate=-1.0, months=12)

        # Non-positive months
        with self.assertRaises(ValueError):
            compute_emi(amount=100000, rate=10.0, months=0)
        with self.assertRaises(ValueError):
            compute_emi(amount=100000, rate=10.0, months=-12)

    def test_compare_options_from_tenures(self):
        """Verify comparison option generation from loan amount and tenures."""
        result = compare_options(amount=500000, tenures_years=[3, 5], rate=10.0)
        self.assertIn("options", result)
        options = result["options"]
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0]["months"], 36)
        self.assertEqual(options[1]["months"], 60)
        self.assertEqual(options[0]["amount"], 500000.0)
        self.assertEqual(options[1]["amount"], 500000.0)

    def test_compare_options_custom_list(self):
        """Verify comparison options standardizes custom input dictionaries."""
        custom = [
            {"name": "Bank A", "amount": 300000, "rate": 9.5, "months": 24},
            {"name": "Bank B", "amount": 300000, "rate": 10.5, "months": 36},
        ]
        result = compare_options(options_list=custom)
        self.assertEqual(len(result["options"]), 2)
        self.assertEqual(result["options"][0]["name"], "Bank A")
        self.assertEqual(result["options"][1]["annual_rate"], 10.5)


if __name__ == "__main__":
    unittest.main()
