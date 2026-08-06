# AgentCore Deployment Guide

## Deployed Resources (Live)

> **Account:** *<your-account-id>* | **Region:** us-east-1 | **Status:** READY

| Resource | ID / ARN | Status |
|----------|----------|--------|
| Gateway | `your-gateway-id` | READY |
| Gateway URL | `https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com` | Active |
| Policy Engine | `your-policy-engine-id` | ENFORCE |
| Cedar Policies | `permit_all`, `forbid_line_scope`, `forbid_equipment_scope` | Active |
| Cognito User Pool | `us-east-1_EXAMPLE` | Active |
| Cognito Users | `sarah.chen`, `raj.patel`, `priya.nair` | Confirmed |
| Cognito M2M Client | `EXAMPLE_M2M_CLIENT_ID` | Active |
| Cognito Domain | `your-cognito-domain.auth.us-east-1.amazoncognito.com` | Active |
| Lambda: Equipment | `MfgInsights-EquipmentTools` | READY |
| Lambda: IoT | `MfgInsights-IoTTools` | READY |
| Lambda: Analytics | `MfgInsights-AnalyticsTools` | READY |
| Test Gateway (no auth) | `your-test-gateway-id` | READY |
| IAM Role (Gateway) | `MfgInsights-Gateway-Role` | Active |

---

## Overview

This guide deploys the Manufacturing Insights system using **real** Amazon Bedrock AgentCore services instead of local simulations.

### Architecture (Production)

```
Users (Sarah/Raj/Priya)
    │ Cognito JWT
    ▼
┌─────────────────────────────────────────────────────────────┐
│  AgentCore Gateway                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  REQUEST     │  │  Policy     │  │  RESPONSE           │ │
│  │  Interceptor │→ │  Engine     │→ │  Interceptor        │ │
│  │  (Lambda)    │  │  (Cedar)    │  │  (Lambda)           │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└──────────┬──────────────────────────────────────────────────┘
           │
    ┌──────┼──────┬──────────┬──────────┐
    ▼      ▼      ▼          ▼          ▼
Equipment  IoT   Supply   Analytics  Semantic
 Target   Target  Target   Target     Target
(Lambda)  (Lambda)(Lambda) (Lambda)  (Lambda)
```

### What Gets Created

| Component | AWS Service | Purpose |
|-----------|-------------|---------|
| Identity | Cognito User Pool | 3 users with role/scope attributes |
| Gateway | AgentCore Gateway | MCP router, JWT validation, 3-tier caching |
| Registry | AgentCore Registry (via Gateway) | Tool discovery, versioning, governance |
| Tool Targets | Lambda (x5) | Domain tool implementations |
| Policy Engine | AgentCore Policy | Cedar rules enforcement |
| Memory | S3 | Short-term (session), long-term (baselines), episodic (events) |
| Interceptors | Lambda (x2) | Request enrichment, response filtering |
| Observability | CloudWatch + X-Ray | Audit logs, traces, metrics, alerts |

## Prerequisites

- AWS Account with AgentCore access (us-west-2 or us-east-1)
- AWS CLI configured (`aws configure`)
- Python 3.10+
- IAM permissions for: Cognito, Lambda, IAM, AgentCore

```bash
pip install boto3 bedrock-agentcore-starter-toolkit requests
```

## Deployment Steps

### Quick Deploy (All at Once)

```bash
python deploy/agentcore/deploy_all.py --region us-east-1
```

### Step-by-Step Deploy (Actual Commands Run)

#### Step 1: Identity (Cognito)

```bash
python deploy/agentcore/setup_identity.py --region us-east-1
```

Output:
```
✅ Created User Pool: us-east-1_EXAMPLE
✅ Created App Client: EXAMPLE_M2M_CLIENT_ID
✅ Created Cognito Domain: your-cognito-domain.auth.us-east-1.amazoncognito.com
✅ Created user: sarah.chen (plant_managers)
✅ Created user: raj.patel (line_supervisors)
✅ Created user: priya.nair (maintenance_technicians)
```

Creates:
- User Pool with custom attributes: `role`, `line_scope`, `plant_scope`, `equipment_scope`
- 3 users: sarah.chen, raj.patel, priya.nair
- 3 groups: plant_managers, line_supervisors, maintenance_technicians
- M2M client for machine-to-machine auth: `EXAMPLE_M2M_CLIENT_ID`

#### Step 2: Gateway + Lambda Targets

```bash
python deploy/agentcore/setup_gateway.py --region us-east-1
```

Output:
```
✅ Created Lambda: MfgInsights-EquipmentTools
✅ Created Lambda: MfgInsights-IoTTools
✅ Created Lambda: MfgInsights-AnalyticsTools
✅ Created IAM Role: MfgInsights-Gateway-Role
✅ Created Gateway: your-gateway-id
   URL: https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com
✅ Created Test Gateway (no auth): your-test-gateway-id
✅ All Lambda targets: READY
```

Creates:
- Gateway with Cognito OAuth authorizer
- 3 Lambda tool targets with MCP tool schemas
- Test gateway (no auth) for development validation

#### Step 3: Policy Engine (Cedar)

```bash
python deploy/agentcore/setup_policy.py --region us-east-1 --mode ENFORCE
```

Output:
```
✅ Created Policy Engine: your-policy-engine-id (mode: ENFORCE)
✅ Created policy: permit_all
✅ Created policy: forbid_line_scope
✅ Created policy: forbid_equipment_scope
✅ Attached Policy Engine to Gateway: your-gateway-id
```

