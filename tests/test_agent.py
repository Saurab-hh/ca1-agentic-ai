"""Unit tests for the LoanAdvisorAgent workflow, multi-turn memory, and trace."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.agent import LoanAdvisorAgent
from src.memory import ConversationMemory


class TestLoanAdvisorAgent(unittest.TestCase):
    """Test suite for LoanAdvisorAgent plan-act loop and multi-turn workflows."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mem_file = Path(self.temp_dir.name) / "test_agent_memory.json"
        self.memory = ConversationMemory(self.mem_file)
        self.agent = LoanAdvisorAgent(memory=self.memory, use_llm_if_available=False)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_example_1_normal_comparison(self):
        """Test Example 1: I earn ₹50,000 per month. Compare a ₹5 lakh loan for 3 years and 5 years."""
        result = self.agent.run(
            "I earn ₹50,000 per month. I need a ₹5 lakh loan. Compare a 3-year and 5-year option."
        )
        self.assertIn("Recommendation", result["answer"])
        self.assertIn("trace", result)
        self.assertIn("[TOOL CALL]\ncompare_options()", result["trace"])
        self.assertIn("[TOOL CALL]\ncompute_emi", result["trace"])
        self.assertIn("[AFFORDABILITY EVALUATION]", result["trace"])

        # Check that 5-year option was recommended because 3-year exceeds 30% cap (₹15,000)
        self.assertEqual(result["recommended_option"]["months"], 60)
        self.assertTrue(result["affordability"]["is_affordable"])
        self.assertEqual(result["memory"]["monthly_income"], 50000.0)

    def test_example_2_multi_turn_memory(self):
        """Test Example 2: Memory across turns."""
        # Turn 1: State income only
        res1 = self.agent.run("My monthly income is ₹60,000.")
        self.assertEqual(self.memory.get_monthly_income(), 60000.0)

        # Turn 2: Ask for loan comparison without restating income
        res2 = self.agent.run("Compare a ₹6 lakh loan for 3 years and 5 years.")
        self.assertIn("Recommendation", res2["answer"])
        self.assertEqual(res2["memory"]["monthly_income"], 60000.0)
        self.assertIn("[MEMORY READ]", res2["trace"])
        self.assertIn("₹60,000.00", res2["trace"])

        # Turn 3: Follow up referencing earlier options
        res3 = self.agent.run("What if I choose the longer tenure?")
        self.assertIn("Recommendation", res3["answer"])
        self.assertEqual(res3["recommended_option"]["months"], 60)

    def test_example_3_unaffordable_loan(self):
        """Test Example 3: Low income high loan request should reject under 30% rule."""
        result = self.agent.run(
            "My income is ₹25,000 and I want a ₹10 lakh loan for 2 years."
        )
        self.assertIn("Alert: No affordable option", result["answer"])
        self.assertFalse(result["affordability"]["is_affordable"])
        self.assertIn("[AFFORDABILITY EVALUATION]", result["trace"])

    def test_honest_failure_missing_income(self):
        """If income is not known in request or memory, refuses to claim affordability."""
        fresh_agent = LoanAdvisorAgent(
            memory_path=Path(self.temp_dir.name) / "empty_mem.json",
            use_llm_if_available=False,
        )
        result = fresh_agent.run("Compare a ₹5 lakh loan for 3 years and 5 years.")
    def test_existing_obligations_in_agent_flow(self):
        """Test agent accounts for existing monthly obligations when computing affordability cap."""
        # Income = 60,000, existing obligations = 20,000 -> effective = 40,000 -> 30% cap = 12,000
        # 5 Lakh loan for 3 yrs (EMI ~16,134) vs 5 yrs (EMI ~10,624)
        result = self.agent.run(
            "I earn ₹60,000 per month and already pay ₹20,000 in other EMIs. Compare a ₹5 lakh loan for 3 years and 5 years."
        )
        self.assertEqual(self.memory.get_existing_obligations(), 20000.0)
        self.assertIn("Recommendation", result["answer"])
        self.assertEqual(result["recommended_option"]["months"], 60)
        self.assertEqual(result["affordability"]["max_preferred_emi"], 12000.0)

    def test_direct_months_tenure_in_agent_flow(self):
        """Test agent correctly understands tenures expressed in months."""
        result = self.agent.run(
            "My income is ₹50,000. Compare a ₹4 lakh loan for 24 months and 48 months at 10%."
        )
        self.assertIn("Recommendation", result["answer"])
        self.assertEqual(len(result["all_options"]), 2)
        months_set = {opt["months"] for opt in result["all_options"]}
        self.assertEqual(months_set, {24, 48})

    def test_out_of_scope_guardrail(self):
        """Test agent rejects non-financial out-of-scope queries with domain guardrail."""
        result = self.agent.run("How to make a chocolate cake recipe at home?")
        self.assertFalse(result.get("is_in_domain", True))
        self.assertIn("Out of Scope / Domain Guardrail", result["answer"])
        self.assertIn("[GUARDRAIL / SCOPE CHECK]", result["trace"])


if __name__ == "__main__":
    unittest.main()

