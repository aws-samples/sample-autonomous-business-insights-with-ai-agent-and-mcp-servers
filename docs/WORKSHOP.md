# Workshop: Build Autonomous Business Insights with AI Agents, MCP Servers, and Amazon Bedrock AgentCore

**Duration:** 3 hours
**Level:** 300 (Intermediate to Advanced)
**Audience:** Developers, Solutions Architects, Security Engineers

---

## Workshop Description

Deploy and explore Amazon Bedrock AgentCore end-to-end using a pre-built manufacturing insights agent with MCP servers. Walk through each component hands-on: Runtime (microVM isolation), Gateway (MCP routing + interceptors), Registry (tool discovery + governance), Identity (Cognito JWT scopes), Policy (Cedar authorization), Memory (cross-session persistence with namespace isolation), and Observability (X-Ray + audit logs). Test queries as three personas with different access boundaries. All code provided — focus on deploying, testing, and understanding.

---

## Modules

| # | Module | Duration | What Participants Do |
|---|--------|----------|---------------------|
| 1 | Introduction & Architecture | 10 min | Understand the problem, architecture, personas |
| 2 | Prerequisites & Setup | 10 min | Clone repo, set up environment, verify credentials |
| 3 | MCP Servers | 25 min | Explore, start, and test 4 domain MCP servers |
| 4 | Strands Agent | 20 min | Connect agent to MCP servers, run queries, see reasoning |
| 5 | AgentCore Runtime | 15 min | Understand Firecracker microVMs, session isolation |
| 6 | AgentCore Gateway | 20 min | Deploy Gateway, register MCP servers as Lambda targets, interceptor pipeline |
| 7 | AgentCore Registry | 15 min | Tool discovery, versioning, governance, adding new servers |
| 8 | AgentCore Identity | 15 min | Set up Cognito, users with scope attributes, JWT flow |
| 9 | AgentCore Policy | 25 min | Write Cedar policies, test ALLOW/DENY scenarios |
| 10 | AgentCore Memory | 15 min | Explore short-term, long-term, episodic memory with code |
| 11 | AgentCore Evaluations | 20 min | Run 7 eval metrics, understand rubrics, validate system |
| 12 | AgentCore Observability | 15 min | X-Ray tracing, CloudWatch logs, metrics, alerts |
| 13 | Cleanup | 5 min | Remove all AWS resources |
| 14 | Conclusion | 5 min | Recap, resources, next steps |

---

## AgentCore Components Covered

| Component | What It Does | Module |
|-----------|-------------|--------|
| **Runtime** | Firecracker microVMs with session isolation, <50ms cold start | 5 |
| **Gateway** | MCP routing, interceptor pipeline, 3-tier caching | 6 |
| **Registry** | Tool discovery, versioning, governance, deprecation | 7 |
| **Identity** | OAuth/Cognito integration, JWT scope propagation | 8 |
| **Policy** | Cedar deterministic authorization, forbid/permit, <1ms evaluation | 9 |
| **Memory** | Short-term (session), long-term (baselines), episodic (events) | 10 |
| **Evaluations** | 7 metrics: tool accuracy, policy compliance, faithfulness, trajectory | 11 |
| **Observability** | X-Ray traces, CloudWatch audit logs, latency/cost metrics | 12 |

---

## Evaluation Metrics

| # | Metric | Target | When to Use |
|---|--------|--------|-------------|
| 1 | Tool Selection Accuracy | > 90% | After changing prompts or tool descriptions |
| 2 | Tool Parameter Accuracy | > 95% | After changing schemas or identity models |
| 3 | Policy Denial Compliance | 100% | After every Cedar policy change (non-negotiable) |
| 4 | Faithfulness | > 0.90 | After model upgrades or prompt changes |
| 5 | Helpfulness | > 0.85 | When users report unhelpful responses |
| 6 | Trajectory Quality | > 0.85 | After adding new MCP servers or changing semantic layer |
| 7 | Goal Success Rate | > 0.85 | Weekly regression check |

---

## Memory Constructs

| Type | Scope | Lifetime | Use Case |
|------|-------|----------|----------|
| **Short-term** | Session | End of session | Follow-ups: "Is that normal?" |
| **Long-term** | User/Team/Org | TTL (90-365 days) | Baselines: "Machine 42 normal = 2.5 mm/s" |
| **Episodic** | User | TTL (90 days) | Events: "July 2 — flagged vibration at 3.8" |

---

## User Personas

| User | Role | Scope | Access |
|------|------|-------|--------|
| Sarah Chen | Plant Manager | All plants, all lines | Full access |
| Raj Patel | Line Supervisor | Plant 2, Line 7 | Line 7 only |
| Priya Nair | Maintenance Technician | Plant 1, Line 4, Machines 41-45 | Equipment-scoped |

---

## Resources Required

| Resource | Purpose |
|----------|---------|
| AgentCore Gateway | MCP routing + policy enforcement |
| Lambda (x5) | Tool targets (Equipment, IoT, Analytics, Supply Chain, Semantic) |
| Lambda (x2) | Interceptors (Request, Response) |
| Cognito User Pool | 3 users with role/scope attributes |
| Policy Engine | Cedar policies (3 forbid + 1 permit) |
| CloudWatch | Dashboard, logs, alarms |
| S3 | Memory persistence (user/team/org namespaces) |

---

## Workshop Content Location

```
workshop/
├── contentspec.yaml
├── static/images/
└── content/
    ├── index.en.md                    # Landing page
    ├── 010_introduction/
    ├── 020_prerequisites/
    ├── 030_mcp_servers/
    ├── 040_strands_agent/
    ├── 050_agentcore_runtime/
    ├── 060_agentcore_gateway/
    ├── 065_agentcore_registry/
    ├── 070_agentcore_identity/
    ├── 080_agentcore_policy/
    ├── 090_agentcore_memory/
    ├── 100_agentcore_evaluations/
    ├── 110_agentcore_observability/
    ├── 120_cleanup/
    └── 130_conclusion/
```

Published at: [AWS Workshop Studio](https://studio.us-east-1.prod.workshops.aws/workshops/d0a69ef1-5881-481c-a6b4-172edb8c2a6d)
