"""
Phase 12, P8: Operational Calm Metrics

Measures psychological sustainability of the runtime:
- interruption density (interruptions per time window)
- alert frequency
- approval pressure (approvals per workflow)
- recovery stress
- workflow turbulence (unexpected state changes)
- explanation overload

Principle: System must not only work — it must remain psychologically sustainable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class CalmDimension(Enum):
    INTERRUPTION_DENSITY = "interruption_density"
    ALERT_FREQUENCY = "alert_frequency"
    APPROVAL_PRESSURE = "approval_pressure"
    RECOVERY_STRESS = "recovery_stress"
    WORKFLOW_TURBULENCE = "workflow_turbulence"
    EXPLANATION_OVERLOAD = "explanation_overload"


class CalmLevel(Enum):
    CALM = 0           # Peaceful — minimal interaction needed
    NORMAL = 1         # Normal operational state
    ELEVATED = 2       # Elevated — more interaction than usual
    HIGH = 3           # High — significant cognitive load
    OVERWHELMING = 4   # Overwhelming — immediate reduction needed


@dataclass
class CalmThresholds:
    """Thresholds for each calm dimension."""
    calm_max: float = 0.0
    normal_max: float = 0.0
    elevated_max: float = 0.0
    high_max: float = 0.0
    # Anything above high_max is OVERWHELMING


@dataclass
class CalmReading:
    """A single calm measurement."""
    dimension: CalmDimension
    value: float
    timestamp: float = field(default_factory=time.time)
    context: str = ""


@dataclass
class CalmReport:
    """Complete calm assessment."""
    overall_level: CalmLevel = CalmLevel.CALM
    readings: list[CalmReading] = field(default_factory=list)
    dimension_levels: dict[str, CalmLevel] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# Default thresholds — calibrated for sustainable daily use
DEFAULT_THRESHOLDS: dict[CalmDimension, CalmThresholds] = {
    CalmDimension.INTERRUPTION_DENSITY: CalmThresholds(
        calm_max=2, normal_max=5, elevated_max=10, high_max=20
    ),
    CalmDimension.ALERT_FREQUENCY: CalmThresholds(
        calm_max=1, normal_max=3, elevated_max=7, high_max=15
    ),
    CalmDimension.APPROVAL_PRESSURE: CalmThresholds(
        calm_max=1, normal_max=3, elevated_max=6, high_max=10
    ),
    CalmDimension.RECOVERY_STRESS: CalmThresholds(
        calm_max=0, normal_max=1, elevated_max=3, high_max=5
    ),
    CalmDimension.WORKFLOW_TURBULENCE: CalmThresholds(
        calm_max=1, normal_max=3, elevated_max=7, high_max=12
    ),
    CalmDimension.EXPLANATION_OVERLOAD: CalmThresholds(
        calm_max=1, normal_max=3, elevated_max=6, high_max=10
    ),
}


class OperationalCalmMetrics:
    """
    Measures and tracks operational calm across all dimensions.
    Provides recommendations for reducing cognitive pressure.
    """

    def __init__(
        self,
        thresholds: Optional[dict[CalmDimension, CalmThresholds]] = None,
        window_seconds: float = 300.0,  # 5-minute rolling window
    ) -> None:
        self._thresholds = thresholds or DEFAULT_THRESHOLDS
        self._window_seconds = window_seconds
        self._readings: list[CalmReading] = []

    def record(self, dimension: CalmDimension, value: float, context: str = "") -> CalmReading:
        """Record a calm measurement."""
        reading = CalmReading(
            dimension=dimension,
            value=value,
            context=context,
        )
        self._readings.append(reading)
        return reading

    def increment(self, dimension: CalmDimension, context: str = "") -> CalmReading:
        """Increment a counter-type dimension."""
        current = self._get_window_count(dimension)
        return self.record(dimension, current + 1, context)

    def _get_window_count(self, dimension: CalmDimension) -> float:
        """Get count of readings in the current time window."""
        cutoff = time.time() - self._window_seconds
        return sum(
            1 for r in self._readings
            if r.dimension == dimension and r.timestamp >= cutoff
        )

    def _get_window_average(self, dimension: CalmDimension) -> float:
        """Get average value in the current time window."""
        cutoff = time.time() - self._window_seconds
        values = [
            r.value for r in self._readings
            if r.dimension == dimension and r.timestamp >= cutoff
        ]
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _assess_dimension(self, dimension: CalmDimension, value: float) -> CalmLevel:
        """Assess calm level for a single dimension."""
        thresholds = self._thresholds.get(dimension)
        if not thresholds:
            return CalmLevel.NORMAL

        if value <= thresholds.calm_max:
            return CalmLevel.CALM
        elif value <= thresholds.normal_max:
            return CalmLevel.NORMAL
        elif value <= thresholds.elevated_max:
            return CalmLevel.ELEVATED
        elif value <= thresholds.high_max:
            return CalmLevel.HIGH
        else:
            return CalmLevel.OVERWHELMING

    def assess(self) -> CalmReport:
        """Generate complete calm assessment."""
        report = CalmReport()
        report.readings = list(self._readings)

        max_level = CalmLevel.CALM

        for dimension in CalmDimension:
            value = self._get_window_average(dimension)
            level = self._assess_dimension(dimension, value)
            report.dimension_levels[dimension.value] = level

            if level.value > max_level.value:
                max_level = level

        report.overall_level = max_level
        report.recommendations = self._generate_recommendations(report)
        return report

    def _generate_recommendations(self, report: CalmReport) -> list[str]:
        """Generate recommendations based on calm assessment."""
        recommendations: list[str] = []

        for dim_name, level in report.dimension_levels.items():
            if level == CalmLevel.OVERWHELMING:
                recommendations.append(
                    f"CRITICAL: {dim_name} is overwhelming — immediate reduction required"
                )
            elif level == CalmLevel.HIGH:
                recommendations.append(
                    f"WARNING: {dim_name} is high — consider reducing interaction frequency"
                )
            elif level == CalmLevel.ELEVATED:
                recommendations.append(
                    f"NOTICE: {dim_name} is elevated — monitor for further increase"
                )

        if not recommendations:
            recommendations.append("All dimensions within calm parameters")

        return recommendations

    def get_dimension_trend(self, dimension: CalmDimension, buckets: int = 5) -> list[float]:
        """Get trend for a dimension over time buckets."""
        if not self._readings:
            return []

        now = time.time()
        bucket_size = self._window_seconds / buckets
        counts: list[float] = [0.0] * buckets

        for r in self._readings:
            if r.dimension == dimension:
                age = now - r.timestamp
                if age <= self._window_seconds:
                    bucket = int(age / bucket_size)
                    bucket = min(bucket, buckets - 1)
                    counts[buckets - 1 - bucket] += r.value

        return counts

    def clear_history(self) -> None:
        """Clear all historical readings."""
        self._readings.clear()
