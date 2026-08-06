---
title: "AgentCore Harness"
weight: 55
---

# AgentCore Harness — Managed Deployment with Hard Cost Caps

In this module, you'll deploy your agent using AgentCore Harness — the managed wrapper that provides hard cost limits, session lifecycle management, and auto-instrumented observability without writing infrastructure code.

## What Is Harness?

Harness is the **deployment abstraction** between "I have agent code" and "it's running in production." You provide your Python agent code; Harness handles everything else.

| What You Provide | What Harness Manages |
|-----------------|---------------------|
| Agent code (Python zip) | microVM boot (<50ms cold start) |
| Model selection | Session lifecycle (create/reuse/destroy) |
| Cost limits config | Hard token/iteration caps per invocation |
| Gateway ID | Idle timeout (stop billing when unused) |
| Tags | Observability (auto-traces, no instrumentation) |

```
Without Harness:
  You manage: VM provisioning, session routing, cost tracking, OOM handling, tracing setup
  
With Harness:
  You configure: agent.zip + limits + tags
  Harness manages: everything else
```

## Why Harness Matters for Cost Control

Harness provides **Layer 1** of the three-layer cost model — hard limits that the agent cannot bypass:

```
┌────────────────────────────────────────────────────────────────────┐
│  LAYER 1: HARNESS (Hard Caps — per invocation)                      │
│                                                                     │
│  maxTokens: 5000           ← Agent STOPS if it tries to use more    │
│  maxIterations: 10         ← Reasoning loop forced to conclude      │
│  timeoutSeconds: 120       ← Wall-clock kill switch                 │
│  idleSessionTimeout: 300   ← Idle microVM released (saves memory $) │
│  maxLifetime: 3600         ← Session killed after 1 hour regardless │
│                                                                     │
│  These are ENFORCED BY THE PLATFORM. Not bypassable by the agent.   │
│  Not bypassable by prompt injection. Not bypassable by tool calls.  │
└────────────────────────────────────────────────────────────────────┘
```

## Step 1: Understand Per-Role Harness Limits

Open `deploy/agentcore/budget_config.json` — the single source of truth for all cost limits:

```json
{
  "global_defaults": {
    "max_tokens_per_invocation": 5000,
    "max_iterations_per_invocation": 10,
    "timeout_seconds": 120,
    "idle_session_timeout_seconds": 300,
    "max_session_lifetime_seconds": 3600
  },
  "role_limits": {
    "plant_manager": {
      "max_tokens_per_invocation": 10000,
      "max_iterations_per_invocation": 15,
      "daily_token_limit": 100000,
      "monthly_cost_limit_usd": 50.00,
      "description": "Complex cross-system correlation queries — needs higher budget"
    },
    "line_supervisor": {
      "max_tokens_per_invocation": 5000,
      "max_iterations_per_invocation": 10,
      "daily_token_limit": 50000,
      "monthly_cost_limit_usd": 25.00
    },
    "maintenance_technician": {
      "max_tokens_per_invocation": 3000,
      "max_iterations_per_invocation": 8,
      "daily_token_limit": 30000,
      "monthly_cost_limit_usd": 15.00
    }
  }
}
```

**Why different limits per role?**

- **Sarah (Plant Manager)**: Asks complex cross-system queries that require 4-6 tool calls and correlation — needs 10K tokens and 15 iterations
- **Raj (Line Supervisor)**: Focused on one line — 5K tokens and 10 iterations sufficient
- **Priya (Maintenance Technician)**: Simple machine lookups — 3K tokens and 8 iterations

## Step 2: Deploy the Harness

```bash
python deploy/agentcore/setup_harness.py --region us-east-1
```

Output:

