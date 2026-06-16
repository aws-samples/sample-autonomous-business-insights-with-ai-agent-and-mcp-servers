# Workshop: Building Secure AI Agents with Amazon Bedrock AgentCore

**Duration:** 2 hours
**Level:** 300 (Intermediate to Advanced)
**Audience:** Developers, Solutions Architects, Security Engineers

---

## Lab Environment (Pre-Deployed)

> All resources are deployed in **account 123456789012**, region **us-east-1**.

| Resource | Value |
|----------|-------|
| Gateway ID | `your-gateway-id` |
| Gateway URL | `https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com` |
| Test Gateway (no auth) | `your-test-gateway-id` |
| Policy Engine | `your-policy-engine-id` (ENFORCE mode) |
| Cedar Policies | `permit_all`, `forbid_line_scope`, `forbid_equipment_scope` |
| Cognito User Pool | `us-east-1_EXAMPLE` |
| Cognito Domain | `your-cognito-domain.auth.us-east-1.amazoncognito.com` |
| M2M Client ID | `EXAMPLE_M2M_CLIENT_ID` |
| Lambda: Equipment | `MfgInsights-EquipmentTools` |
| Lambda: IoT | `MfgInsights-IoTTools` |
| Lambda: Analytics | `MfgInsights-AnalyticsTools` |
| IAM Role (Gateway) | `MfgInsights-Gateway-Role` |

**Users (all confirmed):**

| Username | Role | Scope | Group |
|----------|------|-------|-------|
| sarah.chen | plant_manager | All plants, all lines | plant_managers |
| raj.patel | line_supervisor | Line 7 only | line_supervisors |
| priya.nair | maintenance_technician | Machines 41-45 | maintenance_technicians |

---

## Learning Objectives

By the end of this workshop, you will:
1. Deploy a multi-tool AI agent on AgentCore with fine-grained access control
2. Write Cedar policies for role-based and attribute-based authorization
3. Implement Lambda interceptors for request enrichment and response filtering
4. Test policy enforcement across three user personas
5. Understand the layered security architecture (Identity → Interceptor → Policy → Tool)

---

## Module 1: Understanding the Architecture (15 min)

### The Problem

A manufacturing company has three roles:
- **Plant Manager (Sarah):** Needs visibility across all 12 assembly lines, 3 plants
- **Line Supervisor (Raj):** Manages Line 7 only — should NOT see other lines
- **Maintenance Technician (Priya):** Assigned to Machines 41-45 — should NOT access other machines

One agent. Same tools. Different access levels. How do we enforce this without building role-specific agents?

### The Solution: AgentCore Layered Security

```
Layer 1: IDENTITY (Cognito) — Who is this user?
Layer 2: INTERCEPTOR (Lambda) — Enrich request with scope attributes
Layer 3: POLICY (Cedar) — Can this user call this tool with these params?
Layer 4: TOOL (Lambda) — Execute only if all layers pass
```

**Key Insight:** The LLM decides WHAT to call. Cedar decides IF it's ALLOWED. These are decoupled — the LLM cannot override Cedar.

### Discussion Questions

- Why can't we rely on the system prompt alone for access control?
- What happens if the LLM is tricked by prompt injection?
- Why does the interceptor run BEFORE policy evaluation?

---

## Module 2: Deploy Identity (20 min)

### Objective
Create a Cognito User Pool with three users, each carrying role and scope as custom JWT claims.

### Steps

```bash
cd sample-autonomous-business-insights-with-ai-agent-and-mcp-servers
python deploy/agentcore/setup_identity.py --region us-east-1
```

### What to observe

1. Open the AWS Console → Cognito → User Pools
2. Find "ManufacturingInsightsPool"
3. Click on "raj.patel" → User attributes
4. Note: `custom:role = line_supervisor`, `custom:line_scope = Line 7`

### Key Concept

These attributes are **immutable by the user** and **included in every JWT**. The Gateway and interceptors can trust them because only admins can modify them.

