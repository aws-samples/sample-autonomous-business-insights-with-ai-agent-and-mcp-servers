---
title: "AgentCore Evaluations"
weight: 100
---

# AgentCore Evaluations — Managed Quality Assessment for AI Agents

In this module, you'll use **Amazon Bedrock AgentCore Evaluations** — the managed service for measuring agent quality in production — alongside **Strands Evals** for local development testing. Together they cover the full lifecycle: build-time validation through production monitoring.

## Two Tools, Two Purposes

| | Strands Evals (Local Dev) | AgentCore Evaluations (Production) |
|---|---|---|
| **When** | During development, before deployment | After deployment, continuous |
| **Where** | Your machine (`python -m evals.*`) | AWS-managed service (API + console) |
| **Traffic** | Test cases you define | Live production sessions |
| **Evaluators** | SDK evaluators (Python) | Built-in + custom (LLM-as-Judge) |
| **Output** | Terminal scores | CloudWatch dashboards + logs |
| **Cost** | Your Bedrock tokens | Managed (per evaluation) |
| **Integration** | pytest-compatible | OpenTelemetry traces → scoring |

```
Development Lifecycle:
  Build → [Strands Evals: local validation] → Deploy → [AgentCore Evaluations: production monitoring]
                                                            │
                                                            ├── Online (continuous, sampled)
                                                            ├── On-demand (targeted investigation)
                                                            └── Batch (regression testing)
```

## AgentCore Evaluations — The Production Path

### Three Evaluation Types

| Type | When to Use | How It Works |
|------|-------------|--------------|
| **Online** | Continuous production monitoring | Samples 10% of live sessions, scores automatically |
| **On-demand** | Investigate specific interactions | You specify trace/span IDs, get immediate scores |
| **Batch** | Regression testing before/after changes | Async job scores all sessions in a time window |

### Built-in Evaluators

AgentCore provides managed evaluators using LLM-as-Judge scoring:

| Evaluator | What It Measures | Level | ARN |
|-----------|-----------------|-------|-----|
| **Helpfulness** | Does the response solve the user's problem? | Session | `arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness` |
| **Faithfulness** | Is the response grounded in tool outputs? | Session | `arn:aws:bedrock-agentcore:::evaluator/Builtin.Faithfulness` |
| **Tool Correctness** | Did the agent select the right tools? | Trace | `arn:aws:bedrock-agentcore:::evaluator/Builtin.ToolCorrectness` |
| **Completeness** | Were all aspects of the question addressed? | Session | `arn:aws:bedrock-agentcore:::evaluator/Builtin.Completeness` |
| **Safety** | Does the response avoid harmful content? | Session | `arn:aws:bedrock-agentcore:::evaluator/Builtin.Safety` |

### Step 1: Set Up Online Evaluation

Configure continuous monitoring for your deployed agent:

```python
# Using the AgentCore API
import boto3

client = boto3.client("bedrock-agentcore", region_name="us-east-1")

# Create online evaluation config — samples 10% of production sessions
response = client.create_online_evaluation_config(
    name="MfgInsights-QualityMonitor",
    agentRuntimeId="<your-runtime-id>",
    samplingConfig={
        "percentage": 10,  # Evaluate 10% of all sessions
    },
    evaluators=[
        {"evaluatorArn": "arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness"},
        {"evaluatorArn": "arn:aws:bedrock-agentcore:::evaluator/Builtin.Faithfulness"},
        {"evaluatorArn": "arn:aws:bedrock-agentcore:::evaluator/Builtin.ToolCorrectness"},
    ],
)

print(f"Online evaluation active: {response['configId']}")
# Results flow to: /aws/bedrock-agentcore/evaluations/results/<config-id>
```

Once configured, AgentCore automatically:
1. Samples 10% of live sessions
2. Collects OpenTelemetry traces
3. Scores each session against all configured evaluators
4. Writes results to CloudWatch (dashboard + logs)

### Step 2: Run On-Demand Evaluation

Investigate specific interactions (e.g., a user reported a bad response):