Creates:
- Policy Engine: `your-policy-engine-id`
- 3 Cedar policies (permit_all + 2 forbid rules)
- Attaches to Gateway
- Mode set directly to `ENFORCE` (validated via test gateway first)

#### Step 4: Interceptors

```bash
python deploy/agentcore/setup_interceptor.py --region us-east-1
```

Creates:
- REQUEST interceptor (JWT → user context injection + budget counter read)
- RESPONSE interceptor (tool list filtering + budget counter increment)

---

#### Step 5: Harness (Cost-Controlled Deployment)

```bash
python deploy/agentcore/setup_harness.py --region us-east-1
```

Creates:
- AgentCore Harness with per-role maxTokens/maxIterations limits
- Tags for cost allocation (project, cost-center)
- Configuration saved to `harness_config.json`

#### Step 6: Budgets (DynamoDB + Alarms)

```bash
python deploy/agentcore/setup_budgets.py --region us-east-1
```

Creates:
- DynamoDB table (`MfgInsights-BudgetCounters`) with TTL
- Seeds per-role daily/monthly limits
- CloudWatch budget warning alarm

---

## Verifying Deployment

### Check Gateway Status

```bash
aws bedrock-agentcore get-gateway --gateway-id your-gateway-id --region us-east-1
```

Expected: `"status": "READY"`

### Check Policy Engine Status

```bash
aws bedrock-agentcore get-policy-engine --policy-engine-id your-policy-engine-id --region us-east-1
```

Expected: `"mode": "ENFORCE"`, `"status": "ACTIVE"`

### Check Lambda Targets

```bash
aws lambda get-function --function-name MfgInsights-EquipmentTools --region us-east-1
aws lambda get-function --function-name MfgInsights-IoTTools --region us-east-1
aws lambda get-function --function-name MfgInsights-AnalyticsTools --region us-east-1
```

Expected: `"State": "Active"` for all three.

### Check Cognito Users

```bash
aws cognito-idp list-users --user-pool-id us-east-1_EXAMPLE --region us-east-1
```

Expected: 3 users (sarah.chen, raj.patel, priya.nair) with status CONFIRMED.

### Test Policy Enforcement (Quick Smoke Test)

```bash
curl -X POST https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_equipment_status"},"id":1}'
```

Expected (no auth): `"Tool Execution Denied: No policy applies"` — confirms deny-by-default enforcement.

## Testing

```bash
python deploy/agentcore/test_agentcore.py --region us-east-1
```

Expected output:
```
  User            Tool           Args           Expected  Actual  Status
  sarah.chen      get_equipment  {"line":"L4"}  ALLOW     ALLOW   ✅
  raj.patel       get_equipment  {"line":"L7"}  ALLOW     ALLOW   ✅
  raj.patel       get_equipment  {"line":"L4"}  DENY      DENY    ✅
  priya.nair      get_sensor     {"machine":42} ALLOW     ALLOW   ✅
  priya.nair      get_sensor     {"machine":72} DENY      DENY    ✅
```

> **Note:** Without a valid JWT (unauthenticated request), all `tools/call` requests return:
> `"Tool Execution Denied: No policy applies"` — this confirms deny-by-default enforcement in ENFORCE mode.

## Cedar Policy Details

### How Policies Map to Roles

| Policy | Who It Restricts | What It Checks |
|--------|-----------------|----------------|
| permit_all | Nobody (baseline) | Allows all authenticated users |
| forbid_line_scope | line_supervisors group | `context.input.line` vs `custom:line_scope` |
| forbid_equipment_scope | maintenance_technicians group | `context.input.machine_id` vs `custom:equipment_scope` |
| forbid_plant_scope | All non-admin users | `context.input.plant` vs `custom:plant_scope` |

### Evaluation Order

1. REQUEST interceptor enriches request (adds user context)
2. Cedar evaluates ALL policies simultaneously
3. If ANY `forbid` matches → DENY (forbid overrides permit)
4. If `permit` matches and no `forbid` → ALLOW
5. If nothing matches → DENY (deny-by-default)

## Adding New Users

```python
# In setup_identity.py, add to DEMO_USERS:
{
    "username": "new.user",
    "email": "new.user@example.com",
    "password": "NewUser!2026",
    "role": "line_supervisor",
    "plant_scope": "Plant 1",
    "line_scope": "Line 3,Line 4",
    "equipment_scope": "",
    "group": "line_supervisors",
}
```

No Cedar policy changes needed — the existing rules evaluate the user's scope dynamically.

## Cleanup

```bash
python deploy/agentcore/cleanup.py --region us-east-1 --confirm
```


## Cost Estimate

| Service | Monthly Cost (demo usage) |
|---------|--------------------------|
| Amazon Bedrock (Claude Sonnet) | ~$2-10 (depends on query volume) |
| Cognito | Free (< 50K MAU) |
| Lambda (tool targets + interceptors) | Free tier (~1M requests) |
| AgentCore Gateway | ~$0.50/1000 requests |
| AgentCore Policy Engine | Included with Gateway |
| AgentCore Memory (S3) | < $0.10/month |
| CloudWatch Logs (policy audit) | ~$0.50/GB ingested |
| CloudWatch Alarms | Free (up to 10) |
| X-Ray Traces | Free tier (100K/month) |
| **Total (AgentCore only)** | **~$3-12/month** |

For full infrastructure (Aurora + Redshift + OpenSearch + Timestream), add ~$140-150/month.
Delete the CloudFormation stack when not actively using live data mode.
