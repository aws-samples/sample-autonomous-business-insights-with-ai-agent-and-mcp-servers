---
title: "Cost Management"
weight: 85
---

# Cost Management — Per-User Budget Enforcement with Cedar + DynamoDB

In this module, you'll implement three-layer cost governance: Harness hard caps (Layer 1), Cedar per-user daily budgets (Layer 2), and CloudWatch visibility + alerts (Layer 3). This is the most requested enterprise capability.

## The Three-Layer Cost Model

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1: HARNESS (per invocation — hard stop)                       │
│  maxTokens: 5000 | maxIterations: 10 | timeout: 120s                │
│  → Agent physically cannot exceed. Platform-enforced.                │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2: CEDAR AT GATEWAY (per user/day — graduated)                │
│  80% → Warn (log) | 90% → Throttle (delay) | 100% → Block (deny)   │
│  → DynamoDB atomic counter + Cedar forbid policy                     │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 3: OBSERVABILITY (visibility — after the fact)                │
│  CloudWatch: tokens/user/day, cost/team/month, trend dashboards      │
│  → Enable chargeback, budgeting, anomaly detection                   │
└─────────────────────────────────────────────────────────────────────┘
```

Why three layers? Because each catches different failure modes:

| Layer | Catches | Example |
|-------|---------|---------|
| Harness | Single runaway query | LLM in infinite reasoning loop |
| Cedar | User consuming too much over a day | 100 normal queries still exceed budget |
| Observability | Team/org spending trends | Department costs growing 3x month-over-month |

## Step 1: Deploy the Budget Infrastructure

```bash
python deploy/agentcore/setup_budgets.py --region us-east-1
```

This creates:
- DynamoDB table (`MfgInsights-BudgetCounters`) for atomic token counters
- Seeds budget limits per role
- CloudWatch alarm for budget warnings

Output:

```
  Budget Infrastructure Ready!
  ════════════════════════════════════════════════════════

  Configured Limits:
  Role                      Daily Tokens    Monthly USD
  ──────────────────────────────────────────────────────
  plant_manager                100,000        $50.00
  line_supervisor               50,000        $25.00
  maintenance_technician        30,000        $15.00

  Enforcement Mode: enforce
    80% → Warn  | 90% → Throttle  | 100% → Block
```

## Step 2: Understand the DynamoDB Counter

Every tool call increments an atomic counter per user per day:

```
Table: MfgInsights-BudgetCounters
────────────────────────────────────────────────────────────────────
  user_id (PK)      date (SK)     daily_token_count   invocation_count
  ─────────────────────────────────────────────────────────────────
  sarah.chen        2026-08-05    4,200               12
  raj.patel         2026-08-05    1,850               8
  priya.nair        2026-08-05    28,500              42    ← Approaching limit!
  ─────────────────────────────────────────────────────────────────
```

**Why DynamoDB?**
- **Atomic increment** — `ADD :tokens` is lock-free, handles concurrent queries
- **Single-digit ms latency** — No perceptible delay on tool calls
- **Pay-per-request** — Zero cost when idle
- **TTL** — Old records auto-deleted after 90 days

The REQUEST interceptor reads this counter before every tool call. The RESPONSE interceptor increments it after every successful call.

## Step 3: The Cedar Budget Policy

Open `deploy/agentcore/cedar_policies/forbid_budget_exceeded.cedar`:

```cedar
// Block tool calls when user's daily token budget is exhausted.
// The REQUEST interceptor injects _budget_context from DynamoDB.
// Cedar evaluates deterministically: same budget state → same decision.

forbid(
    principal is AgentCore::OAuthUser,
    action,
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    context.input has _budget_context &&
    context.input._budget_context has daily_token_count &&
    context.input._budget_context has daily_token_limit &&
    context.input._budget_context.daily_token_count >=
        context.input._budget_context.daily_token_limit
};
```

This is the same Cedar pattern as scope enforcement — just checking a different field. The agent cannot bypass it because:
1. The counter is in DynamoDB (agent can't modify)
2. Cedar evaluates at the Gateway (agent can't skip)
3. Forbid overrides all permits (deterministic)

## Step 4: How the REQUEST Interceptor Injects Budget

The interceptor (already deployed in Module 6) adds a budget read:

```python
# deploy/agentcore/lambda_functions/request_interceptor.py (budget addition)

# After extracting user_context from JWT...
# Read budget counter from DynamoDB
budget_table = boto3.resource("dynamodb").Table("MfgInsights-BudgetCounters")
today = date.today().isoformat()

response = budget_table.get_item(Key={"user_id": username, "date": today})
item = response.get("Item", {})

budget_context = {
    "daily_token_count": int(item.get("daily_token_count", 0)),
    "daily_token_limit": get_limit_for_role(role),  # From DynamoDB LIMITS record
    "invocation_count": int(item.get("invocation_count", 0)),
}

# Inject into tool arguments (Cedar can read it)
body["params"]["arguments"]["_budget_context"] = budget_context
```

Cedar then evaluates: "Is `daily_token_count >= daily_token_limit`?" → If yes, DENY.

## Step 5: Graduated Enforcement (Not Just Block)

The system doesn't just hard-block at 100%. It has three graduated responses:

| Budget Used | Enforcement | What Happens |
|-------------|------------|--------------|
| 0-79% | None | Normal execution |
| 80-89% | **Warn** | Log warning, continue execution |
| 90-99% | **Throttle** | Add 2s delay between tool calls |
| 100%+ | **Block** | Cedar DENY — tool call rejected |

The warn and throttle are handled by the interceptor (before Cedar evaluates). Cedar only fires the hard block at 100%.

```python
# In request interceptor:
percent_used = daily_count / daily_limit