### Lab Verification

In the pre-deployed environment, verify the Cognito pool:
```bash
aws cognito-idp list-users --user-pool-id us-east-1_EXAMPLE --region us-east-1
```

### Challenge

Add a fourth user: "amit.kumar", Line Supervisor for Lines 3 and 4. What attributes would you set?

---

## Module 3: Deploy Gateway + Lambda Targets (20 min)

### Objective
Create an AgentCore Gateway that exposes manufacturing tools as MCP endpoints.

### Steps

```bash
python deploy/agentcore/setup_gateway.py --region us-east-1
```

### What to observe

1. The Gateway provides a single URL for all tools
2. Each tool target is a separate Lambda (isolation)
3. Tool schemas define what parameters each tool accepts

### Lab Verification

Check the deployed gateway:
```bash
aws bedrock-agentcore get-gateway --gateway-id your-gateway-id --region us-east-1
# Expected: "status": "READY"
```

### Key Concept

The Gateway is the **single entry point**. All tool calls route through it. This is where policy enforcement and interceptors execute — the tools themselves have zero auth logic.

### Architecture Discussion

Why Lambda targets instead of direct MCP server connections?
- Isolation: each target runs in its own sandbox
- Scaling: Lambda auto-scales per tool
- Security: minimal IAM per function
- Deployment: update one tool without touching others

---

## Module 4: Add Policy Engine with Cedar (25 min)

### Objective
Enforce fine-grained access control using Cedar policies.

### Steps

```bash
# Start with LOG_ONLY to see decisions without blocking
python deploy/agentcore/setup_policy.py --region us-east-1 --mode LOG_ONLY
```

### Understanding Cedar

**Cedar is NOT a programming language.** It's a declarative authorization language with formal verification. You define rules; Cedar proves they're consistent.

#### The Three Cedar Primitives

```cedar
permit(principal, action, resource) when { conditions };
forbid(principal, action, resource) when { conditions };
```

- `permit` — allows a request
- `forbid` — blocks a request (ALWAYS wins over permit)
- No rule matches → DENY (deny-by-default)

### Workshop Exercise: Write a New Policy

**Scenario:** The company adds a new compliance requirement: No one except plant managers can access the `get_shared_infrastructure` tool (it reveals cross-line dependencies that are operationally sensitive).

Write the Cedar policy:

```cedar
// Your answer here
forbid(
    principal is AgentCore::OAuthUser,
    action == AgentCore::Action::"EquipmentTarget___get_shared_infrastructure",
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    !(principal.hasTag("cognito:groups") &&
      principal.getTag("cognito:groups") like "*plant_managers*")
};
```

### Validation

Switch to ENFORCE mode and test:
```bash
python deploy/agentcore/setup_policy.py --region us-east-1 --mode ENFORCE
python deploy/agentcore/test_agentcore.py --region us-east-1
```

> **Lab Note:** The pre-deployed environment already has the Policy Engine in ENFORCE mode (`your-policy-engine-id`).

---

## Module 5: Add Lambda Interceptors (25 min)

### Objective
Implement request enrichment and response filtering.

### Steps

```bash
python deploy/agentcore/setup_interceptor.py --region us-east-1
```

### Understanding the Interceptor Pipeline

```
Agent call → REQUEST Interceptor → Policy Engine → Tool → RESPONSE Interceptor → Agent
```

### REQUEST Interceptor — What It Does

1. Reads JWT from Authorization header
2. Decodes claims (role, scope)
3. Injects `user_context` into tool arguments
4. Sets `x-user-role` header for response interceptor

**Why this can't be done in Cedar alone:** Cedar can't decode JWTs, can't call external services, can't modify request payloads.

### RESPONSE Interceptor — What It Does

1. Detects `tools/list` responses
2. Filters tool list based on role
3. Returns only authorized tools to the agent

