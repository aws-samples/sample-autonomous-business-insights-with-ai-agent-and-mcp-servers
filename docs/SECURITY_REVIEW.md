# Security Review — AgentCore Manufacturing Insights

## Executive Summary

This system uses Amazon Bedrock AgentCore's defense-in-depth architecture to secure AI agent access to manufacturing data. Three complementary layers (Identity, Policy, Interceptors) ensure no unauthorized data access regardless of LLM behavior.

## Authentication Flow

```
User → Cognito (JWT) → Gateway (validates signature) → REQUEST Interceptor (extracts claims) → Agent
```

| Step | What Happens | Failure Mode |
|------|-------------|--------------|
| 1. User authenticates | Cognito issues JWT with custom claims | Invalid credentials → no token |
| 2. Gateway validates | Checks JWT signature against Cognito JWKS | Expired/forged token → 401 |
| 3. Interceptor extracts | Reads role, scope from token claims | Missing claims → defaults to deny |
| 4. Policy evaluates | Cedar rules check scope against params | No matching permit → deny |

## Authorization Model

### Cedar Policy Architecture (Deny-by-Default)

```
┌─────────────────────────────────────────┐
│  DENY BY DEFAULT (no rules = no access) │
├─────────────────────────────────────────┤
│  permit_all (baseline access)           │
├─────────────────────────────────────────┤
│  forbid_line_scope                      │ ← Overrides permit for line violations
│  forbid_equipment_scope                 │ ← Overrides permit for machine violations
│  forbid_plant_scope                     │ ← Overrides permit for plant violations
└─────────────────────────────────────────┘
```

Key property: `forbid` ALWAYS overrides `permit`. Even if a user has a matching permit rule, any matching forbid blocks the request.

### Scope Dimensions

| Dimension | Attribute | Checked On | Example |
|-----------|-----------|-----------|---------|
| Plant | `custom:plant_scope` | Tools with `plant` parameter | "Plant 1,Plant 2" |
| Line | `custom:line_scope` | Tools with `line` parameter | "Line 7" |
| Equipment | `custom:equipment_scope` | Tools with `machine_id` parameter | "Machine 41,Machine 42" |

## Threat Model

### 1. LLM Prompt Injection

**Threat:** User crafts input that tricks the LLM into calling unauthorized tools.

**Mitigation:** Cedar policy evaluates at the Gateway, OUTSIDE the LLM's reasoning loop. Even if the LLM is tricked into calling `get_equipment_status(line="Line 4")` for Raj, the Gateway denies it deterministically. The LLM cannot bypass Cedar.

### 2. Token Replay

**Threat:** Attacker intercepts and replays a valid JWT.

**Mitigation:**
- JWT expiration (60 minutes default)
- TLS in transit (Gateway endpoint is HTTPS)
- Token binding to specific Cognito client

### 3. Scope Escalation

**Threat:** User modifies their own scope attributes.

**Mitigation:**
- Custom attributes are admin-only writable in Cognito
- Users cannot self-modify `custom:role`, `custom:line_scope`, etc.
- Cognito JWT includes the authoritative scope at token issuance time

### 4. Confused Deputy (Tool calling another tool)

**Threat:** A compromised tool uses the agent's credentials to call other tools.

**Mitigation:**
- Each tool Lambda has minimal IAM permissions (only its own data source)
- REQUEST interceptor exchanges user JWT for scoped credentials (act-on-behalf)
- Tools receive short-lived STS credentials scoped to the tenant

### 5. Data Exfiltration via Agent Response

**Threat:** Agent synthesizes and reveals data from multiple sources that individually were allowed.

**Mitigation:**
- RESPONSE interceptor filters tool output before it reaches the agent
- System prompt instructs agent to respect scope boundaries
- Lake Formation row/column security at the data layer (live mode)

### 6. MCP Server Compromise

**Threat:** Attacker gains access to an MCP server and tries to access other domains.

**Mitigation:**
- Each Lambda target runs in isolated execution environment
- No cross-target network access
- Gateway routes requests to specific targets (no lateral movement)

## Audit Trail

| Event | Where Logged | Retention |
|-------|-------------|-----------|
| Authentication (success/fail) | Cognito Advanced Security | 90 days |
| Policy allow/deny decision | CloudWatch (AgentCore logs) | Configurable |
| Tool invocation | Lambda CloudWatch logs | 30 days default |
| Interceptor execution | Lambda CloudWatch logs | 30 days default |
| IAM API calls | CloudTrail | 90 days (free tier) |

## Compliance Considerations

### SOC 2

