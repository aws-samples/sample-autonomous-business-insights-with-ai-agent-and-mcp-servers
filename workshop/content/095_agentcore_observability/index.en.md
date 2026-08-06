---
title: "AgentCore Observability"
weight: 95
---

# AgentCore Observability — Tracing, Logging & Metrics

In this module, you'll set up full-stack observability for your agent system — distributed tracing with X-Ray, policy decision logging with CloudWatch, and performance metrics for tool calls.

## Why Observability for Agents?

AI agents are non-deterministic. The same question might trigger different tool call sequences. Without observability:

- *Why did that query take 15 seconds?* → Which tool call was slow?
- *Did the agent try to access unauthorized data?* → What did Cedar decide?
- *How much are we spending on Bedrock?* → Token usage per user/session
- *Is the agent hallucinating?* → Are responses faithful to tool outputs?

## The Observability Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│  AgentCore Observability                                             │
│                                                                      │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐ │
│  │   AWS X-Ray     │  │  CloudWatch Logs  │  │ CloudWatch Metrics │ │
│  │                 │  │                   │  │                    │ │
│  │  Distributed    │  │  Policy Decisions │  │  • Latency (p50,  │ │
│  │  traces across: │  │  (audit trail):   │  │    p99)            │ │
│  │                 │  │                   │  │  • ALLOW/DENY      │ │
│  │  Agent          │  │  • Who?           │  │    counts          │ │
│  │    → Gateway    │  │  • What tool?     │  │  • Token usage     │ │
│  │      → Policy   │  │  • Which params?  │  │  • Error rates     │ │
│  │        → Lambda │  │  • ALLOW/DENY?    │  │  • Cache hit rate  │ │
│  │          → Data │  │  • Matching rule?  │  │  • Active sessions │ │
│  │                 │  │  • Timestamp       │  │                    │ │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  CloudWatch Dashboard (unified view)                            │ │
│  │  ┌─────────────────────────────────────────────────────────┐   │ │
│  │  │  Policy Decisions        │  Tool Call Latency (p99)     │   │ │
│  │  │  ████ ALLOW (247)        │                              │   │ │
│  │  │  ██ DENY (18)            │  Equipment: ██████ 120ms     │   │ │
│  │  │                          │  IoT:       ████ 85ms        │   │ │
│  │  │  Deny Spike: 14:30 ⚠️    │  Analytics: ████████ 180ms  │   │ │
│  │  ├──────────────────────────┼─────────────────────────────┤   │ │
│  │  │  Token Usage / Hour      │  Recent Policy Denials       │   │ │
│  │  │                          │                              │   │ │
│  │  │  Sarah: ████████ 830/q   │  14:30 raj→Line4 DENY       │   │ │
│  │  │  Raj:   ████ 450/q       │  14:28 priya→M72 DENY       │   │ │
│  │  │  Priya: ███ 380/q        │  14:25 raj→Plant1 DENY      │   │ │
│  │  └──────────────────────────┴─────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Step 1: Trace a Complete Request (X-Ray)

Every request generates an end-to-end trace. Here's what a trace looks like for Sarah's query "Which lines need attention?":

```
Trace ID: 1-abc123-def456789
Total Duration: 3.2s
─────────────────────────────────────────────────────────────────────

│ AgentCore Runtime                                          3.2s │
├────────────────────────────────────────────────────────────────────
│  │ LLM Inference #1 (reasoning)                    1.1s   │
│  │ ██████████████████████████████░░░░░░░░░░░░░░░░░░░░░░   │
│  │ Tokens: 420 in / 85 out                                 │
│  │                                                          │
│  │ Gateway: detect_anomaly()                       0.4s    │
│  │ ├── JWT Validation                              5ms     │
│  │ ├── REQUEST Interceptor                         42ms    │
│  │ ├── Cedar Policy Evaluation                     <1ms    │
│  │ │   Result: ALLOW (sarah = plant_manager)               │
│  │ ├── Lambda: MfgInsights-IoTTools               320ms    │
│  │ │   └── Timestream Query                       280ms    │
│  │ └── RESPONSE Interceptor                        8ms     │
│  │                                                          │
│  │ LLM Inference #2 (need more data)              0.9s     │
│  │ ████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░   │
│  │                                                          │
│  │ Gateway: get_oee_trends()                       0.3s    │
│  │ ├── Cedar: ALLOW                               <1ms     │
│  │ ├── Lambda: MfgInsights-AnalyticsTools          250ms   │
│  │ │   └── Redshift Query                         210ms    │
│  │ └── RESPONSE Interceptor                        5ms     │
│  │                                                          │
│  │ LLM Inference #3 (synthesize)                   0.5s    │
│  │ █████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   │
│  │ Tokens: 650 in / 320 out                                │
│                                                             │
└────────────────────────────────────────────────────────────────────

Breakdown:
  LLM Inference:  2.5s  (78%)  ← Dominant cost
  Gateway + Policy: 0.1s  (3%)  ← Negligible overhead
  Tool Targets:    0.6s  (19%) ← Data queries
```

