# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Interactive CLI for the Manufacturing Insights Agent.

This is the entry point for running the demo. By default, it connects to
the deployed AgentCore Gateway which handles MCP routing, Cedar policy
enforcement, and Lambda tool target invocation.

For local development without a Gateway, set SIMULATION_MODE=true to use
local MCP servers with a simulated policy hook.

In production, this CLI would be replaced by a chat UI connected
to AgentCore via API Gateway, with authentication flowing from your IdP.
"""

import logging
import os
import sys

from src.config import AppConfig
from src.identity.models import DEMO_USERS, UserIdentity
from src.agent.agent import ManufacturingInsightsAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


SAMPLE_QUERIES = {
    "sarah": [
        "Which assembly lines need attention this week?",
        "What's the relationship between Line 4 and Line 9 issues?",
        "Give me a maintenance budget impact summary for this month.",
    ],
    "raj": [
        "What's the current status of Line 7?",
        "Are there any anomalies on my line today?",
        "What parts are running low for my equipment?",
    ],
    "priya": [
        "Has the vibration on Machine 42 gotten worse since last week?",
        "What's the maintenance history for Machine 42?",
        "Are replacement bearings in stock for Machine 42?",
    ],
}


def print_header() -> None:
    """Print the application header."""
    print("\n" + "=" * 70)
    print("  🏭  Manufacturing Insights Agent")
    print("  Powered by Amazon Bedrock AgentCore + Strands Agents + MCP")
    print("=" * 70)


def print_user_menu() -> None:
    """Print user selection menu."""
    print("\nSelect a user persona:")
    print("  [1] Sarah Chen    — Plant Manager (full access, all lines)")
    print("  [2] Raj Patel     — Line Supervisor (scoped to Line 7)")
    print("  [3] Priya Nair    — Maintenance Technician (scoped to Machine 41-45)")
    print("  [q] Quit")


def print_sample_queries(user_key: str) -> None:
    """Print sample queries for the selected user."""
    queries = SAMPLE_QUERIES.get(user_key, [])
    if queries:
        print("\n  Sample queries you can try:")
        for i, q in enumerate(queries, 1):
            print(f"    [{i}] {q}")
        print()


def select_user() -> tuple[str, UserIdentity] | None:
    """Interactive user selection."""
    print_user_menu()
    choice = input("\n  Choice: ").strip().lower()

    user_map = {"1": "sarah", "2": "raj", "3": "priya"}

    if choice == "q":
        return None
    if choice in user_map:
        key = user_map[choice]
        return key, DEMO_USERS[key]

    print("  Invalid choice. Please try again.")
    return select_user()


def run_interactive_session(agent: ManufacturingInsightsAgent, user_key: str, user: UserIdentity) -> None:
    """Run an interactive query session for a user."""
    print(f"\n{'─' * 70}")
    print(f"  Logged in as: {user.name} ({user.role.value.replace('_', ' ').title()})")
    print(f"  Scope: {user.line_scope if user.line_scope else 'Full access'}")
    print(f"{'─' * 70}")
    print_sample_queries(user_key)
    print("  Type your question, a sample number [1-3], or 'back' to switch users.\n")

    queries = SAMPLE_QUERIES.get(user_key, [])

    while True:
        try:
            query = input(f"  [{user.name}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not query:
            continue
        if query.lower() in ("back", "exit", "quit"):
            return

        # Allow numeric shortcuts for sample queries
        if query.isdigit() and 1 <= int(query) <= len(queries):
            query = queries[int(query) - 1]
            print(f"  → {query}")

        print("\n  ⏳ Processing query across data sources...\n")

        try:
            response = agent.query(user, query)
            print(f"  {'─' * 60}")
            print(f"  📊 Response:")
            print(f"  {'─' * 60}")
            # Indent the response for readability
            for line in response.split("\n"):
                print(f"  {line}")
            print(f"  {'─' * 60}\n")
        except Exception as e:
            logger.error("Error processing query: %s", e)
            print(f"\n  ❌ Error: {e}")
            print("  Make sure all MCP servers are running (python -m src.servers.start_all)\n")


def main() -> None:
    """Main entry point for the interactive demo."""
    print_header()

    config = AppConfig()
    agent = ManufacturingInsightsAgent(config)

    simulation_mode = os.getenv("SIMULATION_MODE", "false").lower() == "true"
    if simulation_mode:
        print("\n  Mode: SIMULATION (local MCP servers)")
        print("  Ensure MCP servers are running in another terminal:")
        print("    python -m src.servers.start_all\n")
    else:
        print("\n  Mode: AgentCore Gateway (default)")
        print(f"  Gateway: {config.gateway.url}\n")

    while True:
        result = select_user()
        if result is None:
            print("\n  Goodbye! 👋\n")
            sys.exit(0)

        user_key, user = result
        run_interactive_session(agent, user_key, user)


if __name__ == "__main__":
    main()
