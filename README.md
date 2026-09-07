# FinAdvisor AI — Autonomous EMI & Loan Intelligence Agent

An intelligent, multi-step agentic financial advisor that assists users in evaluating and comparing loan options. It extracts parameters from natural language via Groq LPU reasoning, enforces domain boundary guardrails, executes deterministic reducing-balance financial tools, analyzes affordability using a transparent 30% net income heuristic rule, and maintains persistent conversation memory across multiple conversational turns.

The agent leverages two deterministic financial tools: `compute_emi(amount, rate, months)` to compute reducing-balance EMIs and interest totals without LLM calculation errors, and `compare_options()` to standardize candidate loan options across multiple tenures. Its stateful conversation memory stores the user's stated monthly income and previously seen loan options, allowing subsequent conversational turns (such as tenure adjustments or follow-up questions) to recall financial context without re-asking the user.

A key honest failure encountered during development occurs when a user requests a loan recommendation without providing their monthly income (and no prior income exists in session memory). Rather than hallucinating an affordability claim or making an ungrounded assumption, the agent calculates the candidate EMIs, detects the missing income constraint, and explicitly halts the affordability decision—prompting the user for their monthly income before making a responsible recommendation under the project's 30% affordability heuristic.

---

## Quick Start & Verification

### 1. Run the Jupyter Notebook Demo
```bash
jupyter notebook notebooks/CA1_EMI_Loan_Advisor_Demo.ipynb
```

### 2. Run the Unit Test Suite
```bash
python -m unittest discover -s tests
```

---

## LLM Configuration (Groq Cloud)

The project supports ultra-fast cloud LLM parameter extraction via **Groq Cloud**:
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Set your Groq API key in `.env`:
   ```env
   GROQ_API_KEY=gsk_...
   GROQ_MODEL=openai/gpt-oss-120b
   GROQ_BASE_URL=https://api.groq.com/openai/v1
   ```
3. If no key is provided, the agent automatically falls back to the built-in zero-latency deterministic parser without throwing errors.

---

## Architecture & Viva Reference

- **Agent Workflow ([`src/agent.py`](file:///c:/Users/irfan/OneDrive/Documents/Aiagent/emi-loan-advisor/src/agent.py))**: Multi-step Plan -> Act -> Observe -> Decide loop with structured execution trace.
- **Deterministic Tools ([`src/tools.py`](file:///c:/Users/irfan/OneDrive/Documents/Aiagent/emi-loan-advisor/src/tools.py))**: `compute_emi()` and `compare_options()`.
- **Decision Engine ([`src/decision.py`](file:///c:/Users/irfan/OneDrive/Documents/Aiagent/emi-loan-advisor/src/decision.py))**: Deterministic affordability evaluator and option ranking (30% income threshold).
- **Session Memory ([`src/memory.py`](file:///c:/Users/irfan/OneDrive/Documents/Aiagent/emi-loan-advisor/src/memory.py))**: Manages multi-turn state (`monthly_income` and `previously_seen_options`).
- **Configuration ([`src/config.py`](file:///c:/Users/irfan/OneDrive/Documents/Aiagent/emi-loan-advisor/src/config.py))**: Project constants, thresholds, and LLM endpoints (Groq, GitHub Models, OpenAI).

