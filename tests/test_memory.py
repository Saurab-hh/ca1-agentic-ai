"""Unit tests for conversation session memory."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.memory import ConversationMemory


class TestMemory(unittest.TestCase):
    """Test suite for ConversationMemory storage and retrieval across turns."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mem_file = Path(self.temp_dir.name) / "test_memory.json"
        self.memory = ConversationMemory(self.mem_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_store_and_retrieve_income(self):
        """Income stored in memory must persist and be retrievable."""
        self.assertIsNone(self.memory.get_monthly_income())
        self.memory.set_monthly_income(60000.0)
        self.assertEqual(self.memory.get_monthly_income(), 60000.0)

        # Create a new memory instance pointing to the same file to verify persistence
        new_instance = ConversationMemory(self.mem_file)
        self.assertEqual(new_instance.get_monthly_income(), 60000.0)

    def test_store_and_retrieve_options(self):
        """Previously seen loan options should persist across turns."""
        options = [
            {"name": "Option A", "amount": 500000.0, "annual_rate": 10.0, "months": 36},
            {"name": "Option B", "amount": 500000.0, "annual_rate": 10.0, "months": 60},
        ]
        self.memory.set_loan_options(options) if hasattr(self.memory, "set_loan_options") else self.memory.set_previously_seen_options(options)
        retrieved = self.memory.get_previously_seen_options()
        self.assertEqual(len(retrieved), 2)
        self.assertEqual(retrieved[0]["months"], 36)

    def test_clear_memory(self):
        """Clear should reset stored income and options."""
        self.memory.set_monthly_income(50000.0)
        self.memory.clear()
        self.assertIsNone(self.memory.get_monthly_income())
        self.assertEqual(self.memory.get_previously_seen_options(), [])


if __name__ == "__main__":
    unittest.main()