if percent_used >= 0.9:
    # Throttle: add artificial delay to slow consumption
    time.sleep(2)
    logger.warning(f"THROTTLE: {username} at {percent_used:.0%} budget")

elif percent_used >= 0.8:
    logger.info(f"WARN: {username} at {percent_used:.0%} budget")

# Cedar handles the hard block at 100%
```

## Step 6: Test Budget Enforcement

Run the budget tests:

```bash
python -m pytest tests/test_budget.py -v
```

```
tests/test_budget.py::TestBudgetManager::test_initial_budget_status_is_clean PASSED
tests/test_budget.py::TestBudgetManager::test_increment_usage PASSED
tests/test_budget.py::TestBudgetManager::test_budget_check_under_limit PASSED
tests/test_budget.py::TestBudgetManager::test_budget_check_exceeded PASSED
tests/test_budget.py::TestBudgetManager::test_budget_warning_at_80_percent PASSED
tests/test_budget.py::TestBudgetManager::test_budget_throttle_at_90_percent PASSED
tests/test_budget.py::TestBudgetManager::test_budget_block_at_100_percent PASSED
tests/test_budget.py::TestBudgetManager::test_different_limits_per_role PASSED
tests/test_budget.py::TestBudgetManager::test_reset_daily_usage PASSED
tests/test_budget.py::TestBudgetManager::test_update_limits PASSED
============================== 17 passed ==============================
```

## Step 7: Try It in the Demo

In the Streamlit UI, as Priya, keep asking questions until you approach the budget:

```
> What's the vibration on Machine 42?        → 450 tokens
> Show me maintenance history                 → 380 tokens
> Are bearings in stock?                      → 320 tokens
> ... (many more queries)
```

At 80%: You'll see a warning in the logs.
At 90%: Responses will be slightly delayed (throttled).
At 100%: "Daily token budget exceeded. Budget resets at midnight UTC."

## Step 8: Admin Workflow — Changing Limits

One file, one command:

```bash
# 1. Edit the config
vim deploy/agentcore/budget_config.json
# Change maintenance_technician.daily_token_limit from 30000 to 50000

# 2. Deploy the change
python deploy/agentcore/setup_budgets.py --region us-east-1

# Result: DynamoDB updated, Cedar policy regenerated, alarms adjusted
```

No code changes. No redeployment of Lambda. No agent restart. The next tool call picks up the new limit automatically.

## Step 9: Admin UI (Streamlit)

The Streamlit app includes an **Admin** tab for budget management:

- **View current usage** — tokens consumed per user today
- **Budget utilization** — visual bars (green/yellow/red) per user
- **Edit limits** — change daily/monthly caps per role
- **Reset counters** — clear a user's daily count (emergency)
- **Enforcement mode** — toggle between audit (log only) and enforce (block)

## Trade-offs and Design Decisions

| Decision | Alternative | Why We Chose This |
|----------|-------------|-------------------|
| DynamoDB for counters | S3 JSON file | Atomic increments, no race conditions at scale |
| Daily reset (midnight UTC) | Rolling 24-hour window | Simpler, predictable, users understand "daily" |
| Cedar for block enforcement | Interceptor-only | Deterministic, auditable, consistent with scope model |
| Per-role limits | Per-user limits | Simpler admin (3 configs vs N configs). Per-user possible via DynamoDB |
| Graduated (warn→throttle→block) | Binary (allow/deny) | Better UX — agent degrades gracefully, doesn't cliff |
| Single config file | Separate configs per layer | Admin manages ONE file, deploys to ALL places |

## Complete Request Flow with Budget

```
1. User asks question → Agent decides to call tool
2. Agent → Gateway → REQUEST Interceptor
   └── Read DynamoDB: {daily_count: 28500, limit: 30000}
   └── Inject _budget_context into args
   └── percent=95% → THROTTLE (2s delay, log warning)
3. Gateway → Cedar Policy Engine
   └── forbid_budget_exceeded: 28500 < 30000 → NO match
   └── Result: ALLOW (not yet at 100%)
4. Tool executes → returns result
5. RESPONSE Interceptor
   └── Increment DynamoDB: ADD 450 tokens → {28950}
6. Response → Agent → User

Next call: 28950 + 450 = 29400 (still under)
Call after: 29400 + 600 = 30000 → Cedar BLOCKS
```

## Key Takeaways

1. **Three layers** — Harness (per-query hard cap) + Cedar (per-user daily) + Observability (visibility)
2. **Single config file** — `budget_config.json` is the admin's one-stop shop
3. **DynamoDB atomic counters** — Correct under concurrency, single-digit ms
4. **Cedar is the enforcement point** — Same pattern as scope control, same guarantees
5. **Graduated response** — Warn → throttle → block (not just binary cutoff)
6. **Agent-proof** — LLM cannot manipulate counters or bypass Cedar evaluation
7. **Budget resets daily** — Predictable for users and admins
8. **Zero agent code changes** — Budget enforcement is entirely at Gateway + interceptor level

## Next Steps

Your cost controls are in place. In the next module, you'll write Cedar policies for data access control (which uses the same evaluation pattern you just learned here).
