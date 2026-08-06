# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Tests for budget management — enforcement, counters, and limits."""

from src.budget.manager import BudgetConfig, BudgetManager, BudgetStatus


class TestBudgetConfig:
    """Tests for budget configuration loading."""

    def test_load_config_from_file(self):
        """Should load budget_config.json successfully."""
        config = BudgetConfig.load()
        assert "plant_manager" in config.role_limits
        assert "line_supervisor" in config.role_limits
        assert "maintenance_technician" in config.role_limits

    def test_config_has_daily_limits(self):
        """Each role should have a daily_token_limit."""
        config = BudgetConfig.load()
        assert config.role_limits["plant_manager"]["daily_token_limit"] == 100000
        assert config.role_limits["line_supervisor"]["daily_token_limit"] == 50000
        assert config.role_limits["maintenance_technician"]["daily_token_limit"] == 30000

    def test_config_has_monthly_limits(self):
        """Each role should have a monthly_cost_limit_usd."""
        config = BudgetConfig.load()
        assert config.role_limits["plant_manager"]["monthly_cost_limit_usd"] == 50.00
        assert config.role_limits["maintenance_technician"]["monthly_cost_limit_usd"] == 15.00

    def test_config_has_enforcement_thresholds(self):
        """Should have warn/throttle/block percentages."""
        config = BudgetConfig.load()
        assert config.enforcement["warn_at_percent"] == 80
        assert config.enforcement["throttle_at_percent"] == 90
        assert config.enforcement["block_at_percent"] == 100


class TestBudgetManager:
    """Tests for budget tracking and enforcement."""

    def setup_method(self):
        self.config = BudgetConfig.load()
        self.manager = BudgetManager(config=self.config, use_dynamodb=False)

    def test_initial_budget_status_is_clean(self):
        """New user should have zero usage."""
        status = self.manager.get_budget_status("priya.nair", "maintenance_technician")
        assert status.daily_token_count == 0
        assert status.daily_token_limit == 30000
        assert status.enforcement_level == "none"
        assert not status.is_exceeded

    def test_increment_usage(self):
        """Should track token consumption."""
        self.manager.increment_usage("priya.nair", tokens_used=500)
        self.manager.increment_usage("priya.nair", tokens_used=300)

        status = self.manager.get_budget_status("priya.nair", "maintenance_technician")
        assert status.daily_token_count == 800

    def test_budget_check_under_limit(self):
        """Should allow requests under budget."""
        self.manager.increment_usage("raj.patel", tokens_used=1000)
        allowed, reason = self.manager.check_budget("raj.patel", "line_supervisor")
        assert allowed is True
        assert reason == "OK"

    def test_budget_check_exceeded(self):
        """Should block requests when budget is exhausted."""
        # Simulate exceeding the 30000 token daily limit
        self.manager.increment_usage("priya.nair", tokens_used=30001)

        allowed, reason = self.manager.check_budget("priya.nair", "maintenance_technician")
        assert allowed is False
        assert "exceeded" in reason.lower()

    def test_budget_warning_at_80_percent(self):
        """Should warn at 80% budget consumption."""
        # 80% of 30000 = 24000
        self.manager.increment_usage("priya.nair", tokens_used=24500)

        status = self.manager.get_budget_status("priya.nair", "maintenance_technician")
        assert status.enforcement_level == "warn"
        assert status.is_warning

    def test_budget_throttle_at_90_percent(self):
        """Should throttle at 90% budget consumption."""
        # 90% of 30000 = 27000
        self.manager.increment_usage("priya.nair", tokens_used=27500)

        status = self.manager.get_budget_status("priya.nair", "maintenance_technician")
        assert status.enforcement_level == "throttle"
        assert status.is_throttled

    def test_budget_block_at_100_percent(self):
        """Should block at 100% budget consumption."""
        self.manager.increment_usage("priya.nair", tokens_used=30000)

        status = self.manager.get_budget_status("priya.nair", "maintenance_technician")
        assert status.enforcement_level == "block"
        assert status.is_exceeded

    def test_different_limits_per_role(self):
        """Plant manager should have higher limits than technician."""
        pm_status = self.manager.get_budget_status("sarah.chen", "plant_manager")
        tech_status = self.manager.get_budget_status("priya.nair", "maintenance_technician")

        assert pm_status.daily_token_limit == 100000
        assert tech_status.daily_token_limit == 30000

    def test_reset_daily_usage(self):
        """Admin reset should clear the counter."""
        self.manager.increment_usage("priya.nair", tokens_used=25000)
        self.manager.reset_daily_usage("priya.nair")

        status = self.manager.get_budget_status("priya.nair", "maintenance_technician")
        assert status.daily_token_count == 0

    def test_update_limits(self):
        """Admin should be able to change limits."""
        self.manager.update_limits("maintenance_technician", daily_token_limit=50000)

        status = self.manager.get_budget_status("priya.nair", "maintenance_technician")
        assert status.daily_token_limit == 50000

    def test_get_all_usage(self):
        """Should return status for all known users."""
        self.manager.increment_usage("sarah.chen", tokens_used=1000)
        self.manager.increment_usage("raj.patel", tokens_used=2000)

        all_usage = self.manager.get_all_usage()
        assert "sarah.chen" in all_usage
        assert "raj.patel" in all_usage
        assert "priya.nair" in all_usage
        assert all_usage["sarah.chen"].daily_token_count == 1000
        assert all_usage["raj.patel"].daily_token_count == 2000

    def test_multiple_increments_accumulate(self):
        """Multiple tool calls should accumulate tokens."""
        for _ in range(10):
            self.manager.increment_usage("raj.patel", tokens_used=450)

        status = self.manager.get_budget_status("raj.patel", "line_supervisor")
        assert status.daily_token_count == 4500

    def test_percent_used_calculation(self):
        """Percent used should be correctly calculated."""
        # 15000 out of 50000 = 30%
        self.manager.increment_usage("raj.patel", tokens_used=15000)

        status = self.manager.get_budget_status("raj.patel", "line_supervisor")
        assert 0.29 < status.percent_used < 0.31
