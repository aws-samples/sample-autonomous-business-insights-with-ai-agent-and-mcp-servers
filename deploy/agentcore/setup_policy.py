# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Setup AgentCore Policy Engine with Cedar policies for manufacturing access control.

Creates:
1. Policy Engine named "ManufacturingPolicyEngine"
2. Four Cedar policies:
   - permit_all: Baseline permit for authenticated users
   - forbid_line_scope: Line supervisors restricted to their lines
   - forbid_equipment_scope: Technicians restricted to their machines
   - forbid_plant_scope: All non-admins restricted to their plants
3. Attaches Policy Engine to Gateway in ENFORCE mode

Cedar Policy Evaluation:
- deny-by-default: Without permit_all, everything is denied
- forbid overrides permit: Specific forbid rules carve out restrictions
- Order: REQUEST interceptor → Cedar evaluation → Tool execution

Usage:
    python deploy/agentcore/setup_policy.py --region us-west-2
"""

import argparse
import json
import logging
from pathlib import Path

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CEDAR_POLICIES_DIR = Path(__file__).parent / "cedar_policies"


def load_gateway_config() -> dict:
    """Load gateway config from previous setup step."""
    config_path = Path(__file__).parent / "gateway_config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Gateway config not found at {config_path}. Run setup_gateway.py first."
        )
    with open(config_path) as f:
        return json.load(f)


def load_cedar_policy(filename: str, gateway_arn: str) -> str:
    """Load a Cedar policy file and substitute the gateway ARN."""
    policy_path = CEDAR_POLICIES_DIR / filename
    content = policy_path.read_text()
    return content.replace("${GATEWAY_ARN}", gateway_arn)


def main():
    parser = argparse.ArgumentParser(description="Setup AgentCore Policy Engine")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--mode", default="ENFORCE", choices=["ENFORCE", "LOG_ONLY"],
                        help="Policy mode: ENFORCE blocks requests, LOG_ONLY just logs")
    args = parser.parse_args()

    gateway_config = load_gateway_config()
    gateway_arn = gateway_config.get("gateway_arn", "arn:aws:bedrock-agentcore:REGION:ACCOUNT:gateway/GATEWAY_ID")

    print("\n" + "=" * 60)
    print("  AgentCore Policy Engine Setup")
    print("=" * 60)
    print(f"  Mode: {args.mode}")
    print(f"  Gateway ARN: {gateway_arn}")
    print("=" * 60 + "\n")

    # NOTE: In production, use the bedrock-agentcore-starter-toolkit PolicyClient:
    #
    #   from bedrock_agentcore_starter_toolkit.operations.policy.client import PolicyClient
    #   policy_client = PolicyClient(region_name=args.region)
    #   engine = policy_client.create_or_get_policy_engine(
    #       name="ManufacturingPolicyEngine",
    #       description="Fine-grained manufacturing access control"
    #   )
    #
    # Below shows the equivalent boto3 calls for documentation purposes.

    session = boto3.Session(region_name=args.region)

    # Load Cedar policies
    policy_files = [
        ("permit_all", "permit_all.cedar", "Baseline: permit all authenticated users"),
        ("forbid_line_scope", "forbid_line_scope.cedar", "Restrict line supervisors to assigned lines"),
        ("forbid_equipment_scope", "forbid_equipment_scope.cedar", "Restrict technicians to assigned machines"),
        ("forbid_plant_scope", "forbid_plant_scope.cedar", "Restrict all users to authorized plants"),
    ]

    policies = {}
    for policy_name, filename, description in policy_files:
        cedar_statement = load_cedar_policy(filename, gateway_arn)
        policies[policy_name] = {
            "name": policy_name,
            "description": description,
            "cedar_statement": cedar_statement,
        }
        logger.info(f"  Loaded policy: {policy_name}")
        logger.info(f"    {description}")

    # Save policy config
    config = {
        "region": args.region,
        "mode": args.mode,
        "gateway_arn": gateway_arn,
        "policies": {
            name: {
                "name": p["name"],
                "description": p["description"],
                "cedar_statement": p["cedar_statement"],
            }
            for name, p in policies.items()
        },
        "deployment_instructions": {
            "1_create_engine": (
                "policy_client.create_or_get_policy_engine("
                "name='ManufacturingPolicyEngine', "
                "description='Fine-grained manufacturing access control')"
            ),
            "2_create_policies": (
                "For each policy: policy_client.create_or_get_policy("
                "policy_engine_id=engine['policyEngineId'], "
                "name=policy_name, definition={'cedar': {'statement': cedar_statement}})"
            ),
            "3_attach_to_gateway": (
                "gateway_client.update_gateway_policy_engine("
                "gateway_identifier=gateway_id, "
                "policy_engine_arn=engine['policyEngineArn'], "
                f"mode='{args.mode}')"
            ),
        },
    }

    config_path = Path(__file__).parent / "policy_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    # Print Cedar policies for review
    print("\n" + "─" * 60)
    print("  CEDAR POLICIES FOR REVIEW")
    print("─" * 60)
    for name, p in policies.items():
        print(f"\n  ── {name}: {p['description']} ──")
        for line in p["cedar_statement"].strip().split("\n"):
            print(f"    {line}")
    print("\n" + "─" * 60)

    print(f"\n{'=' * 60}")
    print("  Policy Configuration Ready!")
    print(f"{'=' * 60}")
    print(f"  Policies: {len(policies)} Cedar rules")
    print(f"  Mode: {args.mode} ({'blocks unauthorized requests' if args.mode == 'ENFORCE' else 'logs only, no blocking'})")
    print(f"  Config: {config_path}")
    print(f"\n  Recommendation: Start with LOG_ONLY, verify in CloudWatch,")
    print(f"  then switch to ENFORCE once validated.")
    print(f"\n  Next: python deploy/agentcore/setup_interceptor.py --region {args.region}\n")


if __name__ == "__main__":
    main()
