# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Manufacturing Insights Agent — single agent, multiple MCP servers.

Architecture (Default — AgentCore Gateway):
  User Query → Agent (Strands + Bedrock) → AgentCore Gateway → MCP Targets (Lambda)
                                                ↓
                                    REQUEST Interceptor (JWT → user_context)
                                    Cedar Policy Engine (ENFORCE)
                                    Tool Target Lambda (only if PERMIT)

  Policy enforcement is handled entirely by the Gateway. The agent has no
  policy logic — it simply sends tool calls to the Gateway URL, and the Gateway
  evaluates Cedar policies before invoking the Lambda tool target.

  This is the DEFAULT and RECOMMENDED architecture. The Gateway provides
  production-grade policy enforcement, observability, and isolation.

Architecture (Simulation Fallback — SIMULATION_MODE=true):
  User Query → Agent (Strands + Bedrock) → [Local PolicyHook] → MCP Servers (HTTP)

  A local GatewayPolicyHook simulates Gateway enforcement for development.
  Use this ONLY when you don't have a deployed AgentCore Gateway.
  See src/identity/gateway_hook.py for details.

  Set SIMULATION_MODE=true to activate this fallback.

MCP Server Connectivity:
  - PRE-BUILT AWS MCP servers (via stdio/uvx):
    - awslabs.postgres-mcp-server → Aurora PostgreSQL (equipment, maintenance)
    - awslabs.redshift-mcp-server → Redshift Serverless (supply chain, OEE)
  - CUSTOM MCP servers (via streamable HTTP):
    - IoT Telemetry MCP → Amazon Timestream (sensor data, anomaly detection)
    - Analytics/Quality MCP → Amazon OpenSearch (quality metrics, semantic search)
    - Semantic Layer MCP → Data source discovery catalog

This demonstrates the "configuration, not code" approach:
  - Pre-built connectors for common AWS services (zero code needed)
  - Custom servers only for domain-specific tools not covered by pre-built options
