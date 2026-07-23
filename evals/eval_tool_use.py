# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Tool use evaluation — verifies the agent selects correct MCP tools and parameters.

This evaluates two dimensions:
1. Tool Selection: Did the agent call the right MCP server tools for the query?
2. Tool Parameters: Did it pass correct line/machine_id/plant parameters?

Run:
    python -m evals.eval_tool_use
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from strands import Agent
from strands_evals import Case, Experiment, eval_task
from strands_evals.evaluators import (
    ToolParameterAccuracyEvaluator,
    ToolSelectionAccuracyEvaluator,
)

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.agent import ManufacturingInsightsAgent
from src.config import AppConfig
from src.identity.models import DEMO_USERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Map user keys to identity objects
USER_MAP = {
    "sarah": DEMO_USERS["sarah"],
    "raj": DEMO_USERS["raj"],
    "priya": DEMO_USERS["priya"],
}


def load_tool_routing_cases() -> list[Case]:
    """Load test cases from the tool_routing.json file."""
    cases_path = Path(__file__).parent / "cases" / "tool_routing.json"
    with open(cases_path) as f:
        raw_cases = json.load(f)

    cases = []
    for i, raw in enumerate(raw_cases):
        cases.append(
            Case(
                case_id=f"tool_routing_{i}",
                input=raw["input"],
                metadata=raw["metadata"],
                expected_tools=raw["expected_tools"],
            )
        )
    return cases


@eval_task()
def run_agent_query(case: Case):
    """Execute a single agent query and return the agent for trace collection."""
    config = AppConfig()
    agent = ManufacturingInsightsAgent(config)

    user_key = case.metadata["user"]
    user = USER_MAP[user_key]

    # Run the query — this will call MCP tools via the agent's reasoning loop
    response = agent.query(user, case.input)

    return response


def build_evaluators():
    """Build the evaluator suite for tool use assessment."""
    return [
        ToolSelectionAccuracyEvaluator(),
        ToolParameterAccuracyEvaluator(),
    ]


async def run_tool_use_evals():
    """Run tool use evaluations against the manufacturing insights agent."""
    cases = load_tool_routing_cases()
    evaluators = build_evaluators()

    experiment = Experiment(
        name="manufacturing_agent_tool_use",
        cases=cases,
        evaluators=evaluators,
    )

    logger.info("Running tool use evaluation with %d cases...", len(cases))
    report = await experiment.run_evaluations_async(run_agent_query)

    # Print summary
    print("\n" + "=" * 70)
    print("  Tool Use Evaluation Results")
    print("=" * 70)

    for result in report.results:
        status = "PASS" if result.test_pass else "FAIL"
        print(f"  [{status}] {result.case_id}: score={result.score:.2f}")
        if not result.test_pass:
            print(f"         Reason: {result.reason}")

    # Aggregate scores
    scores = [r.score for r in report.results if r.score is not None]
    if scores:
        avg_score = sum(scores) / len(scores)
        pass_rate = sum(1 for r in report.results if r.test_pass) / len(report.results)
        print(f"\n  Average Score: {avg_score:.2f}")
        print(f"  Pass Rate:     {pass_rate:.0%}")
        print("=" * 70)

    return report


if __name__ == "__main__":
    asyncio.run(run_tool_use_evals())
