# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""End-to-end budget enforcement tests.

These test the FULL flow:
1. Agent receives query
2. Budget counter is checked (pre-tool)
3. Tool executes (or is blocked)
4. Budget counter is incremented (post-tool)
5. Policy engine denies when limit is reached

Scenarios:
- Normal query under budget → succeeds, counter increments
- Budget at 80% → warn level, query still succeeds
- Budget at 90% → throttle level, query still succeeds (with delay note)
- Budget at 100% → blocked by policy, tool never executes
- Budget reset → counter clears, queries succeed again
- Different roles have different limits
- Cross-session: budget persists after agent restart
"""

import os
from unittest.mock import patch

from src.budget.manager import BudgetConfig, BudgetManager
from src.identity.models import PRIYA_NAIR, RAJ_PATEL, SARAH_CHEN
from src.identity.policy import PolicyEngine


class TestBudgetE2E:
    """End-to-end tests for budget enforcement through the full policy stack."""

    def setup_method(self):
        """Fresh BudgetManager + PolicyEngine for each test."""
        import tempfile
        BudgetManager._instance = None
        self.config = BudgetConfig.load()
        # Use a temp SQLite DB so tests don't share state
        self._tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.budget_mgr = BudgetManager(config=self.config, use_dynamodb=False)
        self.budget_mgr._db_path = self._tmp_db.name
        self.budget_mgr._init_sqlite()
        BudgetManager._instance = self.budget_mgr
        self.policy = PolicyEngine()

    def teardown_method(self):
        """Clean up temp DB."""
        import os
        BudgetManager._instance = None
        try:
            os.unlink(self._tmp_db.name)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Scenario 1: Normal query under budget → allowed
    # ─────────────────────────────────────────────────────────────────────
    def test_scenario_query_under_budget_succeeds(self):
        """Priya asks about Machine 42 — under budget, should be allowed."""
        # Pre-check budget
        self.budget_mgr.increment_usage("priya.nair", tokens_used=1000)
        status = self.budget_mgr.get_budget_status("priya.nair", "maintenance_technician")
        assert not status.is_exceeded

        # Policy evaluation with budget context injected
        decision = self.policy.evaluate(
            PRIYA_NAIR,
            "get_sensor_readings",
            {
                "machine_id": 42,
                "_budget_context": {
                    "daily_token_count": status.daily_token_count,
                    "daily_token_limit": status.daily_token_limit,
                },
            },
        )
        assert decision.allowed is True

        # Post-tool: increment counter
        self.budget_mgr.increment_usage("priya.nair", tokens_used=450)
        new_status = self.budget_mgr.get_budget_status("priya.nair", "maintenance_technician")
        assert new_status.daily_token_count == 1450

    # ─────────────────────────────────────────────────────────────────────
    # Scenario 2: Budget at 80% → warn, but allowed
    # ─────────────────────────────────────────────────────────────────────
    def test_scenario_80_percent_warns_but_allows(self):
        """At 80% budget, system warns but doesn't block."""
        # 80% of 30000 = 24000
        self.budget_mgr.increment_usage("priya.nair", tokens_used=24500)
        status = self.budget_mgr.get_budget_status("priya.nair", "maintenance_technician")

        assert status.enforcement_level == "warn"
        assert status.is_warning
        assert not status.is_exceeded

        # Policy should still ALLOW (budget context shows under limit)
        decision = self.policy.evaluate(
            PRIYA_NAIR,
            "get_sensor_readings",
            {
                "machine_id": 42,
                "_budget_context": {
                    "daily_token_count": status.daily_token_count,
                    "daily_token_limit": status.daily_token_limit,
                },
            },
        )
        assert decision.allowed is True

    # ─────────────────────────────────────────────────────────────────────
    # Scenario 3: Budget at 90% → throttle, but allowed
    # ─────────────────────────────────────────────────────────────────────
    def test_scenario_90_percent_throttles_but_allows(self):
        """At 90% budget, system throttles (delays) but doesn't block."""
        # 90% of 30000 = 27000
        self.budget_mgr.increment_usage("priya.nair", tokens_used=27500)
        status = self.budget_mgr.get_budget_status("priya.nair", "maintenance_technician")

        assert status.enforcement_level == "throttle"
        assert status.is_throttled
        assert not status.is_exceeded

        # check_budget should return allowed=True with throttle reason
        allowed, reason = self.budget_mgr.check_budget("priya.nair", "maintenance_technician")
        assert allowed is True
        assert "THROTTLE" in reason

    # ─────────────────────────────────────────────────────────────────────
    # Scenario 4: Budget at 100% → BLOCKED by Cedar policy
    # ─────────────────────────────────────────────────────────────────────
    def test_scenario_100_percent_blocks_tool_call(self):
        """At 100% budget, Cedar-simulated policy DENIES the tool call."""
        # Exceed the 30000 limit
        self.budget_mgr.increment_usage("priya.nair", tokens_used=30000)
        status = self.budget_mgr.get_budget_status("priya.nair", "maintenance_technician")

        assert status.is_exceeded
        assert status.enforcement_level == "block"

        # Policy evaluation with budget context → DENY
        decision = self.policy.evaluate(
            PRIYA_NAIR,
            "get_sensor_readings",
            {
                "machine_id": 42,  # In scope (would normally be allowed)
                "_budget_context": {
                    "daily_token_count": status.daily_token_count,
                    "daily_token_limit": status.daily_token_limit,
                },
            },
        )
        assert decision.allowed is False
        assert "budget exceeded" in decision.reason.lower()

    # ─────────────────────────────────────────────────────────────────────
    # Scenario 5: Budget blocked even for plant manager
    # ─────────────────────────────────────────────────────────────────────
    def test_scenario_plant_manager_also_has_budget_limit(self):
        """Even Sarah (full access) is blocked when budget is exceeded."""
        # Sarah's limit is 100000
        self.budget_mgr.increment_usage("sarah.chen", tokens_used=100000)
        status = self.budget_mgr.get_budget_status("sarah.chen", "plant_manager")

        assert status.is_exceeded

        # Policy: plant managers bypass scope rules but NOT budget rules
        decision = self.policy.evaluate(
            SARAH_CHEN,
            "detect_anomaly",
            {
                "line": "Line 4",
                "_budget_context": {
                    "daily_token_count": status.daily_token_count,
                    "daily_token_limit": status.daily_token_limit,
                },
            },
        )
        # Note: current policy.py checks budget AFTER full_access bypass
        # Let's verify the budget check is reached
        # Full access users should still be subject to budget (cost governance)
        # This tests that budget enforcement is universal
        assert decision.allowed is False
        assert "budget exceeded" in decision.reason.lower()

    # ─────────────────────────────────────────────────────────────────────
    # Scenario 6: Budget reset → queries succeed again
    # ─────────────────────────────────────────────────────────────────────
    def test_scenario_reset_restores_access(self):
        """Admin resets counter → user can query again."""
        # Exhaust budget
        self.budget_mgr.increment_usage("priya.nair", tokens_used=30000)
        status = self.budget_mgr.get_budget_status("priya.nair", "maintenance_technician")
        assert status.is_exceeded

        # Admin resets
        self.budget_mgr.reset_daily_usage("priya.nair")
        status = self.budget_mgr.get_budget_status("priya.nair", "maintenance_technician")
        assert status.daily_token_count == 0
        assert not status.is_exceeded

        # Policy now allows
        decision = self.policy.evaluate(
            PRIYA_NAIR,
            "get_sensor_readings",
            {
                "machine_id": 42,
                "_budget_context": {
                    "daily_token_count": 0,
                    "daily_token_limit": 30000,
                },
            },
        )
        assert decision.allowed is True

    # ─────────────────────────────────────────────────────────────────────
    # Scenario 7: Different roles hit limits at different points
    # ─────────────────────────────────────────────────────────────────────
    def test_scenario_role_limits_are_independent(self):
        """Raj (50K limit) and Priya (30K) hit limits at different usage."""
        # Both use 35000 tokens
        self.budget_mgr.increment_usage("raj.patel", tokens_used=35000)
        self.budget_mgr.increment_usage("priya.nair", tokens_used=35000)

        raj_status = self.budget_mgr.get_budget_status("raj.patel", "line_supervisor")
        priya_status = self.budget_mgr.get_budget_status("priya.nair", "maintenance_technician")

        # Raj: 35000/50000 = 70% → no enforcement
        assert raj_status.enforcement_level == "none"
        assert not raj_status.is_exceeded

        # Priya: 35000/30000 = 117% → BLOCKED
        assert priya_status.enforcement_level == "block"
        assert priya_status.is_exceeded

    # ─────────────────────────────────────────────────────────────────────
    # Scenario 8: Scope + Budget combined — both must pass
    # ─────────────────────────────────────────────────────────────────────
    def test_scenario_scope_denied_before_budget_check(self):
        """Raj asks about Line 4 — scope denies before budget is relevant."""
        # Raj has plenty of budget
        self.budget_mgr.increment_usage("raj.patel", tokens_used=1000)
        status = self.budget_mgr.get_budget_status("raj.patel", "line_supervisor")
        assert not status.is_exceeded

        # But Line 4 is out of scope → denied by scope rule (not budget)
        decision = self.policy.evaluate(
            RAJ_PATEL,
            "get_equipment_status",
            {
                "line": "Line 4",
                "_budget_context": {
                    "daily_token_count": status.daily_token_count,
                    "daily_token_limit": status.daily_token_limit,
                },
            },
        )
        assert decision.allowed is False
        assert "Line 4" in decision.reason  # Scope denial, not budget

    # ─────────────────────────────────────────────────────────────────────
    # Scenario 9: Simulate a full session — multiple queries accumulate
    # ─────────────────────────────────────────────────────────────────────
    def test_scenario_full_session_accumulates(self):
        """Priya makes 10 queries — tokens accumulate progressively."""
        queries_and_tokens = [
            ("What's Machine 42 vibration?", 450),
            ("Is that above normal?", 380),
            ("Show maintenance history", 520),
            ("Are bearings in stock?", 320),
            ("What's the lead time?", 290),
            ("Temperature on Machine 42?", 410),
            ("Compare to last week", 650),
            ("Any other anomalies?", 480),
            ("Show Line 4 OEE", 520),
            ("Summarize findings", 780),
        ]

        for question, tokens in queries_and_tokens:
            self.budget_mgr.increment_usage("priya.nair", tokens_used=tokens)

        total = sum(t for _, t in queries_and_tokens)
        status = self.budget_mgr.get_budget_status("priya.nair", "maintenance_technician")
        assert status.daily_token_count == total  # 4800 tokens
        assert status.enforcement_level == "none"  # Well under 30000

    # ─────────────────────────────────────────────────────────────────────
    # Scenario 10: Budget context missing → allowed (fail-open for availability)
    # ─────────────────────────────────────────────────────────────────────
    def test_scenario_no_budget_context_allows(self):
        """If budget context is missing (DynamoDB down), query still allowed."""
        # No _budget_context in parameters → budget rule doesn't fire
        decision = self.policy.evaluate(
            PRIYA_NAIR,
            "get_sensor_readings",
            {"machine_id": 42},  # No _budget_context key
        )
        assert decision.allowed is True
