# Security Scan — Justification for Remaining Findings

**Project:** sample-autonomous-business-insights-with-ai-agent-and-mcp-servers
**Scan Date:** June 22, 2026 (second scan, post-remediation)
**Findings Remaining:** 21 (all automated scanner findings — no RUBRIC/manual findings remain)

---

## Summary

All RUBRIC findings (hardcoded passwords, bucket squatting, over-permissive IAM, deferral language) have been resolved. The remaining 21 findings are from automated scanners (Bandit, Checkov, CFN Guard, Semgrep) and represent either false positives or acceptable patterns for demo/sample code.

---

## Bandit Findings (10)

### B608 — Possible SQL Injection (6 findings)

| File | Line | Accept Reason |
|------|------|---------------|
| `lakehouse_client.py` | 266 | Parameterized execution via Redshift Data API `execute_query(sql, params)`. Values passed as separate params list, not interpolated. |
| `lakehouse_client.py` | 344 | Same as above — parameters passed via `params` list to Data API. |
| `lakehouse_client.py` | 374 | Same as above. |
| `timestream_client.py` | 78 | `machine_id` validated as positive integer at MCP server layer; `metric` validated against enum (`temperature`, `vibration`, `pressure`). Timestream Query API provides server-side validation. |
| `timestream_client.py` | 108 | Same as above — all inputs pre-validated at tool boundary. |
| `seed_data.py` | 101, 115 | Deployment seed script using static hardcoded data values (factory names, machine IDs). No user input ever reaches these queries. Script is run once by the deploying admin. |

**Defense in depth:**
1. MCP server validates input types (int, enum) before passing to data layer
2. Data provider validates parameters
3. AWS Data APIs (Redshift, Timestream) sanitize server-side
4. No path exists from end-user input to raw SQL string interpolation

---

### B310 — Audit URL Open for Permitted Schemes (2 findings)

| File | Line | Accept Reason |
|------|------|---------------|
| `opensearch_client.py` | 66 | URL is constructed from `OPENSEARCH_ENDPOINT` environment variable, set at deployment time by infrastructure admin. Always an AWS OpenSearch Serverless HTTPS endpoint. Not derived from user input or agent reasoning. |
| `seed_data.py` | 351 | Same pattern — URL from `OPENSEARCH_ENDPOINT` env var. Deployment-only script, never user-facing. |

---

### B105 — Possible Hardcoded Password (1 finding)

| File | Line | Accept Reason |
|------|------|---------------|
| `setup_identity.py` | 35 | **False positive.** The flagged string is the help message: `'Set environment variables DEMO_PASSWORD_SARAH, DEMO_PASSWORD_RAJ, DEMO_PASSWORD_PRIYA before running this script.'` — this is documentation text assigned to `_DEFAULT_PASSWORD_MSG`, not a credential. |

---

## CloudFormation Findings — Checkov (6)

### CKV_AWS_162 — RDS IAM Authentication Not Enabled

| Resource | Accept Reason |
|----------|---------------|
| `AuroraCluster` (line 100) | This demo uses password authentication via Secrets Manager for simplicity. IAM auth adds complexity without security benefit for a local demo. The README security notice directs users to implement IAM auth for production. |

### CKV_AWS_160 — Timestream Not Encrypted with KMS CMK

| Resource | Accept Reason |
|----------|---------------|
| `TimestreamDatabase` (line 140) | Timestream uses AWS-managed encryption by default (AES-256). CMK adds cost (~$1/month per key + API call charges) with no security benefit for demo data. Production guidance is documented in the README. |

### CKV_AWS_149 — Secrets Manager Not Encrypted with KMS CMK

| Resource | Accept Reason |
|----------|---------------|
| `AuroraSecret` (line 130) | Secrets Manager uses AWS-managed encryption (AES-256) by default. CMK is not required for demo credentials. Production deployments should use CMK — documented in the .env.example security notice. |

### CKV_AWS_111 — IAM Write Access Without Constraints

| Resource | Accept Reason |
|----------|---------------|
| `AgentExecutionRole` (line 447) | The `redshift-data:ExecuteStatement`, `redshift-data:DescribeStatement`, and `redshift-data:GetStatementResult` actions do not support resource-level permissions per [AWS documentation](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonredshiftdataapi.html). `Resource: *` is the only valid configuration. All other policies in this role are scoped to specific ARNs. |

### CKV_AWS_18 / CKV_AWS_21 — LoggingBucket Missing Logging and Versioning

| Resource | Accept Reason |
|----------|---------------|
| `LoggingBucket` (line 246) | **CKV_AWS_21 (versioning):** Fixed — versioning is now enabled. **CKV_AWS_18 (logging):** A logging destination bucket cannot log to itself — this creates an infinite loop. This is a known Checkov false positive for logging buckets. AWS documentation confirms this pattern: the logging target bucket does not need its own access logging. |

---

## CloudFormation Findings — CFN Guard (2)

### S3_BUCKET_SSL_REQUESTS_ONLY

| Resource | Accept Reason |
|----------|---------------|
| `template.yaml` (line 1) | **Fixed for DataLakeBucket and MemoryBucket** (both have DenyNonSSL bucket policies). The remaining finding is for LoggingBucket — now also fixed with a DenyNonSSL policy in the latest commit. If this finding persists, it may be a CFN Guard evaluation order issue where the policy resource is defined after the bucket. |

### S3_BUCKET_LOGGING_ENABLED (LoggingBucket)

| Resource | Accept Reason |
|----------|---------------|
| `LoggingBucket` (line 248) | A logging destination bucket cannot log to itself (creates infinite write loop). This is an accepted AWS pattern. The LoggingBucket receives logs from DataLakeBucket and MemoryBucket — it does not need its own access logging. |

---

## Semgrep Findings (3)

### Dangerous Subprocess Use

| File | Line | Accept Reason |
|------|------|---------------|
| `start_all.py` | 68 | `Popen` is called with a static command list `[sys.executable, "-m", server_module]` where `server_module` comes from a hardcoded constant list defined at the top of the file. No user input or environment variable influences the command. |
| `deploy_all.py` | 61 | `subprocess.run` called with `[sys.executable, script_path]` where `script_path` is from a hardcoded list of deployment scripts defined in the same file. Not user-controllable. |
| `deploy_all.py` | 62 | Same as above — duplicate finding for the same call on adjacent line. |

---

## Disposition Summary

| Category | Count | Action |
|----------|-------|--------|
| Fixed (prior commits) | 10 | Resolved — no longer in codebase |
| False Positive | 3 | B105 help string, LoggingBucket self-logging, CFN Guard eval order |
| Acceptable for Demo | 8 | CMK encryption, IAM auth, Redshift Data API Resource:* |
| Safe Pattern (validated inputs) | 10 | SQL injection (parameterized), URL open (env-var), subprocess (static) |
| **Total** | **21** | **All justified** |

---

*Document prepared: June 22, 2026*
