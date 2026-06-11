# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Configuration management for the multi-agent business insights system."""

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
class MCPServerConfig:
    """MCP server endpoint configuration."""

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
    """Top-level application configuration."""

    bedrock: BedrockConfig = field(default_factory=BedrockConfig)
    mcp_servers: MCPServerConfig = field(default_factory=MCPServerConfig)
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
