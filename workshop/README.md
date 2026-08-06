# Workshop: Build Autonomous Business Insights with AI Agents, MCP Servers, and Amazon Bedrock AgentCore

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
    ├── 055_agentcore_harness/    # Module 6: AgentCore Harness (cost caps)
    ├── 060_agentcore_gateway/    # Module 7: AgentCore Gateway
    ├── 065_agentcore_registry/   # Module 8: AgentCore Registry
    ├── 070_agentcore_identity/   # Module 9: AgentCore Identity
    ├── 080_agentcore_policy/     # Module 10: AgentCore Policy (Cedar)
    ├── 085_cost_management/      # Module 11: Cost Management (Cedar + DynamoDB)
    ├── 090_agentcore_memory/     # Module 12: AgentCore Memory
    ├── 100_agentcore_evaluations/# Module 13: AgentCore Evaluations (7 metrics)
    ├── 110_agentcore_observability/ # Module 14: AgentCore Observability
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
| 6 | AgentCore Harness | 15 min | Managed deployment with hard cost caps (maxTokens, maxIterations) |
| 7 | AgentCore Gateway | 20 min | Deploy Gateway, register MCP servers as Lambda targets |
| 8 | AgentCore Registry | 15 min | Tool discovery, versioning, governance |
| 9 | AgentCore Identity | 15 min | Set up Cognito, users with scope attributes, JWT flow |
| 10 | AgentCore Policy | 25 min | Write Cedar policies, test ALLOW/DENY scenarios |
| 11 | Cost Management | 25 min | Three-layer budget enforcement (Harness + Cedar + DynamoDB) |
| 12 | AgentCore Memory | 15 min | Explore short-term, long-term, episodic memory |
| 13 | Evaluations | 20 min | Run 7 eval metrics, validate system |
| 14 | Observability | 15 min | X-Ray tracing, CloudWatch logs, metrics, alerts |
| 15 | Cleanup | 5 min | Remove all AWS resources |
| 16 | Conclusion | 5 min | Recap, resources, next steps |

**Total: ~3.5 hours**

## Local Development

To preview the workshop locally, use the Workshop Studio preview tool:

```bash
# From the workshop/ directory
./preview_build
# Open http://localhost:8080
```

## Adding Content

- Each module is a directory under `content/` with an `index.en.md` file
- The `weight` field in the YAML front matter (`---`) controls navigation order
- Static assets (images, diagrams) go in `static/images/`
- Use `:::alert{type="info"}` / `:::alert{type="warning"}` for callouts (not Hugo shortcodes)

## Publishing

Upload this workshop to AWS Workshop Studio via the content creation workflow at https://catalog.workshops.aws.

Workshop ID: `d0a69ef1-5881-481c-a6b4-172edb8c2a6d`
