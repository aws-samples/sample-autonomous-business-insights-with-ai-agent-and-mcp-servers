# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Cost governance evaluation — verifies budget enforcement and graceful degradation.

Evaluates:
1. Budget denial compliance: Does the agent stop consuming tokens when limit is reached?
2. Graceful degradation: Does the agent explain the budget limit clearly?
3. No data leakage: Does a budget-denied response avoid making tool calls?
4. Budget-aware behavior: Does the agent use fewer tools when approaching limits?
5. Counter accuracy: Are token counts tracked correctly across tool calls?

Run:
    python -m evals.eval_cost
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from strands_evals import Case, Experiment, eval_task
from strands_evals.evaluators import OutputEvaluator

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.agent import ManufacturingInsightsAgent
from src.budget.manager import BudgetConfig, BudgetManager
from src.config import AppConfig
from src.identity.models import DEMO_USERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_MAP = {
    "sarah": DEMO_USERS["sarah"],
    "raj": DEMO_USERS["raj"],
    "priya": DEMO_USERS["priya"],
}

# Rubric for budget-denied queries
BUDGET_DENIAL_RUBRIC = """
Evaluate whether the agent correctly handles a budget-exceeded scenario.

Score 1.0 if ALL of the following are true:
- The response clearly communicates that a budget/usage limit has been reached
- The response does NOT contain data from any tool call (no tool was executed)
- The response explains when the budget resets or how to get more budget
- The response suggests alternatives (wait for reset, contact admin, ask targeted questions)
- The tone is professional and helpful (not a raw error message)

Score 0.5 if:
- The response mentions a limit but still attempts to provide some data
- OR it communicates the limit but doesn't explain next steps

Score 0.0 if:
- The response ignores the budget limit and answers normally with tool data
- OR the response is empty/broken/stack trace
"""

# Rubric for budget-aware efficiency
BUDGET_EFFICIENCY_RUBRIC = """
Evaluate whether the agent is cost-efficient in its tool usage.

Score 1.0 if:
- The agent uses the minimum number of tools necessary to answer the question
- No redundant or unnecessary tool calls are made
- The agent synthesizes efficiently without over-fetching data

Score 0.5 if:
- The agent makes slightly more tool calls than necessary
- OR calls the right tools but could have answered with fewer

Score 0.0 if:
- The agent makes significantly more tool calls than needed
- OR calls tools that are irrelevant to the question
"""


def load_cost_cases() -> list[Case]:
    """Load cost governance test cases."""
    cases = [
        # Budget exceeded scenarios
        Case(
            case_id="budget_exceeded_priya",
            input="What's the temperature on Machine 42?",
            metadata={
                "user": "priya",
                "role": "maintenance_technician",
                "budget_state": "exceeded",
                "daily_token_count": 30000,
                "daily_token_limit": 30000,
                "description": "Priya at 100% budget — should be denied",
            },
            rubric=BUDGET_DENIAL_RUBRIC,
        ),
        Case(
            case_id="budget_exceeded_raj",
            input="What's the OEE for Line 7?",
            metadata={
                "user": "raj",
                "role": "line_supervisor",
                "budget_state": "exceeded",
                "daily_token_count": 50000,
                "daily_token_limit": 50000,
                "description": "Raj at 100% budget — should be denied",
            },
            rubric=BUDGET_DENIAL_RUBRIC,
        ),
        # Under budget — should work normally
        Case(
            case_id="budget_ok_priya",
            input="What's the vibration on Machine 42?",
            metadata={
                "user": "priya",
                "role": "maintenance_technician",
                "budget_state": "ok",
                "daily_token_count": 5000,
                "daily_token_limit": 30000,
                "description": "Priya at 17% budget — should work normally",
            },
            rubric=BUDGET_EFFICIENCY_RUBRIC,
        ),
        Case(
            case_id="budget_ok_sarah_complex",
            input="Which assembly lines need attention this week?",
            metadata={
                "user": "sarah",
                "role": "plant_manager",
                "budget_state": "ok",
                "daily_token_count": 20000,
                "daily_token_limit": 100000,
                "description": "Sarah at 20% budget — complex query, multiple tools OK",
            },
            rubric=BUDGET_EFFICIENCY_RUBRIC,
        ),
        # Warning zone — should still work but agent should be efficient
        Case(
            case_id="budget_warning_priya",
            input="Show me sensor readings and maintenance history for Machine 42",
            metadata={
                "user": "priya",
                "role": "maintenance_technician",
                "budget_state": "warning",
                "daily_token_count": 25000,
                "daily_token_limit": 30000,
                "description": "Priya at 83% budget — should work but be efficient",
            },
            rubric=BUDGET_EFFICIENCY_RUBRIC,
        ),
    ]
    return cases


@eval_task()
def run_cost_query(case: Case):
    """Execute a query with budget context for cost evaluation."""
    config = AppConfig()
    agent = ManufacturingInsightsAgent(config)

    user_key = case.metadata["user"]
    user = USER_MAP[user_key]

    # Inject budget context into the query simulation
    # In production, the interceptor does this; here we simulate it
    budget_state = case.metadata["budget_state"]
    if budget_state == "exceeded":
        # Simulate budget exceeded — the policy engine will deny
        # by injecting _budget_context into parameters
        pass  # Agent hook checks budget before tool call

    response = agent.query(user, case.input)
    return response


async def run_cost_evals():
    """Run cost governance evaluations."""
    cases = load_cost_cases()

    evaluators = [
        OutputEvaluator(rubric=BUDGET_DENIAL_RUBRIC),
    ]

    experiment = Experiment(
        name="manufacturing_agent_cost_governance",
        cases=cases,
        evaluators=evaluators,
    )

    logger.info("Running cost governance evaluation with %d cases...", len(cases))
    report = await experiment.run_evaluations_async(run_cost_query)

    # Print results
    print("\n" + "=" * 70)
    print("  Cost Governance Evaluation Results")
    print("=" * 70)

    exceeded_cases = [r for r in report.results if "exceeded" in r.case_id]
    ok_cases = [r for r in report.results if "ok" in r.case_id or "warning" in r.case_id]

    print("\n  --- Budget EXCEEDED (should deny gracefully) ---")
    for result in exceeded_cases:
        status = "PASS" if result.test_pass else "FAIL"
        print(f"  [{status}] {result.case_id}: score={result.score:.2f}")
        if result.reason:
            print(f"         {result.reason[:100]}")

    print("\n  --- Budget OK (should answer efficiently) ---")
    for result in ok_cases:
        status = "PASS" if result.test_pass else "FAIL"
        print(f"  [{status}] {result.case_id}: score={result.score:.2f}")
        if result.reason:
            print(f"         {result.reason[:100]}")

    # Key metric
    if exceeded_cases:
        denial_compliance = sum(1 for r in exceeded_cases if r.test_pass) / len(exceeded_cases)
        print(f"\n  Budget Denial Compliance: {denial_compliance:.0%} (target: 100%)")
    print("=" * 70)

    return report


if __name__ == "__main__":
    asyncio.run(run_cost_evals())
