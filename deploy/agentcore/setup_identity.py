# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Setup AgentCore Identity — Cognito User Pool with manufacturing personas.

Creates:
1. Cognito User Pool with custom attributes (role, line_scope, plant_scope, equipment_scope)
2. User Pool Client (for OAuth flows)
3. Three demo users: Sarah (plant_manager), Raj (line_supervisor), Priya (maintenance_technician)
4. Three groups matching the roles

Usage:
    python deploy/agentcore/setup_identity.py --region us-west-2
"""

import argparse
import json
import logging
import time
from pathlib import Path

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Demo users matching the blog narrative
# Passwords are read from environment variables. Users must set these before running.
# Example:  export DEMO_PASSWORD_SARAH="<your-secure-password>"
#           export DEMO_PASSWORD_RAJ="<your-secure-password>"
#           export DEMO_PASSWORD_PRIYA="<your-secure-password>"
import os

_DEFAULT_PASSWORD_MSG = (
    "Set environment variables DEMO_PASSWORD_SARAH, DEMO_PASSWORD_RAJ, "
    "DEMO_PASSWORD_PRIYA before running this script."
)

DEMO_USERS = [
    {
        "username": "sarah.chen",
        "email": "sarah.chen@example.com",
        "password": os.environ.get("DEMO_PASSWORD_SARAH", ""),
        "role": "plant_manager",
        "plant_scope": "Plant 1,Plant 2,Plant 3",
        "line_scope": ",".join(f"Line {i}" for i in range(1, 13)),
        "equipment_scope": "",  # Full access
        "group": "plant_managers",
    },
    {
        "username": "raj.patel",
        "email": "raj.patel@example.com",
        "password": os.environ.get("DEMO_PASSWORD_RAJ", ""),
        "role": "line_supervisor",
        "plant_scope": "Plant 2",
        "line_scope": "Line 7",
        "equipment_scope": "Machine 71,Machine 72,Machine 73,Machine 74,Machine 75",
        "group": "line_supervisors",
    },
    {
        "username": "priya.nair",
        "email": "priya.nair@example.com",
        "password": os.environ.get("DEMO_PASSWORD_PRIYA", ""),
        "role": "maintenance_technician",
        "plant_scope": "Plant 1",
        "line_scope": "Line 4",
        "equipment_scope": "Machine 41,Machine 42,Machine 43,Machine 44,Machine 45",
        "group": "maintenance_technicians",
    },
]

GROUPS = ["plant_managers", "line_supervisors", "maintenance_technicians"]


def create_user_pool(cognito_client, pool_name: str) -> dict:
    """Create Cognito User Pool with custom attributes for manufacturing roles."""
    logger.info(f"Creating User Pool: {pool_name}")

    response = cognito_client.create_user_pool(
        PoolName=pool_name,
        AutoVerifiedAttributes=["email"],
        UsernameAttributes=["email"],
        Schema=[
            {"Name": "email", "Required": True, "Mutable": True,
             "AttributeDataType": "String"},
            {"Name": "role", "Required": False, "Mutable": True,
             "AttributeDataType": "String",
             "StringAttributeConstraints": {"MinLength": "1", "MaxLength": "50"}},
            {"Name": "line_scope", "Required": False, "Mutable": True,
             "AttributeDataType": "String",
             "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "500"}},
            {"Name": "plant_scope", "Required": False, "Mutable": True,
             "AttributeDataType": "String",
             "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "200"}},
            {"Name": "equipment_scope", "Required": False, "Mutable": True,
             "AttributeDataType": "String",
             "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "500"}},
        ],
        Policies={
            "PasswordPolicy": {
                "MinimumLength": 8,
                "RequireUppercase": True,
                "RequireLowercase": True,
                "RequireNumbers": True,
                "RequireSymbols": True,
            }
        },
        AdminCreateUserConfig={"AllowAdminCreateUserWithoutVerification": True},
    )

    pool_id = response["UserPool"]["Id"]
    pool_arn = response["UserPool"]["Arn"]
    logger.info(f"  User Pool created: {pool_id}")
    return {"pool_id": pool_id, "pool_arn": pool_arn}


def create_user_pool_client(cognito_client, pool_id: str, client_name: str) -> dict:
    """Create User Pool Client with client credentials for machine-to-machine auth."""
    logger.info(f"Creating User Pool Client: {client_name}")

    # Create resource server for client_credentials flow
    try:
        cognito_client.create_resource_server(
            UserPoolId=pool_id,
            Identifier="manufacturing-insights",
            Name="Manufacturing Insights API",
            Scopes=[
                {"ScopeName": "read", "ScopeDescription": "Read manufacturing data"},
                {"ScopeName": "write", "ScopeDescription": "Write manufacturing data"},
            ],
        )
    except cognito_client.exceptions.InvalidParameterException:
        logger.info("  Resource server already exists, skipping")

    # Create domain for OAuth endpoints
    try:
        domain_prefix = f"mfg-insights-{int(time.time()) % 100000}"
        cognito_client.create_user_pool_domain(
            Domain=domain_prefix,
            UserPoolId=pool_id,
        )
        logger.info(f"  Domain created: {domain_prefix}")
    except Exception as e:
        logger.info(f"  Domain creation skipped: {e}")
        domain_prefix = None

    # Create client
    response = cognito_client.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName=client_name,
        GenerateSecret=True,
        ExplicitAuthFlows=[
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
            "ALLOW_ADMIN_USER_PASSWORD_AUTH",
        ],
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthScopes=["manufacturing-insights/read"],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
    )

    client_id = response["UserPoolClient"]["ClientId"]
    client_secret = response["UserPoolClient"].get("ClientSecret", "")
    logger.info(f"  Client created: {client_id}")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "domain_prefix": domain_prefix,
    }


def create_groups(cognito_client, pool_id: str) -> None:
    """Create user groups for each manufacturing role."""
    for group in GROUPS:
        try:
            cognito_client.create_group(
                GroupName=group,
                UserPoolId=pool_id,
                Description=f"Manufacturing {group.replace('_', ' ').title()}",
            )
            logger.info(f"  Group created: {group}")
        except cognito_client.exceptions.GroupExistsException:
            logger.info(f"  Group exists: {group}")


def create_users(cognito_client, pool_id: str) -> None:
    """Create demo users with custom attributes and group assignments."""
    for user in DEMO_USERS:
        username = user["username"]
        try:
            cognito_client.admin_create_user(
                UserPoolId=pool_id,
                Username=username,
                UserAttributes=[
                    {"Name": "email", "Value": user["email"]},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "custom:role", "Value": user["role"]},
                    {"Name": "custom:line_scope", "Value": user["line_scope"]},
                    {"Name": "custom:plant_scope", "Value": user["plant_scope"]},
                    {"Name": "custom:equipment_scope", "Value": user["equipment_scope"]},
                ],
                TemporaryPassword=user["password"],
                MessageAction="SUPPRESS",
            )
            # Set permanent password
            cognito_client.admin_set_user_password(
                UserPoolId=pool_id,
                Username=username,
                Password=user["password"],
                Permanent=True,
            )
            # Add to group
            cognito_client.admin_add_user_to_group(
                UserPoolId=pool_id,
                Username=username,
                GroupName=user["group"],
            )
            logger.info(f"  User created: {username} (role={user['role']}, group={user['group']})")
        except cognito_client.exceptions.UsernameExistsException:
            logger.info(f"  User exists: {username}")


def main():
    parser = argparse.ArgumentParser(description="Setup AgentCore Identity (Cognito)")
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    parser.add_argument("--pool-name", default="ManufacturingInsightsPool")
    args = parser.parse_args()

    # Validate that passwords are provided via environment variables
    missing = [u["username"] for u in DEMO_USERS if not u["password"]]
    if missing:
        print(f"\nERROR: Passwords not set for: {', '.join(missing)}")
        print(_DEFAULT_PASSWORD_MSG)
        print("\nPasswords must meet Cognito policy: 8+ chars, upper, lower, number, symbol.")
        raise SystemExit(1)

    session = boto3.Session(region_name=args.region)
    cognito = session.client("cognito-idp")

    print("\n" + "=" * 60)
    print("  AgentCore Identity Setup — Cognito User Pool")
    print("=" * 60 + "\n")

    # Create User Pool
    pool_info = create_user_pool(cognito, args.pool_name)

    # Create Client
    client_info = create_user_pool_client(cognito, pool_info["pool_id"], "ManufacturingInsightsClient")

    # Create Groups
    create_groups(cognito, pool_info["pool_id"])

    # Create Users
    create_users(cognito, pool_info["pool_id"])

    # Save config
    config = {
        "region": args.region,
        "user_pool_id": pool_info["pool_id"],
        "user_pool_arn": pool_info["pool_arn"],
        "client_id": client_info["client_id"],
        "client_secret": client_info["client_secret"],
        "domain_prefix": client_info["domain_prefix"],
        "users": {u["username"]: {"email": u["email"], "role": u["role"]} for u in DEMO_USERS},
    }

    config_path = Path(__file__).parent / "identity_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n{'=' * 60}")
    print("  Identity Setup Complete!")
    print(f"{'=' * 60}")
    print(f"  User Pool ID:  {pool_info['pool_id']}")
    print(f"  Client ID:     {client_info['client_id']}")
    print(f"  Users created: {', '.join(u['username'] for u in DEMO_USERS)}")
    print(f"  Config saved:  {config_path}")
    print(f"\n  Next: python deploy/agentcore/setup_gateway.py --region {args.region}\n")


if __name__ == "__main__":
    main()
