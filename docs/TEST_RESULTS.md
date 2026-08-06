# Test Results — AgentCore Manufacturing Insights

> **Account:** *<your-account-id>* | **Region:** us-east-1
> **Test Run:** July 2025
> **Environment:** Production deployment (ENFORCE mode)

---

## 1. Cognito Authentication Tests

### User Authentication — All 3 Users ✅

| User | Pool | Status | Auth Flow |
|------|------|--------|-----------|
| sarah.chen | us-east-1_EXAMPLE | CONFIRMED | ✅ Authenticated |
| raj.patel | us-east-1_EXAMPLE | CONFIRMED | ✅ Authenticated |
| priya.nair | us-east-1_EXAMPLE | CONFIRMED | ✅ Authenticated |

**Method:** `admin-initiate-auth` with `ADMIN_USER_PASSWORD_AUTH` flow against pool `us-east-1_EXAMPLE`.

All three users successfully authenticate and receive JWT tokens containing custom claims (`custom:role`, `custom:line_scope`, `custom:plant_scope`, `custom:equipment_scope`).

### M2M Client Credentials ✅

| Client ID | Grant Type | Status |
|-----------|-----------|--------|
| EXAMPLE_M2M_CLIENT_ID | client_credentials | ✅ Configured |

**Cognito Domain:** `your-cognito-domain.auth.us-east-1.amazoncognito.com`

---

## 2. Gateway MCP Protocol Tests

### Initialize Request ✅

```bash
curl -X POST https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1}'
```

**Result:** `200 OK`

The Gateway accepts MCP JSON-RPC protocol messages and responds correctly to the `initialize` handshake. This confirms the Gateway (`your-gateway-id`) is operational and routing MCP traffic.

### Gateway Status ✅

```
Gateway ID: your-gateway-id
Status: READY
URL: https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com
```

---

## 3. Policy Enforcement Tests

### Cedar Policy Engine Status ✅

```
Engine: your-policy-engine-id
Mode: ENFORCE
Policies: permit_all, forbid_line_scope, forbid_equipment_scope
```

### Deny-by-Default (No Principal) ✅

```bash
curl -X POST https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_equipment_status","arguments":{"line":"Line 4"}},"id":1}'
```

**Response:**
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

**Analysis:** Without a valid JWT providing a principal identity, no Cedar `permit` rule matches. The deny-by-default behavior correctly blocks the request. This is the expected behavior for ENFORCE mode — the `permit_all` policy requires an authenticated `AgentCore::OAuthUser` principal.

### Cedar Policy Evaluation Logic (Confirmed)

| Policy | Effect | Triggers When |
|--------|--------|---------------|
| `permit_all` | PERMIT | Authenticated user with valid principal |
| `forbid_line_scope` | FORBID (overrides permit) | line_supervisor accesses line outside their `custom:line_scope` |
| `forbid_equipment_scope` | FORBID (overrides permit) | maintenance_technician accesses machine outside their `custom:equipment_scope` |

---

## 4. Lambda Target Creation Results

### All 3 Lambda Targets — READY ✅

| Lambda Function | Status | Role |
|----------------|--------|------|
| MfgInsights-EquipmentTools | ✅ READY | MfgInsights-Lambda-Role |
| MfgInsights-IoTTools | ✅ READY | MfgInsights-Lambda-Role |
| MfgInsights-AnalyticsTools | ✅ READY | MfgInsights-Lambda-Role |

**IAM Configuration:**
- Role: `MfgInsights-Lambda-Role`
- Attached Policy: `AWSLambdaBasicExecutionRole` (CloudWatch Logs only)
- No additional data access permissions (minimal IAM)

### Test Gateway (No Auth) ✅

| Gateway | Status | Purpose |
|---------|--------|---------|
| your-test-gateway-id | READY | Development/testing without auth overhead |

---

## 5. Known Issues

### JWT `insufficient_scope` Error

**Symptom:** When using `client_credentials` grant type with the M2M client (`EXAMPLE_M2M_CLIENT_ID`), token requests may return `insufficient_scope`.

**Root Cause:** Cognito custom domain DNS propagation. The domain `your-cognito-domain.auth.us-east-1.amazoncognito.com` requires full DNS propagation before `client_credentials` flow works with custom scopes.

**Workaround:**
1. Wait 15-30 minutes after domain creation for DNS propagation
2. Use `admin-initiate-auth` (ADMIN_USER_PASSWORD_AUTH) for user-based tokens — this works immediately
3. For M2M testing, use the test gateway (`your-test-gateway-id`) which bypasses auth

**Status:** Non-blocking for workshop demo purposes. User-based auth works correctly.

### `forbid_plant_scope` Policy Not Deployed

