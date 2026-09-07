"""Conversation memory management for the EMI and Loan Advisor session."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DEFAULT_MEMORY_FILE


class ConversationMemory:
    """Manages session memory across multiple conversation turns."""

    def __init__(self, memory_path: str | Path | None = None):
        self.memory_path = Path(memory_path) if memory_path else DEFAULT_MEMORY_FILE
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Create storage directory if not present."""
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.memory_path.exists():
            self._save_raw({"monthly_income": None, "previously_seen_options": []})

    def _read_raw(self) -> dict[str, Any]:
        """Read state from JSON file."""
        if not self.memory_path.exists():
            return {"monthly_income": None, "previously_seen_options": []}
        try:
            return json.loads(self.memory_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"monthly_income": None, "previously_seen_options": []}

    def _save_raw(self, state: dict[str, Any]) -> None:
        """Write state to JSON file."""
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def get_monthly_income(self) -> float | None:
        """Retrieve stored monthly income."""
        state = self._read_raw()
        income = state.get("monthly_income")
        return float(income) if income is not None else None

    def set_monthly_income(self, income: float) -> None:
        """Store or update user's monthly income."""
        if income <= 0:
            raise ValueError("Monthly income must be positive.")
        state = self._read_raw()
        state["monthly_income"] = float(income)
        self._save_raw(state)

    def get_previously_seen_options(self) -> list[dict[str, Any]]:
        """Retrieve previously seen loan options."""
        state = self._read_raw()
        return state.get("previously_seen_options", [])

    def set_previously_seen_options(self, options: list[dict[str, Any]]) -> None:
        """Store latest loan options seen by the user."""
        state = self._read_raw()
        state["previously_seen_options"] = options
        self._save_raw(state)

    def get_existing_obligations(self) -> float:
        """Retrieve stored existing monthly debt obligations."""
        state = self._read_raw()
        return float(state.get("existing_obligations", 0.0) or 0.0)

    def set_existing_obligations(self, obligations: float) -> None:
        """Store or update user's existing monthly debt obligations."""
        if obligations < 0:
            raise ValueError("Existing obligations must be non-negative.")
        state = self._read_raw()
        state["existing_obligations"] = float(obligations)
        self._save_raw(state)

    def clear(self) -> None:
        """Reset memory for a fresh conversation session."""
        self._save_raw({"monthly_income": None, "existing_obligations": 0.0, "previously_seen_options": []})

    def to_dict(self) -> dict[str, Any]:
        """Return memory as dictionary snapshot."""
        return self._read_raw()
