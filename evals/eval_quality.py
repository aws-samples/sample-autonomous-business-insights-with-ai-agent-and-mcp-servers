# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Response quality evaluation — faithfulness and helpfulness of agent answers.

Evaluates:
1. Faithfulness: Is the response grounded in actual tool outputs (not hallucinated)?
2. Helpfulness: Does it answer the manufacturing question usefully?
3. Correctness: Are the data points and conclusions accurate?

Run:
    python -m evals.eval_quality
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from strands_evals import Case, Experiment, eval_task
from strands_evals.evaluators import (
    CorrectnessEvaluator,
    FaithfulnessEvaluator,
    HelpfulnessEvaluator,
    OutputEvaluator,
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

MANUFACTURING_QUALITY_RUBRIC = """
Evaluate the response quality for a manufacturing insights query.

Score 1.0 if ALL of the following:
- The response directly answers the manufacturing question asked
- Data points cited (vibration levels, OEE percentages, dates) are specific and plausible
- The response provides actionable insight (not just raw data dumps)
- Technical terminology is used correctly (OEE, vibration mm/s, anomaly severity)
- The response synthesizes data from multiple sources when the question requires it

Score 0.5 if:
- The response partially answers the question but misses key data points
- OR the response is accurate but not actionable (just lists raw numbers)
- OR it answers correctly but misses the synthesis across data sources

Score 0.0 if:
- The response contains fabricated data points not from any tool output
- OR it fails to answer the core question
- OR it provides generic advice without referencing actual equipment/line data
"""


def load_quality_cases() -> list[Case]:
    """Load cases for quality evaluation — reuse tool routing cases (allowed queries)."""
    cases_path = Path(__file__).parent / "cases" / "tool_routing.json"
    with open(cases_path) as f:
        raw_cases = json.load(f)

    cases = []
    for i, raw in enumerate(raw_cases):
        cases.append(
            Case(
                case_id=f"quality_{i}",
                input=raw["input"],
                metadata=raw["metadata"],
            )
        )
    return cases


@eval_task()
def run_quality_query(case: Case):
    """Execute a query for quality assessment."""
    config = AppConfig()
    agent = ManufacturingInsightsAgent(config)

    user_key = case.metadata["user"]
    user = USER_MAP[user_key]

    response = agent.query(user, case.input)
    return response


async def run_quality_evals():
    """Run response quality evaluations."""
    cases = load_quality_cases()

    evaluators = [
        FaithfulnessEvaluator(),
        HelpfulnessEvaluator(),
        OutputEvaluator(rubric=MANUFACTURING_QUALITY_RUBRIC),
    ]

    experiment = Experiment(
        name="manufacturing_agent_quality",
        cases=cases,
        evaluators=evaluators,
    )

    logger.info("Running quality evaluation with %d cases...", len(cases))
    report = await experiment.run_evaluations_async(run_quality_query)

    # Print results grouped by evaluator
    print("\n" + "=" * 70)
    print("  Response Quality Evaluation Results")
    print("=" * 70)

    for result in report.results:
        status = "PASS" if result.test_pass else "FAIL"
        print(f"  [{status}] {result.case_id}: score={result.score:.2f}")
        if result.reason:
            # Truncate long reasons
            reason = result.reason[:120] + "..." if len(result.reason) > 120 else result.reason
            print(f"         {reason}")

    scores = [r.score for r in report.results if r.score is not None]
    if scores:
        print(f"\n  Average Quality Score: {sum(scores) / len(scores):.2f}")
        print(f"  Faithfulness target:   > 0.90")
        print(f"  Helpfulness target:    > 0.85")
    print("=" * 70)

    return report


if __name__ == "__main__":
    asyncio.run(run_quality_evals())
