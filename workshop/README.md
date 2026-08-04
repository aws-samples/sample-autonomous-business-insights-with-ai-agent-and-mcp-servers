# Workshop: Generate Autonomous Business Insights with AI Agents and MCP Servers

This directory contains the content for the AWS Workshop Studio workshop.

## Structure

```
workshop/
├── contentspec.yaml              # Workshop Studio version spec
├── README.md                     # This file
├── static/
│   └── images/                   # Workshop diagrams and screenshots
└── content/
    ├── index.en.md               # Landing page
    ├── 010_introduction/         # Module 1: Introduction & Architecture
    ├── 020_prerequisites/        # Module 2: Prerequisites & Setup
    ├── 030_mcp_servers/          # Module 3: Understanding MCP Servers
    ├── 040_strands_agent/        # Module 4: Building the Strands Agent
    ├── 050_agentcore_runtime/    # Module 5: AgentCore Runtime
    ├── 060_agentcore_gateway/    # Module 6: AgentCore Gateway
    ├── 070_agentcore_identity/   # Module 7: AgentCore Identity
    ├── 080_agentcore_policy/     # Module 8: AgentCore Policy (Cedar)
    ├── 090_agentcore_memory/     # Module 9: AgentCore Memory
    ├── 100_agentcore_evaluations/# Module 10: AgentCore Evaluations
    ├── 110_agentcore_observability/ # Module 11: AgentCore Observability
    ├── 120_cleanup/              # Cleanup
    └── 130_conclusion/           # Conclusion & Next Steps
```

## Module Flow

| # | Module | Duration | What Participants Do |
|---|--------|----------|---------------------|
| 1 | Introduction | 10 min | Understand the problem, architecture, personas |
| 2 | Prerequisites | 10 min | Set up environment, verify credentials |
| 3 | MCP Servers | 25 min | Explore, start, and test 4 domain MCP servers |
| 4 | Strands Agent | 20 min | Connect agent to servers, run queries, see reasoning |
| 5 | AgentCore Runtime | 15 min | Understand Firecracker microVMs, session isolation |
| 6 | AgentCore Gateway | 20 min | Deploy Gateway, Lambda targets, interceptor pipeline |
| 7 | AgentCore Identity | 15 min | Set up Cognito, users with scope attributes, JWT flow |
| 8 | AgentCore Policy | 25 min | Write Cedar policies, test ALLOW/DENY scenarios |
| 9 | AgentCore Memory | 15 min | Explore session + cross-session memory, TTL |
| 10 | Evaluations | 20 min | Run policy tests, integration tests, validation |
| 11 | Observability | 15 min | X-Ray tracing, CloudWatch logs, metrics, alerts |
| 12 | Cleanup | 5 min | Remove all AWS resources |
| 13 | Conclusion | 5 min | Recap, resources, next steps |

**Total: ~3 hours**

## Local Development

To preview the workshop locally, use the Workshop Studio preview tool:

```bash
# From the workshop/ directory
./preview_build
# Open http://localhost:8080
```

## Adding Content

- Each module is a directory under `content/` with an `index.en.md` file
- The `weight` field in the front matter controls navigation order
- Static assets (images, diagrams) go in `static/images/`
- Use `{{% notice info %}}` / `{{% notice warning %}}` / `{{% notice tip %}}` for callouts

## Publishing

Upload this workshop to AWS Workshop Studio via the content creation workflow at https://catalog.workshops.aws.
