# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
"""Deploy budget infrastructure from budget_config.json.

Single command deploys all cost governance resources:
1. DynamoDB table for atomic token counters (if not exists via CFN)
2. Seed initial budget limits per role
3. Generate Cedar budget policy from thresholds
4. Create CloudWatch alarms for budget warnings

Admin workflow:
    1. Edit deploy/agentcore/budget_config.json
    2. Run: python deploy/agentcore/setup_budgets.py --region us-east-1
    3. All limits propagated everywhere

Usage:
    python deploy/agentcore/setup_budgets.py --region us-east-1
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_budget_config() -> dict:
    """Load budget configuration."""
    config_path = Path(__file__).parent / "budget_config.json"
    with open(config_path) as f:
        return json.load(f)


def ensure_dynamodb_table(dynamodb_client, table_name: str, region: str):
    """Create DynamoDB budget counters table if it doesn't exist."""
    try:
        dynamodb_client.describe_table(TableName=table_name)
        logger.info(f"  DynamoDB table exists: {table_name}")
    except dynamodb_client.exceptions.ResourceNotFoundException:
        logger.info(f"  Creating DynamoDB table: {table_name}")
        dynamodb_client.create_table(
            TableName=table_name,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "date", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "date", "KeyType": "RANGE"},
            ],
            Tags=[
                {"Key": "Project", "Value": "MfgInsights"},
                {"Key": "Purpose", "Value": "Budget token counters"},
            ],
        )
        # Wait for table to be active
        waiter = dynamodb_client.get_waiter("table_exists")
        waiter.wait(TableName=table_name)

        # Enable TTL
        dynamodb_client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                "Enabled": True,
                "AttributeName": "expires_at",
            },
        )
        logger.info(f"  Table created with TTL enabled: {table_name}")


def seed_budget_limits(dynamodb_resource, table_name: str, config: dict):
    """Seed the budget limits into DynamoDB for each role."""
    table = dynamodb_resource.Table(table_name)

    # Store limits as a reference record (date = "LIMITS")
    for role, limits in config["role_limits"].items():
        table.put_item(
            Item={
                "user_id": f"ROLE_LIMIT#{role}",
                "date": "LIMITS",
                "daily_token_limit": limits["daily_token_limit"],
                "monthly_cost_limit_usd": str(limits["monthly_cost_limit_usd"]),
                "max_tokens_per_invocation": limits["max_tokens_per_invocation"],
                "max_iterations_per_invocation": limits["max_iterations_per_invocation"],
                "expires_at": int(time.time()) + (365 * 86400),  # 1 year
            }
        )
    logger.info(f"  Seeded limits for {len(config['role_limits'])} roles")


def setup_budget_alarms(cloudwatch_client, config: dict, region: str):
    """Create CloudWatch alarms for budget warnings."""
    alerts = config.get("alerts", {})
    sns_topic = alerts.get("notify_sns_topic", "")

    # Alarm: High token usage (any user approaching daily limit)
    try:
        cloudwatch_client.put_metric_alarm(
            AlarmName="AgentCore-BudgetWarning",
            AlarmDescription="User approaching daily token budget limit",
            Namespace="AgentCore/Budget",
            MetricName="DailyTokenUsagePercent",
            Statistic="Maximum",
            Period=300,
            EvaluationPeriods=1,
            Threshold=alerts.get("warn_at_percent", 80),
            ComparisonOperator="GreaterThanThreshold",
            ActionsEnabled=bool(sns_topic),
            AlarmActions=[sns_topic] if sns_topic and "<ACCOUNT_ID>" not in sns_topic else [],
        )
        logger.info("  Created alarm: AgentCore-BudgetWarning")
    except Exception as e:
        logger.warning(f"  Alarm creation: {e}")


def main():
    parser = argparse.ArgumentParser(description="Deploy Budget Infrastructure")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()

    config = load_budget_config()
    table_name = config["dynamo_table"]["table_name"]

    session = boto3.Session(region_name=args.region)
    dynamodb_client = session.client("dynamodb")
    dynamodb_resource = session.resource("dynamodb")
    cloudwatch_client = session.client("cloudwatch")

    print("\n" + "=" * 60)
    print("  Budget Infrastructure Setup")
    print("=" * 60)
    print(f"  Region: {args.region}")
    print(f"  Table:  {table_name}")
    print(f"  Config: deploy/agentcore/budget_config.json")
    print()

    # Step 1: DynamoDB table
    logger.info("Step 1: Ensuring DynamoDB table exists...")
    ensure_dynamodb_table(dynamodb_client, table_name, args.region)

    # Step 2: Seed limits
    logger.info("\nStep 2: Seeding budget limits...")
    seed_budget_limits(dynamodb_resource, table_name, config)

    # Step 3: CloudWatch alarms
    logger.info("\nStep 3: Creating budget alarms...")
    setup_budget_alarms(cloudwatch_client, config, args.region)

    # Step 4: Display summary
    print(f"\n{'=' * 60}")
    print("  Budget Infrastructure Ready!")
    print(f"{'=' * 60}")
    print()
    print("  Configured Limits:")
    print(f"  {'Role':<25} {'Daily Tokens':<15} {'Monthly USD':<12}")
    print("  " + "─" * 52)
    for role, limits in config["role_limits"].items():
        print(
            f"  {role:<25} "
            f"{limits['daily_token_limit']:>10,}   "
            f"${limits['monthly_cost_limit_usd']:>8.2f}"
        )
    print()
    print("  Enforcement Mode:", config["enforcement"]["mode"])
    print("    80% → Warn  | 90% → Throttle  | 100% → Block")
    print()
    print("  Admin: Edit budget_config.json and re-run this script to update limits.")
    print()


if __name__ == "__main__":
    main()