**Key insight:** LLM inference dominates latency (78%). Gateway + Cedar adds only 3% overhead. Optimization should focus on prompt efficiency and caching.

## Step 2: View Policy Decision Logs

Every Cedar evaluation is logged. Query recent denials:

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
  "request_id": "req-xyz789",
  "decision": "DENY",
  "evaluation_time_ms": 0.4,
  "principal": {
    "username": "raj.patel",
    "groups": ["line_supervisors"],
    "line_scope": "Line 7"
  },
  "action": "AnalyticsTarget___get_oee_trends",
  "context": {
    "input": {"line": "Line 4"}
  },
  "matching_policy": "forbid_line_scope",
  "reason": "Line 4 not in authorized scope [Line 7]"
}
```

This is your **compliance audit trail**. For every denied request, you can prove exactly who tried to access what, when, and which Cedar rule blocked it.

## Step 3: Monitor Real-Time Metrics

### Policy Decision Metrics

```
CloudWatch Metric: AgentCore/Gateway/PolicyDecisionCount

  Time     ALLOW   DENY
  14:00    32      2
  14:05    28      1
  14:10    35      0
  14:15    30      3
  14:20    27      1
  14:25    33      2
  14:30    25      8  ← Spike! Alert fires
  14:35    31      1

  ⚠️ Alert: DENY count > 5 in 5-min window at 14:30
     User: raj.patel (4 denials), unknown_user (4 denials)
     Action: Investigate — possible unauthorized probing
```

### Tool Call Latency Metrics

```
CloudWatch Metric: AgentCore/Gateway/ToolCallDuration

  Target                    p50      p99      Max
  ──────────────────────────────────────────────────
  MfgInsights-Equipment     85ms     180ms    420ms
  MfgInsights-IoT          120ms     310ms    890ms
  MfgInsights-Analytics    150ms     450ms    1.2s
  ──────────────────────────────────────────────────

  ⚠️ IoT target p99 degradation: 310ms → 890ms over 2 hours
     Cause: Timestream table scan (missing partition key)
```

### Token Usage Per User

```
CloudWatch Metric: AgentCore/Runtime/TokensUsed

  User          Queries/Day   Avg Tokens/Query   Est. Daily Cost
  ─────────────────────────────────────────────────────────────────
  sarah.chen        15           830 (complex)      ~$0.12
  raj.patel         25           450 (focused)      ~$0.11
  priya.nair        40           380 (simple)       ~$0.15
  ─────────────────────────────────────────────────────────────────

  Sarah: fewer queries but more tokens (multi-tool correlation)
  Priya: many queries but simple (single-tool lookups)
```

### Cache Hit Rate

```
CloudWatch Metric: AgentCore/Gateway/CacheHitRate

  Cache Tier         Hit Rate    Avg Latency (hit)    Savings
  ───────────────────────────────────────────────────────────────
  Edge (CloudFront)    12%         5ms                High
  Regional (ElastiCache) 34%      15ms               Medium
  Per-session          58%         <1ms               Highest
  ───────────────────────────────────────────────────────────────
  Combined: 62% of tool calls served from cache

  Top cached calls:
  - get_data_catalog() → 95% hit (rarely changes)
  - get_oee_trends(line="Line 7") → 70% hit (Raj asks daily)
  - detect_anomaly() → 40% hit (changes frequently)
```

## Step 4: Set Up the CloudWatch Dashboard

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
          "period": 60, "stat": "Sum"
        }
      },
      {
        "type": "metric",
        "properties": {
          "title": "Tool Call Latency (p99)",
          "metrics": [
            ["AgentCore/Gateway", "ToolCallDuration", "Target", "MfgInsights-EquipmentTools"],
            ["AgentCore/Gateway", "ToolCallDuration", "Target", "MfgInsights-IoTTools"],
            ["AgentCore/Gateway", "ToolCallDuration", "Target", "MfgInsights-AnalyticsTools"]
          ],
          "period": 300, "stat": "p99"
        }
      },
      {
        "type": "metric",
        "properties": {
          "title": "Token Usage by User",
          "metrics": [
            ["AgentCore/Runtime", "TokensUsed", "User", "sarah.chen"],
            ["AgentCore/Runtime", "TokensUsed", "User", "raj.patel"],
            ["AgentCore/Runtime", "TokensUsed", "User", "priya.nair"]
          ],
          "period": 3600, "stat": "Sum"
        }
      },
      {
        "type": "log",
        "properties": {
          "title": "Recent Policy Denials",
          "query": "fields @timestamp, principal.username, action, reason\n| filter decision = \"DENY\"\n| sort @timestamp desc\n| limit 20",
          "region": "us-east-1",
          "logGroupName": "/aws/agentcore/gateway/policy-decisions"
        }
      }
    ]
  }' --region us-east-1
```

## Step 5: Set Up Alerts