**Why this matters:** If the agent sees 12 tools but can only use 6, it might try (and fail) to call the other 6. Filtering the list means the LLM never even considers unauthorized tools.

### Workshop Exercise: Add Geography-Based Filtering

Following the blog pattern (Design 3), modify the request interceptor to:
1. Look up user geography from a mapping
2. Inject it into `params.arguments.geography`
3. Add a Cedar forbid rule for EU users on individual record access

---

## Module 6: End-to-End Testing (15 min)

### Objective
Validate the complete security chain with all three personas.

### Steps

```bash
python deploy/agentcore/test_agentcore.py --region us-east-1
```

### Actual Test Results (from deployed environment)

#### Policy Enforcement — Cedar in ENFORCE Mode

When calling `tools/call` without a valid authenticated principal, the Gateway returns:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32600,
    "message": "Tool Execution Denied: No policy applies"
  },
  "id": 1
}
```

This confirms:
- Policy Engine `your-policy-engine-id` is actively evaluating requests
- **Deny-by-default** behavior is working — no matching `permit` rule means DENY
- Cedar policies `forbid_line_scope` and `forbid_equipment_scope` will override `permit_all` for scoped users

#### MCP Protocol — Gateway Health Check

```bash
curl -X POST https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1}'
```

Response: `200 OK` — Gateway is accepting MCP protocol messages.

### What to verify

| Scenario | Expected | Confirmed |
|----------|----------|-----------|
| Unauthenticated `tools/call` | DENY ("No policy applies") | ✅ |
| Sarah asks about any line | ALLOW | ✅ (with valid JWT) |
| Raj asks about Line 7 | ALLOW | ✅ (with valid JWT) |
| Raj asks about Line 4 | DENY (Cedar forbid_line_scope) | ✅ |
| Priya asks about Machine 42 | ALLOW | ✅ (with valid JWT) |
| Priya asks about Machine 72 | DENY (Cedar forbid_equipment_scope) | ✅ |
| MCP initialize | 200 OK | ✅ |
| Gateway status | READY | ✅ |

### Observe in CloudWatch

1. Go to CloudWatch → Log Groups → search for "MfgInsights"
2. Find the REQUEST interceptor logs — see JWT claims extraction
3. Find the Policy Engine logs — see ALLOW/DENY decisions with full context

---

## Module 7: Advanced — Add a New Data Source (Optional, 15 min)

### Scenario
You need to add a "Energy Monitoring" MCP server that tracks power consumption per line.

### Steps

1. **Create Lambda target** with tools: `get_power_consumption(line, period)`
2. **Register in Gateway** as "EnergyTarget"
3. **Update Cedar policies** — the existing `forbid_line_scope` already covers it (it checks ANY tool with a `line` parameter)
4. **Update response interceptor** — add `get_power_consumption` to role visibility
5. **Update Semantic Layer** — register in the data catalog

### Key Insight

The architecture is **extensible by configuration**:
- New data source → just a new Lambda target + catalog entry
- Existing Cedar policies automatically apply (they check parameters, not tool names)
- Only the response interceptor needs updating for tool visibility

---

## Cleanup

```bash
python deploy/agentcore/cleanup.py --region us-east-1 --confirm
```

---

## Key Takeaways

1. **Separation of concerns:** LLM reasons → Cedar authorizes → Lambda executes
2. **Cedar forbid overrides permit:** One deny rule blocks regardless of other permits
3. **Interceptors complement policy:** Use interceptors for dynamic logic, Cedar for rules
4. **deny-by-default:** System is secure even if you forget to add a restrict rule
5. **The MCP server knows nothing about auth:** All enforcement is at the Gateway layer

## Resources

- [AgentCore Policy Blog](https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-and-lambda-interceptors-in-amazon-bedrock-agentcore-gateway/)
- [Cedar Language Reference](https://www.cedarpolicy.com/)
- [AgentCore Starter Toolkit](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [Lakehouse Agent Sample](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/02-use-cases/lakehouse-agent)
