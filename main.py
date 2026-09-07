"""Interactive CLI and Demonstration Interface for FinAdvisor AI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.agent import LoanAdvisorAgent
from src.config import DEFAULT_AFFORDABILITY_THRESHOLD, DEFAULT_MEMORY_FILE
from src.memory import ConversationMemory


def print_banner() -> None:
    """Print welcome header."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 72)
    print("     FINADVISOR AI — AUTONOMOUS EMI & LOAN INTELLIGENCE AGENT")
    print("=" * 72)
    print("Features:")
    print("  • Plan -> Act -> Observe -> Decide multi-step agentic loop")
    print("  • Powered by Groq Cloud LPU + Deterministic Python Math Tools")
    print("  • Domain guardrail boundary enforcement for loan advisory")
    print(f"  • Affordability heuristic evaluation (max {DEFAULT_AFFORDABILITY_THRESHOLD:.0%} of net income)")
    print("  • Stateful multi-turn conversation memory")
    print("-" * 72)
    print("Commands:")
    print("  • Type 'memory' to view session state")
    print("  • Type 'clear'  to reset conversation memory")
    print("  • Type 'trace'  to toggle step-by-step agent trace")
    print("  • Type 'exit'   to quit")
    print("=" * 72)


def run_interactive(verbose_trace: bool = True) -> None:
    """Run interactive terminal session with the agent."""
    print_banner()
    memory = ConversationMemory(DEFAULT_MEMORY_FILE)
    agent = LoanAdvisorAgent(memory=memory)

    while True:
        try:
            print("\n👤 You: ", end="")
            user_input = input().strip()
            if not user_input:
                continue

            cmd = user_input.lower()
            if cmd in ("exit", "quit", "q"):
                print("\n👋 Goodbye! Thank you for using the EMI & Loan Advisor.")
                break

            if cmd == "memory":
                state = memory.to_dict()
                print("\n🧠 Current Session Memory:")
                print(f"  • Monthly Income: ₹{state.get('monthly_income', 'Not Stated')}")
                print(f"  • Existing Obligations: ₹{state.get('existing_obligations', 0.0):,.2f}")
                print(f"  • Previously Seen Options: {len(state.get('previously_seen_options', []))} options stored")
                continue

            if cmd == "clear":
                memory.clear()
                print("\n🧹 Session memory cleared successfully.")
                continue

            if cmd == "trace":
                verbose_trace = not verbose_trace
                print(f"\n🔍 Trace display is now: {'ON' if verbose_trace else 'OFF'}")
                continue

            print("\n🤖 Agent is thinking and executing tools...")
            result = agent.run(user_input)

            if verbose_trace and "trace" in result:
                print("\n" + "=" * 70)
                print("📋 EXECUTION TRACE:")
                print("=" * 70)
                print(result["trace"])
                print("=" * 70)

            print("\n💡 AGENT RESPONSE:")
            print(result["answer"])

        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Session ended.")
            break
        except Exception as err:
            print(f"\n⚠️ An error occurred: {err}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="EMI and Loan Advisor Agent CLI")
    parser.add_argument(
        "--no-trace", action="store_true", help="Hide detailed execution traces by default"
    )
    args = parser.parse_args()
    run_interactive(verbose_trace=not args.no_trace)


if __name__ == "__main__":
    main()
