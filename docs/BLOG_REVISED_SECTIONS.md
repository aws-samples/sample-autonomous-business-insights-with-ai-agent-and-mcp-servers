# Revised Blog Sections: AgentCore Components

Use these to replace the "How It Works" component sections in the blog.
Each uses official AWS language as the lead, then grounds it in the implementation.

---

## AgentCore Runtime: Isolated Execution for Every User

AgentCore Runtime deploys agents to secure, isolated Firecracker microVM environments — the same technology that powers AWS Lambda and AWS Fargate — with no servers to manage and automatic scaling.

When Sarah submits her query, Runtime spins up a dedicated microVM. Raj's session runs in a separate microVM. Priya's in a third. No shared filesystem, no shared memory, no shared networking. When the session ends, the microVM is destroyed. Multi-tenancy is a runtime guarantee, not a software convention.

In our implementation: The sample runs locally for development. In production, deploy with the AgentCore CLI and Runtime handles isolation automatically.

---

## AgentCore Gateway: Connect Across Your Stack, Control Every Call

AgentCore Gateway provides secure, authenticated connectivity between agents and tools — MCP servers, APIs, Lambda functions, and knowledge bases — with built-in tool discovery, routing, and caching.

The Gateway is the single entry point through which every tool call flows. When an MCP server is registered, the Gateway indexes all its tools. The agent calls tools by name; the Gateway routes to the correct server. A three-tier cache (organization-scoped, user-scoped, policy-aware) reduces latency for repeated queries.

In our implementation: We simulate the Gateway using a Strands BeforeToolCallEvent hook that intercepts every tool call for policy evaluation before it reaches the MCP server. See src/identity/gateway_hook.py.

---

## AgentCore Identity: Securing Agentic AI at Scale

AgentCore Identity provides robust identity and access management so that agents can access resources or tools either on behalf of users or themselves, with pre-authorized user consent, minimizing the need for custom access controls and identity infrastructure development.

Identity integrates with your existing providers (Okta, IAM, Cognito, any OAuth 2.0 system) and propagates user context through the entire call chain via the Mcp-Session-Id header. Two flows are supported: agent-level access (service-to-service) and user-delegated access (agent acts on behalf of a specific user with their scoped token).

In practice for Precision Manufacturing:

- Sarah's token (from Cognito) grants access to all three plants, all 12 lines
- Raj's token scopes to Plant 2, Line 7 only
- Priya's token scopes to Machine 41-45

These restrictions come from the IdP. AgentCore propagates them through the call chain and enforces them automatically. If Raj's scope changes in Cognito, the system reflects it immediately without code changes.

In our implementation: src/identity/models.py defines three user identities with explicit scopes. In production, these come from Cognito claims that AgentCore propagates automatically.

---

## AgentCore Policy: Authorization in Plain English

Policy in AgentCore integrates with Gateway to intercept every tool call in real time, ensuring agents stay within defined boundaries. Teams create policies using natural language that automatically convert to Cedar — the AWS open-source policy language — with automated reasoning that validates policies for completeness before deployment.

Policy enforcement happens at the Gateway level, intercepting every tool call before execution. Rules operate across multiple dimensions: user role, geographic scope, data classification, time of day, and specific tool parameters. A policy might read: "Line supervisors can call get_equipment_status only for lines within their assigned plant." When Raj asks about Line 8, the Gateway evaluates his identity against this rule and returns a deny decision before the MCP server is ever called. Every decision is logged to AWS CloudTrail.

In our implementation: src/identity/policy.py implements Cedar-style rules. src/identity/gateway_hook.py enforces them via BeforeToolCallEvent. When Raj asks about Line 4, the call is denied before the MCP server is ever contacted.

---

## AgentCore Memory: Context That Persists

AgentCore Memory enables agents to learn and adapt from experiences, building knowledge over time, with support for episodic memory that creates more humanlike interactions.

Memory operates at two levels:

Short-term memory captures turn-by-turn context within a single session. When Priya asks "Show me vibration trends on Machine 42," then follows with "Compare that to last week," the second question is understood in context without repeating the machine identifier.

Long-term memory persists selected insights across sessions, organized into namespaces:
- User-scoped: Priya's preferred units, her assigned equipment list
- Team-scoped: The maintenance team's standard anomaly thresholds
- Organization-scoped: Equipment catalog, site codes, product definitions

Retrieval always passes through Policy — even if an insight exists in long-term memory, it will not surface to a user who lacks access to the underlying data.

In our implementation: src/memory/manager.py provides SessionMemory (short-term) and MemoryManager (long-term with namespaces). Priya's memory contains last week's Machine 42 baseline (3.8 mm/s), enabling week-over-week comparison without repeating context.

---

## AgentCore Registry: Governed Tool Discovery

AWS Agent Registry enables organizations to discover, share, and reuse agents, tools, and agent skills across the organization through a governed catalog with publish-and-approve workflows.

New MCP servers enter the Registry in draft state. Administrators review and approve them. Once approved, the agent automatically discovers the new tools on the next invocation — no redeployment needed. The Registry also enables versioning: an updated connector can be staged alongside the current version, tested, and promoted without disrupting live sessions.

This governance model means the system grows incrementally. New data sources, new tools, and new connectors are added through a structured publish-and-approve workflow rather than code changes to the orchestration layer.

In our implementation: The Semantic Layer MCP server (src/servers/semantic_layer_server.py) simulates this — it maintains a catalog of registered data sources with their tools, glossary terms, and lineage. Adding a new source is one catalog entry, not a code change.
