# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Manufacturing Insights Agent — single agent, multiple MCP servers.

Architecture:
  User Query → Agent (Strands + Bedrock) → Gateway (policy) → MCP Servers → Data

This agent connects to a mix of:
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

# Environment variable to control whether to use pre-built AWS MCP servers
USE_PREBUILT_MCP = os.getenv("USE_PREBUILT_MCP", "false").lower() == "true"


class ManufacturingInsightsAgent:
    """Single agent connected to multiple MCP servers (pre-built + custom).

    When USE_PREBUILT_MCP=true:
      - Equipment/Maintenance: awslabs.postgres-mcp-server (via stdio/uvx)
      - Supply Chain/OEE: awslabs.redshift-mcp-server (via stdio/uvx)
      - IoT Telemetry: Custom MCP server (streamable HTTP, port 8002)
      - Quality/Analytics: Custom MCP server (streamable HTTP, port 8004)
      - Semantic Layer: Custom MCP server (streamable HTTP, port 8005)

    When USE_PREBUILT_MCP=false (default, for simulated mode):
      - All servers run locally via streamable HTTP (ports 8001-8005)
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.policy_engine = PolicyEngine()
        self.memory_manager = MemoryManager()

    def _create_mcp_clients(self) -> list[MCPClient]:
        """Create MCP client connections — pre-built (stdio) or custom (HTTP).

        Pre-built AWS MCP servers (awslabs) use stdio transport via uvx.
        Custom MCP servers use streamable HTTP on localhost.
        """
        if USE_PREBUILT_MCP:
            return self._create_prebuilt_clients()
        else:
            return self._create_local_clients()

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
        """Create clients for all-local development (streamable HTTP).

        All 5 MCP servers run locally via python -m src.servers.start_all.
        Used when USE_PREBUILT_MCP=false (default).
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

        Flow:
        1. Build system prompt with identity + memory context
        2. Connect to MCP servers (pre-built via stdio OR custom via HTTP)
        3. Collect all tools into one flat list
        4. Create agent with GatewayPolicyHook for access control
        5. Agent reasons, calls tools, synthesizes response
        6. Record in memory

        Args:
            user: Authenticated user identity with scope attributes.
            question: Natural language query.

        Returns:
            Synthesized response from the agent.
        """
        session_id = str(uuid.uuid4())
        logger.info(
            "Processing query for user '%s' (role=%s, session=%s, prebuilt=%s)",
            user.name,
            user.role.value,
            session_id[:8],
            USE_PREBUILT_MCP,
        )

        system_prompt = self._build_system_prompt(user, session_id)
        mcp_clients = self._create_mcp_clients()

        try:
            for client in mcp_clients:
                client.__enter__()

            all_tools = []
            for client in mcp_clients:
                tools = client.list_tools_sync()
                all_tools.extend(tools)

            logger.info(
                "Connected to %d MCP servers, %d tools available",
                len(mcp_clients),
                len(all_tools),
            )

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

            response = agent(question)
            response_text = str(response)

            session = self.memory_manager.get_or_create_session(user.user_id, session_id)
            session.add_interaction(
                query=question,
                response_summary=response_text[:200],
            )

            return response_text

        finally:
            for client in mcp_clients:
                try:
                    client.__exit__(None, None, None)
                except Exception:
                    pass
