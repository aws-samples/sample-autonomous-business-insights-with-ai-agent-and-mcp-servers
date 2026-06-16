#!/usr/bin/env python3
"""Debug JWT token to fix Gateway auth."""
import boto3
import json
import base64

REGION = "us-east-1"
POOL_ID = "us-east-1_wBnf60sfQ"
CLIENT_ID = "5fu4vkccn1ndlr62vp79nnb5po"

cognito = boto3.client("cognito-idp", region_name=REGION)
resp = cognito.admin_initiate_auth(
    UserPoolId=POOL_ID, ClientId=CLIENT_ID,
    AuthFlow="ADMIN_USER_PASSWORD_AUTH",
    AuthParameters={"USERNAME": "raj.patel", "PASSWORD": "RajPatel!2026"},
)

# Decode ID token
id_token = resp["AuthenticationResult"]["IdToken"]
payload = id_token.split(".")[1]
padding = 4 - len(payload) % 4
if padding != 4:
    payload += "=" * padding
claims = json.loads(base64.urlsafe_b64decode(payload))

print("ID Token claims:")
for k, v in claims.items():
    if not k.startswith("cognito:"):
        print(f"  {k}: {v}")

print("\n  custom claims:")
for k, v in claims.items():
    if "custom:" in k or "cognito:" in k:
        print(f"  {k}: {v}")

# Access token
access_token = resp["AuthenticationResult"]["AccessToken"]
payload2 = access_token.split(".")[1]
padding2 = 4 - len(payload2) % 4
if padding2 != 4:
    payload2 += "=" * padding2
access_claims = json.loads(base64.urlsafe_b64decode(payload2))

print("\nAccess Token claims:")
for k, v in access_claims.items():
    print(f"  {k}: {v}")

print(f"\nGateway allowedAudience: [{CLIENT_ID}]")
print(f"ID token aud: {claims.get('aud')}")
print(f"Access token client_id: {access_claims.get('client_id')}")
print(f"\nRECOMMENDATION:")
print(f"  Gateway should use allowedClients=['{CLIENT_ID}'] for access tokens")
print(f"  OR switch to ID token with aud matching the client_id")
