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
│   │   ├── _index.md               # Module 1: The Problem
│   │   ├── 01-scenario.md          # Manufacturing scenario
│   │   ├── 02-architecture.md      # Architecture overview
│   │   └── 03-what-you-will-build.md
│   ├── 02-setup/
│   │   ├── _index.md               # Module 2: Environment Setup
│   │   ├── 01-prerequisites.md     # AWS account, CLI, Python
│   │   ├── 02-clone-and-install.md # Clone repo, create venv
│   │   └── 03-verify.md            # Verify Bedrock access
│   ├── 03-mcp-servers/
│   │   ├── _index.md               # Module 3: Build MCP Servers
│   │   ├── 01-what-is-mcp.md       # MCP protocol overview
│   │   ├── 02-equipment-server.md  # Build equipment MCP server
│   │   ├── 03-iot-server.md        # Build IoT telemetry server
│   │   ├── 04-test-servers.md      # Test MCP servers locally
│   │   └── 05-semantic-layer.md    # Data catalog as MCP server
│   ├── 04-agent/
│   │   ├── _index.md               # Module 4: Build the Agent
│   │   ├── 01-strands-agent.md     # Strands SDK basics
│   │   ├── 02-connect-mcp.md       # Connect agent to MCP servers
│   │   ├── 03-system-prompt.md     # Identity-aware prompts
│   │   └── 04-first-query.md       # Run your first query
│   ├── 05-policy/
│   │   ├── _index.md               # Module 5: Access Control
│   │   ├── 01-identity-model.md    # User roles and scopes
│   │   ├── 02-cedar-policy.md      # Cedar-style policy engine
│   │   ├── 03-gateway-hook.md      # Gateway-level Cedar enforcement (+ local simulation)
│   │   └── 04-test-access.md       # Verify policy enforcement
│   ├── 06-memory/
│   │   ├── _index.md               # Module 6: Memory & Context
│   │   ├── 01-session-memory.md    # Short-term context
│   │   ├── 02-long-term-memory.md  # Cross-session persistence
│   │   └── 03-test-memory.md       # Week-over-week comparison
│   ├── 07-live-infrastructure/
│   │   ├── _index.md               # Module 7: Real AWS Services
│   │   ├── 01-deploy-stack.md      # Deploy CloudFormation
│   │   ├── 02-seed-data.md         # Populate all services
│   │   ├── 03-switch-live.md       # Toggle to live mode
│   │   └── 04-query-live.md        # Query against real infra
│   ├── 08-web-ui/
│   │   ├── _index.md               # Module 8: Streamlit Demo UI
│   │   ├── 01-launch-ui.md         # Start Streamlit
│   │   └── 02-demo-scenarios.md    # Walk through all 3 personas
│   └── 09-cleanup/
│       ├── _index.md               # Module 9: Cleanup
│       └── 01-delete-resources.md  # Delete stack, clean up
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
