"""Deterministic financial calculation tools for the EMI and Loan Advisor."""

from __future__ import annotations

import math
from typing import Any


def compute_emi(amount: float, rate: float, months: int) -> dict[str, Any]:
    """Calculate the monthly EMI using the standard reducing-balance formula.

    Formula:
        EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
        where:
          P = principal loan amount
          r = monthly interest rate (annual_rate / 12 / 100)
          n = number of monthly payments
    """
    if amount <= 0 or not math.isfinite(amount):
        raise ValueError("Loan amount must be a positive number.")
    if rate < 0 or not math.isfinite(rate):
        raise ValueError("Interest rate must be non-negative.")
    if months <= 0 or not isinstance(months, int):
        raise ValueError("Tenure in months must be a positive integer.")

    amount = float(amount)
    rate = float(rate)
    months = int(months)

    monthly_rate = rate / 12.0 / 100.0

    if monthly_rate == 0.0:
        emi = amount / months
    else:
        compounded = (1.0 + monthly_rate) ** months
        emi = (amount * monthly_rate * compounded) / (compounded - 1.0)

    total_payment = emi * months
    total_interest = total_payment - amount

    return {
        "loan_amount": round(amount, 2),
        "annual_rate": round(rate, 2),
        "months": months,
        "monthly_emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
    }


def compare_options(
    amount: float | None = None,
    tenures_years: list[int] | None = None,
    rate: float = 10.0,
    options_list: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Return structured candidate loan options for comparison.

    Generates or formats candidate loan options with principal amount, interest rate,
    and tenure (in months) so the agent can subsequently compute and compare EMIs.
    """
    if options_list:
        formatted_options = []
        for idx, opt in enumerate(options_list, start=1):
            name = opt.get("name", f"Option {chr(64 + idx)}")
            opt_amount = float(opt["amount"])
            opt_rate = float(opt.get("rate", opt.get("annual_rate", rate)))
            opt_months = int(opt["months"])
            formatted_options.append({
                "name": name,
                "amount": opt_amount,
                "annual_rate": opt_rate,
                "months": opt_months,
            })
        return {"options": formatted_options}

    if amount is not None and tenures_years:
        if amount <= 0:
            raise ValueError("Loan amount must be positive.")
        formatted_options = []
        for idx, years in enumerate(tenures_years, start=1):
            formatted_options.append({
                "name": f"Option {chr(64 + idx)} ({years} Years)",
                "amount": float(amount),
                "annual_rate": float(rate),
                "months": int(years * 12),
            })
        return {"options": formatted_options}

    raise ValueError("Either options_list or amount and tenures_years must be provided.")
