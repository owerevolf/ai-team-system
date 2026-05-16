"""
Phase 17, P1: Long-Run Runtime Sessions

Multi-day / multi-week runtime session simulation.
Measures degradation, drift, latency growth, state corruption,
trust erosion, cognitive fatigue accumulation.

Principle: Runtime must survive time, not just tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class SessionPhase(Enum):
    STARTUP = "startup"
    ACTIVE_WORK = "active_work"
    IDLE = "idle"
    RECOVERY = "recovery"
    GOVERNANCE = "governance"
    PLUGIN_OPERATION = "plugin_operation"
    SHUTDOWN = "shutdown"


class HealthIndicator(Enum):
    STATE_SIZE = "state_size"              # Growth of runtime state
    LATENCY = "latency"                    # Operation latency
    MEMORY_PRESSURE = "memory_pressure"    # Memory usage trend
    TRUST_SCORE = "trust_score"            # User trust level
    COGNITIVE_LOAD = "cognitive_load"      # Accumulated cognitive pressure
    GOVERNANCE_BACKLOG = "governance_backlog"  # Pending approvals
    ERROR_RATE = "error_rate"              # Errors per operation
    RECOVERY_SUCCESS = "recovery_success"  # Recovery success rate


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class HealthSnapshot:
    """A single health measurement."""
    indicator: HealthIndicator
    value: float
    timestamp: float = field(default_factory=time.time)
    status: HealthStatus = HealthStatus.HEALTHY
    notes: str = ""


@dataclass
class SessionReport:
    """Full long-run session report."""
    session_id: str
    duration_hours: float = 0.0
    snapshots: list[HealthSnapshot] = field(default_factory=list)
    phases_completed: list[SessionPhase] = field(default_factory=list)
    issues_detected: list[str] = field(default_factory=list)
    overall_health: HealthStatus = HealthStatus.HEALTHY

    @property
    def degradation_detected(self) -> bool:
        return any(s.status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.CRITICAL)
                    for s in self.snapshots)

    @property
    def health_trend(self) -> dict[str, list[float]]:
        """Get health trend per indicator."""
        trends: dict[str, list[float]] = {}
        for s in self.snapshots:
            trends.setdefault(s.indicator.value, []).append(s.value)
        return trends


class LongRunSessionSimulator:
    """
    Simulates and tracks long-run runtime sessions.
    Identifies degradation patterns that only appear over time.
    """

    # Thresholds for health degradation
    THRESHOLDS: dict[HealthIndicator, dict] = {
        HealthIndicator.STATE_SIZE: {"warning": 10000, "critical": 50000},
        HealthIndicator.LATENCY: {"warning": 1000, "critical": 5000},  # ms
        HealthIndicator.MEMORY_PRESSURE: {"warning": 0.7, "critical": 0.9},  # ratio
        HealthIndicator.TRUST_SCORE: {"warning": 0.6, "critical": 0.3},  # inverted
        HealthIndicator.COGNITIVE_LOAD: {"warning": 0.6, "critical": 0.8},
        HealthIndicator.GOVERNANCE_BACKLOG: {"warning": 50, "critical": 200},
        HealthIndicator.ERROR_RATE: {"warning": 0.05, "critical": 0.15},
        HealthIndicator.RECOVERY_SUCCESS: {"warning": 0.9, "critical": 0.7},  # inverted
    }

    def __init__(self, session_id: str = "default") -> None:
        self.session_id = session_id
        self._snapshots: list[HealthSnapshot] = []
        self._phases: list[SessionPhase] = []
        self._issues: list[str] = []

    def record_snapshot(self, indicator: HealthIndicator, value: float, notes: str = "") -> HealthSnapshot:
        """Record a health snapshot."""
        thresholds = self.THRESHOLDS.get(indicator, {})
        status = HealthStatus.HEALTHY

        # For inverted indicators (lower is worse)
        inverted = {HealthIndicator.TRUST_SCORE, HealthIndicator.RECOVERY_SUCCESS}

        if indicator in inverted:
            if value < thresholds.get("critical", 0):
                status = HealthStatus.CRITICAL
            elif value < thresholds.get("warning", 0):
                status = HealthStatus.DEGRADED
        else:
            if value > thresholds.get("critical", float("inf")):
                status = HealthStatus.CRITICAL
            elif value > thresholds.get("warning", float("inf")):
                status = HealthStatus.DEGRADED

        snapshot = HealthSnapshot(
            indicator=indicator,
            value=value,
            status=status,
            notes=notes,
        )
        self._snapshots.append(snapshot)

        if status != HealthStatus.HEALTHY:
            self._issues.append(
                f"{indicator.value}: {value} ({status.value}) — {notes}"
            )

        return snapshot

    def record_phase(self, phase: SessionPhase) -> None:
        """Record a session phase completion."""
        self._phases.append(phase)

    def generate_report(self, duration_hours: float = 0.0) -> SessionReport:
        """Generate full session report."""
        # Determine overall health
        statuses = [s.status for s in self._snapshots]
        if HealthStatus.CRITICAL in statuses:
            overall = HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return SessionReport(
            session_id=self.session_id,
            duration_hours=duration_hours,
            snapshots=list(self._snapshots),
            phases_completed=list(self._phases),
            issues_detected=list(self._issues),
            overall_health=overall,
        )

    def simulate_typical_session(self, days: int = 7) -> SessionReport:
        """Simulate a typical multi-day session with realistic patterns."""
        # Day 1: Startup, healthy
        self.record_phase(SessionPhase.STARTUP)
        self.record_snapshot(HealthIndicator.STATE_SIZE, 100, "Initial state")
        self.record_snapshot(HealthIndicator.LATENCY, 50, "Fresh runtime")
        self.record_snapshot(HealthIndicator.TRUST_SCORE, 1.0, "Full trust")
        self.record_snapshot(HealthIndicator.COGNITIVE_LOAD, 0.1, "Fresh start")

        # Day 2-3: Active work, growing state
        self.record_phase(SessionPhase.ACTIVE_WORK)
        self.record_snapshot(HealthIndicator.STATE_SIZE, 5000, "After 2 days of work")
        self.record_snapshot(HealthIndicator.LATENCY, 200, "Growing state impact")
        self.record_snapshot(HealthIndicator.GOVERNANCE_BACKLOG, 20, "Accumulating approvals")

        # Day 4-5: Plugin usage, potential issues
        self.record_phase(SessionPhase.PLUGIN_OPERATION)
        self.record_snapshot(HealthIndicator.STATE_SIZE, 15000, "Plugin state accumulation")
        self.record_snapshot(HealthIndicator.ERROR_RATE, 0.03, "Plugin errors")
        self.record_snapshot(HealthIndicator.COGNITIVE_LOAD, 0.5, "Accumulated fatigue")

        # Day 6: Recovery needed
        self.record_phase(SessionPhase.RECOVERY)
        self.record_snapshot(HealthIndicator.RECOVERY_SUCCESS, 0.95, "Recovery mostly successful")
        self.record_snapshot(HealthIndicator.TRUST_SCORE, 0.8, "Slight trust erosion")

        # Day 7: Governance catch-up
        self.record_phase(SessionPhase.GOVERNANCE)
        self.record_snapshot(HealthIndicator.GOVERNANCE_BACKLOG, 80, "Backlog accumulated")
        self.record_snapshot(HealthIndicator.COGNITIVE_LOAD, 0.7, "Governance fatigue")

        return self.generate_report(duration_hours=days * 24)

    @property
    def total_snapshots(self) -> int:
        return len(self._snapshots)
