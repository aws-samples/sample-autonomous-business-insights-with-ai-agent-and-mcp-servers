# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Budget management for per-user and per-team cost controls.

Provides:
- Token counter tracking (daily, monthly) per user and team
- Budget limit checking with graduated enforcement (warn/throttle/block)
- Integration with DynamoDB for atomic counters (production)
- In-memory counters for local simulation (SIMULATION_MODE=true)

In production, the REQUEST interceptor reads from DynamoDB and injects
budget context into the request. Cedar evaluates forbid_budget_exceeded.
The RESPONSE interceptor increments the counter after successful tool calls.

For local simulation, BudgetManager maintains in-memory counters and the
PolicyEngine checks limits directly.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BudgetStatus:
    """Current budget state for a user."""

    user_id: str
    role: str
    daily_token_count: int = 0
    daily_token_limit: int = 50000
    monthly_cost_usd: float = 0.0
    monthly_cost_limit_usd: float = 25.00
    percent_used: float = 0.0
    enforcement_level: str = "none"  # none, warn, throttle, block

    @property
    def is_exceeded(self) -> bool:
        return self.daily_token_count >= self.daily_token_limit

    @property
    def is_warning(self) -> bool:
        return 0.8 <= self.percent_used < 0.9

    @property
    def is_throttled(self) -> bool:
        return 0.9 <= self.percent_used < 1.0


@dataclass
class BudgetConfig:
    """Loaded from budget_config.json."""

    role_limits: dict[str, dict] = field(default_factory=dict)
    team_limits: dict[str, dict] = field(default_factory=dict)
    enforcement: dict[str, Any] = field(default_factory=dict)
    global_defaults: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: str | None = None) -> "BudgetConfig":
        """Load budget configuration from JSON file."""
        if config_path is None:
            config_path = str(
                Path(__file__).parent.parent.parent
                / "deploy"
                / "agentcore"
                / "budget_config.json"
            )

        if not os.path.exists(config_path):
            logger.warning("Budget config not found at %s, using defaults", config_path)
            return cls()

        with open(config_path) as f:
            data = json.load(f)

        return cls(
            role_limits=data.get("role_limits", {}),
            team_limits=data.get("team_limits", {}),
            enforcement=data.get("enforcement", {}),
            global_defaults=data.get("global_defaults", {}),
        )


