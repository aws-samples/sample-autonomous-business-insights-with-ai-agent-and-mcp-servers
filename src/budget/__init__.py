# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from src.budget.manager import BudgetManager, BudgetConfig, BudgetStatus

# Module-level singleton — shared across all imports in the same process
_budget_manager: BudgetManager | None = None


def get_budget_manager() -> BudgetManager:
    """Get the shared BudgetManager instance (module-level singleton)."""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = BudgetManager(use_dynamodb=False)
    return _budget_manager
