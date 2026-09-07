"""Configuration constants and environment settings for EMI and Loan Advisor."""

from __future__ import annotations

import os
from pathlib import Path

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parents[1]

# Safely load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# Financial & Decision Constants (Project-level heuristics)
DEFAULT_AFFORDABILITY_THRESHOLD: float = 0.30  # Max preferred EMI = 30% of monthly income
DEFAULT_ANNUAL_INTEREST_RATE: float = 10.0     # Default simulated annual interest rate in %
DEFAULT_CURRENCY_SYMBOL: str = "₹"

# Memory Paths
DEFAULT_MEMORY_FILE = BASE_DIR / "data" / "memory.json"

# LLM / Groq / GitHub Models / OpenAI Settings
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
GITHUB_MODELS_ENDPOINT: str = os.getenv(
    "GITHUB_MODELS_ENDPOINT", "https://models.inference.ai.azure.com"
)
GITHUB_MODEL: str = os.getenv("GITHUB_MODEL", "gpt-4o-mini")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# Project Disclaimer
DISCLAIMER_TEXT: str = (
    "Based on the inputs you provided and the project's affordability heuristic (max 30% of income). "
    "This is an educational project heuristic, not official bank eligibility or professional financial advice."
)
