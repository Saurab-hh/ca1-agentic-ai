"""Multi-step Plan-Act-Observe-Decide Agent for EMI and Loan Advisory."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Callable

from .config import (
    DEFAULT_AFFORDABILITY_THRESHOLD,
    DEFAULT_ANNUAL_INTEREST_RATE,
    DEFAULT_MEMORY_FILE,
    DISCLAIMER_TEXT,
    GITHUB_MODEL,
    GITHUB_MODELS_ENDPOINT,
    GITHUB_TOKEN,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    OPENAI_API_KEY,
)
from .decision import evaluate_affordability, rank_and_recommend
from .memory import ConversationMemory
from .tools import compare_options, compute_emi


class AgentTrace:
    """Records and formats the step-by-step agentic execution trace."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def log(self, stage: str, message: str, data: Any = None) -> None:
        """Add an event to the trace."""
        event = {"stage": stage, "message": message}
        if data is not None:
            event["data"] = data
        self.events.append(event)

    def get_formatted_trace(self) -> str:
        """Format the trace into clean, human-readable sections."""
        lines = []
        for event in self.events:
            stage = event["stage"].upper()
            msg = event["message"]
            lines.append(f"[{stage}]\n{msg}")
            if "data" in event:
                data = event["data"]
                if isinstance(data, dict):
                    for k, v in data.items():
                        lines.append(f"  • {k}: {v}")
                elif isinstance(data, list):
                    for item in data:
                        lines.append(f"  • {item}")
            lines.append("")
        return "\n".join(lines).strip()

    def print_trace(self) -> None:
        """Print formatted trace to stdout."""
        print(self.get_formatted_trace())


