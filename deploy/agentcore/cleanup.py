# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Cleanup ALL AgentCore resources created by the deployment scripts.

Removes (in reverse dependency order):
1. Cedar policies + Policy Engine (must detach from Gateway first)
2. Interceptor Lambdas + Tool target Lambdas
3. AgentCore Gateway
4. Cognito User Pool + Client
5. IAM roles created for Lambda functions and Gateway
6. Local config files

Usage:
    python deploy/agentcore/cleanup.py --region us-east-1
    python deploy/agentcore/cleanup.py --region us-east-1 --confirm  # Skip prompt
"""

import argparse
import json
import logging
import time
from pathlib import Path

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_PREFIX = "MfgInsights"


def cleanup_policy_engine(agentcore_client, region: str):
    """Delete Policy Engine and all Cedar policies attached to it."""
    logger.info("Listing Policy Engines...")
    try:
        response = agentcore_client.list_policy_engines()
        engines = response.get("policyEngines", response.get("items", []))
    except Exception as e:
        logger.warning(f"  Cannot list policy engines: {e}")
        return

    for engine in engines:
        if PROJECT_PREFIX in engine.get("name", ""):
            pe_id = engine["policyEngineId"]
            logger.info(f"  Found Policy Engine: {engine['name']} ({pe_id})")

            # Delete all policies in the engine
            try:
                policies_resp = agentcore_client.list_policies(policyEngineId=pe_id)
                policies = policies_resp.get("policies", policies_resp.get("items", []))
                for policy in policies:
                    policy_id = policy.get("policyId", policy.get("id", ""))
                    policy_name = policy.get("name", policy_id)
                    try:
                        agentcore_client.delete_policy(
                            policyEngineId=pe_id, policyId=policy_id
                        )
                        logger.info(f"    Deleted Cedar policy: {policy_name}")
                    except Exception as e:
                        logger.warning(f"    Failed to delete policy {policy_name}: {e}")
            except Exception as e:
                logger.warning(f"  Cannot list policies for {pe_id}: {e}")

            # Delete the Policy Engine itself
            try:
                agentcore_client.delete_policy_engine(policyEngineId=pe_id)
                logger.info(f"  Deleted Policy Engine: {engine['name']}")
            except Exception as e:
                logger.warning(f"  Failed to delete Policy Engine {pe_id}: {e}")


def cleanup_gateway(agentcore_client, region: str):
    """Delete AgentCore Gateway(s) matching the project prefix."""
    logger.info("Listing Gateways...")
    try:
        response = agentcore_client.list_gateways()
        gateways = response.get("gateways", response.get("items", []))
    except Exception as e:
        logger.warning(f"  Cannot list gateways: {e}")
        return

    for gw in gateways:
        if PROJECT_PREFIX in gw.get("name", ""):
            gw_id = gw["gatewayId"]
            logger.info(f"  Found Gateway: {gw['name']} ({gw_id})")

            # Delete all targets first
            try:
                targets_resp = agentcore_client.list_gateway_targets(gatewayIdentifier=gw_id)
                targets = targets_resp.get("targets", targets_resp.get("items", []))
                for target in targets:
                    target_id = target.get("targetId", target.get("id", ""))
                    target_name = target.get("name", target_id)
                    try:
                        agentcore_client.delete_gateway_target(
                            gatewayIdentifier=gw_id, targetId=target_id
                        )
                        logger.info(f"    Deleted target: {target_name}")
                    except Exception as e:
                        logger.warning(f"    Failed to delete target {target_name}: {e}")
            except Exception as e:
                logger.warning(f"  Cannot list targets for {gw_id}: {e}")

            # Wait for targets to be removed
            time.sleep(5)

            # Delete the Gateway
            try:
                agentcore_client.delete_gateway(gatewayIdentifier=gw_id)
                logger.info(f"  Deleted Gateway: {gw['name']} ({gw_id})")
                logger.info("  Waiting for Gateway deletion to propagate...")
                time.sleep(10)
            except Exception as e:
                logger.warning(f"  Failed to delete Gateway {gw_id}: {e}")


def cleanup_lambdas(lambda_client, prefix="MfgInsights-"):
    """Delete all Lambda functions with the project prefix."""
    logger.info("Deleting Lambda functions...")
    paginator = lambda_client.get_paginator("list_functions")
    deleted = 0
    for page in paginator.paginate():
        for fn in page["Functions"]:
            if fn["FunctionName"].startswith(prefix):
                logger.info(f"  Deleting Lambda: {fn['FunctionName']}")
                lambda_client.delete_function(FunctionName=fn["FunctionName"])
                deleted += 1
    if deleted == 0:
        logger.info("  No Lambda functions found with prefix '%s'", prefix)
    else:
        logger.info(f"  Deleted {deleted} Lambda functions")


def cleanup_roles(iam_client):
    """Delete IAM roles created for Lambda functions and Gateway."""
    logger.info("Deleting IAM roles...")
    prefixes = ["Lambda-MfgInsights-", "AgentCore-Manufacturing"]
    paginator = iam_client.get_paginator("list_roles")
    deleted = 0
    for page in paginator.paginate():
        for role in page["Roles"]:
            role_name = role["RoleName"]
            if any(role_name.startswith(p) for p in prefixes):
                try:
                    # Detach managed policies
                    attached = iam_client.list_attached_role_policies(RoleName=role_name)
                    for policy in attached["AttachedPolicies"]:
                        iam_client.detach_role_policy(
                            RoleName=role_name, PolicyArn=policy["PolicyArn"]
                        )

                    # Delete inline policies
                    inline = iam_client.list_role_policies(RoleName=role_name)
                    for policy_name in inline["PolicyNames"]:
                        iam_client.delete_role_policy(
                            RoleName=role_name, PolicyName=policy_name
                        )

                    iam_client.delete_role(RoleName=role_name)
                    logger.info(f"  Deleted role: {role_name}")
                    deleted += 1
                except Exception as e:
                    logger.warning(f"  Failed to delete role {role_name}: {e}")
    if deleted == 0:
        logger.info("  No matching IAM roles found")


def cleanup_cognito(cognito_client, region: str):
    """Delete Cognito User Pool(s) matching the project prefix."""
    logger.info("Deleting Cognito User Pool...")
    try:
        pools = cognito_client.list_user_pools(MaxResults=60)
        for pool in pools["UserPools"]:
            if PROJECT_PREFIX in pool["Name"] or "MfgInsights" in pool["Name"]:
                pool_id = pool["Id"]
                # Delete domain if exists
                try:
                    desc = cognito_client.describe_user_pool(UserPoolId=pool_id)
                    domain = desc["UserPool"].get("Domain")
                    if domain:
                        cognito_client.delete_user_pool_domain(
                            Domain=domain, UserPoolId=pool_id
                        )
                        logger.info(f"  Deleted domain: {domain}")
                except Exception:
                    pass

                cognito_client.delete_user_pool(UserPoolId=pool_id)
                logger.info(f"  Deleted User Pool: {pool['Name']} ({pool_id})")
    except Exception as e:
        logger.warning(f"  Cognito cleanup failed: {e}")


def cleanup_config_files():
    """Remove local config files generated by deployment scripts."""
    logger.info("Removing local config files...")
    base = Path(__file__).parent
    config_files = [
        "identity_config.json",
        "gateway_config.json",
        "policy_config.json",
        "interceptor_config.json",
    ]
    for f in config_files:
        fp = base / f
        if fp.exists():
            fp.unlink()
            logger.info(f"  Removed: {f}")

    # Reset live_config.json to empty template
    live_config = base / "live_config.json"
    if live_config.exists():
        empty_config = {
            "_README": "This file is auto-generated by deploy_live.py. Do not edit manually.",
            "_INSTRUCTIONS": "Run: python deploy/agentcore/deploy_live.py to populate with your real resource IDs.",
            "region": "",
            "account": "",
            "gateway_id": "",
            "gateway_url": "",
            "policy_engine_id": "",
            "pool_id": "",
            "client_id": "",
        }
        with open(live_config, "w") as f:
            json.dump(empty_config, f, indent=2)
        logger.info("  Reset: live_config.json")


def cleanup_cloudwatch(cloudwatch_client, logs_client, region: str):
    """Delete CloudWatch dashboards, alarms, and log groups created by the project."""
    logger.info("Deleting CloudWatch resources...")

    # Delete dashboards
    dashboard_name = "ManufacturingInsights-AgentCore"
    try:
        cloudwatch_client.delete_dashboards(DashboardNames=[dashboard_name])
        logger.info(f"  Deleted dashboard: {dashboard_name}")
    except Exception as e:
        logger.info(f"  No dashboard to delete: {dashboard_name}")

    # Delete alarms
    alarm_names = [
        "AgentCore-HighDenyRate",
        "AgentCore-HighLatency",
        "AgentCore-TokenBudget",
    ]
    try:
        cloudwatch_client.delete_alarms(AlarmNames=alarm_names)
        logger.info(f"  Deleted alarms: {alarm_names}")
    except Exception as e:
        logger.info(f"  No alarms to delete: {e}")

    # Delete log groups
    log_group_prefixes = [
        "/aws/agentcore/gateway/policy-decisions",
        "/aws/lambda/MfgInsights-",
    ]
    try:
        paginator = logs_client.get_paginator("describe_log_groups")
        for prefix in log_group_prefixes:
            for page in paginator.paginate(logGroupNamePrefix=prefix):
                for lg in page.get("logGroups", []):
                    logs_client.delete_log_group(logGroupName=lg["logGroupName"])
                    logger.info(f"  Deleted log group: {lg['logGroupName']}")
    except Exception as e:
        logger.info(f"  Log group cleanup: {e}")


def cleanup_memory_data(s3_client, region: str):
    """Delete memory data from S3 (user/team/org namespaces)."""
    logger.info("Cleaning memory bucket data...")

    # Find the memory bucket
    try:
        buckets = s3_client.list_buckets()["Buckets"]
        memory_buckets = [b["Name"] for b in buckets if "agentcore-memory" in b["Name"]]

        for bucket_name in memory_buckets:
            # List and delete all objects
            paginator = s3_client.get_paginator("list_objects_v2")
            deleted = 0
            for page in paginator.paginate(Bucket=bucket_name):
                objects = page.get("Contents", [])
                if objects:
                    s3_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={"Objects": [{"Key": obj["Key"]} for obj in objects]},
                    )
                    deleted += len(objects)
            if deleted > 0:
                logger.info(f"  Deleted {deleted} objects from {bucket_name}")
            else:
                logger.info(f"  Memory bucket {bucket_name} already empty")
    except Exception as e:
        logger.info(f"  Memory cleanup: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup ALL AgentCore resources for Manufacturing Insights"
    )
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument(
        "--confirm", action="store_true", help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--keep-cognito", action="store_true",
        help="Keep Cognito User Pool (useful if shared with other apps)"
    )
    args = parser.parse_args()

    if not args.confirm:
        print("\n" + "=" * 60)
        print("  ⚠️  FULL CLEANUP — This will delete ALL project resources:")
        print("=" * 60)
        print(f"  Region: {args.region}")
        print(f"  Resources to delete:")
        print(f"    • AgentCore Gateway (MfgInsights*)")
        print(f"    • Policy Engine + Cedar policies")
        print(f"    • Lambda tool targets + interceptors (MfgInsights-*)")
        print(f"    • IAM roles (Lambda-MfgInsights-*, AgentCore-Manufacturing*)")
        if not args.keep_cognito:
            print(f"    • Cognito User Pool (MfgInsights-*)")
        print(f"    • CloudWatch dashboard + alarms + log groups")
        print(f"    • Memory bucket data (user/team/org)")
        print(f"    • Local config files")
        print()
        response = input("  Type 'yes' to confirm deletion: ")
        if response.strip().lower() != "yes":
            print("  Aborted.")
            return

    session = boto3.Session(region_name=args.region)

    print("\n" + "=" * 60)
    print("  Cleaning up ALL AgentCore resources...")
    print("=" * 60 + "\n")

    # Step 1: Policy Engine (must be detached from Gateway before Gateway deletion)
    logger.info("Step 1: Deleting Policy Engine + Cedar policies...")
    try:
        agentcore = session.client("bedrock-agentcore-control")
        cleanup_policy_engine(agentcore, args.region)
    except Exception as e:
        logger.warning(f"  AgentCore client error (policy engine): {e}")

    # Step 2: Gateway targets + Gateway
    logger.info("\nStep 2: Deleting AgentCore Gateway...")
    try:
        agentcore = session.client("bedrock-agentcore-control")
        cleanup_gateway(agentcore, args.region)
    except Exception as e:
        logger.warning(f"  AgentCore client error (gateway): {e}")

    # Step 3: Lambda functions
    logger.info("\nStep 3: Deleting Lambda functions...")
    cleanup_lambdas(session.client("lambda"))

    # Step 4: IAM roles
    logger.info("\nStep 4: Deleting IAM roles...")
    cleanup_roles(session.client("iam"))

    # Step 5: Cognito
    if not args.keep_cognito:
        logger.info("\nStep 5: Deleting Cognito User Pool...")
        cleanup_cognito(session.client("cognito-idp"), args.region)
    else:
        logger.info("\nStep 5: Skipping Cognito (--keep-cognito)")

    # Step 6: Config files
    logger.info("\nStep 6: Removing local config files...")
    cleanup_config_files()

    # Step 7: CloudWatch (dashboards, alarms, log groups)
    logger.info("\nStep 7: Deleting CloudWatch resources...")
    cleanup_cloudwatch(
        session.client("cloudwatch"),
        session.client("logs"),
        args.region,
    )

    # Step 8: Memory bucket data
    logger.info("\nStep 8: Cleaning memory bucket data...")
    cleanup_memory_data(session.client("s3"), args.region)

    # Step 9: DynamoDB budget counters table
    logger.info("\nStep 9: Deleting DynamoDB budget table...")
    try:
        dynamodb = session.client("dynamodb")
        table_name = "MfgInsights-BudgetCounters"
        dynamodb.delete_table(TableName=table_name)
        logger.info(f"  Deleted table: {table_name}")
    except dynamodb.exceptions.ResourceNotFoundException:
        logger.info("  No budget table to delete")
    except Exception as e:
        logger.info(f"  Budget table cleanup: {e}")

    print(f"\n{'=' * 60}")
    print("  ✅ Full cleanup complete!")
    print(f"{'=' * 60}")
    print(f"\n  All AgentCore resources in {args.region} have been deleted.")
    print(f"  To also delete the data infrastructure stack:")
    print(f"    aws cloudformation delete-stack --stack-name manufacturing-insights-dev --region {args.region}")
    print()


if __name__ == "__main__":
    main()
