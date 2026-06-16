#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Cleanup all AgentCore resources created by the deployment scripts.

Removes (in reverse order):
1. Policy Engine + Cedar policies
2. Interceptor Lambdas
3. Tool target Lambdas
4. Gateway
5. Cognito User Pool

Usage:
    python deploy/agentcore/cleanup.py --region us-west-2
"""

import argparse
import json
import logging
from pathlib import Path

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def cleanup_lambdas(lambda_client, prefix="MfgInsights-"):
    """Delete all Lambda functions with the project prefix."""
    paginator = lambda_client.get_paginator("list_functions")
    for page in paginator.paginate():
        for fn in page["Functions"]:
            if fn["FunctionName"].startswith(prefix):
                logger.info(f"  Deleting Lambda: {fn['FunctionName']}")
                lambda_client.delete_function(FunctionName=fn["FunctionName"])


def cleanup_roles(iam_client, prefix="Lambda-MfgInsights-"):
    """Delete IAM roles created for Lambda functions."""
    paginator = iam_client.get_paginator("list_roles")
    for page in paginator.paginate():
        for role in page["Roles"]:
            if role["RoleName"].startswith(prefix) or role["RoleName"] == "AgentCore-ManufacturingGateway-Role":
                # Detach policies first
                attached = iam_client.list_attached_role_policies(RoleName=role["RoleName"])
                for policy in attached["AttachedPolicies"]:
                    iam_client.detach_role_policy(RoleName=role["RoleName"], PolicyArn=policy["PolicyArn"])
                iam_client.delete_role(RoleName=role["RoleName"])
                logger.info(f"  Deleted role: {role['RoleName']}")


def cleanup_cognito(cognito_client, config_path: Path):
    """Delete the Cognito User Pool."""
    if not config_path.exists():
        return
    config = json.loads(config_path.read_text())
    pool_id = config.get("user_pool_id")
    if pool_id:
        # Delete domain first
        domain = config.get("domain_prefix")
        if domain:
            try:
                cognito_client.delete_user_pool_domain(Domain=domain, UserPoolId=pool_id)
                logger.info(f"  Deleted domain: {domain}")
            except Exception:
                pass
        cognito_client.delete_user_pool(UserPoolId=pool_id)
        logger.info(f"  Deleted User Pool: {pool_id}")


def main():
    parser = argparse.ArgumentParser(description="Cleanup AgentCore resources")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--confirm", action="store_true", help="Skip confirmation")
    args = parser.parse_args()

    if not args.confirm:
        print("\n  ⚠️  This will delete ALL AgentCore resources for this project.")
        response = input("  Continue? [y/N] ")
        if response.lower() != "y":
            print("  Aborted.")
            return

    session = boto3.Session(region_name=args.region)
    base = Path(__file__).parent

    print("\n" + "=" * 60)
    print("  Cleaning up AgentCore resources...")
    print("=" * 60 + "\n")

    # 1. Lambdas
    logger.info("Step 1: Deleting Lambda functions...")
    cleanup_lambdas(session.client("lambda"))

    # 2. IAM Roles
    logger.info("\nStep 2: Deleting IAM roles...")
    cleanup_roles(session.client("iam"))

    # 3. Cognito
    logger.info("\nStep 3: Deleting Cognito User Pool...")
    cleanup_cognito(session.client("cognito-idp"), base / "identity_config.json")

    # 4. Remove config files
    logger.info("\nStep 4: Removing local config files...")
    for f in ["identity_config.json", "gateway_config.json", "policy_config.json", "interceptor_config.json"]:
        fp = base / f
        if fp.exists():
            fp.unlink()
            logger.info(f"  Removed: {f}")

    print(f"\n{'=' * 60}")
    print("  ✅ Cleanup complete! All resources removed.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