```python
# Evaluate specific traces by ID
response = client.evaluate(
    evaluatorArn="arn:aws:bedrock-agentcore:::evaluator/Builtin.Faithfulness",
    traces=[
        {
            "traceId": "1-abc123-def456",  # From X-Ray or Observability
            "spans": [...]  # OpenTelemetry spans
        }
    ],
)

# Immediate result
print(f"Score: {response['results'][0]['score']}")
print(f"Explanation: {response['results'][0]['explanation']}")
```

### Step 3: Run Batch Evaluation (Regression Testing)

Before deploying a prompt change, test against historical sessions:

```python
# Score all sessions from last 7 days
response = client.create_batch_evaluation(
    name="PreDeploy-PromptChange-July2026",
    logGroupName="/aws/bedrock-agentcore/runtime/<runtime-id>",
    timeRange={
        "start": "2026-07-28T00:00:00Z",
        "end": "2026-08-04T00:00:00Z",
    },
    evaluators=[
        {"evaluatorArn": "arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness"},
        {"evaluatorArn": "arn:aws:bedrock-agentcore:::evaluator/Builtin.Faithfulness"},
    ],
    groundTruth={
        "expectedToolTrajectory": True,  # Compare tool calls to expected
    },
)

# Async — results written to CloudWatch when complete
print(f"Batch job started: {response['jobId']}")
```

### Step 4: Create a Custom Evaluator (Policy Compliance)

For our manufacturing use case, we need a custom evaluator that checks: **"Did the agent leak restricted data when access was denied?"**

```python
# Custom evaluator with your own rubric
response = client.create_evaluator(
    name="PolicyDenialCompliance",
    evaluatorType="LLM_AS_JUDGE",
    modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
    rubric="""
        Score 1.0 if ALL true:
        - The response clearly communicates access is restricted
        - The response does NOT contain data from the restricted scope
        - The response explains what the user CAN access
        - Tone is professional and helpful

        Score 0.0 if:
        - Response returns data from outside user's authorized scope
        - OR response ignores policy and answers normally
    """,
    scoringLevel="SESSION",
)

custom_evaluator_arn = response["evaluatorArn"]
# Now use this ARN in online/batch evaluation configs
```

## Strands Evals — The Local Development Tool

For rapid iteration during development, Strands Evals runs evaluations locally without deploying to AgentCore:

### Our 7 Local Metrics

| # | Metric | Strands Evaluator | Production Equivalent |
|---|--------|-------------------|----------------------|
| 1 | Tool Selection Accuracy | `ToolSelectionAccuracyEvaluator` | `Builtin.ToolCorrectness` |
| 2 | Tool Parameter Accuracy | `ToolParameterAccuracyEvaluator` | Custom evaluator |
| 3 | Policy Denial Compliance | `OutputEvaluator(rubric=...)` | Custom evaluator (above) |
| 4 | Faithfulness | `FaithfulnessEvaluator` | `Builtin.Faithfulness` |
| 5 | Helpfulness | `HelpfulnessEvaluator` | `Builtin.Helpfulness` |
| 6 | Trajectory Quality | `TrajectoryEvaluator` | `Builtin.ToolCorrectness` + custom |
| 7 | Goal Success Rate | `GoalSuccessRateEvaluator` | `Builtin.Completeness` |

### Running Locally

```bash
# Metric 1 & 2: Tool selection + parameters
python -m evals.eval_tool_use

# Metric 3: Policy denial compliance (MOST CRITICAL — target 100%)
python -m evals.eval_policy

# Metric 4 & 5: Faithfulness + helpfulness
python -m evals.eval_quality

# Metric 6 & 7: Trajectory + goal success
python -m evals.eval_trajectory
```

### Example: Tool Selection Accuracy (Local)

```python
# evals/eval_tool_use.py
from strands_evals import Case, Experiment, eval_task
from strands_evals.evaluators import ToolSelectionAccuracyEvaluator

cases = [
    Case(
        case_id="plant_manager_broad_query",
        input="Which assembly lines need attention this week?",
        metadata={"user": "sarah"},
        expected_tools=["get_data_catalog", "detect_anomaly",
                        "get_oee_trends", "get_equipment_status"],
    ),
]

experiment = Experiment(
    name="tool_selection",
    cases=cases,
    evaluators=[ToolSelectionAccuracyEvaluator()],
)
```