"""

import logging
import os
import uuid
from contextlib import ExitStack

from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import StdioServerParameters, stdio_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient

from src.config import AppConfig
from src.identity.models import UserIdentity
from src.identity.gateway_hook import GatewayPolicyHook
from src.identity.policy import PolicyEngine
from src.memory.manager import MemoryManager
from src.agent.prompts import build_agent_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Operating mode flags
# ---------------------------------------------------------------------------
# SIMULATION_MODE: When true, the agent uses local MCP servers and a local
# policy hook instead of the real AgentCore Gateway. This is the development
# fallback — NOT the default production path.
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"

# USE_PREBUILT_MCP: When true (and not in simulation mode), use pre-built
# AWS MCP servers (postgres, redshift) via stdio/uvx for the data layer.
USE_PREBUILT_MCP = os.getenv("USE_PREBUILT_MCP", "false").lower() == "true"

# Memory summary truncation length
MEMORY_SUMMARY_MAX_LEN = 200


class ManufacturingInsightsAgent:
    """Single agent connected to multiple MCP servers via AgentCore Gateway.

    Default mode (AgentCore Gateway — production):
      All tool calls route through the deployed Gateway which handles MCP
      protocol, Cedar policy enforcement, and Lambda target invocation.
      No local policy logic is needed.

    Simulation mode (SIMULATION_MODE=true — development fallback):
      When USE_PREBUILT_MCP=true:
        - Equipment/Maintenance: awslabs.postgres-mcp-server (via stdio/uvx)
        - Supply Chain/OEE: awslabs.redshift-mcp-server (via stdio/uvx)
        - IoT Telemetry: Custom MCP server (streamable HTTP, port 8002)
        - Quality/Analytics: Custom MCP server (streamable HTTP, port 8004)
        - Semantic Layer: Custom MCP server (streamable HTTP, port 8005)

      When USE_PREBUILT_MCP=false:
        - All servers run locally via streamable HTTP (ports 8001-8005)

      A local GatewayPolicyHook approximates Cedar policy enforcement.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.policy_engine = PolicyEngine()
        self.memory_manager = MemoryManager()

    def _create_mcp_clients(self) -> list[MCPClient]:
        """Create MCP client connections based on the current operating mode.

        Priority (highest first):
          1. AgentCore Gateway (default) — routes through deployed Gateway URL
          2. Pre-built + custom MCP (SIMULATION_MODE=true, USE_PREBUILT_MCP=true)
          3. All-local HTTP MCP (SIMULATION_MODE=true, USE_PREBUILT_MCP=false)
        """
        if SIMULATION_MODE:
            if USE_PREBUILT_MCP:
                return self._create_prebuilt_clients()
            return self._create_local_clients()

        # Default: AgentCore Gateway
        return self._create_gateway_client()

    def _create_gateway_client(self) -> list[MCPClient]:
        """Connect to tools via AgentCore Gateway (DEFAULT production path).

        All tool calls route through the Gateway URL which handles:
        - MCP protocol (initialize, tools/list, tools/call)
        - REQUEST Interceptor: JWT extraction → user_context injection
        - Cedar Policy Engine: evaluate forbid/permit rules (ENFORCE mode)
        - Lambda target invocation (only if Cedar permits)
        - RESPONSE Interceptor: filter tool list by role
        - CloudTrail audit logging of every policy decision
        - Firecracker microVM isolation per session

        No local policy hook is needed — the Gateway enforces policies
        server-side before the Lambda tool target is ever invoked.
        """
        gateway_url = os.getenv(
            "AGENTCORE_GATEWAY_URL",
            "https://your-test-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp/",
        )
        logger.info("Using AgentCore Gateway (default): %s", gateway_url)

        gateway_client = MCPClient(
            lambda: streamablehttp_client(gateway_url)
        )
        return [gateway_client]

    def _create_prebuilt_clients(self) -> list[MCPClient]:
        """Create clients using pre-built AWS MCP servers (stdio via uvx).

        Uses:
          - awslabs.postgres-mcp-server for Aurora (equipment + maintenance)
          - awslabs.redshift-mcp-server for Redshift (supply chain + OEE)
          - Custom HTTP servers for IoT, Quality, and Semantic Layer
        """
        clients = []

        # Pre-built: Aurora PostgreSQL MCP Server (equipment + maintenance)
        postgres_client = MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command="uvx",
                args=["awslabs.postgres-mcp-server@latest", "--allow_write_query"],
                env={
                    "AWS_REGION": os.getenv("AWS_REGION", "us-east-1"),
                    "AWS_PROFILE": os.getenv("AWS_PROFILE", "default"),
                    "FASTMCP_LOG_LEVEL": "ERROR",
                },
            )
        ))
        clients.append(postgres_client)

        # Pre-built: Amazon Redshift MCP Server (supply chain + OEE)
        redshift_client = MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command="uvx",
                args=["awslabs.redshift-mcp-server@latest"],
                env={
                    "AWS_REGION": os.getenv("AWS_REGION", "us-east-1"),
                    "AWS_PROFILE": os.getenv("AWS_PROFILE", "default"),
                    "FASTMCP_LOG_LEVEL": "ERROR",
                },
            )
        ))
        clients.append(redshift_client)

        # Custom: IoT Telemetry (streamable HTTP — no pre-built Timestream MCP)
        iot_client = MCPClient(
            lambda: streamablehttp_client(self.config.mcp_servers.iot_telemetry_url)
        )
        clients.append(iot_client)

        # Custom: Analytics/Quality (streamable HTTP — no pre-built OpenSearch MCP)
        analytics_client = MCPClient(
            lambda: streamablehttp_client(self.config.mcp_servers.analytics_url)
        )
        clients.append(analytics_client)

        # Custom: Semantic Layer (streamable HTTP — data source discovery)
        semantic_client = MCPClient(
            lambda: streamablehttp_client(self.config.mcp_servers.semantic_layer_url)
        )
        clients.append(semantic_client)

        return clients

    def _create_local_clients(self) -> list[MCPClient]:
        """Create clients for all-local simulation (streamable HTTP).

        All 5 MCP servers run locally via python -m src.servers.start_all.
        Used only in SIMULATION_MODE when USE_PREBUILT_MCP=false.
        """
        server_urls = [
            self.config.mcp_servers.semantic_layer_url,
            self.config.mcp_servers.equipment_url,
            self.config.mcp_servers.iot_telemetry_url,
            self.config.mcp_servers.supply_chain_url,
            self.config.mcp_servers.analytics_url,
        ]

        return [
            MCPClient(lambda url=url: streamablehttp_client(url))
            for url in server_urls
        ]

    def _build_system_prompt(self, user: UserIdentity, session_id: str) -> str:
        """Build the system prompt with user identity, scope, and memory context."""
        preferences = self.memory_manager.get_user_preferences(user.user_id)
        pref_str = preferences.get("output_format", "None specified")

        memory_entries = self.memory_manager.get_long_term_context(user.user_id)
        memory_str = "\n".join(
            f"- [{e.timestamp}] {e.content}" for e in memory_entries
        ) if memory_entries else "No prior context available"

        session = self.memory_manager.get_or_create_session(user.user_id, session_id)
        recent = session.get_recent_context()
        if recent:
            memory_str += "\n\nRecent session context:\n" + "\n".join(
                f"- Q: {r['query']}" for r in recent
            )

        if user.has_full_access:
            scope_str = "Full access - all plants, all assembly lines"
        else:
            scope_str = (
                f"Plants: {user.plant_scope}, "
                f"Lines: {user.line_scope}, "
                f"Equipment: {user.equipment_scope or 'via line scope'}"
            )

        return build_agent_prompt(
            user_name=user.name,
            user_role=user.role.value.replace("_", " ").title(),
            user_scope=scope_str,
            user_preferences=pref_str,
            memory_context=memory_str,
        )

    def query(self, user: UserIdentity, question: str) -> str:
        """Process a natural language query.

        Flow (Default — AgentCore Gateway):
        1. Build system prompt with identity + memory context
        2. Connect to AgentCore Gateway (single MCP endpoint)
        3. Gateway provides tools/list (filtered by RESPONSE Interceptor)
        4. Create agent WITHOUT policy hooks (Gateway enforces server-side)
        5. Agent reasons, calls tools via Gateway
        6. Gateway evaluates Cedar → invokes Lambda target → returns result
        7. Record in memory

        Flow (Simulation Fallback — SIMULATION_MODE=true):
        1. Build system prompt with identity + memory context
        2. Connect to local MCP servers (HTTP or stdio)
        3. Create agent WITH local GatewayPolicyHook (approximates Gateway)
        4. Agent reasons, calls tools with local policy check
        5. Record in memory

        Args:
            user: Authenticated user identity with scope attributes.
            question: Natural language query.

        Returns:
            Synthesized response from the agent.
        """
        session_id = str(uuid.uuid4())
        logger.info(
            "Processing query for user '%s' (role=%s, session=%s, mode=%s)",
            user.name,
            user.role.value,
            session_id[:8],
            "simulation" if SIMULATION_MODE else "agentcore_gateway",
        )

        system_prompt = self._build_system_prompt(user, session_id)
        mcp_clients = self._create_mcp_clients()

        with ExitStack() as stack:
            for client in mcp_clients:
                stack.enter_context(client)

            all_tools = []
            for client in mcp_clients:
                tools = client.list_tools_sync()
                all_tools.extend(tools)

            logger.info(
                "Connected to %d MCP servers, %d tools available",
                len(mcp_clients),
                len(all_tools),
            )

            if SIMULATION_MODE:
                # Simulation fallback: local policy hook approximates Gateway enforcement
                gateway_hook = GatewayPolicyHook(
                    user=user,
                    policy_engine=self.policy_engine,
                )
                agent = Agent(
                    system_prompt=system_prompt,
                    tools=all_tools,
                    hooks=[gateway_hook],
                    callback_handler=None,
                )
                logger.info("Policy enforcement: Local GatewayPolicyHook (simulation fallback)")
            else:
                # Default: AgentCore Gateway handles policy enforcement server-side
                # No local hook — Cedar evaluates at the Gateway before Lambda invocation
                agent = Agent(
                    system_prompt=system_prompt,
                    tools=all_tools,
                    callback_handler=None,
                )
                logger.info("Policy enforcement: AgentCore Gateway (server-side Cedar)")

            response = agent(question)
            response_text = str(response)

            # Track token usage for budget management
            # Estimate tokens: ~4 chars per token (rough approximation)
            estimated_tokens = (len(question) + len(response_text)) // 4
            try:
                from src.budget.manager import BudgetManager
                budget_mgr = BudgetManager.get_instance(use_dynamodb=False)
                budget_mgr.increment_usage(user.user_id, tokens_used=estimated_tokens)
                logger.info(
                    "Budget: user=%s consumed ~%d tokens this query",
                    user.user_id, estimated_tokens,
                )
            except Exception as e:
                logger.debug("Budget tracking skipped: %s", e)

            session = self.memory_manager.get_or_create_session(user.user_id, session_id)
            session.add_interaction(
                query=question,
                response_summary=response_text[:MEMORY_SUMMARY_MAX_LEN],
            )

            return response_text
