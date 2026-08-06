+++
title = "AgentCore Policy (Cedar)"
weight: 75
+++

# AgentCore Policy — Cedar-Based Deterministic Authorization

In this module, you'll write and deploy Cedar policies that enforce fine-grained access control. You'll understand the evaluation model, test permit/deny scenarios, and see why Cedar is fundamentally different from LLM-based guardrails.

## Why Cedar?

| Approach | Deterministic? | Bypassable? | Auditable? | Speed |
|----------|---------------|-------------|------------|-------|
| Prompt instruction | No | Yes (injection) | No | N/A |
| LLM guardrail | No | Sometimes | Partially | 100ms+ |
| **Cedar policy** | **Yes** | **No** | **Yes** | **<1ms** |

Cedar is a policy language developed by AWS and [formally verified](https://www.cedarpolicy.com/). Same input always produces the same decision. The LLM cannot influence or bypass it.

## Cedar Evaluation Model

```
┌────────────────────────────────────────────────────────────┐
│  Cedar Evaluation (runs for EVERY tool call)                │
│                                                             │
│  Input:                                                     │
│    principal = user identity (from JWT)                     │
│    action = tool being called                               │
│    resource = gateway ARN                                   │
│    context = tool arguments + user attributes               │
│                                                             │
│  Evaluation:                                                │
│    1. Evaluate ALL policies simultaneously                  │
│    2. If ANY forbid matches → DENY (forbid overrides all)   │
│    3. If permit matches and no forbid → ALLOW               │
│    4. If nothing matches → DENY (deny-by-default)           │
│                                                             │
│  Output: ALLOW or DENY + reason                             │
└────────────────────────────────────────────────────────────┘
```

Three rules to remember:
1. **Deny by default** — No matching permit = DENY
2. **Forbid overrides permit** — One forbid match blocks regardless
3. **All policies evaluate** — No short-circuit; every policy checked

## Step 1: Explore the Cedar Policies

The policies are in `deploy/agentcore/cedar_policies/`:

```bash
ls deploy/agentcore/cedar_policies/
```

```
forbid_equipment_scope.cedar
forbid_line_scope.cedar
forbid_plant_scope.cedar
permit_all.cedar
```

### permit_all.cedar — The Baseline

```cedar
// Baseline: allow all authenticated users to invoke tools.
// Without this, deny-by-default blocks everything.
permit(
    principal,
    action,
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
);
```

This permits **any** authenticated principal to call **any** action. Without it, nothing works.

### forbid_line_scope.cedar — Line Supervisors

```cedar
// Line supervisors denied access to lines outside their scope.
forbid(
    principal is AgentCore::OAuthUser,
    action in [
        AgentCore::Action::"EquipmentTarget___get_equipment_status",
        AgentCore::Action::"EquipmentTarget___get_shared_infrastructure",
        AgentCore::Action::"IoTTarget___detect_anomaly",
        AgentCore::Action::"AnalyticsTarget___get_oee_trends",
        AgentCore::Action::"AnalyticsTarget___get_quality_metrics"
    ],
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    context.input has line &&
    principal.hasTag("cognito:groups") &&
    principal.getTag("cognito:groups") like "*line_supervisors*" &&
    principal.hasTag("custom:line_scope") &&
    !(principal.getTag("custom:line_scope") like ("*" + context.input.line + "*"))
};
```

Reading this in English: "If a user in the `line_supervisors` group calls one of these tools with a `line` parameter, and that line is NOT found in their `custom:line_scope`, DENY."

### forbid_equipment_scope.cedar — Maintenance Technicians

```cedar
// Maintenance technicians denied access to machines outside their scope.
forbid(
    principal is AgentCore::OAuthUser,
    action in [
        AgentCore::Action::"EquipmentTarget___get_equipment_status",
        AgentCore::Action::"EquipmentTarget___get_maintenance_history",
        AgentCore::Action::"IoTTarget___get_sensor_readings"
    ],
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    context.input has machine_id &&
    principal.hasTag("cognito:groups") &&
    principal.getTag("cognito:groups") like "*maintenance_technicians*" &&
    principal.hasTag("custom:equipment_scope") &&
    !(principal.getTag("custom:equipment_scope") like
        ("*Machine " + context.input.machine_id + "*"))
};
```

### forbid_plant_scope.cedar — Cross-Plant Restriction

```cedar
// All non-admin users denied access to plants outside their scope.
forbid(
    principal is AgentCore::OAuthUser,
    action,
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    context.input has plant &&
    principal.hasTag("custom:plant_scope") &&
    !(principal.getTag("custom:plant_scope") like ("*" + context.input.plant + "*"))
};
```

## Step 2: Deploy the Policy Engine

```bash
python deploy/agentcore/setup_policy.py --region us-east-1 --mode ENFORCE
```

Expected output:

```
✅ Created Policy Engine: <policy-engine-id> (mode: ENFORCE)
✅ Created policy: permit_all
✅ Created policy: forbid_line_scope
✅ Created policy: forbid_equipment_scope
✅ Created policy: forbid_plant_scope
✅ Attached Policy Engine to Gateway: <gateway-id>
```

### Policy Engine Modes

| Mode | Behavior | Use When |
|------|----------|----------|
| `MONITOR` | Logs decisions but allows all | Testing new policies |
| `ENFORCE` | Actually blocks denied requests | Production |

{{% notice tip %}}
Start in MONITOR mode when developing new policies. Check CloudWatch logs for unexpected denials before switching to ENFORCE.
{{% /notice %}}

## Step 3: Walk Through an Evaluation

Let's trace what happens when **Raj calls `get_oee_trends(line="Line 4")`**:

```
Input to Cedar:
  principal: OAuthUser {
    tags: {
      "cognito:groups": "line_supervisors",
      "custom:role": "line_supervisor",
      "custom:line_scope": "Line 7"
    }
  }
  action: "AnalyticsTarget___get_oee_trends"
  resource: Gateway::"arn:aws:...:gateway/mfg-insights"
  context.input: { "line": "Line 4" }

Evaluation:
  permit_all → matches (PERMIT candidate)

  forbid_line_scope:
    - action in list? YES (get_oee_trends is listed)
    - context.input has line? YES ("Line 4")
    - principal in line_supervisors? YES
    - "Line 7" like "*Line 4*"? NO → scope check FAILS
    → FORBID MATCHES

  Result: FORBID overrides PERMIT → DENY
  Reason: "Line 4 not in authorized line_scope (Line 7)"
```

The MCP server is **never called**. Raj gets a policy denial message.

## Step 4: Trace an ALLOWED Evaluation

Now **Raj calls `get_oee_trends(line="Line 7")`**:

```
Evaluation:
  permit_all → matches (PERMIT candidate)

  forbid_line_scope:
    - action in list? YES
    - context.input has line? YES ("Line 7")
    - principal in line_supervisors? YES
    - "Line 7" like "*Line 7*"? YES → scope check PASSES
    → forbid condition NOT met (no forbid)

  Result: PERMIT matched, no FORBID → ALLOW
```

Tool executes normally.

## Step 5: Understand Why Forbid Overrides Permit

This is Cedar's key security property. Consider this scenario:

```
Policy 1: permit(principal, action, resource)     → PERMIT
Policy 2: forbid(principal, action, ...) when {   → FORBID
              context.input has line &&
              !(line in scope)
           }
```

Even though Policy 1 says "allow everything," Policy 2's forbid wins. This means:
- You can start with a broad permit and add specific forbids
- Accidental over-permitting is prevented by explicit forbids
- Adding new tools doesn't bypass existing restrictions

## Step 6: Verify Policy Engine Status

```bash
aws bedrock-agentcore get-policy-engine \
  --policy-engine-id <your-policy-engine-id> \
  --region us-east-1
```

Expected: `"mode": "ENFORCE"`, `"status": "ACTIVE"`

## Step 7: Test Policy Enforcement

Run the full test suite:

```bash
python deploy/agentcore/test_agentcore.py --region us-east-1
```

Expected:

```
  User            Tool              Args             Expected  Actual  Status
  sarah.chen      get_equipment     {"line":"L4"}    ALLOW     ALLOW   ✅
  raj.patel       get_equipment     {"line":"L7"}    ALLOW     ALLOW   ✅
  raj.patel       get_equipment     {"line":"L4"}    DENY      DENY    ✅
  priya.nair      get_sensor        {"machine":42}   ALLOW     ALLOW   ✅
  priya.nair      get_sensor        {"machine":72}   DENY      DENY    ✅
```

## Writing New Cedar Policies

To add a new restriction (e.g., time-based access):

```cedar
// Example: Deny access outside business hours (8am-6pm)
forbid(
    principal is AgentCore::OAuthUser,
    action,
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    context.request_time.hour < 8 || context.request_time.hour >= 18
};
```

## Key Cedar Properties

| Property | What It Means | Why It Matters |
|----------|---------------|----------------|
| Deterministic | Same input → same output | Unlike LLMs, no variance |
| Formally verified | AWS tools prove consistency | No policy conflicts |
| <1ms evaluation | No Lambda cold start | Negligible latency |
| Auditable | Every decision logged | Compliance-ready |
| Composable | Combine permit + forbid | Build incrementally |

## Key Takeaways

1. **Deny-by-default** — Must have at least one `permit` or everything is blocked
2. **Forbid always wins** — Simple mental model, hard to accidentally grant access
3. **Parameter-level** — Same tool, different boundaries per user
4. **Fast** — <1ms evaluation, unlike LLM-based approaches
5. **Formally verifiable** — Can prove your policies are complete and consistent

## Next Steps

Policies are enforced. But how do you control costs? In the next module, you'll implement **Cost Management** — three-layer budget enforcement using the same Cedar pattern you just learned, plus DynamoDB counters and graduated controls.
