# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Configuration management for the Manufacturing Insights Agent.

Operating Modes:
  Default (AgentCore Gateway):
    The agent routes all tool calls through the deployed AgentCore Gateway.
    Set AGENTCORE_GATEWAY_URL to your Gateway endpoint.

  Simulation Fallback (SIMULATION_MODE=true):
    The agent connects to local MCP servers and uses a local policy hook.
    MCPServerConfig ports are only used in this mode.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class BedrockConfig:
    """Amazon Bedrock model configuration."""

    region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))
    model_id: str = field(
        default_factory=lambda: os.getenv(
            "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
        )
    )


@dataclass(frozen=True)
class GatewayConfig:
    """AgentCore Gateway configuration (default production mode)."""

    url: str = field(
        default_factory=lambda: os.getenv(
            "AGENTCORE_GATEWAY_URL",
            "https://your-test-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp/",
        )
    )


@dataclass(frozen=True)
class MCPServerConfig:
    """MCP server endpoint configuration (used in SIMULATION_MODE only).

    These local server ports are only relevant when SIMULATION_MODE=true.
    In the default mode, tool calls route through the AgentCore Gateway.
    """

    semantic_layer_port: int = field(
        default_factory=lambda: int(os.getenv("SEMANTIC_LAYER_SERVER_PORT", "8005"))
    )
    equipment_port: int = field(
        default_factory=lambda: int(os.getenv("EQUIPMENT_SERVER_PORT", "8001"))
    )
    iot_telemetry_port: int = field(
        default_factory=lambda: int(os.getenv("IOT_TELEMETRY_SERVER_PORT", "8002"))
    )
    supply_chain_port: int = field(
        default_factory=lambda: int(os.getenv("SUPPLY_CHAIN_SERVER_PORT", "8003"))
    )
    analytics_port: int = field(
        default_factory=lambda: int(os.getenv("ANALYTICS_SERVER_PORT", "8004"))
    )

    @property
    def semantic_layer_url(self) -> str:
        return f"http://localhost:{self.semantic_layer_port}/mcp/"

    @property
    def equipment_url(self) -> str:
        return f"http://localhost:{self.equipment_port}/mcp/"

    @property
    def iot_telemetry_url(self) -> str:
        return f"http://localhost:{self.iot_telemetry_port}/mcp/"

    @property
    def supply_chain_url(self) -> str:
        return f"http://localhost:{self.supply_chain_port}/mcp/"

    @property
    def analytics_url(self) -> str:
        return f"http://localhost:{self.analytics_port}/mcp/"


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration.

    The agent operates in one of two modes:
      - Default: AgentCore Gateway (gateway config used)
      - Fallback: Simulation mode (mcp_servers config used)

    Set SIMULATION_MODE=true to activate the local simulation fallback.
    """

    bedrock: BedrockConfig = field(default_factory=BedrockConfig)
    gateway: GatewayConfig = field(default_factory=GatewayConfig)
    mcp_servers: MCPServerConfig = field(default_factory=MCPServerConfig)
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
