+++
title = "AgentCore Evaluations"
weight = 100
+++

# AgentCore Evaluations — Testing & Validation

In this module, you'll systematically validate that policy enforcement works correctly, the agent produces accurate responses, and access boundaries hold across all personas.

## Why Evaluate?

AI agents introduce non-determinism (the LLM), but their guardrails must be deterministic. Evaluations verify:

- **Policy correctness** — Cedar rules ALLOW/DENY the right things
- **Agent behavior** — Responses are accurate and scope-aware
- **Regression safety** — New policies don't break existing access

```
┌────────────────────────────────────────────────────────────┐
│  Evaluation Layers                                          │
│                                                             │
│  Layer 1: Policy Unit Tests (deterministic)                 │
│  → Does Cedar produce correct ALLOW/DENY for known inputs?  │
│                                                             │
│  Layer 2: Integration Tests (deterministic)                 │
│  → Does Gateway + Policy + Lambda work end-to-end?          │
│                                                             │
│  Layer 3: Agent Behavior Tests (probabilistic)              │
│  → Does the agent produce correct, scope-aware responses?   │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

## Step 1: Run Policy Unit Tests

These test the policy engine in isolation — no network calls, no LLM:

```bash
python -m pytest tests/test_policy.py -v
```

Expected output:

```
tests/test_policy.py::test_sarah_full_access PASSED
tests/test_policy.py::test_sarah_all_tools_allowed PASSED
tests/test_policy.py::test_raj_line7_allowed PASSED
tests/test_policy.py::test_raj_line4_denied PASSED
tests/test_policy.py::test_raj_plant1_denied PASSED
tests/test_policy.py::test_priya_machine42_allowed PASSED
tests/test_policy.py::test_priya_machine72_denied PASSED
tests/test_policy.py::test_priya_line7_denied PASSED
tests/test_policy.py::test_deny_by_default_no_permit PASSED
tests/test_policy.py::test_forbid_overrides_permit PASSED
```

## Step 2: Explore the Policy Test Cases

Open `tests/test_policy.py`:

```python
def test_raj_line4_denied(policy_engine, raj_user):
    """Raj (line_supervisor, scope=Line 7) denied Line 4 access."""
    decision = policy_engine.evaluate(
        user=raj_user,
        tool_name="get_oee_trends",
        params={"line": "Line 4"},
    )
    assert decision.allowed is False
    assert "Line 4" in decision.reason


def test_priya_machine42_allowed(policy_engine, priya_user):
    """Priya (maintenance_tech, scope=Machine 41-45) allowed Machine 42."""
    decision = policy_engine.evaluate(
        user=priya_user,
        tool_name="get_sensor_readings",
        params={"machine_id": 42},
    )
    assert decision.allowed is True
```

These are fast, deterministic, and require no AWS resources.

## Step 3: Run Gateway Hook Tests

These test the Strands hook that simulates Gateway behavior locally:

```bash
python -m pytest tests/test_gateway_hook.py -v
```

```
tests/test_gateway_hook.py::test_hook_blocks_denied_tool PASSED
tests/test_gateway_hook.py::test_hook_allows_permitted_tool PASSED
tests/test_gateway_hook.py::test_hook_cancels_with_reason PASSED
tests/test_gateway_hook.py::test_hook_does_not_cancel_allowed PASSED
```

## Step 4: Run MCP Server Tests

Validate that MCP tools return correct data:

```bash
python -m pytest tests/test_mcp_servers.py -v
```

```
tests/test_mcp_servers.py::test_equipment_status_returns_data PASSED
tests/test_mcp_servers.py::test_equipment_status_filters_by_line PASSED
tests/test_mcp_servers.py::test_sensor_readings_validates_machine_id PASSED
tests/test_mcp_servers.py::test_detect_anomaly_returns_alerts PASSED
tests/test_mcp_servers.py::test_oee_trends_returns_weekly_data PASSED
tests/test_mcp_servers.py::test_parts_inventory_checks_reorder PASSED
```

## Step 5: Run the Full AgentCore Integration Test

This hits the deployed Gateway with real JWT tokens and validates end-to-end:

```bash
python deploy/agentcore/test_agentcore.py --region us-east-1
```

The test matrix:

```
╔══════════════════════════════════════════════════════════════════════════╗
║  AgentCore Integration Test Results                                      ║
╠══════════════╦═══════════════════╦════════════════════╦══════╦═══════════╣
║  User        ║  Tool             ║  Args              ║ Exp  ║  Result   ║
╠══════════════╬═══════════════════╬════════════════════╬══════╬═══════════╣
║  sarah.chen  ║  get_equipment    ║  {"line":"Line 4"} ║ ALLOW║  ALLOW ✅ ║
║  sarah.chen  ║  get_sensor       ║  {"machine":72}    ║ ALLOW║  ALLOW ✅ ║
║  sarah.chen  ║  get_oee_trends   ║  {"line":"Line 9"} ║ ALLOW║  ALLOW ✅ ║
║  raj.patel   ║  get_equipment    ║  {"line":"Line 7"} ║ ALLOW║  ALLOW ✅ ║
║  raj.patel   ║  get_oee_trends   ║  {"line":"Line 7"} ║ ALLOW║  ALLOW ✅ ║
║  raj.patel   ║  get_equipment    ║  {"line":"Line 4"} ║ DENY ║  DENY  ✅ ║
║  raj.patel   ║  get_oee_trends   ║  {"line":"Line 4"} ║ DENY ║  DENY  ✅ ║
║  priya.nair  ║  get_sensor       ║  {"machine":42}    ║ ALLOW║  ALLOW ✅ ║
║  priya.nair  ║  get_sensor       ║  {"machine":72}    ║ DENY ║  DENY  ✅ ║
║  priya.nair  ║  get_oee_trends   ║  {"line":"Line 4"} ║ ALLOW║  ALLOW ✅ ║
║  priya.nair  ║  get_oee_trends   ║  {"line":"Line 7"} ║ DENY ║  DENY  ✅ ║
╚══════════════╩═══════════════════╩════════════════════╩══════╩═══════════╝

  Result: 11/11 passed ✅