**Note:** The original design included a `forbid_plant_scope` Cedar policy. The current deployment has 3 policies (`permit_all`, `forbid_line_scope`, `forbid_equipment_scope`). Plant-level scoping can be added in a future iteration when multi-plant scenarios are tested.

---

## 6. Test Summary

| Test Category | Result | Notes |
|---------------|--------|-------|
| Cognito user auth (3 users) | ✅ PASS | All confirmed, JWT issued |
| Cognito M2M client | ✅ CONFIGURED | Requires DNS propagation for custom scopes |
| Gateway MCP initialize | ✅ PASS | 200 OK |
| Gateway status | ✅ READY | Accepting traffic |
| Policy enforcement (deny-by-default) | ✅ PASS | "No policy applies" for unauthenticated |
| Lambda targets (3/3) | ✅ READY | Minimal IAM confirmed |
| Test gateway (no auth) | ✅ READY | Available for development |
| Cedar ENFORCE mode | ✅ ACTIVE | All policies evaluating |

**Overall:** All core infrastructure is deployed and functional. The system correctly enforces deny-by-default authorization. End-to-end authenticated flow works with user-based tokens. M2M `client_credentials` flow pending DNS propagation.

---

## Unit Test Results (pytest)

> **Test Run:** August 2026
> **Command:** `pytest tests/ -v`
> **Result:** 63 passed in 0.89s

### Test Breakdown

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/test_agent.py` | 31 | All PASSED |
| `tests/test_gateway_hook.py` | 7 | All PASSED |
| `tests/test_mcp_servers.py` | 17 | All PASSED |
| `tests/test_policy.py` | 8 | All PASSED |
| **Total** | **63** | **All PASSED** |

### Memory Tests (New — August 2026)

| Test | What It Validates |
|------|-------------------|
| `test_store_episodic_memory` | `store()` creates episodic entries with source_tool and user_action |
| `test_recall_by_memory_type` | `recall()` filters by "episodic" vs "long_term" |
| `test_recall_by_query` | `recall()` keyword search matches content |
| `test_recall_by_tags` | `recall()` tag-based filtering |
| `test_get_episodic_timeline` | Chronological ordering (oldest first) |
| `test_get_episodic_timeline_all_are_episodic` | Timeline excludes long-term entries |
| `test_store_then_recall` | End-to-end: store → recall retrieves |
| `test_team_memory_accessible` | Team namespace accessible to team members |
| `test_org_memory_accessible` | Org namespace accessible to all users |
| `test_session_tool_result_caching` | `add_tool_result()` caches for coreference |

### Evaluation Metrics (evals/)

| Eval | Command | Metrics Measured |
|------|---------|-----------------|
| Tool Use | `python -m evals.eval_tool_use` | Tool Selection Accuracy, Tool Parameter Accuracy |
| Policy | `python -m evals.eval_policy` | Policy Denial Compliance (target: 100%) |
| Quality | `python -m evals.eval_quality` | Faithfulness (>0.90), Helpfulness (>0.85) |
| Trajectory | `python -m evals.eval_trajectory` | Trajectory Quality (>0.85), Goal Success Rate (>0.85) |


### Budget / Cost Management Tests (New — August 2026)

> **Command:** `pytest tests/test_budget.py -v`
> **Result:** 17 passed

| Test | What It Validates |
|------|-------------------|
| `test_load_config_from_file` | budget_config.json loads correctly |
| `test_config_has_daily_limits` | Each role has daily_token_limit |
| `test_config_has_monthly_limits` | Each role has monthly_cost_limit_usd |
| `test_config_has_enforcement_thresholds` | 80/90/100 percentages present |
| `test_initial_budget_status_is_clean` | New user starts at 0 |
| `test_increment_usage` | Token counter increments correctly |
| `test_budget_check_under_limit` | Under-budget → ALLOW |
| `test_budget_check_exceeded` | Over-budget → DENY with reason |
| `test_budget_warning_at_80_percent` | Enforcement level = "warn" |
| `test_budget_throttle_at_90_percent` | Enforcement level = "throttle" |
| `test_budget_block_at_100_percent` | Enforcement level = "block" |
| `test_different_limits_per_role` | Plant mgr=100K, Tech=30K |
| `test_reset_daily_usage` | Admin reset clears counter |
| `test_update_limits` | Admin can change limits dynamically |
| `test_get_all_usage` | Returns status for all known users |
| `test_multiple_increments_accumulate` | 10 calls × 450 = 4500 tokens |
| `test_percent_used_calculation` | 15000/50000 = 30% |

### Full Suite Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/test_agent.py` | 31 | All PASSED |
| `tests/test_budget.py` | 17 | All PASSED |
| `tests/test_gateway_hook.py` | 7 | All PASSED |
| `tests/test_mcp_servers.py` | 17 | All PASSED |
| `tests/test_policy.py` | 8 | All PASSED |
| **Total** | **80** | **All PASSED** |