class LoanAdvisorAgent:
    """An agent that follows a multi-step Plan -> Act -> Observe -> Decide loop

    to advise users on loan options, compute EMIs using deterministic Python tools,
    evaluate affordability heuristics, and maintain stateful session memory.
    """

    def __init__(
        self,
        memory: ConversationMemory | None = None,
        memory_path: str | Path | None = None,
        use_llm_if_available: bool = True,
    ) -> None:
        if memory is not None:
            self.memory = memory
        elif memory_path is not None:
            self.memory = ConversationMemory(memory_path)
        else:
            self.memory = ConversationMemory(DEFAULT_MEMORY_FILE)

        self.use_llm = use_llm_if_available and bool(
            GROQ_API_KEY or GITHUB_TOKEN or OPENAI_API_KEY
        )

    def _extract_intent_deterministic(self, user_goal: str) -> dict[str, Any]:
        """Extract financial parameters and intent using robust regex rules."""
        normalized = user_goal.lower().replace(",", "")

        # Extract tenures / years or months
        tenure_years = [
            int(match)
            for match in re.findall(
                r"(\d+)\s*(?:-|–|\s)?\s*(?:year|years|yr|yrs)", normalized
            )
        ]
        tenure_months = [
            int(match)
            for match in re.findall(
                r"(\d+)\s*(?:-|–|\s)?\s*(?:month|months|mo|mos)", normalized
            )
        ]
        # Combine year and month specifications
        all_tenures = list(tenure_years)
        for m in tenure_months:
            if m % 12 == 0:
                all_tenures.append(m // 12)
            else:
                all_tenures.append(round(m / 12, 1))

        # Extract income
        income = None
        income_match = re.search(
            r"(?:income|earn|salary|make|earning)\D{0,12}(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(k|thousand|lakh|lac)?",
            normalized,
        )
        if income_match:
            val = float(income_match.group(1))
            unit = income_match.group(2)
            if unit in ("k", "thousand"):
                income = val * 1000.0
            elif unit in ("lakh", "lac"):
                income = val * 100000.0
            else:
                income = val

        # Extract existing obligations
        obligations = None
        ob_match = re.search(
            r"(?:existing|current|other|ongoing|paying|already pay)\s*(?:emi|obligation|loan|debt|payment)?\D{0,12}(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(k|thousand|lakh|lac)?",
            normalized,
        )
        if ob_match:
            val = float(ob_match.group(1))
            unit = ob_match.group(2)
            if unit in ("k", "thousand"):
                obligations = val * 1000.0
            elif unit in ("lakh", "lac"):
                obligations = val * 100000.0
            else:
                obligations = val

        # Extract loan amount
        amount = None
        amount_patterns = [
            r"(?:want|need|borrow|require|get|take|increase(?: to)?|loan(?:\s+amount)?)\D{0,15}(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(lakh|lac|k|thousand|cr|crore)?",
            r"(?:₹|rs\.?\s*)(\d+(?:\.\d+)?)\s*(lakh|lac|k|thousand|cr|crore)?(?:\s+loan)?",
            r"(\d+(?:\.\d+)?)\s*(lakh|lac|cr|crore)\s*(?:loan)?",
        ]

        for pat in amount_patterns:
            for match in re.finditer(pat, normalized):
                val_str, unit = match.group(1), match.group(2)
                val = float(val_str)
                # Ignore if this match overlaps with the income match
                if income_match and match.start() <= income_match.end() and match.end() >= income_match.start():
                    continue
                # Ignore if this is a tenure number without unit
                if not unit and int(val) in tenure_years and "year" in normalized[match.start():match.end() + 10]:
                    continue

                if unit in ("lakh", "lac"):
                    amt = val * 100000.0
                elif unit in ("k", "thousand"):
                    amt = val * 1000.0
                elif unit in ("cr", "crore"):
                    amt = val * 10000000.0
                else:
                    amt = val

                if amt >= 1000:
                    amount = amt
                    break
            if amount is not None:
                break

        # Extract interest rate if specified
        rate_match = re.search(r"(\d+(?:\.\d+)?)\s*%", normalized)
        rate = float(rate_match.group(1)) if rate_match else DEFAULT_ANNUAL_INTEREST_RATE

        is_follow_up_longer = "longer" in normalized or "higher tenure" in normalized
        is_follow_up_shorter = "shorter" in normalized or "lower tenure" in normalized

        # Check if the query relates to the financial/loan advisory domain using regex boundaries
        domain_patterns = [
            r"\b(loan|loans|emi|emis|interest|annual rate|borrow|borrowing|tenure|tenures|repay|repayment)\b",
            r"\b(salary|income|earn|earning|debt|debts|obligation|obligations|afford|affordability|budget)\b",
            r"\b(lakh|lakhs|lac|lacs|crore|crores|rupee|rupees|₹|rs\.?)\b",
            r"\b(home loan|car loan|personal loan|education loan|gold loan)\b",
            r"\b(higher tenure|lower tenure|longer tenure|shorter tenure|longer|shorter)\b",
            r"^(hi|hello|hey|help|start|advisor)\b",
        ]
        has_domain_keyword = (
            any(re.search(p, normalized) for p in domain_patterns)
            or (amount is not None)
            or (income is not None)
        )

        # Out-of-domain rejection if clearly non-financial query
        is_in_domain = True
        out_of_scope_reason = None
        if not has_domain_keyword and len(normalized.split()) >= 2:
            is_in_domain = False
            out_of_scope_reason = (
                "Query does not contain personal loan, EMI, income, or financial advisory topics."
            )

        return {
            "income": income,
            "obligations": obligations,
            "amount": amount,
            "tenures_years": all_tenures,
            "rate": rate,
            "is_follow_up_longer": is_follow_up_longer,
            "is_follow_up_shorter": is_follow_up_shorter,
            "is_in_domain": is_in_domain,
            "out_of_scope_reason": out_of_scope_reason,
        }

    def _call_llm_json(
        self, endpoint: str, api_key: str, model: str, prompt: str
    ) -> dict[str, Any]:
        """Make an OpenAI-compatible JSON Chat Completion request using standard library urllib."""
        import json
        import urllib.request

        url = (
            endpoint
            if endpoint.endswith("/chat/completions")
            else f"{endpoint.rstrip('/')}/chat/completions"
        )
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a specialized loan parameter extractor and domain classifier for a financial advisory agent. "
                        "You must strictly return a valid JSON object matching the requested schema."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (LoanAdvisorAgent/1.0)",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            raw_text = res_data["choices"][0]["message"]["content"]
            # Handle potential markdown fence wrapping from some models
            clean_text = raw_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            return json.loads(clean_text.strip())

    def _extract_intent_llm(self, user_goal: str) -> tuple[dict[str, Any], str]:
        """LLM parser supporting Groq Cloud, GitHub Models, or OpenAI."""
        if GROQ_API_KEY:
            endpoint = GROQ_BASE_URL
            api_key = GROQ_API_KEY
            model = GROQ_MODEL
            provider_name = f"Groq Cloud ({GROQ_MODEL})"
        elif GITHUB_TOKEN:
            endpoint = GITHUB_MODELS_ENDPOINT
            api_key = GITHUB_TOKEN
            model = GITHUB_MODEL
            provider_name = f"GitHub Models ({GITHUB_MODEL})"
        elif OPENAI_API_KEY:
            endpoint = "https://api.openai.com/v1"
            api_key = OPENAI_API_KEY
            model = "gpt-4o-mini"
            provider_name = "OpenAI (gpt-4o-mini)"
        else:
            raise ValueError("No LLM API key configured.")

        prompt = (
            "Analyze the user's input and extract key financial parameters into a JSON object with these exact keys:\n"
            "- 'is_in_domain': boolean (Set false if the user asks something completely outside personal finance/loan/EMI advisory like coding, cooking recipes, general trivia, weather, history, physics, etc. Set true for financial queries, loan questions, budget discussions, or greetings).\n"
            "- 'out_of_scope_reason': string or null (Short explanation if is_in_domain is false, otherwise null).\n"
            "- 'income': monthly income as float or null\n"
            "- 'obligations': existing monthly debt/EMIs as float or null\n"
            "- 'amount': requested loan amount as float or null (convert lakhs/k to full number, e.g. 5 lakh = 500000.0)\n"
            "- 'tenures_years': list of tenures in years as numbers (e.g. [3, 5]) or empty list\n"
            "- 'rate': annual interest rate as float (default 10.0 if not specified)\n"
            "- 'is_follow_up_longer': boolean (true if user wants longer tenure)\n"
            "- 'is_follow_up_shorter': boolean (true if user wants shorter tenure)\n\n"
            f"User request: {user_goal}"
        )
        data = self._call_llm_json(endpoint, api_key, model, prompt)
        return data, provider_name

    def _extract_intent(self, user_goal: str) -> tuple[dict[str, Any], str]:
        """Extract user parameters using LLM or deterministic fallback."""
        if self.use_llm:
            try:
                return self._extract_intent_llm(user_goal)
            except Exception:
                pass
        return self._extract_intent_deterministic(user_goal), "Deterministic Rule Parser (Local)"

    def run(self, user_goal: str) -> dict[str, Any]:
        """Execute the multi-step agentic plan-act-observe-decide workflow."""
        trace = AgentTrace()
        trace.log("USER", user_goal)

        # -------------------------------------------------------------
        # STEP 1: Understand Goal & Extract Parameters
        # -------------------------------------------------------------
        extracted, provider = self._extract_intent(user_goal)
        trace.log(
            "AGENT PLAN",
            f"Analyzing natural language request using {provider} and extracting financial parameters.",
        )
        trace.log("OBSERVE", "Extracted initial parameters.", extracted)

        # -------------------------------------------------------------
        # GUARDRAIL: Out-of-Scope / Domain Boundary Enforcement
        # -------------------------------------------------------------
        if not extracted.get("is_in_domain", True):
            reason = extracted.get("out_of_scope_reason") or "Query is outside the scope of Loan & EMI Advisory."
            trace.log(
                "GUARDRAIL / SCOPE CHECK",
                f"Query classified as OUT-OF-SCOPE ({reason}). Triggering domain boundary guardrail response.",
                {"reason": reason},
            )
            answer = (
                "**⚠️ Out of Scope / Domain Guardrail**\n\n"
                f"This request is outside the scope of the **Loan & EMI Financial Advisory Agent**.\n\n"
                f"*Reason: {reason}*\n\n"
                "**I specialize exclusively in:**\n"
                "- 📊 **Loan Comparison**: Comparing reducing-balance EMIs across multiple tenures (e.g. 3 vs 5 years)\n"
                "- 💰 **Affordability Analysis**: Evaluating monthly loan eligibility against your income using the 30% heuristic rule\n"
                "- 💳 **Debt-to-Income Adjustments**: Factoring in existing loan EMIs to protect your disposable budget\n\n"
                "💡 *Example prompt: 'I earn ₹60,000 per month. Compare a ₹5 lakh loan for 3 years and 5 years.'*"
            )
            trace.log("FINAL RECOMMENDATION", answer)
            return {
                "answer": answer,
                "is_in_domain": False,
                "trace": trace.get_formatted_trace(),
                "trace_events": trace.events,
                "memory": self.memory.to_dict(),
            }

        # -------------------------------------------------------------
        # STEP 2: Read Memory
        # -------------------------------------------------------------
        stored_income = self.memory.get_monthly_income()
        stored_obligations = self.memory.get_existing_obligations()
        stored_options = self.memory.get_previously_seen_options()
        trace.log(
            "MEMORY READ",
            f"Retrieved session memory state.",
            {
                "stored_monthly_income": f"₹{stored_income:,.2f}" if stored_income else "None",
                "stored_existing_obligations": f"₹{stored_obligations:,.2f}" if stored_obligations else "₹0.00",
                "previously_seen_options_count": len(stored_options),
            },
        )

        # Update income in memory if newly provided
        if extracted.get("income") is not None:
            self.memory.set_monthly_income(extracted["income"])
            active_income = extracted["income"]
            trace.log("MEMORY UPDATE", f"Saved monthly income: ₹{active_income:,.2f}")
        else:
            active_income = stored_income

        # Update existing obligations if newly provided
        if extracted.get("obligations") is not None:
            self.memory.set_existing_obligations(extracted["obligations"])
            active_obligations = extracted["obligations"]
            trace.log("MEMORY UPDATE", f"Saved existing monthly obligations: ₹{active_obligations:,.2f}")
        else:
            active_obligations = stored_obligations

        # Handle follow-ups and tenure adjustments using prior options
        amount = extracted.get("amount")
        tenures = extracted.get("tenures_years") or []
        rate = extracted.get("rate", DEFAULT_ANNUAL_INTEREST_RATE)

        if not amount and stored_options:
            amount = stored_options[0].get("amount")
        if not tenures and stored_options:
            tenures = [int(opt["months"] / 12) if opt["months"] % 12 == 0 else round(opt["months"] / 12, 1) for opt in stored_options]

        # -------------------------------------------------------------
        # STEP 3: Handle Edge Cases / Missing Details (Honest Failure)
        # -------------------------------------------------------------
        if amount is None or not tenures:
            if active_income and not amount:
                answer = f"I noted your monthly income of ₹{active_income:,.2f}. Please specify the loan amount and tenures you want to compare."
            else:
                answer = "Please provide the loan amount and the loan tenures (e.g., 3 years and 5 years) to begin comparison."
            trace.log("AGENT DECISION", "Insufficient loan details provided to perform comparison.")
            trace.log("FINAL RECOMMENDATION", answer)
            return {
                "answer": answer,
                "trace": trace.get_formatted_trace(),
                "trace_events": trace.events,
                "memory": self.memory.to_dict(),
            }

        # -------------------------------------------------------------
        # STEP 4: Call Tool 1 — compare_options()
        # -------------------------------------------------------------
        trace.log(
            "TOOL CALL",
            "compare_options()",
            {"amount": amount, "tenures_years": tenures, "rate": rate},
        )
        comparison_candidates = compare_options(amount=amount, tenures_years=tenures, rate=rate)
        candidate_options = comparison_candidates["options"]
        trace.log(
            "TOOL RESULT",
            f"Generated {len(candidate_options)} candidate loan option profiles.",
            candidate_options,
        )

        # -------------------------------------------------------------
        # STEP 5: Sequential Tool Calling — compute_emi() for each option
        # -------------------------------------------------------------
        trace.log(
            "AGENT PLAN",
            f"Agent will now calculate reducing-balance EMIs for all {len(candidate_options)} candidate options using compute_emi().",
        )
        evaluated_options: list[dict[str, Any]] = []

        for opt in candidate_options:
            trace.log(
                "TOOL CALL",
                f"compute_emi(amount={opt['amount']}, rate={opt['annual_rate']}, months={opt['months']})",
            )
            emi_calc = compute_emi(
                amount=opt["amount"],
                rate=opt["annual_rate"],
                months=opt["months"],
            )
            trace.log(
                "TOOL RESULT",
                f"Computed EMI for {opt['name']}: ₹{emi_calc['monthly_emi']:,.2f}/month (Total Interest: ₹{emi_calc['total_interest']:,.2f})",
                emi_calc,
            )
            evaluated_options.append({
                "name": opt["name"],
                "amount": opt["amount"],
                "annual_rate": opt["annual_rate"],
                "months": opt["months"],
                **emi_calc,
            })

        # Check if user requested specific preference like longer tenure
        if extracted.get("is_follow_up_longer"):
            preferred_months = max(opt["months"] for opt in evaluated_options)
            evaluated_options.sort(key=lambda x: (x["months"] != preferred_months, x["monthly_emi"]))
        elif extracted.get("is_follow_up_shorter"):
            preferred_months = min(opt["months"] for opt in evaluated_options)
            evaluated_options.sort(key=lambda x: (x["months"] != preferred_months, x["monthly_emi"]))

        # -------------------------------------------------------------
        # STEP 6: Evaluate Affordability (Honest Failure if Income Missing)
        # -------------------------------------------------------------
        if active_income is None:
            trace.log(
                "AGENT DECISION",
                "Cannot perform affordability evaluation because monthly income is missing from both request and memory.",
            )
            options_summary = ", ".join(
                f"{opt['name']}: ₹{opt['monthly_emi']:,.2f}/mo" for opt in evaluated_options
            )
            answer = (
                f"I calculated the EMIs for your loan ({options_summary}). "
                "However, I cannot provide an affordability recommendation because your monthly income is not known. "
                "Please state your monthly income to evaluate affordability."
            )
            self.memory.set_previously_seen_options(evaluated_options)
            trace.log("FINAL RECOMMENDATION", answer)
            return {
                "answer": answer,
                "trace": trace.get_formatted_trace(),
                "trace_events": trace.events,
                "evaluated_options": evaluated_options,
                "memory": self.memory.to_dict(),
            }

        trace.log(
            "AFFORDABILITY EVALUATION",
            f"Evaluating options against stated income (₹{active_income:,.2f}) and existing obligations (₹{active_obligations:,.2f}) using the {DEFAULT_AFFORDABILITY_THRESHOLD:.0%} project heuristic rule.",
        )
        recommendation_data = rank_and_recommend(
            evaluated_options=evaluated_options,
            monthly_income=active_income,
            threshold=DEFAULT_AFFORDABILITY_THRESHOLD,
            existing_obligations=active_obligations,
        )
        rec_opt = recommendation_data["recommended_option"]
        trace.log(
            "AGENT DECISION",
            f"Affordability evaluation completed. Recommended: {rec_opt['name']} (EMI: ₹{rec_opt['monthly_emi']:,.2f}/mo). Status: {rec_opt['affordability']['status']}.",
            {
                "recommended_option": rec_opt["name"],
                "monthly_emi": f"₹{rec_opt['monthly_emi']:,.2f}",
                "max_budget_cap": f"₹{rec_opt['affordability']['max_preferred_emi']:,.2f}",
                "is_affordable": rec_opt["affordability"]["is_affordable"],
                "reason": recommendation_data["reason"],
            },
        )

        # -------------------------------------------------------------
        # STEP 7: Update Memory
        # -------------------------------------------------------------
        self.memory.set_previously_seen_options(evaluated_options)
        trace.log(
            "MEMORY UPDATE",
            f"Stored {len(evaluated_options)} evaluated options in memory for future conversation turns.",
        )

        # -------------------------------------------------------------
        # STEP 8: Generate Final Recommendation Explanation
        # -------------------------------------------------------------
        options_detail = " | ".join(
            f"{opt['name']}: EMI ₹{opt['monthly_emi']:,.2f}/mo (Interest: ₹{opt['total_interest']:,.2f})"
            for opt in evaluated_options
        )
        aff_status = rec_opt["affordability"]["status"]
        cap_val = rec_opt["affordability"]["max_preferred_emi"]

        obligation_note = (
            f" (after adjusting for ₹{active_obligations:,.2f} existing monthly obligations)"
            if active_obligations > 0
            else ""
        )

        if rec_opt["affordability"]["is_affordable"]:
            answer = (
                f"**Recommendation: {rec_opt['name']}**\n\n"
                f"- **Monthly EMI**: ₹{rec_opt['monthly_emi']:,.2f} for {rec_opt['months']} months (Rate: {rec_opt['annual_rate']}%)\n"
                f"- **Total Interest**: ₹{rec_opt['total_interest']:,.2f} (Total repayment: ₹{rec_opt['total_payment']:,.2f})\n"
                f"- **Affordability**: **{aff_status}** (EMI is {rec_opt['affordability']['emi_to_income_ratio']}% of your ₹{active_income:,.2f} monthly income, within the 30% cap of ₹{cap_val:,.2f}{obligation_note})\n"
                f"- **Comparison**: {options_detail}\n\n"
                f"> *{DISCLAIMER_TEXT}*"
            )
        else:
            answer = (
                f"**Alert: No affordable option within preferred threshold**\n\n"
                f"For a monthly income of ₹{active_income:,.2f}{obligation_note}, your maximum preferred 30% EMI budget is **₹{cap_val:,.2f}/month**.\n"
                f"The closest option is **{rec_opt['name']}** at **₹{rec_opt['monthly_emi']:,.2f}/month**, which exceeds your preferred budget by ₹{rec_opt['monthly_emi'] - cap_val:,.2f}/month.\n\n"
                f"- **All Options Evaluated**: {options_detail}\n"
                f"- **Suggestion**: Consider increasing the loan tenure or lowering the principal loan amount.\n\n"
                f"> *{DISCLAIMER_TEXT}*"
            )

        trace.log("FINAL RECOMMENDATION", answer)

        return {
            "answer": answer,
            "recommended_option": rec_opt,
            "all_options": evaluated_options,
            "affordability": rec_opt["affordability"],
            "trace": trace.get_formatted_trace(),
            "trace_events": trace.events,
            "memory": self.memory.to_dict(),
        }