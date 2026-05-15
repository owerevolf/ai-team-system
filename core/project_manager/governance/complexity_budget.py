"""
P4 — Complexity Budget System.

Tracks and enforces complexity budgets across the platform.

Budgets:
- Dependency depth (max chain length)
- Fan-in / fan-out per module
- Subsystem coupling (cross-subsystem dependencies)
- Workflow complexity (steps per workflow)
- Validation chain length (max validation pipeline depth)
- Retrieval pipeline depth (max stages)

When a budget is exceeded → warning or enforcement action.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class BudgetStatus(Enum):
    OK = "ok"
    WARNING = "warning"  # approaching limit
    EXCEEDED = "exceeded"  # over budget


@dataclass
class Budget:
    """A single complexity budget."""
    name: str
    current: float = 0.0
    warning_threshold: float = 0.0
    hard_limit: float = 0.0
    unit: str = ""

    @property
    def status(self) -> BudgetStatus:
        if self.hard_limit > 0 and self.current >= self.hard_limit:
            return BudgetStatus.EXCEEDED
        if self.warning_threshold > 0 and self.current >= self.warning_threshold:
            return BudgetStatus.WARNING
        return BudgetStatus.OK

    @property
    def utilization_pct(self) -> float:
        if self.hard_limit <= 0:
            return 0.0
        return round((self.current / self.hard_limit) * 100, 1)


@dataclass
class BudgetViolation:
    """A budget that has been exceeded."""
    budget_name: str
    current: float
    limit: float
    unit: str
    message: str


class ComplexityBudgetSystem:
    """
    Manages complexity budgets for the platform.

    Default budgets:
    - dependency_depth: max 10 (chain of imports)
    - fan_out: max 15 (imports per module)
    - fan_in: max 20 (importers per module)
    - subsystem_coupling: max 5 (cross-subsystem deps per subsystem)
    - workflow_steps: max 20 (steps in a single workflow)
    - validation_chain: max 10 (validation checks in pipeline)
    - retrieval_stages: max 5 (retrieval pipeline stages)
    - event_chain_depth: max 5 (event handler chain)
    - lock_depth: max 3 (nested locks)
    """

    DEFAULT_BUDGETS = {
        'dependency_depth': {'warning': 8, 'hard': 10, 'unit': 'hops'},
        'fan_out': {'warning': 12, 'hard': 15, 'unit': 'imports'},
        'fan_in': {'warning': 15, 'hard': 20, 'unit': 'importers'},
        'subsystem_coupling': {'warning': 4, 'hard': 5, 'unit': 'cross_deps'},
        'workflow_steps': {'warning': 15, 'hard': 20, 'unit': 'steps'},
        'validation_chain': {'warning': 8, 'hard': 10, 'unit': 'checks'},
        'retrieval_stages': {'warning': 4, 'hard': 5, 'unit': 'stages'},
        'event_chain_depth': {'warning': 4, 'hard': 5, 'unit': 'handlers'},
        'lock_depth': {'warning': 2, 'hard': 3, 'unit': 'nested_locks'},
    }

    def __init__(self, custom_budgets: Optional[Dict[str, Dict[str, float]]] = None):
        self._budgets: Dict[str, Budget] = {}
        budgets_config = custom_budgets or self.DEFAULT_BUDGETS
        for name, cfg in budgets_config.items():
            self._budgets[name] = Budget(
                name=name,
                warning_threshold=cfg.get('warning', 0),
                hard_limit=cfg.get('hard', 0),
                unit=cfg.get('unit', ''),
            )

    def update(self, name: str, value: float) -> Optional[BudgetViolation]:
        """
        Update a budget's current value.
        Returns BudgetViolation if exceeded, None otherwise.
        """
        budget = self._budgets.get(name)
        if not budget:
            return None
        budget.current = value
        if budget.status == BudgetStatus.EXCEEDED:
            return BudgetViolation(
                budget_name=name,
                current=value,
                limit=budget.hard_limit,
                unit=budget.unit,
                message=f"Budget '{name}' exceeded: {value}/{budget.hard_limit} {budget.unit}"
            )
        return None

    def get_budget(self, name: str) -> Optional[Budget]:
        """Get a budget by name."""
        return self._budgets.get(name)

    def get_all_budgets(self) -> Dict[str, Budget]:
        """Get all budgets."""
        return dict(self._budgets)

    def check_all(self) -> List[BudgetViolation]:
        """Check all budgets. Returns list of violations."""
        violations = []
        for name, budget in self._budgets.items():
            if budget.status == BudgetStatus.EXCEEDED:
                violations.append(BudgetViolation(
                    budget_name=name,
                    current=budget.current,
                    limit=budget.hard_limit,
                    unit=budget.unit,
                    message=f"Budget '{name}' exceeded: {budget.current}/{budget.hard_limit} {budget.unit}"
                ))
        return violations

    def get_status(self) -> Dict[str, Any]:
        """Get status of all budgets."""
        result = {}
        for name, budget in self._budgets.items():
            result[name] = {
                'current': budget.current,
                'warning_threshold': budget.warning_threshold,
                'hard_limit': budget.hard_limit,
                'utilization_pct': budget.utilization_pct,
                'status': budget.status.value,
                'unit': budget.unit,
            }
        return result

    def set_custom_budget(self, name: str, warning: float, hard: float, unit: str = "") -> None:
        """Set a custom budget."""
        self._budgets[name] = Budget(
            name=name,
            warning_threshold=float(warning),
            hard_limit=float(hard),
            unit=str(unit),
        )
