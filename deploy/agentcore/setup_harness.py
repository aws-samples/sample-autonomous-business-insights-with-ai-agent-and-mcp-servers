# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
"""Deploy AgentCore Harness with per-role cost limits.

Harness is the managed deployment wrapper that provides:
- Firecracker microVM lifecycle management
- Hard cost caps (maxTokens, maxIterations, timeoutSeconds)
- Session management (idle timeout, max lifetime)
- Tag-based cost allocation
- Auto-instrumented observability

Cost limits are loaded from budget_config.json.

Usage:
    python deploy/agentcore/setup_harness.py --region us-east-1
"""

import argparse
import json
import logging
from pathlib import Path

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_budget_config() -> dict:
    """Load budget configuration."""
    config_path = Path(__file__).parent / "budget_config.json"
    with open(config_path) as f:
        return json.load(f)


def load_gateway_config() -> dict:
    """Load gateway config for Gateway URL."""
    config_path = Path(__file__).parent / "gateway_config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(description="Deploy AgentCore Harness")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()

    budget_config = load_budget_config()
    gateway_config = load_gateway_config()
    defaults = budget_config["global_defaults"]
    role_limits = budget_config["role_limits"]

    print("\n" + "=" * 60)
    print("  AgentCore Harness Setup — Cost-Controlled Deployment")
    print("=" * 60)
    print(f"  Region: {args.region}")
    print(f"  Gateway: {gateway_config.get('gateway_url', 'Not configured')}")
    print()

    # Display the per-role limits being configured
    print("  Per-Role Limits (from budget_config.json):")
    print("  " + "─" * 56)
    print(f"  {'Role':<25} {'maxTokens':<12} {'maxIter':<10} {'Daily Limit':<12}")
    print("  " + "─" * 56)
    for role, limits in role_limits.items():
        print(
            f"  {role:<25} "
            f"{limits.get('max_tokens_per_invocation', defaults['max_tokens_per_invocation']):<12} "
            f"{limits.get('max_iterations_per_invocation', defaults['max_iterations_per_invocation']):<10} "
            f"{limits.get('daily_token_limit', 'N/A'):<12}"
        )
    print()

    # In production: create harness via AgentCore API
    # agentcore.create_harness(
    #     name="MfgInsights-Harness",
    #     agentCode={"s3": {"bucket": "...", "key": "agent.zip"}},
    #     model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    #     gateway=gateway_config.get("gateway_id"),
    #     memory={"managed": True},
    #     limits={
    #         "maxTokens": defaults["max_tokens_per_invocation"],
    #         "maxIterations": defaults["max_iterations_per_invocation"],
    #         "timeoutSeconds": defaults["timeout_seconds"],
    #         "idleRuntimeSessionTimeout": defaults["idle_session_timeout_seconds"],
    #         "maxLifetime": defaults["max_session_lifetime_seconds"],
    #     },
    #     tags={
    #         "project": "manufacturing-insights",
    #         "cost-center": "operations-ai",
    #     },
    # )

    # Save harness config
    harness_config = {
        "region": args.region,
        "harness_name": "MfgInsights-Harness",
        "global_defaults": defaults,
        "role_limits": role_limits,
        "gateway_url": gateway_config.get("gateway_url", ""),
        "tags": {
            "project": "manufacturing-insights",
            "cost-center": "operations-ai",
        },
    }

    config_path = Path(__file__).parent / "harness_config.json"
    with open(config_path, "w") as f:
        json.dump(harness_config, f, indent=2)

    print("  Harness Configuration:")
    print(f"    Name:              MfgInsights-Harness")
    print(f"    Max Tokens:        {defaults['max_tokens_per_invocation']} (per invocation)")
    print(f"    Max Iterations:    {defaults['max_iterations_per_invocation']} (per invocation)")
    print(f"    Timeout:           {defaults['timeout_seconds']}s")
    print(f"    Idle Timeout:      {defaults['idle_session_timeout_seconds']}s")
    print(f"    Max Lifetime:      {defaults['max_session_lifetime_seconds']}s")
    print(f"    Config saved:      {config_path}")
    print()
    print("  NOTE: In production, run with AgentCore SDK:")
    print("    pip install bedrock-agentcore-starter-toolkit")
    print("    # Then use HarnessClient.create_harness()")
    print()
    print(f"  Next: python deploy/agentcore/setup_budgets.py --region {args.region}")
    print()


if __name__ == "__main__":
    main()
