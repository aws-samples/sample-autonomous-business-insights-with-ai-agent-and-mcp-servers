# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Trajectory evaluation — verifies multi-step reasoning and tool call sequences.

Evaluates:
1. Semantic layer first: Does the agent consult the data catalog before querying?
2. Logical sequencing: Are tool calls in a sensible order?
3. Multi-turn memory: Does the agent use prior session context for follow-ups?
4. Synthesis: Does the agent combine outputs from multiple tools coherently?

Run:
    python -m evals.eval_trajectory
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from strands_evals import Case, Experiment, eval_task
from strands_evals.evaluators import (
    GoalSuccessRateEvaluator,
    TrajectoryEvaluator,
)

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.agent import ManufacturingInsightsAgent
from src.config import AppConfig
from src.identity.models import DEMO_USERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_MAP = {
    "sarah": DEMO_USERS["sarah"],
    "raj": DEMO_USERS["raj"],
    "priya": DEMO_USERS["priya"],
}

TRAJECTORY_RUBRIC = """
Evaluate the agent's tool call trajectory (sequence of actions) for a manufacturing query.

Score 1.0 if:
- The agent consulted the semantic layer / data catalog first to discover data sources
- Tool calls are in a logical order (gather data before synthesizing)
- No redundant or wasted tool calls
- The final response synthesizes all gathered data coherently

Score 0.75 if:
- Tool calls are correct but not in optimal order
- OR the agent skipped the semantic layer but still called the right tools

Score 0.5 if:
- Some unnecessary tool calls were made
- OR the agent called correct tools but failed to synthesize results

Score 0.0 if:
- The agent called irrelevant tools
- OR the sequence shows no coherent reasoning strategy
"""

MULTI_TOOL_SYNTHESIS_RUBRIC = """
Evaluate how well the agent synthesizes information from multiple data sources.

Score 1.0 if:
- The response clearly draws connections between data from different tools
- Correlations are identified (e.g., vibration spike + maintenance history + parts availability)
- The conclusion is actionable and supported by cross-referenced evidence

Score 0.5 if:
- Data from multiple tools is presented but not connected/synthesized
- OR correlations are superficial

Score 0.0 if:
- The agent only uses one data source when multiple are needed
- OR synthesis is incorrect/contradictory
"""


def load_trajectory_cases() -> list[Case]:
    """Load cases that require multi-step reasoning."""
    cases_path = Path(__file__).parent / "cases" / "tool_routing.json"
    with open(cases_path) as f:
        raw_cases = json.load(f)

    # Filter to cases that require multiple tools (multi-step reasoning)
    cases = []
    for i, raw in enumerate(raw_cases):
        if len(raw["expected_tools"]) >= 2:
            cases.append(
                Case(
                    case_id=f"trajectory_{i}",
                    input=raw["input"],
                    metadata=raw["metadata"],
                    expected_tools=raw["expected_tools"],
                )
            )
    return cases


def load_multi_turn_cases() -> list[Case]:
    """Load multi-turn conversation cases for memory/trajectory evaluation."""
    cases_path = Path(__file__).parent / "cases" / "multi_turn.json"
    with open(cases_path) as f:
        raw_sessions = json.load(f)

    cases = []
    for session in raw_sessions:
        # Use the first turn as the primary case input
        first_turn = session["turns"][0]
        cases.append(
            Case(
                case_id=session["session_id"],
                input=first_turn["input"],
                metadata={
                    **session["metadata"],
                    "turns": session["turns"],
                    "total_turns": len(session["turns"]),
                },
                expected_tools=first_turn.get("expected_tools", []),
            )
        )
    return cases


@eval_task()
def run_trajectory_query(case: Case):
    """Execute a multi-tool query for trajectory evaluation."""
    config = AppConfig()
    agent = ManufacturingInsightsAgent(config)

    user_key = case.metadata["user"]
    user = USER_MAP[user_key]

    response = agent.query(user, case.input)
    return response


async def run_trajectory_evals():
    """Run trajectory and multi-step reasoning evaluations."""
    single_turn_cases = load_trajectory_cases()
    multi_turn_cases = load_multi_turn_cases()

    all_cases = single_turn_cases + multi_turn_cases

    evaluators = [
        TrajectoryEvaluator(rubric=TRAJECTORY_RUBRIC),
        GoalSuccessRateEvaluator(),
    ]

    experiment = Experiment(
        name="manufacturing_agent_trajectory",
        cases=all_cases,
        evaluators=evaluators,
    )

    logger.info(
        "Running trajectory evaluation: %d single-turn + %d multi-turn cases...",
        len(single_turn_cases),
        len(multi_turn_cases),
    )
    report = await experiment.run_evaluations_async(run_trajectory_query)

    print("\n" + "=" * 70)
    print("  Trajectory & Multi-Step Reasoning Results")
    print("=" * 70)

    for result in report.results:
        status = "PASS" if result.test_pass else "FAIL"
        print(f"  [{status}] {result.case_id}: score={result.score:.2f}")
        if result.reason:
            reason = result.reason[:120] + "..." if len(result.reason) > 120 else result.reason
            print(f"         {reason}")

    scores = [r.score for r in report.results if r.score is not None]
    if scores:
        print(f"\n  Average Trajectory Score: {sum(scores) / len(scores):.2f}")
        print(f"  Goal Success target:      > 0.85")
    print("=" * 70)

    return report


if __name__ == "__main__":
    asyncio.run(run_trajectory_evals())
