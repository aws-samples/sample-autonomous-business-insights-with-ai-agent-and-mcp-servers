+++
title = "AgentCore Observability"
weight = 110
+++

# AgentCore Observability — Tracing, Logging & Metrics

In this module, you'll set up full-stack observability for your agent system — distributed tracing with X-Ray, policy decision logging with CloudWatch, and performance metrics for tool calls.

## Why Observability for Agents?

AI agents are non-deterministic. The same question might trigger different tool call sequences. Without observability, you're flying blind:

- *Why did that query take 15 seconds?* → Which tool call was slow?
- *Did the agent try to access unauthorized data?* → What did Cedar decide?
- *How much are we spending on Bedrock?* → Token usage per user/session
- *Is the agent misbehaving?* → Did it call tools it shouldn't have tried?

```
┌─────────────────────────────────────────────────────────────────┐
│  Observability Stack                                             │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  X-Ray      │  │ CloudWatch  │  │  CloudWatch Metrics     │ │
│  │  Traces     │  │  Logs       │  │                         │ │
│  │             │  │             │  │  • Tool call latency    │ │
│  │ End-to-end  │  │ Policy      │  │  • ALLOW/DENY counts   │ │
│  │ request     │  │ decisions   │  │  • Token usage/session  │ │
│  │ flow        │  │ (audit)     │  │  • Error rates          │ │
│  │             │  │             │  │  • Active sessions      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Step 1: Understand the Tracing Model

Every request generates a trace through the full stack:

```
Trace: user-query-abc123
│
├── Segment: AgentCore Runtime
│   ├── Subsegment: LLM Inference (Claude Sonnet)
│   │   └── Duration: 1.2s, Tokens: 450 in / 380 out
│   ├── Subsegment: Tool Selection (reasoning)
│   │   └── Duration: 0.8s
│   └── Subsegment: Response Synthesis
│       └── Duration: 0.6s
│
├── Segment: AgentCore Gateway
│   ├── Subsegment: JWT Validation
│   │   └── Duration: 5ms, Result: VALID
│   ├── Subsegment: REQUEST Interceptor
│   │   └── Duration: 45ms, Claims: {role: line_supervisor}
│   ├── Subsegment: Cedar Policy Evaluation
│   │   └── Duration: <1ms, Result: ALLOW
│   └── Subsegment: Tool Target Invocation
│       └── Duration: 120ms, Target: MfgInsights-AnalyticsTools
│
└── Segment: Lambda Tool Target
    ├── Subsegment: Query Redshift
    │   └── Duration: 85ms, Rows: 4
    └── Subsegment: Format Response
        └── Duration: 12ms
```

## Step 2: View Policy Decision Logs

Every Cedar evaluation is logged to CloudWatch. View recent decisions:

```bash
aws logs filter-log-events \
  --log-group-name "/aws/agentcore/gateway/policy-decisions" \
  --filter-pattern "{ $.decision = \"DENY\" }" \
  --region us-east-1 \
  --limit 5 \
  --query "events[].message" --output text
```

Example log entry:

```json
{
  "timestamp": "2026-07-23T14:30:00.123Z",
  "decision": "DENY",
  "principal": "raj.patel",
  "action": "AnalyticsTarget___get_oee_trends",
  "resource": "gateway/mfg-insights",
  "context": {
    "input": {"line": "Line 4"},
    "user_groups": ["line_supervisors"],
    "user_line_scope": "Line 7"
  },
  "matching_policy": "forbid_line_scope",
  "evaluation_time_ms": 0.4,
  "request_id": "req-xyz789"
}
```

This is your **audit trail**. For compliance, you can prove exactly who tried to access what, when, and what the policy decided.

## Step 3: Monitor Tool Call Performance

Check tool call latency across all targets:

```bash
aws cloudwatch get-metric-statistics \
  --namespace "AgentCore/Gateway" \
  --metric-name "ToolCallDuration" \
  --dimensions Name=TargetName,Value=MfgInsights-AnalyticsTools \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average p99 \
  --region us-east-1
