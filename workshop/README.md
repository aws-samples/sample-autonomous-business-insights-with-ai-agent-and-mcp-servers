# Workshop: Generate Autonomous Business Insights with MCP Servers

This directory contains the AWS Workshop content for the Manufacturing Insights Agent sample.

## Workshop URL

Once published: `https://catalog.workshops.aws/autonomous-business-insights-mcp`

## Structure

The workshop follows the standard AWS Workshop Studio format:

```
workshop/
├── content/
│   ├── _index.md                    # Workshop landing page
│   ├── 01-introduction/
│   │   ├── _index.md               # Module 1: The Problem & Architecture
│   │   └── 01-architecture.md      # Architecture overview + sequence diagrams
│   ├── 02-setup/
│   │   ├── _index.md               # Module 2: Environment Setup
│   │   ├── 01-prerequisites.md     # AWS account, CLI, Python
│   │   └── 02-clone-and-install.md # Clone repo, create venv, verify
│   ├── 03-mcp-servers/
│   │   ├── _index.md               # Module 3: Build MCP Servers
│   │   ├── 01-what-is-mcp.md       # MCP protocol overview
│   │   ├── 02-equipment-server.md  # Build equipment MCP server (step-by-step)
│   │   ├── 03-iot-server.md        # Build IoT telemetry server
│   │   ├── 04-semantic-layer.md    # Data catalog as MCP server
│   │   └── 05-test-servers.md      # Start & test all 5 servers
│   ├── 04-agent/
│   │   ├── _index.md               # Module 4: Build the Agent
│   │   └── 01-connect-and-query.md # Connect to MCP servers + first query
│   ├── 05-policy/
│   │   ├── _index.md               # Module 5: Access Control
│   │   └── 01-gateway-hook.md      # Gateway Cedar enforcement + local simulation
│   ├── 06-memory/
│   │   ├── _index.md               # Module 6: Memory & Context
│   │   └── 01-memory-demo.md       # Session + long-term memory demo
│   ├── 07-live-infrastructure/
│   │   ├── _index.md               # Module 7: Real AWS Services (optional)
│   │   └── 01-deploy-stack.md      # Deploy CloudFormation + seed data
│   ├── 08-web-ui/
│   │   └── _index.md               # Module 8: Streamlit Demo UI + scenarios
│   └── 09-cleanup/
│       └── _index.md               # Module 9: Cleanup resources
└── static/
    └── images/                      # Architecture diagrams, screenshots
```

## Running Locally

```bash
cd workshop
hugo server
```

## Duration

- **Self-paced**: 2-3 hours
- **Instructor-led**: 90 minutes (skip Module 7 for time)
