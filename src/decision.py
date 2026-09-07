"""Deterministic affordability decision engine for loan comparisons."""

from __future__ import annotations

import math
from typing import Any

from .config import DEFAULT_AFFORDABILITY_THRESHOLD, DISCLAIMER_TEXT


def evaluate_affordability(
    monthly_emi: float,
    monthly_income: float | None,
    threshold: float = DEFAULT_AFFORDABILITY_THRESHOLD,
    existing_obligations: float = 0.0,
) -> dict[str, Any]:
    """Evaluate whether a specific monthly EMI is affordable under project heuristics.

    Deterministic Rule:
        Maximum Affordable EMI = (monthly_income - existing_obligations) * threshold
    """
    if monthly_income is None or monthly_income <= 0 or not math.isfinite(monthly_income):
        raise ValueError("Valid positive monthly income is required for affordability analysis.")
    if monthly_emi < 0 or not math.isfinite(monthly_emi):
        raise ValueError("Monthly EMI must be non-negative.")
    if existing_obligations < 0 or not math.isfinite(existing_obligations):
        raise ValueError("Existing obligations must be non-negative.")

    effective_income = max(0.0, monthly_income - existing_obligations)
    max_preferred_emi = effective_income * threshold
    is_affordable = monthly_emi <= max_preferred_emi
    emi_to_income_ratio = (monthly_emi / monthly_income) if monthly_income > 0 else 0.0

    return {
        "monthly_income": round(monthly_income, 2),
        "existing_obligations": round(existing_obligations, 2),
        "effective_income": round(effective_income, 2),
        "threshold_percentage": round(threshold * 100, 1),
        "max_preferred_emi": round(max_preferred_emi, 2),
        "monthly_emi": round(monthly_emi, 2),
        "is_affordable": is_affordable,
        "emi_to_income_ratio": round(emi_to_income_ratio * 100, 2),
        "status": "Affordable" if is_affordable else "Above Preferred Threshold",
        "rule_description": f"Maximum preferred EMI is {threshold:.0%} of monthly income ({round(max_preferred_emi, 2)})",
        "disclaimer": DISCLAIMER_TEXT,
    }


def rank_and_recommend(
    evaluated_options: list[dict[str, Any]],
    monthly_income: float,
    threshold: float = DEFAULT_AFFORDABILITY_THRESHOLD,
    existing_obligations: float = 0.0,
) -> dict[str, Any]:
    """Rank multiple loan options and select the most affordable recommendation."""
    if not evaluated_options:
        raise ValueError("At least one evaluated loan option is required for recommendation.")

    analyzed = []
    for opt in evaluated_options:
        aff = evaluate_affordability(
            monthly_emi=opt["monthly_emi"],
            monthly_income=monthly_income,
            threshold=threshold,
            existing_obligations=existing_obligations,
        )
        analyzed.append({**opt, "affordability": aff})

    # Sort options: Affordable first, then by lower EMI
    affordable_options = [o for o in analyzed if o["affordability"]["is_affordable"]]
    unaffordable_options = [o for o in analyzed if not o["affordability"]["is_affordable"]]

    if affordable_options:
        # Pick the lowest EMI among affordable options
        best_option = min(affordable_options, key=lambda x: x["monthly_emi"])
        decision_reason = (
            f"{best_option['name']} has the most affordable EMI (₹{best_option['monthly_emi']:,.2f}/mo), "
            f"which is within your ₹{best_option['affordability']['max_preferred_emi']:,.2f}/mo project budget cap."
        )
    else:
        # If none affordable, pick the closest one but clearly mark as unaffordable
        best_option = min(unaffordable_options, key=lambda x: x["monthly_emi"])
        decision_reason = (
            f"None of the compared options fit within the {threshold:.0%} affordability threshold (₹{best_option['affordability']['max_preferred_emi']:,.2f}/mo). "
            f"The closest option is {best_option['name']} at ₹{best_option['monthly_emi']:,.2f}/mo."
        )

    return {
        "recommended_option": best_option,
        "all_options": analyzed,
        "is_recommended_affordable": best_option["affordability"]["is_affordable"],
        "reason": decision_reason,
    }