```

Key metrics to monitor:

| Metric | What It Measures | Alert Threshold |
|--------|-----------------|-----------------|
| `ToolCallDuration` | Time from Gateway to response | p99 > 5s |
| `PolicyDecisionCount` | ALLOW/DENY per minute | Spike in DENY |
| `TokensUsed` | LLM tokens per session | > 10K per query |
| `ActiveSessions` | Concurrent Runtime sessions | > 80% capacity |
| `InterceptorDuration` | REQUEST/RESPONSE Lambda time | p99 > 200ms |
| `CacheHitRate` | Gateway cache effectiveness | < 50% hit rate |

## Step 4: Set Up a CloudWatch Dashboard

Create a monitoring dashboard for the manufacturing insights system:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name "ManufacturingInsights-AgentCore" \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "properties": {
          "title": "Policy Decisions (ALLOW vs DENY)",
          "metrics": [
            ["AgentCore/Gateway", "PolicyDecisionCount", "Decision", "ALLOW"],
            ["AgentCore/Gateway", "PolicyDecisionCount", "Decision", "DENY"]
          ],
          "period": 60,
          "stat": "Sum"
        }
      },
      {
        "type": "metric",
        "properties": {
          "title": "Tool Call Latency (p50/p99)",
          "metrics": [
            ["AgentCore/Gateway", "ToolCallDuration", "TargetName", "MfgInsights-EquipmentTools"],
            ["AgentCore/Gateway", "ToolCallDuration", "TargetName", "MfgInsights-IoTTools"],
            ["AgentCore/Gateway", "ToolCallDuration", "TargetName", "MfgInsights-AnalyticsTools"]
          ],
          "period": 300,
          "stat": "p99"
        }
      },
      {
        "type": "log",
        "properties": {
          "title": "Recent Policy Denials",
          "query": "fields @timestamp, principal, action, matching_policy\n| filter decision = \"DENY\"\n| sort @timestamp desc\n| limit 20",
          "region": "us-east-1",
          "logGroupName": "/aws/agentcore/gateway/policy-decisions"
        }
      }
    ]
  }' \
  --region us-east-1
```

## Step 5: Trace a Complete Request

Use X-Ray to trace a full request lifecycle. In the AWS Console:

1. Open **X-Ray → Traces**
2. Filter by: `annotation.user = "raj.patel"`
3. Click a trace to see the full waterfall

You'll see:
- Total request time (e.g., 2.8s)
- LLM inference time (e.g., 1.2s — the dominant cost)
- Gateway overhead (e.g., 50ms — negligible)
- Cedar evaluation (e.g., <1ms — essentially free)
- Tool target execution (e.g., 120ms)

```
Total: 2.8s
├── LLM reasoning: 1.2s  ████████████░░░░░░░░░░░░  (43%)
├── Tool call 1:   0.4s  ████░░░░░░░░░░░░░░░░░░░░  (14%)
├── Tool call 2:   0.5s  █████░░░░░░░░░░░░░░░░░░░  (18%)
├── LLM synthesis: 0.6s  ██████░░░░░░░░░░░░░░░░░░  (21%)
└── Gateway/Policy: 0.1s █░░░░░░░░░░░░░░░░░░░░░░░  ( 4%)
```

## Step 6: Set Up Alerts

Create an alarm for unusual DENY spikes (potential unauthorized access attempts):

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "AgentCore-HighDenyRate" \
  --metric-name "PolicyDecisionCount" \
  --namespace "AgentCore/Gateway" \
  --dimensions Name=Decision,Value=DENY \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:<account>:agentcore-alerts" \
  --region us-east-1
```

This fires if more than 50 DENY decisions happen in 10 minutes — could indicate:
- A user probing boundaries
- A misconfigured agent trying unauthorized tools
- A policy change with unintended consequences

## Step 7: Token Usage Tracking

Monitor Bedrock token usage per user to manage costs:

```bash
aws cloudwatch get-metric-statistics \
  --namespace "AgentCore/Runtime" \
  --metric-name "TokensUsed" \
  --dimensions Name=User,Value=sarah.chen \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region us-east-1
```

| User | Avg Tokens/Query | Avg Queries/Day | Est. Daily Cost |
|------|-----------------|-----------------|-----------------|
| Sarah | 830 (complex queries) | 15 | ~$0.12 |
| Raj | 450 (focused queries) | 25 | ~$0.11 |
| Priya | 380 (simple lookups) | 40 | ~$0.15 |

## Observability Best Practices

1. **Log all DENY decisions** — They're your security audit trail
2. **Alert on DENY spikes** — Early warning for probing or misconfig
3. **Track p99 latency** — LLM inference is usually the bottleneck
4. **Monitor token usage** — Cost control per user/team
5. **Trace slow queries** — X-Ray pinpoints which tool or LLM step is slow
6. **Retention policies** — Keep policy logs for 1 year (compliance), traces for 30 days

## Key Takeaways

1. **Full-stack tracing** — X-Ray shows agent → gateway → interceptor → policy → tool
2. **Policy audit trail** — Every ALLOW/DENY logged with full context
3. **Sub-millisecond Cedar** — Policy evaluation adds negligible latency
4. **LLM dominates latency** — Focus optimization on prompt efficiency and caching
5. **Cost visibility** — Token usage per user/session enables chargeback
6. **Alerting on anomalies** — DENY spikes or latency outliers trigger notifications

## Next Steps

Your system is observable and auditable. In the final modules, you'll clean up resources and review what you've built.
