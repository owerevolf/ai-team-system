"""
Phase 12, P5: Runtime Latency Reduction

Measures and minimizes operational latency:
- cognitive latency (time to understand)
- approval latency (time to approve)
- explanation latency (time to explain)
- workflow transition latency
- recovery decision latency

Principle: Minimize operational waiting states.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class LatencyType(Enum):
    COGNITIVE = "cognitive"        # time to understand what's happening
    APPROVAL = "approval"          # time to get approval decision
    EXPLANATION = "explanation"    # time to generate explanation
    WORKFLOW = "workflow"          # time for state transition
    RECOVERY = "recovery"          # time to decide on recovery action


@dataclass
class LatencyMeasurement:
    """A single latency measurement."""
    name: str
    latency_type: LatencyType
    duration_ms: float
    context: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class LatencyBudget:
    """Maximum acceptable latency for a given operation type."""
    latency_type: LatencyType
    max_ms: float
    warning_ms: float = 0.0

    def __post_init__(self):
        if self.warning_ms == 0:
            self.warning_ms = self.max_ms * 0.7


@dataclass
class LatencyReport:
    """Report of latency analysis."""
    measurements: list[LatencyMeasurement] = field(default_factory=list)
    budgets: dict[str, LatencyBudget] = field(default_factory=dict)
    violations: list[LatencyMeasurement] = field(default_factory=list)

    @property
    def average_by_type(self) -> dict[str, float]:
        totals: dict[str, list[float]] = {}
        for m in self.measurements:
            key = m.latency_type.value
            totals.setdefault(key, []).append(m.duration_ms)
        return {k: sum(v) / len(v) for k, v in totals.items() if v}

    @property
    def p95_by_type(self) -> dict[str, float]:
        from statistics import quantiles
        groups: dict[str, list[float]] = {}
        for m in self.measurements:
            key = m.latency_type.value
            groups.setdefault(key, []).append(m.duration_ms)
        result = {}
        for k, v in groups.items():
            if len(v) >= 2:
                sorted_v = sorted(v)
                idx = int(len(sorted_v) * 0.95)
                result[k] = sorted_v[min(idx, len(sorted_v) - 1)]
            elif v:
                result[k] = v[0]
        return result


class RuntimeLatencyReducer:
    """
    Measures and tracks runtime latency across all operational dimensions.
    Identifies bottlenecks and enforces latency budgets.
    """

    # Default latency budgets (milliseconds)
    DEFAULT_BUDGETS: dict[LatencyType, tuple[float, float]] = {
        LatencyType.COGNITIVE: (2000, 1400),    # 2s max for understanding
        LatencyType.APPROVAL: (5000, 3500),      # 5s max for approval
        LatencyType.EXPLANATION: (1000, 700),    # 1s max for explanation
        LatencyType.WORKFLOW: (3000, 2100),      # 3s max for transition
        LatencyType.RECOVERY: (4000, 2800),      # 4s max for recovery decision
    }

    def __init__(self) -> None:
        self._measurements: list[LatencyMeasurement] = []
        self._budgets: dict[str, LatencyBudget] = {}
        self._init_default_budgets()

    def _init_default_budgets(self) -> None:
        for ltype, (max_ms, warn_ms) in self.DEFAULT_BUDGETS.items():
            self._budgets[ltype.value] = LatencyBudget(
                latency_type=ltype,
                max_ms=max_ms,
                warning_ms=warn_ms,
            )

    def set_budget(self, latency_type: LatencyType, max_ms: float, warning_ms: float = 0) -> None:
        """Set a custom latency budget."""
        self._budgets[latency_type.value] = LatencyBudget(
            latency_type=latency_type,
            max_ms=max_ms,
            warning_ms=warning_ms,
        )

    def measure(self, name: str, latency_type: LatencyType, duration_ms: float, context: str = "") -> LatencyMeasurement:
        """Record a latency measurement."""
        m = LatencyMeasurement(
            name=name,
            latency_type=latency_type,
            duration_ms=duration_ms,
            context=context,
        )
        self._measurements.append(m)
        return m

    def time_operation(self, name: str, latency_type: LatencyType, context: str = ""):
        """Context manager for timing operations."""
        return _LatencyTimer(self, name, latency_type, context)

    def check_budget(self, measurement: LatencyMeasurement) -> Optional[str]:
        """Check if a measurement violates its budget. Returns warning or None."""
        budget = self._budgets.get(measurement.latency_type.value)
        if not budget:
            return None
        if measurement.duration_ms > budget.max_ms:
            return (
                f"BUDGET VIOLATION: {measurement.name} took {measurement.duration_ms:.0f}ms "
                f"(budget: {budget.max_ms:.0f}ms)"
            )
        if measurement.duration_ms > budget.warning_ms:
            return (
                f"BUDGET WARNING: {measurement.name} took {measurement.duration_ms:.0f}ms "
                f"(warning at: {budget.warning_ms:.0f}ms)"
            )
        return None

    def get_report(self) -> LatencyReport:
        """Generate latency report with violations."""
        violations = []
        for m in self._measurements:
            if self.check_budget(m):
                violations.append(m)

        return LatencyReport(
            measurements=list(self._measurements),
            budgets=dict(self._budgets),
            violations=violations,
        )

    def get_slowest(self, n: int = 10) -> list[LatencyMeasurement]:
        """Get the N slowest measurements."""
        return sorted(self._measurements, key=lambda m: -m.duration_ms)[:n]

    def clear(self) -> None:
        """Clear all measurements."""
        self._measurements.clear()


class _LatencyTimer:
    """Context manager for timing operations."""

    def __init__(
        self,
        reducer: RuntimeLatencyReducer,
        name: str,
        latency_type: LatencyType,
        context: str = "",
    ):
        self.reducer = reducer
        self.name = name
        self.latency_type = latency_type
        self.context = context
        self.start_time: float = 0
        self.measurement: Optional[LatencyMeasurement] = None

    def __enter__(self) -> _LatencyTimer:
        self.start_time = time.time()
        return self

    def __exit__(self, *args) -> None:
        duration_ms = (time.time() - self.start_time) * 1000
        self.measurement = self.reducer.measure(
            self.name, self.latency_type, duration_ms, self.context
        )
