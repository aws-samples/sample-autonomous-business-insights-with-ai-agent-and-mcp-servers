# Security Findings — Justification for Acceptance

**Project:** sample-autonomous-business-insights-with-ai-agent-and-mcp-servers
**Publication Target:** AWS Blog (aws-samples)

---

## Summary: 0 High, 7 Medium (all justified), 27 Low (informational)

---

## Medium Findings — Individual Justifications

### M1: B113 — requests without timeout

| | |
|---|---|
| **File** | `deploy/agentcore/test_agentcore.py:46` |
| **CWE** | CWE-400 (Uncontrolled Resource Consumption) |
| **Risk** | Theoretical DoS if target hangs |
| **Accept Reason** | Test-only script. Not part of production agent code. Run manually by developers during deployment validation. Adding timeout would add complexity without security benefit in this context. |
| **Action** | Accept (test code only) |

---

### M2-M5: B608 — SQL injection via f-string

| | |
|---|---|
| **Files** | `src/data/lakehouse_client.py:266,344,374` and `src/data/timestream_client.py:78,108` |
| **CWE** | CWE-89 (SQL Injection) |
| **Risk** | SQL injection if user input reaches query construction |
| **Accept Reason** | **False positive.** Analysis: |

**lakehouse_client.py:**
- WHERE clauses are built from a fixed list of column names (`where_clauses` is constructed from validated parameters)
- Actual values are passed via `params` list to `client.execute_query(sql, params)` — this is parameterized execution
- The Redshift Data API further sanitizes inputs server-side

**timestream_client.py:**
- `machine_id` is validated as a positive integer at the MCP server layer before reaching this function
- `metric` is validated against an enum (`temperature`, `vibration`, `pressure`)
- Timestream query API provides server-side query validation

**Defense in depth:**
1. MCP server validates input types (int, enum)
2. Data provider validates parameters
3. AWS Data API sanitizes server-side

| **Action** | Accept (parameterized + validated inputs) |

---

### M6: B310 — urllib.request.urlopen

| | |
|---|---|
| **File** | `src/data/opensearch_client.py:66` |
| **CWE** | CWE-22 (Path Traversal) / SSRF |
| **Risk** | SSRF if URL is attacker-controlled |
| **Accept Reason** | The URL is constructed from `OPENSEARCH_ENDPOINT` environment variable, set at deployment time by the infrastructure admin. It is NOT derived from user input or agent reasoning. The endpoint is always an AWS OpenSearch Serverless collection URL (HTTPS). |
| **Action** | Accept (env-var controlled, not user input) |

---

## Low Findings (27) — Blanket Justification

All 27 low-severity findings are:
- `B101` (assert statements) — used in test code only
- `B104` (binding to 0.0.0.0) — MCP servers bind for local development, not production deployment
- `B311` (random) — used for generating sample/demo data, not for cryptographic purposes

These are standard patterns for demo/sample code and do not represent security vulnerabilities in the published context.

---

## Pre-Publication Checklist

- [x] No AWS account IDs in code (replaced with 123456789012)
- [x] No resource ARNs from real accounts
- [x] No API keys, tokens, or secrets
- [x] No personal email addresses (using @example.com)
- [x] .env in .gitignore
- [x] MIT-0 license headers on all source files
- [x] requirements.txt pinned to exact versions
- [x] README includes security disclaimer
- [x] Bandit scan: 0 High severity
- [x] Manual review: PASS