class BudgetManager:
    """Manages budget tracking and enforcement.

    In production: reads/writes DynamoDB atomic counters.
    In simulation: uses in-memory dict.

    Note: In the Streamlit demo, use the "Simulate Usage" button on the Admin tab
    to add tokens and observe graduated enforcement (warn/throttle/block).
    In production, the Gateway interceptors automatically read/write DynamoDB counters
    on every tool call — no application code changes needed.

    Usage:
        budget_mgr = BudgetManager.get_instance()
        status = budget_mgr.get_budget_status("priya.nair", "maintenance_technician")
        if status.is_exceeded:
            # Block the request
        budget_mgr.increment_usage("priya.nair", tokens_used=450)
    """

    _instance: "BudgetManager | None" = None

    @classmethod
    def get_instance(cls, config: "BudgetConfig | None" = None,
                     use_dynamodb: bool = False) -> "BudgetManager":
        """Get or create the singleton BudgetManager instance."""
        if cls._instance is None:
            cls._instance = cls(config=config, use_dynamodb=use_dynamodb)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def __init__(self, config: BudgetConfig | None = None, use_dynamodb: bool = False):
        self.config = config or BudgetConfig.load()
        self.use_dynamodb = use_dynamodb
        self._counters: dict[str, dict] = {}  # Fallback in-memory

        if use_dynamodb:
            import boto3
            table_name = os.getenv("BUDGET_TABLE_NAME", "MfgInsights-BudgetCounters")
            region = os.getenv("AWS_REGION", "us-east-1")
            self._table = boto3.resource("dynamodb", region_name=region).Table(table_name)
        else:
            # Use SQLite for local persistence (survives restarts)
            import sqlite3
            db_path = os.getenv(
                "BUDGET_DB_PATH",
                str(Path(__file__).parent.parent.parent / ".budget_counters.db"),
            )
            self._db_path = db_path
            self._init_sqlite()

    def get_budget_status(self, user_id: str, role: str) -> BudgetStatus:
        """Get current budget status for a user.

        Returns:
            BudgetStatus with current usage, limits, and enforcement level.
        """
        limits = self.config.role_limits.get(role, {})
        daily_limit = limits.get("daily_token_limit", 50000)
        monthly_limit = limits.get("monthly_cost_limit_usd", 25.00)

        # Get current usage
        daily_count = self._get_daily_count(user_id)
        monthly_cost = self._get_monthly_cost(user_id)

        # Calculate percent used (based on daily tokens)
        percent_used = daily_count / daily_limit if daily_limit > 0 else 0.0

        # Determine enforcement level
        warn_threshold = self.config.enforcement.get("warn_at_percent", 80) / 100
        throttle_threshold = self.config.enforcement.get("throttle_at_percent", 90) / 100
        block_threshold = self.config.enforcement.get("block_at_percent", 100) / 100

        if percent_used >= block_threshold:
            level = "block"
        elif percent_used >= throttle_threshold:
            level = "throttle"
        elif percent_used >= warn_threshold:
            level = "warn"
        else:
            level = "none"

        return BudgetStatus(
            user_id=user_id,
            role=role,
            daily_token_count=daily_count,
            daily_token_limit=daily_limit,
            monthly_cost_usd=monthly_cost,
            monthly_cost_limit_usd=monthly_limit,
            percent_used=percent_used,
            enforcement_level=level,
        )

    def check_budget(self, user_id: str, role: str) -> tuple[bool, str]:
        """Check if user has budget remaining.

        Returns:
            (allowed, reason) tuple.
        """
        status = self.get_budget_status(user_id, role)

        if status.enforcement_level == "block":
            return False, (
                f"Daily token budget exceeded. "
                f"Used: {status.daily_token_count:,} / "
                f"Limit: {status.daily_token_limit:,} tokens. "
                f"Budget resets at midnight UTC."
            )

        if status.enforcement_level == "throttle":
            logger.warning(
                "Budget throttle: user=%s used %d/%d tokens (%.0f%%)",
                user_id, status.daily_token_count, status.daily_token_limit,
                status.percent_used * 100,
            )
            # In throttle mode: allow but add delay (handled by caller)
            return True, f"THROTTLE: {status.percent_used:.0%} budget consumed"

        if status.enforcement_level == "warn":
            logger.info(
                "Budget warning: user=%s at %.0f%% of daily limit",
                user_id, status.percent_used * 100,
            )

        return True, "OK"

    def increment_usage(self, user_id: str, tokens_used: int) -> None:
        """Increment token counter after a successful tool call.

        Args:
            user_id: The user who consumed tokens.
            tokens_used: Number of tokens consumed (input + output).
        """
        if self.use_dynamodb:
            self._dynamodb_increment(user_id, tokens_used)
        else:
            self._memory_increment(user_id, tokens_used)

    def get_all_usage(self) -> dict[str, BudgetStatus]:
        """Get budget status for all known users (for admin UI)."""
        users_and_roles = {
            "sarah.chen": "plant_manager",
            "raj.patel": "line_supervisor",
            "priya.nair": "maintenance_technician",
        }
        return {
            user: self.get_budget_status(user, role)
            for user, role in users_and_roles.items()
        }

    def reset_daily_usage(self, user_id: str) -> None:
        """Reset daily token counter for a user (admin action)."""
        today = date.today().isoformat()

        if self.use_dynamodb:
            self._table.put_item(
                Item={
                    "user_id": user_id,
                    "date": today,
                    "daily_token_count": 0,
                    "invocation_count": 0,
                    "last_reset": datetime.now().isoformat(),
                    "expires_at": int(time.time()) + (90 * 86400),
                },
            )
        else:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "INSERT OR REPLACE INTO budget_counters (user_id, date, daily_token_count, invocation_count, last_updated) "
                "VALUES (?, ?, 0, 0, ?)",
                (user_id, today, datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()

        logger.info("Reset daily budget for user '%s'", user_id)

    def update_limits(self, role: str, daily_token_limit: int | None = None,
                      monthly_cost_limit: float | None = None) -> None:
        """Update limits for a role (admin action)."""
        if role in self.config.role_limits:
            if daily_token_limit is not None:
                self.config.role_limits[role]["daily_token_limit"] = daily_token_limit
            if monthly_cost_limit is not None:
                self.config.role_limits[role]["monthly_cost_limit_usd"] = monthly_cost_limit
            logger.info("Updated limits for role '%s'", role)

    # --- Private methods ---

    def _init_sqlite(self):
        """Initialize SQLite database for local budget persistence."""
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS budget_counters (
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                daily_token_count INTEGER DEFAULT 0,
                invocation_count INTEGER DEFAULT 0,
                last_updated TEXT,
                PRIMARY KEY (user_id, date)
            )
        """)
        conn.commit()
        conn.close()

    def _get_daily_count(self, user_id: str) -> int:
        """Get today's token count for a user."""
        today = date.today().isoformat()

        if self.use_dynamodb:
            return self._dynamodb_get_count(user_id, today)
        else:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            row = conn.execute(
                "SELECT daily_token_count FROM budget_counters WHERE user_id = ? AND date = ?",
                (user_id, today),
            ).fetchone()
            conn.close()
            return row[0] if row else 0

    def _get_monthly_cost(self, user_id: str) -> float:
        """Get current month's estimated cost (simplified: tokens x rate)."""
        daily_count = self._get_daily_count(user_id)
        return (daily_count / 1000) * 0.01

    def _memory_increment(self, user_id: str, tokens_used: int) -> None:
        """Increment SQLite counter (local persistent mode)."""
        import sqlite3
        today = date.today().isoformat()
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            INSERT INTO budget_counters (user_id, date, daily_token_count, invocation_count, last_updated)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                daily_token_count = daily_token_count + ?,
                invocation_count = invocation_count + 1,
                last_updated = ?
        """, (user_id, today, tokens_used, datetime.now().isoformat(),
              tokens_used, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def _dynamodb_increment(self, user_id: str, tokens_used: int) -> None:
        """Atomic increment in DynamoDB."""
        today = date.today().isoformat()
        expires_at = int(time.time()) + (90 * 86400)  # 90 days TTL

        self._table.update_item(
            Key={"user_id": user_id, "date": today},
            UpdateExpression=(
                "SET daily_token_count = if_not_exists(daily_token_count, :zero) + :tokens, "
                "invocation_count = if_not_exists(invocation_count, :zero) + :one, "
                "last_updated = :now, "
                "expires_at = :ttl"
            ),
            ExpressionAttributeValues={
                ":tokens": tokens_used,
                ":one": 1,
                ":zero": 0,
                ":now": datetime.now().isoformat(),
                ":ttl": expires_at,
            },
        )

    def _dynamodb_get_count(self, user_id: str, date_str: str) -> int:
        """Read current count from DynamoDB."""
        try:
            response = self._table.get_item(
                Key={"user_id": user_id, "date": date_str},
            )
            item = response.get("Item", {})
            return int(item.get("daily_token_count", 0))
        except Exception as e:
            logger.warning("DynamoDB read failed for %s: %s", user_id, e)
            return 0
