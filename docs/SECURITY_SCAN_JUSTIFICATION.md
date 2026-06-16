# Security Scan Results — Justification

## Scanner: Bandit (Python static analysis)
## Date: 2026-06-11
## Result: 0 High, 6 Medium, 20 Low

---

## Medium Severity Findings (all justified)

### B608: SQL Injection (5 findings) — FALSE POSITIVE

**Files:** `lakehouse_client.py`, `timestream_client.py`

**Explanation:** Bandit flags f-string SQL construction. However:
1. The `where_clauses` are **built from validated, hardcoded strings** — not from user input
2. User-provided values go through **parameterized queries** (`:param_name` with the Redshift Data API)
3. Timestream queries use validated enum values (`metric in VALID_METRICS`) checked before query construction
4. Input validation at the MCP tool layer prevents injection vectors

**Risk:** None. The flagged code does not accept raw user input into SQL.

### B310: URL Open (1 finding) — ACCEPTABLE

**File:** `opensearch_client.py:66`

**Explanation:** `urllib.request.urlopen` is used to call Amazon OpenSearch Serverless with SigV4 authentication. The URL is constructed from environment variables (not user input) and the request is signed with AWS credentials.

**Risk:** None. The endpoint is a configured AWS service, not user-supplied.

---

## Low Severity Findings (all justified)

### B311: Random (15 findings) — BY DESIGN

**File:** `sample_data.py`

**Explanation:** `random` module used to generate **simulated demo data** (fake sensor readings, OEE values). This is explicitly not for security/cryptographic purposes — it's manufacturing sample data for demonstration.

**Risk:** None. Simulated data generation has no security implication.

### B110: Try/Except/Pass (1 finding) — ACCEPTABLE

**File:** `agent.py:258`

**Explanation:** Cleanup code in `finally` block that exits MCP client connections. If cleanup fails, there's nothing actionable — the connection is being discarded anyway.

**Risk:** None. Standard cleanup pattern.

### B404/B603: Subprocess (2 findings) — BY DESIGN

**File:** `start_all.py`

**Explanation:** Used to start MCP server subprocesses during local development. The command is constructed from `sys.executable` (current Python) and hardcoded module names — no user input.

**Risk:** None. No untrusted input enters the subprocess call.

---

## Summary

| Severity | Count | Justified | Action Needed |
|----------|-------|-----------|---------------|
| High | 0 | — | None |
| Medium | 6 | All 6 | None (false positives + acceptable patterns) |
| Low | 20 | All 20 | None (demo data generation + standard patterns) |

**Conclusion:** No remediation required. All findings are either false positives or acceptable patterns for a non-production sample code repository.
