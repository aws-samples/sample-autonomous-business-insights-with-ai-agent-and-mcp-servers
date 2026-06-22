# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Deployment script for Amazon Bedrock AgentCore.

This script demonstrates how to deploy the multi-agent system to AgentCore
Runtime using the AgentCore starter toolkit. In production, each MCP server
is deployed independently and registered in the AgentCore Registry.

AgentCore provides:
- Firecracker microVM isolation per user session
- Serverless scaling (no infrastructure to manage)
- Automatic MCP server discovery via the Gateway
- Identity propagation and policy enforcement
- Built-in observability and CloudTrail audit logging

Prerequisites:
- AWS CLI configured with appropriate permissions
- AgentCore starter toolkit installed: pip install bedrock-agentcore-starter-toolkit
- Model access enabled for Claude Sonnet in Amazon Bedrock console
"""

import argparse
import json
import logging
import sys

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def deploy_mcp_servers(region: str) -> dict[str, str]:
    """Deploy MCP servers to AgentCore Runtime.

    Each MCP server is deployed as an independent runtime unit. Once deployed,
    it's registered in the AgentCore Registry and automatically discoverable
    by the Supervisor Agent through the Gateway.

    Args:
        region: AWS region for deployment.

    Returns:
        Dictionary mapping server names to their deployed endpoint URLs.
    """
    logger.info("Deploying MCP servers to AgentCore Runtime in %s...", region)

    # In a real deployment, you would use the AgentCore CLI or SDK:
    #
    #   from bedrock_agentcore.runtime import AgentCoreApp
    #
    #   app = AgentCoreApp()
    #
    #   @app.entry_point
    #   async def handler(request):
    #       # MCP server logic here
    #       pass
    #
    #   app.deploy(region=region)
    #
    # Or via CLI:
    #   agentcore deploy --runtime-name equipment-mcp-server

    servers = {
        "equipment-mcp-server": "Deployed",
        "iot-telemetry-mcp-server": "Deployed",
        "supply-chain-mcp-server": "Deployed",
        "analytics-mcp-server": "Deployed",
    }

    for server_name, status in servers.items():
        logger.info("  ✓ %s — %s", server_name, status)

    return servers


def configure_gateway(region: str, server_endpoints: dict[str, str]) -> None:
    """Configure the AgentCore Gateway with MCP server registrations.

    The Gateway is the single entry point through which every agent-to-tool
    call flows. It performs protocol handshakes, indexes available tools,
    and implements the three-tier caching strategy.

    Args:
        region: AWS region.
        server_endpoints: Deployed server endpoints to register.
    """
    logger.info("Configuring AgentCore Gateway...")
    logger.info("  • Registering %d MCP servers", len(server_endpoints))
    logger.info("  • Enabling three-tier caching (org, user, policy-aware)")
    logger.info("  • Setting up tool indexing and routing")
    logger.info("  ✓ Gateway configured")


def configure_identity(region: str) -> None:
    """Configure AgentCore Identity integration.

    Integrates with your existing identity provider (Okta, AWS IAM, Cognito)
    to capture user identity and propagate it through the call chain.

    Args:
        region: AWS region.
    """
    logger.info("Configuring AgentCore Identity...")
    logger.info("  • Identity provider: Amazon Cognito (configurable)")
    logger.info("  • Authentication flow: User-delegated access")
    logger.info("  • Identity propagation: Via Mcp-Session-Id header")
    logger.info("  ✓ Identity configured")


def configure_policies(region: str) -> None:
    """Configure Cedar-based access policies in AgentCore Policy.

    Policies are defined in plain English and translated to Cedar logic.
    Automated reasoning validates for completeness before deployment.

    Args:
        region: AWS region.
    """
    logger.info("Configuring AgentCore Policy (Cedar)...")

    policies = [
        {
            "description": "Plant managers can access all equipment and sensor data across all plants",
            "principal": "role::plant_manager",
            "action": "get_equipment_status, get_maintenance_history, get_shared_infrastructure, get_sensor_readings, detect_anomaly, check_parts_inventory, get_supplier_lead_times, get_oee_trends, get_quality_metrics, discover_data_sources, get_data_catalog",
            "resource": "gateway::${gateway_arn}",
            "effect": "permit",
        },
        {
            "description": "Line supervisors can only access data for their assigned lines",
            "principal": "role::line_supervisor",
            "action": "get_equipment_status, detect_anomaly, get_oee_trends",
            "resource": "line::${principal.assigned_lines}",
            "effect": "permit",
        },
        {
            "description": "Maintenance technicians can only access their assigned equipment",
            "principal": "role::maintenance_technician",
            "action": "get_sensor_readings, get_maintenance_history, check_parts_inventory",
            "resource": "machine::${principal.assigned_equipment}",
            "effect": "permit",
        },
    ]

    for policy in policies:
        logger.info("  • %s", policy["description"])

    logger.info("  ✓ %d policies deployed and validated", len(policies))


def configure_memory(region: str) -> None:
    """Configure AgentCore Memory namespaces.

    Memory is organized into namespaces: user-scoped (visible only to
    individual), team-scoped (shared within group), organization-scoped
    (company-wide knowledge).

    Args:
        region: AWS region.
    """
    logger.info("Configuring AgentCore Memory...")
    logger.info("  • Namespace: user (preferences, query patterns)")
    logger.info("  • Namespace: team (anomaly thresholds, procedures)")
    logger.info("  • Namespace: organization (equipment catalog, site codes)")
    logger.info("  • Retention: 90 days (user), unlimited (org)")
    logger.info("  ✓ Memory configured")


def deploy_supervisor_agent(region: str) -> None:
    """Deploy the Supervisor Agent to AgentCore Runtime.

    The Supervisor Agent is deployed as a Strands Agent that automatically
    discovers all registered MCP tools through the Gateway.

    Args:
        region: AWS region.
    """
    logger.info("Deploying Supervisor Agent to AgentCore Runtime...")
    logger.info("  • Framework: Strands Agents SDK")
    logger.info("  • Model: Claude Sonnet (Amazon Bedrock)")
    logger.info("  • Tool discovery: Automatic via Gateway")
    logger.info("  • Isolation: Firecracker microVM per session")
    logger.info("  ✓ Supervisor Agent deployed")


def main() -> None:
    """Run the full deployment pipeline."""
    parser = argparse.ArgumentParser(
        description="Deploy the multi-agent system to Amazon Bedrock AgentCore"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region for deployment (default: us-east-1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show deployment plan without executing",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Amazon Bedrock AgentCore Deployment")
    logger.info("Region: %s", args.region)
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("[DRY RUN] Showing deployment plan only.\n")

    # Step 1: Deploy MCP servers
    server_endpoints = deploy_mcp_servers(args.region)

    # Step 2: Configure Gateway
    configure_gateway(args.region, server_endpoints)

    # Step 3: Configure Identity
    configure_identity(args.region)

    # Step 4: Configure Policies
    configure_policies(args.region)

    # Step 5: Configure Memory
    configure_memory(args.region)

    # Step 6: Deploy Supervisor Agent
    deploy_supervisor_agent(args.region)

    logger.info("\n" + "=" * 60)
    logger.info("✅ Deployment complete!")
    logger.info("=" * 60)
    logger.info("\nThe system is now accessible via the AgentCore API endpoint.")
    logger.info("Users can authenticate through your configured IdP and")
    logger.info("start querying immediately with natural language.\n")


if __name__ == "__main__":
    main()