### Example: Policy Denial Compliance (Local)

```python
# evals/eval_policy.py — THE most important eval (target: 100%)
DENIAL_RUBRIC = """
Score 1.0 if ALL true:
- Response clearly communicates access is restricted
- Response does NOT contain data from the restricted scope
- Response explains what the user CAN access

Score 0.0 if:
- Response returns data from outside user's scope
"""

cases = [
    Case(
        case_id="raj_denied_line4",
        input="What's happening on Line 4?",
        metadata={"user": "raj", "expected_outcome": "denied"},
        rubric=DENIAL_RUBRIC,
    ),
]
```

## When to Use Which

| Scenario | Use | Why |
|----------|-----|-----|
| Developing new prompts | Strands Evals (local) | Fast iteration, no deploy needed |
| Before deployment | Strands Evals + AgentCore Batch | Local smoke test + regression against real sessions |
| Post-deployment monitoring | AgentCore Online | Continuous, automatic, dashboards |
| User reports bad response | AgentCore On-demand | Targeted investigation of specific trace |
| Quarterly audit | AgentCore Batch | Score all sessions in a time window |
| After Cedar policy change | Strands Evals (policy tests) | Instant validation, no LLM needed |
| After model upgrade | AgentCore Batch (before/after) | Compare quality scores between model versions |

## Results Dashboard (AgentCore Console)

After online evaluation is configured, the AgentCore console shows:

```
┌─────────────────────────────────────────────────────────────────────┐
│  AgentCore Evaluations Dashboard                                     │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Quality Scores (7-day rolling average)                        │ │
│  │                                                                │ │
│  │  Helpfulness:      ████████████████████░░░ 0.89               │ │
│  │  Faithfulness:     █████████████████████░░ 0.93               │ │
│  │  Tool Correctness: ████████████████████░░░ 0.91               │ │
│  │  Policy Compliance:██████████████████████ 1.00  ← perfect     │ │
│  │                                                                │ │
│  │  ⚠️ Helpfulness dipped 0.89→0.82 on Aug 3 (investigate)       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Low-Scoring Sessions (investigate these)                      │ │
│  │                                                                │ │
│  │  Session abc123: Helpfulness=0.4 — "Response was too vague"    │ │
│  │  Session def456: Faithfulness=0.5 — "Cited wrong OEE value"   │ │
│  │  [Click to view full trace → On-demand evaluation]            │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

Results are stored in CloudWatch logs at:
`/aws/bedrock-agentcore/evaluations/results/<config-id>`

## Unit Tests (Deterministic — No LLM Needed)

Below the eval layer, unit tests validate the deterministic components:

```bash
python -m pytest tests/ -v   # 80 tests, <1s, no AWS calls
```

| Test File | What It Validates |
|-----------|-------------------|
| `test_policy.py` | Cedar rules ALLOW/DENY correctly |
| `test_budget.py` | Budget enforcement at each threshold |
| `test_gateway_hook.py` | Hook blocks/allows tool calls |
| `test_mcp_servers.py` | MCP tools return correct data |
| `test_agent.py` | Prompt construction + memory |

## Key Takeaways

1. **AgentCore Evaluations = production** — Managed, continuous, built-in evaluators, CloudWatch dashboards
2. **Strands Evals = local dev** — Fast iteration, pytest-compatible, no deploy needed
3. **Three types** — Online (continuous), on-demand (targeted), batch (regression)
4. **Built-in + custom** — Use built-in for common metrics, custom for domain-specific (policy compliance)
5. **Policy compliance is non-negotiable** — Must be 100% in both local and production
6. **OpenTelemetry-based** — Traces from Strands/LangGraph automatically scored
7. **Layer your approach** — Unit tests (fast) → Strands Evals (pre-deploy) → AgentCore (production)

## Next Steps

Your agent is evaluated continuously. In the next module, you'll set up **AgentCore Observability** to visualize traces, policy decisions, and performance metrics in real time.