```

## Step 6: Test Agent Behavior (Probabilistic)

Run the agent test that validates the LLM handles denials gracefully:

```bash
python -m pytest tests/test_agent.py -v
```

```
tests/test_agent.py::test_agent_builds_prompt_with_identity PASSED
tests/test_agent.py::test_agent_includes_memory_context PASSED
tests/test_agent.py::test_agent_handles_policy_denial_gracefully PASSED
```

The graceful denial test verifies that when a tool call is blocked, the agent:
1. Does NOT retry the same tool with the same parameters
2. Explains the scope limitation to the user
3. Offers an alternative within the user's scope

## Step 7: Write Your Own Evaluation

Add a new test case to verify a custom scenario:

```python
# In tests/test_policy.py

def test_raj_no_scope_param_allowed(policy_engine, raj_user):
    """Raj calling a tool with no line param should be allowed.
    (Cedar forbid only fires when context.input has line)"""
    decision = policy_engine.evaluate(
        user=raj_user,
        tool_name="detect_anomaly",
        params={},  # No line parameter
    )
    assert decision.allowed is True
```

Run it:

```bash
python -m pytest tests/test_policy.py::test_raj_no_scope_param_allowed -v
```

This tests an important edge case: `detect_anomaly()` without parameters returns all anomalies. The forbid rule doesn't fire because `context.input has line` is false. In production, you might want a separate policy to handle this.

## Step 8: Test Unauthenticated Access

Verify that requests without a JWT are denied:

```bash
curl -s -X POST \
  "https://<your-gateway-id>.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_equipment_status"},"id":1}' \
  | python -m json.tool
```

Expected: `"Tool Execution Denied: No policy applies"` — deny-by-default with no authenticated principal.

## Evaluation Strategy Summary

| Layer | What It Tests | Speed | Deterministic? |
|-------|---------------|-------|---------------|
| Policy unit tests | Cedar logic | <1s | Yes |
| Hook tests | Local simulation | <1s | Yes |
| MCP server tests | Tool logic | <2s | Yes |
| Gateway integration | End-to-end | ~5s | Yes |
| Agent behavior | LLM responses | ~30s | Mostly |

{{% notice tip %}}
Run policy and hook tests on every code change. Run gateway integration tests before each deployment. Run agent behavior tests weekly or after prompt changes.
{{% /notice %}}

## Key Takeaways

1. **Layer your tests** — Policy (fast, deterministic) → Integration → Agent behavior
2. **Test the deny path** — It's more important to verify blocks than allows
3. **Edge cases matter** — Missing parameters, empty scopes, expired tokens
4. **Agent graceful degradation** — Verify the LLM handles denials well
5. **Regression testing** — New policies must not break existing access patterns

## Next Steps

Your system is validated. In the next module, you'll set up **AgentCore Observability** — tracing every request, logging policy decisions, and monitoring agent performance.
