+++
title = "AgentCore Identity"
weight = 70
+++

# AgentCore Identity — Authentication & Scope Propagation

In this module, you'll set up Amazon Cognito as the identity provider, create users with role-based scope attributes, and understand how identity propagates through the entire system.

## What Is AgentCore Identity?

AgentCore Identity integrates your existing OAuth 2.0 provider (Cognito, Okta, Entra ID) with the agent system. It ensures:

- Every tool call carries **authenticated user context**
- User scope attributes (role, line, plant, equipment) are available to Cedar policies
- Tokens are validated at the Gateway before any processing
- Users cannot escalate their own scope (admin-only writable attributes)

```
User authenticates → JWT issued with scope claims → Agent passes JWT →
Gateway validates → Interceptor extracts claims → Cedar evaluates scope
```

## How Identity Flows Through the System

```
┌──────────┐     ┌─────────┐     ┌─────────┐     ┌─────────────┐
│  User    │────►│ Cognito │────►│  Agent  │────►│   Gateway   │
│          │     │         │     │(Runtime)│     │             │
│ username │     │ Issues  │     │ Passes  │     │ Validates   │
│ password │     │ JWT     │     │ JWT in  │     │ signature   │
│          │     │         │     │ header  │     │ + expiry    │
└──────────┘     └─────────┘     └─────────┘     └──────┬──────┘
                                                         │
                                                         ▼
                                                  ┌─────────────┐
                                                  │  REQUEST    │
                                                  │ Interceptor │
                                                  │             │
                                                  │ Decodes JWT │
                                                  │ Extracts:   │
                                                  │  - role     │
                                                  │  - scope    │
                                                  │  - groups   │
                                                  └──────┬──────┘
                                                         │
                                                         ▼
                                                  ┌─────────────┐
                                                  │   Cedar     │
                                                  │   Policy    │
                                                  │             │
                                                  │ Checks user │
                                                  │ scope vs    │
                                                  │ request     │
                                                  │ parameters  │
                                                  └─────────────┘
```

## Step 1: Deploy the Identity Layer

Run the identity setup script:

```bash
python deploy/agentcore/setup_identity.py --region us-east-1
```

Expected output:

```
✅ Created User Pool: us-east-1_XXXXXXXX
✅ Created App Client: <client-id>
✅ Created Cognito Domain: mfg-insights-<account>.auth.us-east-1.amazoncognito.com
✅ Created user: sarah.chen (plant_managers)
✅ Created user: raj.patel (line_supervisors)
✅ Created user: priya.nair (maintenance_technicians)
```

## Step 2: Understand the User Pool Configuration

The Cognito User Pool has custom attributes that carry scope information:

| Attribute | Type | Example (Sarah) | Example (Raj) | Example (Priya) |
|-----------|------|-----------------|---------------|-----------------|
| `custom:role` | String | plant_manager | line_supervisor | maintenance_technician |
| `custom:plant_scope` | String | Plant 1,Plant 2,Plant 3 | Plant 2 | Plant 1 |
| `custom:line_scope` | String | Line 1,...,Line 12 | Line 7 | Line 4 |
| `custom:equipment_scope` | String | (all) | Machine 71-75 | Machine 41-45 |

These attributes are:
- **Admin-only writable** — Users cannot change their own scope
- **Included in the JWT** — Available to the Gateway and Cedar at runtime
- **String-typed** — Cedar uses `like` operators for wildcard matching

## Step 3: Explore the User Configuration

Open `deploy/agentcore/setup_identity.py` and find the user definitions:

```python
DEMO_USERS = [
    {
        "username": "sarah.chen",
        "email": "sarah.chen@example.com",
        "password": os.getenv("DEMO_PASSWORD_SARAH", "Sarah!2026Plant"),
        "role": "plant_manager",
        "plant_scope": "Plant 1,Plant 2,Plant 3",
        "line_scope": "Line 1,Line 2,Line 3,Line 4,Line 5,Line 6,"
                      "Line 7,Line 8,Line 9,Line 10,Line 11,Line 12",
        "equipment_scope": "all",
        "group": "plant_managers",
    },
    {
        "username": "raj.patel",
        "email": "raj.patel@example.com",
        "password": os.getenv("DEMO_PASSWORD_RAJ", "Raj!2026Line7"),
        "role": "line_supervisor",
        "plant_scope": "Plant 2",
        "line_scope": "Line 7",
        "equipment_scope": "Machine 71,Machine 72,Machine 73,Machine 74,Machine 75",
        "group": "line_supervisors",
    },
    {
        "username": "priya.nair",
        "email": "priya.nair@example.com",
        "password": os.getenv("DEMO_PASSWORD_PRIYA", "Priya!2026Maint"),
        "role": "maintenance_technician",
        "plant_scope": "Plant 1",
        "line_scope": "Line 4",
        "equipment_scope": "Machine 41,Machine 42,Machine 43,Machine 44,Machine 45",
        "group": "maintenance_technicians",
    },
]
```