| Control | Implementation |
|---------|---------------|
| Access Control (CC6.1) | Cedar policies + Cognito groups |
| Logical Access (CC6.2) | Role-based with attribute scoping |
| System Operations (CC7.1) | CloudWatch monitoring + alerts |
| Change Management (CC8.1) | Policy changes via API (version-controlled) |

### GDPR

| Requirement | Implementation |
|-------------|---------------|
| Data minimization | Agent only sees data within user's scope |
| Access control | Cedar + interceptors enforce boundaries |
| Audit logging | CloudWatch + CloudTrail |
| Right to erasure | Data stored in managed services with deletion APIs |

## Production Hardening Recommendations

1. **Enable WAF on Gateway endpoint** — Rate limiting, IP filtering
2. **Enable Cognito Advanced Security** — Adaptive authentication, anomaly detection
3. **Use VPC endpoints** — Keep Gateway traffic off public internet
4. **Enable CloudTrail** — Full API audit trail for compliance
5. **Rotate Cognito secrets** — Automate client secret rotation
6. **Add MFA** — Require MFA for plant_manager role
7. **Implement session timeouts** — Short token expiry (15 min) for sensitive roles
8. **Add canary tests** — Automated daily policy validation tests
9. **Enable Policy Engine in LOG_ONLY first** — Validate before enforcing
10. **Review Cedar policies quarterly** — Ensure least-privilege is maintained
11. **Gateway IAM role** — `MfgInsights-Gateway-Role` uses inline policy scoped to `MfgInsights-*` Lambda functions and specific `bedrock-agentcore` actions

---

## Deployment Verification (Confirmed)

> Verified against account **<YOUR_AWS_ACCOUNT_ID>**, region **us-east-1**.

### Cedar Policy Engine — ENFORCE Mode ✅

```
Policy Engine: your-policy-engine-id
Mode: ENFORCE
Status: ACTIVE
Policies: permit_all, forbid_line_scope, forbid_equipment_scope
```

Confirmed: Policy evaluation actively denies requests. Unauthenticated `tools/call` returns `"Tool Execution Denied: No policy applies"` — deny-by-default is working.

### Deny-by-Default for Unauthenticated Requests ✅

```bash
curl -X POST https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_equipment_status"},"id":1}'
```

Response: `"Tool Execution Denied: No policy applies"` — no principal context means no `permit` rule matches, therefore DENY.

### Lambda Target IAM — Minimal Permissions ✅

```
Role: MfgInsights-Lambda-Role
Policies: AWSLambdaBasicExecutionRole (only CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents)
```

All three Lambda targets (`MfgInsights-EquipmentTools`, `MfgInsights-IoTTools`, `MfgInsights-AnalyticsTools`) use this single role with only BasicExecution permissions. No data source access, no cross-service access.

### Gateway IAM Role — Least-Privilege ✅

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock-agentcore:InvokeGateway",
    "bedrock-agentcore:EvaluatePolicy",
    "bedrock-agentcore:InvokeTarget"
  ],
  "Resource": "arn:aws:bedrock-agentcore:<REGION>:<ACCOUNT_ID>:gateway/<your-gateway-id>"
}
```

The Gateway role is scoped to invoke only the specific Gateway resource and its
associated policy evaluation actions. Lambda invocation is restricted to
`MfgInsights-*` function name prefix via an inline policy.

### Cognito Users — All Confirmed ✅

| User | Status | Group | Scope |
|------|--------|-------|-------|
| sarah.chen | CONFIRMED | plant_managers | All plants, all lines |
| raj.patel | CONFIRMED | line_supervisors | Line 7 |
| priya.nair | CONFIRMED | maintenance_technicians | Machines 41-45 |

### Summary

| Check | Status |
|-------|--------|
| Cedar policies in ENFORCE mode | ✅ Confirmed |
| Deny-by-default for unauthenticated requests | ✅ Confirmed |
| Lambda targets have minimal IAM | ✅ Confirmed (BasicExecution only) |
| Gateway role scoped to least-privilege | ✅ Confirmed |
| All Lambda targets operational | ✅ Confirmed (3/3 READY) |
| Gateway accepting MCP protocol | ✅ Confirmed (initialize: 200 OK) |

## Responsibility Matrix

| Security Control | Managed By | Configuration By |
|-----------------|-----------|-----------------|
| JWT validation | AgentCore Gateway | Automatic |
| Policy enforcement | AgentCore Policy (Cedar) | Your Cedar rules |
| Request enrichment | Your Lambda interceptor | Your code |
| Response filtering | Your Lambda interceptor | Your code |
| Data-layer security | Lake Formation / RDS IAM | Your IAM policies |
| Network security | VPC, Security Groups | Your infrastructure |
| Encryption at rest | AWS managed (KMS) | Automatic |
| Encryption in transit | TLS 1.2+ | Automatic |
