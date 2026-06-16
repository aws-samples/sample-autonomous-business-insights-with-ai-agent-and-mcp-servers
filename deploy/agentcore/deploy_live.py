#!/usr/bin/env python3
"""Deploy REAL AgentCore infrastructure for Manufacturing Insights."""

import boto3
import json
import time
from pathlib import Path

REGION = "us-east-1"
ACCOUNT = "338277320360"

def main():
    cognito = boto3.client("cognito-idp", region_name=REGION)
    agentcore = boto3.client("bedrock-agentcore-control", region_name=REGION)

    print("=" * 60)
    print("  DEPLOYING REAL AGENTCORE STACK")
    print("  Account:", ACCOUNT, "| Region:", REGION)
    print("=" * 60)

    config = {"region": REGION, "account": ACCOUNT}

    # ═══ STEP 1: Cognito User Pool ═══
    print("\n[Step 1] Creating Cognito User Pool...")
    try:
        pool_resp = cognito.create_user_pool(
            PoolName="MfgInsights-AgentCore",
            AutoVerifiedAttributes=["email"],
            Schema=[
                {"Name": "email", "Required": True, "Mutable": True, "AttributeDataType": "String"},
                {"Name": "role", "Required": False, "Mutable": True, "AttributeDataType": "String",
                 "StringAttributeConstraints": {"MinLength": "1", "MaxLength": "50"}},
                {"Name": "line_scope", "Required": False, "Mutable": True, "AttributeDataType": "String",
                 "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "500"}},
                {"Name": "plant_scope", "Required": False, "Mutable": True, "AttributeDataType": "String",
                 "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "200"}},
                {"Name": "equipment_scope", "Required": False, "Mutable": True, "AttributeDataType": "String",
                 "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "500"}},
            ],
            AdminCreateUserConfig={"AllowAdminCreateUserOnly": True},
        )
        pool_id = pool_resp["UserPool"]["Id"]
        pool_arn = pool_resp["UserPool"]["Arn"]
        print(f"  OK User Pool: {pool_id}")
    except Exception as e:
        print(f"  Pool error (may exist): {e}")
        pools = cognito.list_user_pools(MaxResults=20)
        pool_id = None
        for p in pools["UserPools"]:
            if "MfgInsights" in p["Name"]:
                pool_id = p["Id"]
                break
        if not pool_id:
            print("  FATAL: Cannot find or create pool")
            return
        pool_arn = f"arn:aws:cognito-idp:{REGION}:{ACCOUNT}:userpool/{pool_id}"
        print(f"  Using existing: {pool_id}")

    config["pool_id"] = pool_id
    config["pool_arn"] = pool_arn

    # Create users
    users = [
        ("sarah.chen", "SarahChen!2026", "sarah@example.com", "plant_manager",
         "Plant 1,Plant 2,Plant 3", ",".join(f"Line {i}" for i in range(1, 13)), ""),
        ("raj.patel", "RajPatel!2026", "raj@example.com", "line_supervisor",
         "Plant 2", "Line 7", "Machine 71,Machine 72,Machine 73,Machine 74,Machine 75"),
        ("priya.nair", "PriyaNair!2026", "priya@example.com", "maintenance_technician",
         "Plant 1", "Line 4", "Machine 41,Machine 42,Machine 43,Machine 44,Machine 45"),
    ]

    for username, pwd, email, role, plant, line, equip in users:
        try:
            cognito.admin_create_user(
                UserPoolId=pool_id, Username=username,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "custom:role", "Value": role},
                    {"Name": "custom:plant_scope", "Value": plant},
                    {"Name": "custom:line_scope", "Value": line},
                    {"Name": "custom:equipment_scope", "Value": equip},
                ],
                TemporaryPassword=pwd, MessageAction="SUPPRESS",
            )
            cognito.admin_set_user_password(
                UserPoolId=pool_id, Username=username, Password=pwd, Permanent=True
            )
            print(f"  OK User: {username} ({role})")
        except cognito.exceptions.UsernameExistsException:
            print(f"  EXISTS: {username}")
        except Exception as e:
            print(f"  ERR {username}: {e}")

    # Create client
    try:
        cr = cognito.create_user_pool_client(
            UserPoolId=pool_id, ClientName="MfgInsights-Agent",
            ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH",
                               "ALLOW_ADMIN_USER_PASSWORD_AUTH"],
        )
        config["client_id"] = cr["UserPoolClient"]["ClientId"]
        print(f"  OK Client: {config['client_id']}")
    except Exception as e:
        print(f"  Client error: {e}")
        config["client_id"] = "unknown"

    # ═══ STEP 2: Create AgentCore Gateway ═══
    print("\n[Step 2] Creating AgentCore Gateway...")
    try:
        gw_resp = agentcore.create_gateway(
            name="MfgInsights-Gateway",
            protocolType="MCP",
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration={
                "customJWTConfiguration": {
                    "issuer": f"https://cognito-idp.{REGION}.amazonaws.com/{pool_id}",
                    "audiences": [config["client_id"]],
                }
            },
        )
        config["gateway_id"] = gw_resp["gatewayId"]
        config["gateway_arn"] = gw_resp.get("gatewayArn", f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT}:gateway/{gw_resp['gatewayId']}")
        print(f"  OK Gateway: {config['gateway_id']}")
        print(f"  Waiting for READY status...")
        time.sleep(15)
    except Exception as e:
        print(f"  Gateway error: {e}")
        # Try to find existing
        gws = agentcore.list_gateways()
        for gw in gws.get("gateways", gws.get("items", [])):
            if "MfgInsights" in gw.get("name", ""):
                config["gateway_id"] = gw["gatewayId"]
                config["gateway_arn"] = gw.get("gatewayArn", "")
                print(f"  Using existing: {config['gateway_id']}")
                break

    # ═══ STEP 3: Create Policy Engine ═══
    print("\n[Step 3] Creating Policy Engine...")
    try:
        pe_resp = agentcore.create_policy_engine(
            name="MfgInsights-PolicyEngine",
            description="Cedar policies for manufacturing persona-based access control",
        )
        config["policy_engine_id"] = pe_resp["policyEngineId"]
        config["policy_engine_arn"] = pe_resp.get("policyEngineArn", "")
        print(f"  OK PolicyEngine: {config['policy_engine_id']}")
        time.sleep(5)
    except Exception as e:
        print(f"  PolicyEngine error: {e}")
        pes = agentcore.list_policy_engines()
        for pe in pes.get("policyEngines", pes.get("items", [])):
            if "MfgInsights" in pe.get("name", ""):
                config["policy_engine_id"] = pe["policyEngineId"]
                config["policy_engine_arn"] = pe.get("policyEngineArn", "")
                print(f"  Using existing: {config['policy_engine_id']}")
                break

    # ═══ STEP 4: Create Cedar Policies ═══
    print("\n[Step 4] Creating Cedar Policies...")
    gateway_arn = config.get("gateway_arn", "PLACEHOLDER")
    pe_id = config.get("policy_engine_id", "")

    policies = {
        "permit_all": f'permit(principal, action, resource == AgentCore::Gateway::"{gateway_arn}");',
        "forbid_line_scope": (
            f'forbid(principal is AgentCore::OAuthUser, '
            f'action in [AgentCore::Action::"EquipmentTarget___get_equipment_status", '
            f'AgentCore::Action::"IoTTarget___detect_anomaly", '
            f'AgentCore::Action::"AnalyticsTarget___get_oee_trends", '
            f'AgentCore::Action::"AnalyticsTarget___get_quality_metrics"], '
            f'resource == AgentCore::Gateway::"{gateway_arn}") '
            f'when {{ context.input has line && '
            f'principal.hasTag("custom:line_scope") && '
            f'!(principal.getTag("custom:line_scope") like ("*" + context.input.line + "*")) }};'
        ),
        "forbid_equipment_scope": (
            f'forbid(principal is AgentCore::OAuthUser, '
            f'action in [AgentCore::Action::"EquipmentTarget___get_maintenance_history", '
            f'AgentCore::Action::"IoTTarget___get_sensor_readings"], '
            f'resource == AgentCore::Gateway::"{gateway_arn}") '
            f'when {{ context.input has machine_id && '
            f'principal.hasTag("custom:role") && '
            f'principal.getTag("custom:role") == "maintenance_technician" && '
            f'principal.hasTag("custom:equipment_scope") && '
            f'!(principal.getTag("custom:equipment_scope") like ("*" + context.input.machine_id + "*")) }};'
        ),
    }

    for name, statement in policies.items():
        try:
            agentcore.create_policy(
                policyEngineId=pe_id,
                name=name,
                definition={"cedar": {"statement": statement}},
            )
            print(f"  OK Policy: {name}")
        except Exception as e:
            print(f"  Policy {name}: {e}")

    # ═══ SAVE CONFIG ═══
    output = Path(__file__).parent / "live_config.json"
    with open(output, "w") as f:
        json.dump(config, f, indent=2)

    print("\n" + "=" * 60)
    print("  DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print(f"  Cognito Pool:    {config.get('pool_id')}")
    print(f"  Gateway ID:      {config.get('gateway_id')}")
    print(f"  Policy Engine:   {config.get('policy_engine_id')}")
    print(f"  Config saved:    {output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
