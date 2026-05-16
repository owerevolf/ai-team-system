"""
Phase 16, P4: Real Contributor Validation

Measures actual contributor experience:
- onboarding completion time
- architecture comprehension
- contribution success rate
- governance confusion points

Principle: Measure real humans, not theoretical ergonomics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ValidationMetric(Enum):
    ONBOARDING_TIME = "onboarding_time"        # Minutes to first contribution
    COMPREHENSION = "comprehension"            # Architecture understanding score
    SUCCESS_RATE = "success_rate"              # PR acceptance rate
    GOVERNANCE_CONFUSION = "governance_confusion"  # Points of confusion
    DISCOVERABILITY = "discoverability"        # How easy to find code/docs


class MetricStatus(Enum):
    MEASURED = "measured"
    ESTIMATED = "estimated"
    NOT_MEASURED = "not_measured"


@dataclass
class ContributorMetric:
    """A single contributor experience metric."""
    metric: ValidationMetric
    status: MetricStatus
    value: Optional[float] = None
    target: Optional[float] = None
    notes: str = ""


@dataclass
class ContributorValidationReport:
    """Full contributor validation report."""
    metrics: list[ContributorMetric] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class RealContributorValidator:
    """
    Measures actual contributor experience.
    Provides data-driven insights for improving onboarding and contribution flow.
    """

    # Baseline estimates based on system complexity
    BASELINE_METRICS: dict[ValidationMetric, dict] = {
        ValidationMetric.ONBOARDING_TIME: {
            "value": 120,  # Estimated 2 hours for core maintainer
            "target": 60,   # Target: 1 hour
        },
        ValidationMetric.COMPREHENSION: {
            "value": 0.6,   # Estimated 60% comprehension after onboarding
            "target": 0.8,  # Target: 80%
        },
        ValidationMetric.SUCCESS_RATE: {
            "value": 0.7,   # Estimated 70% PR acceptance rate
            "target": 0.85, # Target: 85%
        },
        ValidationMetric.GOVERNANCE_CONFUSION: {
            "value": 5,     # Estimated 5 confusion points
            "target": 2,    # Target: 2 or fewer
        },
        ValidationMetric.DISCOVERABILITY: {
            "value": 0.5,   # Estimated 50% discoverability
            "target": 0.8,  # Target: 80%
        },
    }

    def __init__(self) -> None:
        self._metrics: dict[ValidationMetric, ContributorMetric] = {}
        self._register_baselines()

    def _register_baselines(self) -> None:
        """Register baseline metrics."""
        for metric, data in self.BASELINE_METRICS.items():
            self._metrics[metric] = ContributorMetric(
                metric=metric,
                status=MetricStatus.ESTIMATED,
                value=data["value"],
                target=data["target"],
            )

    def record_measurement(self, metric: ValidationMetric, value: float, notes: str = "") -> None:
        """Record an actual measurement."""
        m = self._metrics.get(metric)
        if m:
            m.value = value
            m.status = MetricStatus.MEASURED
            m.notes = notes

    def generate_report(self) -> ContributorValidationReport:
        """Generate validation report."""
        metrics = list(self._metrics.values())
        recommendations: list[str] = []

        for m in metrics:
            if m.value is not None and m.target is not None:
                if m.metric == ValidationMetric.ONBOARDING_TIME:
                    if m.value > m.target * 1.5:
                        recommendations.append(
                            f"Onboarding time ({m.value:.0f} min) is too long — "
                            f"compress to {m.target:.0f} min"
                        )
                elif m.metric == ValidationMetric.COMPREHENSION:
                    if m.value < m.target:
                        recommendations.append(
                            f"Comprehension ({m.value:.0%}) below target ({m.target:.0%}) — "
                            f"improve learning paths"
                        )
                elif m.metric == ValidationMetric.SUCCESS_RATE:
                    if m.value < m.target:
                        recommendations.append(
                            f"PR success rate ({m.value:.0%}) below target ({m.target:.0%}) — "
                            f"improve contribution guides"
                        )
                elif m.metric == ValidationMetric.GOVERNANCE_CONFUSION:
                    if m.value > m.target:
                        recommendations.append(
                            f"Governance confusion ({m.value:.0f} points) above target ({m.target:.0f}) — "
                            f"simplify governance"
                        )
                elif m.metric == ValidationMetric.DISCOVERABILITY:
                    if m.value < m.target:
                        recommendations.append(
                            f"Discoverability ({m.value:.0%}) below target ({m.target:.0%}) — "
                            f"improve code navigation"
                        )

        if not recommendations:
            recommendations.append("All metrics within target ranges")

        return ContributorValidationReport(metrics=metrics, recommendations=recommendations)

    def get_metric(self, metric: ValidationMetric) -> Optional[ContributorMetric]:
        """Get a specific metric."""
        return self._metrics.get(metric)