## Step 4: Get a JWT Token

Authenticate as Raj to see what the JWT contains:

```bash
python deploy/agentcore/debug_token.py --user raj.patel --region us-east-1
```

This outputs the decoded JWT payload:

```json
{
  "sub": "abc123-...",
  "cognito:username": "raj.patel",
  "cognito:groups": ["line_supervisors"],
  "custom:role": "line_supervisor",
  "custom:plant_scope": "Plant 2",
  "custom:line_scope": "Line 7",
  "custom:equipment_scope": "Machine 71,Machine 72,Machine 73,Machine 74,Machine 75",
  "token_use": "access",
  "exp": 1750000000,
  "iat": 1749996400
}
```

This JWT is what the Gateway validates and the REQUEST interceptor decodes.

## Step 5: Understand How Cedar Uses Identity

Cedar policies reference JWT claims through the `principal` entity:

```cedar
forbid(
    principal is AgentCore::OAuthUser,
    action in [AgentCore::Action::"EquipmentTarget___get_equipment_status"],
    resource == AgentCore::Gateway::"${GATEWAY_ARN}"
) when {
    context.input has line &&
    principal.hasTag("cognito:groups") &&
    principal.getTag("cognito:groups") like "*line_supervisors*" &&
    !(principal.getTag("custom:line_scope") like ("*" + context.input.line + "*"))
};
```

Breaking this down:
- `principal.hasTag("cognito:groups")` — Check if user has group membership
- `principal.getTag("custom:line_scope")` — Read the user's scope attribute
- `context.input.line` — The `line` parameter from the tool call
- `like ("*" + context.input.line + "*")` — Wildcard match: is the requested line in scope?

## Step 6: Verify Users in Cognito

```bash
aws cognito-idp list-users \
  --user-pool-id <your-pool-id> \
  --region us-east-1 \
  --query "Users[].{Username:Username,Status:UserStatus}" \
  --output table
```

Expected:

```
┌──────────────┬───────────┐
│   Username   │  Status   │
├──────────────┼───────────┤
│ sarah.chen   │ CONFIRMED │
│ raj.patel    │ CONFIRMED │
│ priya.nair   │ CONFIRMED │
└──────────────┴───────────┘
```

## Step 7: Test Token-Based Access (Authenticated Gateway Call)

```bash
# Get a token for Raj
TOKEN=$(python deploy/agentcore/debug_token.py --user raj.patel --region us-east-1 --raw)

# Call the production gateway with Raj's token
curl -s -X POST \
  "https://<your-gateway-id>.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params":{"name":"get_oee_trends","arguments":{"line":"Line 7"}},
    "id":1
  }' | python -m json.tool
```

This should **succeed** — Line 7 is in Raj's scope.

Now try Line 4:

```bash
curl -s -X POST \
  "https://<your-gateway-id>.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params":{"name":"get_oee_trends","arguments":{"line":"Line 4"}},
    "id":2
  }' | python -m json.tool
```

Expected: **DENY** — "Line 4 not in authorized scope."

## Adding New Users

To add a fourth user, add an entry to `DEMO_USERS` in `setup_identity.py`:

```python
{
    "username": "alex.wong",
    "email": "alex.wong@example.com",
    "password": "Alex!2026Supv",
    "role": "line_supervisor",
    "plant_scope": "Plant 1",
    "line_scope": "Line 3,Line 4",
    "equipment_scope": "",
    "group": "line_supervisors",
}
```

No Cedar policy changes needed—the existing `forbid_line_scope` rule dynamically evaluates the new user's `line_scope` attribute.

## Production Identity Providers

In production, you'd swap Cognito for your enterprise IdP:

| Provider | Integration | Scope Propagation |
|----------|-------------|-------------------|
| Amazon Cognito | Native | Custom attributes in JWT |
| Okta | OIDC federation | Custom claims via authorization server |
| Microsoft Entra ID | OIDC federation | Azure AD custom claims |
| Auth0 | OIDC federation | Rules/Actions inject claims |

AgentCore Identity handles the federation — you configure the OIDC issuer URL and claim mappings.

## Key Takeaways

1. **Identity = scope claims in JWT** — Every access decision uses JWT attributes
2. **Admin-only writable** — Users cannot escalate their own permissions
3. **Dynamic evaluation** — Add users without changing policies
4. **Token expiry** — Forces re-authentication (60min default)
5. **Provider-agnostic** — Swap Cognito for Okta/Entra without changing policies or agent code

## Next Steps

You have users with scope attributes. In the next module, you'll write **Cedar policies** that use these attributes to make deterministic allow/deny decisions.