```
  AgentCore Harness Setup — Cost-Controlled Deployment
  ════════════════════════════════════════════════════════
  Region: us-east-1

  Per-Role Limits (from budget_config.json):
  ────────────────────────────────────────────────────────
  Role                      maxTokens    maxIter    Daily Limit
  ────────────────────────────────────────────────────────
  plant_manager             10000        15         100000
  line_supervisor           5000         10         50000
  maintenance_technician    3000         8          30000

  Harness Configuration:
    Name:              MfgInsights-Harness
    Max Tokens:        5000 (per invocation, default)
    Max Iterations:    10 (per invocation, default)
    Timeout:           120s
    Idle Timeout:      300s
    Max Lifetime:      3600s
```

## Step 3: What Happens When maxTokens Is Hit

If Priya asks a complex query that requires more than 3000 tokens:

```
Priya: "Give me a full analysis of Machine 42 including maintenance history,
        vibration trends, parts inventory, and comparison to fleet average"

Agent reasoning:
  Iteration 1: Call get_sensor_readings(machine_id=42) → 450 tokens
  Iteration 2: Call get_maintenance_history(machine_id=42) → 380 tokens
  Iteration 3: Call check_parts_inventory(machine_id=42) → 320 tokens
  Iteration 4: Call get_oee_trends(line="Line 4") → 400 tokens
  Iteration 5: Synthesizing... → 850 tokens
  Iteration 6: More detail... → 600 tokens
  ─── TOKEN BUDGET HIT (3000) ───
  Agent forced to conclude with available data.

Response: "Based on what I've gathered so far: [partial synthesis]
           Note: Response may be abbreviated due to query complexity limits.
           For a more detailed analysis, please ask about specific aspects."
```

The agent doesn't crash — it gracefully concludes. The user gets partial results rather than nothing.

## Step 4: Harness vs Runtime — Trade-offs

| Aspect | Raw Runtime (Module 5) | Harness (this module) |
|--------|----------------------|-------------------------|
| Deployment | Manual CLI/SDK | Declarative config |
| Cost limits | You build them | Built-in (maxTokens, etc.) |
| Session timeout | You implement | Managed (idleSessionTimeout) |
| Observability | Manual X-Ray setup | Auto-instrumented |
| Cold start | Same (~50ms) | Same (~50ms) |
| Flexibility | Full control | Opinionated defaults |
| Tags | Manual per resource | Auto-propagated to Runtime + Memory |

**When to use Harness:** Production deployments where you want guardrails without writing infrastructure code.

**When to use Raw Runtime:** Development/testing where you need full control, or when Harness defaults don't fit.

## Step 5: Understand the Billing Model

Harness itself is **free** — you pay for what it uses:

| Capability | What You Pay For | What Determines Cost |
|-----------|-----------------|---------------------|
| Runtime (microVM) | CPU-seconds + peak memory/second | Agent reasoning time (not I/O wait) |
| Model inference | Input + output tokens per call | Prompt size × number of tool calls |
| Memory | Events written + records stored + retrievals | Conversation depth |
| Gateway | API operations + tool invocations | Number of tool calls |

**Key insight:** `idleRuntimeSessionTimeout` controls how long a microVM stays warm (billable for memory). Lower = cheaper but more cold starts.

```
idleSessionTimeout: 60   → Cheap but 50ms cold start every minute
idleSessionTimeout: 300  → Balanced (default)
idleSessionTimeout: 900  → Expensive but instant responses
```

## Key Takeaways

1. **Harness = hard caps** — Agent physically cannot exceed maxTokens/maxIterations
2. **Per-role configuration** — Complex queries get more budget, simple queries get less
3. **Platform-enforced** — Cannot be bypassed by the LLM, prompt injection, or tool manipulation
4. **Graceful degradation** — Agent concludes with partial results, not an error
5. **Free wrapper** — No additional charge; you pay for underlying services only
6. **Tags propagate** — Cost allocation works out of the box (Cost Explorer)

## Next Steps

Harness provides hard per-invocation caps (Layer 1). In the next module, you'll set up the **AgentCore Gateway** — the MCP router that connects your agent to all registered tool targets with security enforcement, caching, and interceptors.
