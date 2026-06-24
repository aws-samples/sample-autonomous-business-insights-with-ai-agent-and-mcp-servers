---
title: "Gateway Policy Enforcement"
weight: 51
---

# Gateway Policy Enforcement

## The Problem

Without access control, any user can query any data. Raj (Line Supervisor for Line 7) could ask about Line 4 — and get answers he shouldn't have access to.

## The Production Architecture: Gateway-Level Cedar Enforcement

In production, the **AgentCore Gateway** evaluates Cedar policies **server-side** before invoking Lambda tool targets. The agent has no policy logic — it simply sends tool calls to the Gateway URL, and the Gateway decides whether to invoke the target or deny the request.

```
Agent → Gateway → REQUEST Interceptor (JWT → user_context)
                → Cedar Policy Engine (ENFORCE mode)
                → Lambda Tool Target (only if PERMIT)
```

### How It Works

1. **REQUEST Interceptor** (Lambda): Extracts JWT claims from the `Authorization` header, parses Cognito custom attributes (`custom:role`, `custom:line_scope`, etc.), and injects `user_context` into tool arguments. This makes identity attributes available to Cedar as `context.input.*`.

2. **Cedar Policy Engine**: Evaluates forbid/permit rules. Uses deny-by-default — a baseline `permit_all.cedar` allows authenticated users, then specific `forbid_*` rules carve out restrictions per role.

3. **Result**: Denied requests return an error without ever invoking the Lambda tool target. Every decision is logged to CloudTrail.

### Cedar Policy Example

From `deploy/agentcore/cedar_policies/forbid_line_scope.cedar`:

```cedar
// Line supervisors denied access to lines outside their scope
forbid(
    principal is AgentCore::OAuthUser,
    action in [
        AgentCore::Action::"EquipmentTarget___get_equipment_status",
        AgentCore::Action::"IoTTarget___detect_anomaly",
        AgentCore::Action::"AnalyticsTarget___get_oee_trends"
    ],
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    context.input has line &&
    principal.hasTag("cognito:groups") &&
    principal.getTag("cognito:groups") like "*line_supervisors*" &&
    !(principal.getTag("custom:line_scope") like ("*" + context.input.line + "*"))
};
```

### Deploy the Policy Engine

```bash
# Deploy Cedar policies to the Gateway
python deploy/agentcore/setup_policy.py --region us-west-2
```

See `deploy/agentcore/setup_policy.py` for full deployment, and `deploy/agentcore/cedar_policies/` for all Cedar rules.

---

## The Local Simulation: Development Fallback

For local development without a deployed Gateway (`SIMULATION_MODE=true`), a Strands `BeforeToolCallEvent` hook in `src/identity/gateway_hook.py` **approximates** what the Gateway does server-side. This is a development-only simulation — not the production architecture.

Open `src/identity/gateway_hook.py`:

```python
from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry

from src.identity.models import UserIdentity
from src.identity.policy import PolicyDecision, PolicyEngine

class GatewayPolicyHook(HookProvider):
    """SIMULATION FALLBACK — Local approximation of AgentCore Gateway policy enforcement.

    ⚠️  This hook is ONLY active when SIMULATION_MODE=true.
    In the default mode, the AgentCore Gateway evaluates Cedar policies
    server-side and this class is never instantiated.
    """

    def __init__(self, user: UserIdentity, policy_engine: PolicyEngine):
        self.user = user
        self.policy_engine = policy_engine

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(BeforeToolCallEvent, self._enforce_policy)

    def _enforce_policy(self, event: BeforeToolCallEvent):
        tool_name = event.tool_use["name"]
        tool_input = event.tool_use.get("input", {})

        # Extract policy-relevant parameters (line, machine_id, plant)
        parameters = self._extract_policy_params(tool_input)

        # Evaluate against local Cedar-style policies (simulates Gateway)
        decision: PolicyDecision = self.policy_engine.evaluate(
            user=self.user,
            tool_name=tool_name,
            parameters=parameters,
        )

        if not decision.allowed:
            # BLOCK the call — MCP server never sees it
            event.cancel_tool = (
                f"[Policy Enforcement - Simulation] {decision.reason} "
                f"Please only query data within your authorized scope."
            )

    def _extract_policy_params(self, tool_input):
        """Extract policy-relevant parameters from tool input."""
        if not isinstance(tool_input, dict):
            return {}
        params = {}
        if "line" in tool_input and tool_input["line"]:
            params["line"] = tool_input["line"]
        if "machine_id" in tool_input and tool_input["machine_id"] is not None:
            params["machine_id"] = tool_input["machine_id"]
        if "plant" in tool_input and tool_input["plant"]:
            params["plant"] = tool_input["plant"]
        return params
```

## How It's Wired In

```python
# In agent.py — dual-mode selection
if not SIMULATION_MODE:
    # PRODUCTION: Gateway handles Cedar policy enforcement server-side
    agent = Agent(system_prompt=system_prompt, tools=all_tools)
else:
    # DEV ONLY: Local hook simulates Gateway policy enforcement
    gateway_hook = GatewayPolicyHook(user=user, policy_engine=self.policy_engine)
    agent = Agent(system_prompt=system_prompt, tools=all_tools, hooks=[gateway_hook])
```

## Test It (Local Simulation)

```bash
SIMULATION_MODE=true python -c "
from src.config import AppConfig
from src.identity.models import RAJ_PATEL
from src.agent.agent import ManufacturingInsightsAgent

agent = ManufacturingInsightsAgent(AppConfig())
# Raj asks about Line 4 — which is OUTSIDE his scope (he only has Line 7)
response = agent.query(RAJ_PATEL, 'What is the status of Line 4?')
print(response)
"
```

Expected: The agent explains that Line 4 is outside Raj's authorized scope and offers to query Line 7 instead.

## What Happened Under the Hood

### Production (Gateway mode):
```
1. Agent decides to call get_equipment_status(line="Line 4")
2. Request sent to AgentCore Gateway
3. REQUEST Interceptor extracts Raj's JWT → user_context (line_scope: ["Line 7"])
4. Cedar evaluates forbid_line_scope.cedar: "Line 4" not in scope → FORBID
5. Gateway returns error — Lambda target never invoked
6. Agent receives denial, explains limitation to user
```

### Local Simulation (SIMULATION_MODE=true):
```
1. Agent decides to call get_equipment_status(line="Line 4")
2. BeforeToolCallEvent fires
3. GatewayPolicyHook evaluates: Raj's scope is ["Line 7"]
4. "Line 4" not in scope → DENY
5. event.cancel_tool set → tool call cancelled
6. Agent receives "Access denied" message
7. Agent explains the limitation to the user
```

In both cases, the MCP server / Lambda target was **never contacted**. Policy enforcement happened before the tool was invoked — at the Gateway level (production) or in the agent hook (dev simulation).

{{% notice success %}}
**Checkpoint:** If Raj's query about Line 4 is denied and he's told to ask about Line 7, policy enforcement is working!
{{% /notice %}}

{{% notice warning %}}
**Important:** The local `GatewayPolicyHook` is a development convenience only. In production, policy enforcement happens at the AgentCore Gateway — the agent code has no policy logic and cannot bypass Gateway-level Cedar rules.
{{% /notice %}}
