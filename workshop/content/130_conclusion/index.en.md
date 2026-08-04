+++
title = "Conclusion"
weight = 130
+++

# Conclusion

Congratulations! You've built a complete multi-agent system that transforms natural language questions into cross-system manufacturing insights.

## What You Built

```
┌─────────────────────────────────────────────────────────────────┐
│  Your Complete System                                            │
│                                                                  │
│  ✅ 4 MCP Servers — Equipment, IoT, Supply Chain, Analytics     │
│  ✅ 1 Strands Agent — Autonomous multi-tool reasoning           │
│  ✅ AgentCore Runtime — Isolated serverless execution            │
│  ✅ AgentCore Gateway — MCP routing + security enforcement      │
│  ✅ AgentCore Identity — Cognito with role-based scope           │
│  ✅ AgentCore Policy — Cedar deterministic authorization        │
│  ✅ AgentCore Memory — Session + cross-session persistence      │
│  ✅ AgentCore Observability — Tracing, logging, metrics         │
│  ✅ Evaluations — Policy tests + integration tests              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Concepts You Learned

### 1. MCP (Model Context Protocol)
- Open standard for connecting AI agents to data sources
- Self-describing tools with typed parameters
- Streamable HTTP transport — standard, testable, composable

### 2. Strands Agents SDK
- Lightweight agent framework with tool-use
- LLM autonomously selects which tools to call
- No orchestration code — reasoning replaces workflows

### 3. Amazon Bedrock AgentCore
- **Runtime** — Firecracker microVMs with session isolation
- **Gateway** — Single chokepoint for all tool calls, policy enforcement
- **Identity** — OAuth integration with scope propagation
- **Policy** — Cedar-based deterministic authorization (<1ms)
- **Memory** — User/team/org namespaces with TTL
- **Observability** — X-Ray tracing + CloudWatch audit

### 4. Cedar Policy Language
- Deny-by-default, forbid-overrides-permit
- Parameter-level access control (same tool, different boundaries)
- Formally verified — provably consistent
- Deterministic — same input, same output, every time

## Architecture Recap

```
Users (JWT) → Runtime (microVM) → Gateway → Cedar → Lambda Targets → Data
                                      ↑
                             Interceptors enrich
                             context for policy
```

Three users, same agent, different data boundaries — enforced deterministically.

## What's Different About This Approach

| Traditional BI | This Solution |
|----------------|---------------|
| Hours of manual data stitching | Seconds — agent correlates automatically |
| Role-specific dashboards to maintain | One agent serves all roles |
| Custom integrations per data source | MCP servers — configuration, not code |
| Soft guardrails (prompt-based) | Deterministic Cedar policies |
| Per-user auth logic in each app | Zero auth in tools — Gateway handles all |

## Where To Go From Here

### Add More Data Sources
- Write a new MCP server (FastMCP makes it ~30 lines of Python)
- Register the tool target with the Gateway
- Cedar policies automatically apply to new tools

### Add More Users
- Add entries to `setup_identity.py`
- Existing Cedar policies evaluate dynamically — no policy changes needed

### Customize Policies
- Write new Cedar `forbid` rules for your access patterns
- Start in MONITOR mode, validate with CloudWatch, then switch to ENFORCE

### Production Considerations
- Replace simulated data with real data sources (Zero-ETL, MSK, IoT Core)
- Swap Cognito for your enterprise IdP (Okta, Entra ID)
- Enable 3-tier caching at the Gateway for frequently-asked queries
- Set up CI/CD for Cedar policy deployment

## Resources

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [Strands Agents SDK](https://strandsagents.com/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Cedar Policy Language](https://www.cedarpolicy.com/)
- [AWS Blog: Generate Autonomous Business Insights](https://aws.amazon.com/blogs/machine-learning/generate-autonomous-business-insights-with-ai-agent-and-mcp-servers/)
- [Sample Code Repository](https://github.com/aws-samples/sample-autonomous-business-insights-with-ai-agent-and-mcp-servers)

## Feedback

We'd love to hear your feedback on this workshop. Please share:
- What worked well
- What could be improved
- Topics you'd like to see covered in more depth

Thank you for completing this workshop!