### Alert 1: High Deny Rate (Security)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "AgentCore-HighDenyRate" \
  --metric-name "PolicyDecisionCount" \
  --namespace "AgentCore/Gateway" \
  --dimensions Name=Decision,Value=DENY \
  --statistic Sum --period 300 \
  --evaluation-periods 2 --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:<account>:agentcore-alerts"
```

Fires when: > 10 DENY decisions in 10 minutes. Could indicate probing.

### Alert 2: Latency Degradation (Performance)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "AgentCore-HighLatency" \
  --metric-name "ToolCallDuration" \
  --namespace "AgentCore/Gateway" \
  --statistic p99 --period 300 \
  --evaluation-periods 3 --threshold 5000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:<account>:agentcore-alerts"
```

Fires when: p99 latency > 5 seconds for 15 minutes. Data source likely degraded.

### Alert 3: Token Budget Exceeded (Cost)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "AgentCore-TokenBudget" \
  --metric-name "TokensUsed" \
  --namespace "AgentCore/Runtime" \
  --statistic Sum --period 3600 \
  --evaluation-periods 1 --threshold 100000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:<account>:agentcore-alerts"
```

Fires when: > 100K tokens used in 1 hour across all users.

## Step 6: Trace a Denied Request

When Raj asks about Line 4, the trace shows the deny clearly:

```
Trace ID: 1-def789-abc123456
Total Duration: 0.8s (fast — no tool execution!)
─────────────────────────────────────────────────────────────────────

│ AgentCore Runtime                                          0.8s │
├────────────────────────────────────────────────────────────────────
│  │ LLM Inference (reasoning)                       0.7s    │
│  │ ████████████████████████████████████████████████████░   │
│  │ Decision: call get_oee_trends(line="Line 4")            │
│  │                                                          │
│  │ Gateway: get_oee_trends(line="Line 4")          0.06s   │
│  │ ├── JWT Validation                              5ms     │
│  │ ├── REQUEST Interceptor                         40ms    │
│  │ ├── Cedar Policy Evaluation                     <1ms    │
│  │ │   ┌──────────────────────────────────────┐            │
│  │ │   │ Result: ██ DENY                       │            │
│  │ │   │ Rule: forbid_line_scope               │            │
│  │ │   │ Reason: Line 4 ∉ scope [Line 7]      │            │
│  │ │   └──────────────────────────────────────┘            │
│  │ ├── Lambda Target: NOT CALLED (denied)                   │
│  │ └── Return: "Access denied: Line 4 not authorized"       │
│  │                                                          │
│  │ LLM Inference (adapt response)                  0.1s    │
│  │ "I don't have access to Line 4. I can show Line 7."     │
│                                                             │
└────────────────────────────────────────────────────────────────────

Key: Lambda target NEVER CALLED. Zero data exposure risk.
     Total Gateway overhead: 46ms. Cedar evaluation: <1ms.
```

## Step 7: Agent Reasoning Trace

X-Ray also captures the agent's reasoning steps:

```
Agent Reasoning Trace (sarah.chen — "Which lines need attention?")

Step  Action                        Duration  Result
────  ────────────────────────────  ────────  ──────────────────────────
1     LLM reasons: need overview    1.1s      Decides: call detect_anomaly()
2     Tool: detect_anomaly()        0.4s      Found: Machine 42 (temp+vib)
3     LLM reasons: need trends      0.9s      Decides: call get_oee_trends()
4     Tool: get_oee_trends()        0.3s      Found: Line 4 dropping, Line 9 dipping
5     LLM reasons: shared infra?    0.3s      Decides: call get_shared_infrastructure()
6     Tool: get_shared_infra()      0.2s      Found: coolant loop shared L4↔L9
7     LLM synthesizes               0.5s      Generates severity-ranked response

Total: 7 steps, 3.7s, 3 tool calls, 1 synthesis
Tokens: 1,480 input / 420 output = 1,900 total
Cost: ~$0.014 per query
```

## Observability Best Practices

| Practice | Why | How |
|----------|-----|-----|
| Log ALL deny decisions | Security audit trail | CloudWatch log group + 1yr retention |
| Alert on deny spikes | Early warning for probing | CloudWatch Alarm > threshold |
| Track p99 latency | User experience | Per-target metric + alert |
| Monitor token usage | Cost management | Per-user metric + budget alarm |
| Trace slow queries | Identify bottlenecks | X-Ray annotation filters |
| Cache hit rate | Cost + latency optimization | Gateway cache metrics |
| Retention policies | Compliance + cost | Logs: 1yr, Traces: 30 days |

## Key Takeaways

1. **LLM inference = 78% of latency** — Optimize prompts and caching, not Gateway
2. **Cedar = <1ms** — Policy adds negligible overhead
3. **Denied requests are fast** — No tool execution means shorter traces
4. **Full audit trail** — Every ALLOW/DENY logged with user, tool, params, rule
5. **Three alert types** — Security (deny spikes), Performance (latency), Cost (tokens)
6. **Cache saves money** — 62% hit rate means most repeated queries don't hit data sources

## Next Steps

Your system is fully observable. In the final modules, you'll clean up resources and review everything you've built.
