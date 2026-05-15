"""
P5 — Platform Health Model.

Computes a runtime health score based on multiple health factors.

Health factors:
- Validation stability (validation pass rate)
- Rollback frequency (how often tasks roll back)
- Workflow failures (failed workflow executions)
- Lock contention (lock wait time / conflicts)
- Cache invalidation storms (mass invalidation events)
- Retrieval overload (retrieval time exceeding budget)
- Event recursion (event chain depth)
- Subsystem instability (error rate per subsystem)

Health score: STABLE → DEGRADED → UNSTABLE → CRITICAL
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from collections import defaultdict


class HealthStatus(Enum):
    STABLE = "stable"
    DEGRADED = "degraded"
    UNSTABLE = "unstable"
    CRITICAL = "critical"


@dataclass
class HealthFactor:
    """A single health factor measurement."""
    name: str
    value: float  # 0.0 (worst) to 1.0 (best)
    weight: float = 1.0  # importance weight
    status: HealthStatus = HealthStatus.STABLE
    message: str = ""


@dataclass
class HealthReport:
    """Complete platform health report."""
    overall_status: HealthStatus
    overall_score: float  # 0.0 to 1.0
    factors: List[HealthFactor]
    recommendations: List[str]
    timestamp: str = ""


class PlatformHealthModel:
    """
    Computes platform health score from multiple factors.

    Scoring:
    - Each factor has a value (0=worst, 1=best) and weight.
    - Overall score = weighted average of all factors.
    - Status thresholds:
      STABLE:   score >= 0.8
      DEGRADED: score >= 0.6
      UNSTABLE: score >= 0.4
      CRITICAL: score < 0.4
    """

    # Thresholds for individual factors
    FACTOR_THRESHOLDS = {
        'warning': 0.7,   # below this = WARNING for the factor
        'critical': 0.4,  # below this = CRITICAL for the factor
    }

    # Overall status thresholds
    STATUS_THRESHOLDS = {
        HealthStatus.STABLE: 0.8,
        HealthStatus.DEGRADED: 0.6,
        HealthStatus.UNSTABLE: 0.4,
    }

    def __init__(self):
        self._factor_history: Dict[str, List[float]] = defaultdict(list)
        self._max_history = 100

    def record_factor(self, name: str, value: float) -> None:
        """Record a health factor measurement."""
        history = self._factor_history[name]
        history.append(value)
        if len(history) > self._max_history:
            history.pop(0)

    def compute_health(self, factors: Optional[Dict[str, float]] = None) -> HealthReport:
        """
        Compute overall platform health.

        Args:
            factors: Dict of factor_name -> value (0=worst, 1=best).
                     If None, uses recorded history (latest values).

        Returns:
            HealthReport with overall status and per-factor breakdown.
        """
        if factors is None:
            factors = {}
            for name, history in self._factor_history.items():
                if history:
                    factors[name] = history[-1]

        # Default factor weights
        weights = {
            'validation_stability': 1.5,
            'rollback_frequency': 1.2,
            'workflow_failures': 1.3,
            'lock_contention': 1.0,
            'cache_invalidation': 0.8,
            'retrieval_overload': 0.9,
            'event_recursion': 1.1,
            'subsystem_stability': 1.4,
        }

        health_factors: List[HealthFactor] = []
        total_weight = 0.0
        weighted_sum = 0.0

        for name, value in factors.items():
            weight = weights.get(name, 1.0)

            # Determine factor status
            if value < self.FACTOR_THRESHOLDS['critical']:
                status = HealthStatus.CRITICAL
            elif value < self.FACTOR_THRESHOLDS['warning']:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.STABLE

            factor = HealthFactor(
                name=name,
                value=value,
                weight=weight,
                status=status,
                message=self._factor_message(name, value, status)
            )
            health_factors.append(factor)
            weighted_sum += value * weight
            total_weight += weight

        # Compute overall score
        overall_score = weighted_sum / total_weight if total_weight > 0 else 1.0
        overall_score = round(max(0.0, min(1.0, overall_score)), 3)

        # Determine overall status
        if overall_score >= self.STATUS_THRESHOLDS[HealthStatus.STABLE]:
            overall_status = HealthStatus.STABLE
        elif overall_score >= self.STATUS_THRESHOLDS[HealthStatus.DEGRADED]:
            overall_status = HealthStatus.DEGRADED
        elif overall_score >= self.STATUS_THRESHOLDS[HealthStatus.UNSTABLE]:
            overall_status = HealthStatus.UNSTABLE
        else:
            overall_status = HealthStatus.CRITICAL

        # Generate recommendations
        recommendations = self._generate_recommendations(health_factors, overall_status)

        return HealthReport(
            overall_status=overall_status,
            overall_score=overall_score,
            factors=health_factors,
            recommendations=recommendations,
        )

    def _factor_message(self, name: str, value: float, status: HealthStatus) -> str:
        """Generate a human-readable message for a health factor."""
        pct = round(value * 100, 1)
        messages = {
            'validation_stability': f"Validation pass rate: {pct}%",
            'rollback_frequency': f"Rollback rate: {round((1-value)*100, 1)}%",
            'workflow_failures': f"Workflow failure rate: {round((1-value)*100, 1)}%",
            'lock_contention': f"Lock contention: {round((1-value)*100, 1)}%",
            'cache_invalidation': f"Cache stability: {pct}%",
            'retrieval_overload': f"Retrieval performance: {pct}%",
            'event_recursion': f"Event system health: {pct}%",
            'subsystem_stability': f"Subsystem stability: {pct}%",
        }
        return messages.get(name, f"{name}: {pct}%")

    def _generate_recommendations(self, factors: List[HealthFactor],
                                   overall: HealthStatus) -> List[str]:
        """Generate actionable recommendations based on health factors."""
        recommendations = []

        for f in factors:
            if f.status == HealthStatus.CRITICAL:
                if f.name == 'validation_stability':
                    recommendations.append("CRITICAL: Validation is failing — check recent changes for syntax/import errors")
                elif f.name == 'rollback_frequency':
                    recommendations.append("CRITICAL: High rollback rate — review task risk assessment and approval gates")
                elif f.name == 'workflow_failures':
                    recommendations.append("CRITICAL: Workflows failing — check workflow definitions and resource availability")
                elif f.name == 'lock_contention':
                    recommendations.append("CRITICAL: Severe lock contention — reduce concurrency or increase timeouts")
                elif f.name == 'event_recursion':
                    recommendations.append("CRITICAL: Event recursion detected — audit event handlers for loops")
                elif f.name == 'subsystem_stability':
                    recommendations.append("CRITICAL: Subsystem errors — check error logs for root cause")
            elif f.status == HealthStatus.DEGRADED:
                if f.name == 'cache_invalidation':
                    recommendations.append("WARNING: Cache invalidation storms — review dependency tracking")
                elif f.name == 'retrieval_overload':
                    recommendations.append("WARNING: Retrieval slow — consider indexing optimization")

        if overall == HealthStatus.STABLE:
            recommendations.append("Platform is stable — no action needed")

        return recommendations

    def get_trend(self, factor_name: str, window: int = 10) -> Optional[float]:
        """
        Get trend for a health factor.
        Returns: positive = improving, negative = degrading, None = no data.
        """
        history = self._factor_history.get(factor_name, [])
        if len(history) < 2:
            return None
        recent = history[-window:]
        if len(recent) < 2:
            return None
        # Simple linear trend: difference between avg of first half and second half
        mid = len(recent) // 2
        first_half = sum(recent[:mid]) / mid
        second_half = sum(recent[mid:]) / (len(recent) - mid)
        return round(second_half - first_half, 4)
