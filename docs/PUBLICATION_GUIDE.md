# Publication Guide — Steps to Publish on aws-samples

## Status: Git Repo Ready ✅ | Awaiting Security Review

---

## Step 1: OpenSourcerer Self-Certification

Go to: https://console.harmony.a2z.com/open-sourcerer/aws-sample-code

### Form Answers (copy-paste these):

**Repository Name:**
```
sample-autonomous-business-insights-with-ai-agent-and-mcp-servers
```

**Description:**
```
This sample demonstrates how to build an autonomous business insights agent using Amazon Bedrock AgentCore, Strands Agents SDK, and MCP servers to query across multiple enterprise data sources with role-based access control and persistent memory.
```

**License:**
```
MIT-0
```

**Content Type:**
```
Blog post code sample
```

**Blog Title:**
```
Generate Autonomous Business Insights with AI Agent and MCP Servers
```

**Blog URL (draft):**
```
https://aws.amazon.com/blogs/machine-learning/generate-autonomous-business-insights-with-ai-agent-and-mcp-servers/
```

**AWS Services Used:**
```
Amazon Bedrock, Amazon Bedrock AgentCore, Amazon Aurora PostgreSQL Serverless v2, Amazon Timestream, Amazon Redshift Serverless, Amazon OpenSearch Serverless, Amazon S3, AWS IoT Core, Amazon Cognito
```

**Does this code replicate significant functionality of Amazon products?**
```
No. It demonstrates the use of AWS services via their public APIs and SDKs.
```

**Does this code include Amazon Confidential Information?**
```
No. All code uses publicly available AWS APIs, the open-source Strands Agents SDK, and the open MCP standard.
```

**Third-party dependencies:**
```
All dependencies use permissive licenses (Apache-2.0, MIT, BSD-3-Clause) compatible with MIT-0. See THIRD-PARTY-LICENSES file.
- strands-agents (Apache-2.0)
- mcp (MIT)
- boto3 (Apache-2.0)
- pydantic (MIT)
- python-dotenv (BSD-3-Clause)
- pydantic-settings (MIT)
- streamlit (Apache-2.0)
```

**Has this been discussed with the product team?**
```
Yes — this demonstrates Amazon Bedrock AgentCore capabilities with the Strands Agents SDK, both publicly available AWS services/tools.
```

---

## Step 2: Create Repository

After self-certification creates a SIM ticket:

Go to: https://console.harmony.a2z.com/open-sourcerer/create-repo

- **SIM Ticket:** (paste the SIM ID from step 1)
- **Repository Name:** `sample-autonomous-business-insights-with-ai-agent-and-mcp-servers`
- **Template:** MIT-0
- **GitHub Team:** (your team — e.g., `us-aisasp-team` or ask your manager)

---

## Step 3: Run Automated Security Helper (ash)

Requires Docker + mwinit:

```bash
# 1. Ensure Docker is running
docker info

# 2. Clone ash (if not already)
git clone https://github.com/awslabs/automated-security-helper.git --recurse-submodules

# 3. Run scan against our code
cd automated-security-helper
./ash --source-dir /path/to/sample-autonomous-business-insights-with-ai-agent-and-mcp-servers --output-dir ./ash-output

# 4. Review results
cat ash-output/ash_report.txt
```

Expected: No critical findings. Our code:
- Has no hardcoded credentials
- Uses parameterized queries (no SQL injection)
- Has input validation on all tools
- Uses environment variables for all configuration
- Has encryption at rest on all storage (CloudFormation)

---

## Step 4: Submit Content Security Review (CSR)

Go to: https://river.amazon.com/?org=SAESO

**Ticket Type:** Content Security Review

**C/T/I:** SA Content Security Review / (your segment) / (your team)

### Description (copy-paste):

```
Content Security Review Request — Blog Code Sample

Blog Title: Generate Autonomous Business Insights with AI Agent and MCP Servers

Repository: sample-autonomous-business-insights-with-ai-agent-and-mcp-servers (aws-samples)

Summary:
Sample code for an AWS Machine Learning blog demonstrating how to build an
autonomous business insights agent using Amazon Bedrock AgentCore, Strands
Agents SDK, and MCP servers. The code queries multiple AWS data services
(Aurora, Timestream, Redshift, OpenSearch) through pre-built and custom MCP
server connectors.

AWS Services Used:
- Amazon Bedrock (Claude Sonnet model inference)
- Amazon Bedrock AgentCore (Runtime, Gateway, Identity, Policy, Memory)
- Amazon Aurora PostgreSQL Serverless v2 (equipment/maintenance data)
- Amazon Timestream (IoT sensor time-series)
- Amazon Redshift Serverless (supply chain, OEE analytics)
- Amazon OpenSearch Serverless (quality metrics, semantic search)
- Amazon S3 (data lake, configuration)
- AWS IoT Core (sensor data ingestion)
- Amazon Cognito (authentication)

Security Controls:
- All credentials via environment variables (no hardcoded secrets)
- IAM least-privilege roles in CloudFormation
- S3 buckets: encryption at rest, public access blocked, SSL-only policy
- Aurora: storage encryption enabled
- Input validation on all MCP tool functions
- Cedar-style policy enforcement blocks unauthorized data access
- No eval(), exec(), os.system(), or subprocess.call(shell=True) usage

Third-Party Dependencies:
All use permissive licenses (Apache-2.0, MIT, BSD-3-Clause). See THIRD-PARTY-LICENSES.

Automated Security Scan:
[Attach ash results here after running]

Open Source Approval:
SIM Ticket: [paste SIM ID from Step 1]
```

---

## Step 5: Push Code

After CSR approval and repo creation:

```bash
cd /path/to/sample-autonomous-business-insights-with-ai-agent-and-mcp-servers

# Add the remote (repo URL from OpenSourcerer)
git remote add origin git@github.com:aws-samples/sample-autonomous-business-insights-with-ai-agent-and-mcp-servers.git

# Push (keep PRIVATE until blog publishes)
git push -u origin main
```

---

## Step 6: Make Public

When the blog post is published:
1. Go to the repo settings on GitHub
2. Change visibility from Private → Public
3. Verify the blog link in README works

---

## Checklist Summary

- [ ] OpenSourcerer self-certification submitted
- [ ] SIM ticket received
- [ ] ash security scan run (no critical findings)
- [ ] CSR ticket submitted at River
- [ ] CSR approved by guardian
- [ ] Repository created via OpenSourcerer
- [ ] Code pushed to aws-samples (private)
- [ ] Blog published
- [ ] Repository made public
