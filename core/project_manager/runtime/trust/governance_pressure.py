"""
P9 — Governance Pressure Monitoring (Phase 11)

Measures governance pressure on the user:
approval fatigue, interruption frequency, cognitive load spikes,
hidden-event reveal rates, override frequency, trust instability.

Key principle: governance must not become bureaucracy.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class PressureType(Enum):
    APPROVAL_FATIGUE = "approval_fatigue"
    INTERRUPTION_FREQUENCY = "interruption_frequency"
    COGNITIVE_LOAD_SPIKE = "cognitive_load_spike"
    HIDDEN_REVEAL_RATE = "hidden_reveal_rate"
    OVERRIDE_FREQUENCY = "override_frequency"
    TRUST_INSTABILITY = "trust_instability"


class PressureLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PressureReading:
    """A single pressure measurement."""
    pressure_type: PressureType
    level: PressureLevel
    value: float
    threshold: float
    description: str
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "pressure_type": self.pressure_type.value,
            "level": self.level.value,
            "value": self.value,
            "threshold": self.threshold,
            "description": self.description,
            "timestamp": self.timestamp,
        }


@dataclass
class PressureThresholds:
    """Thresholds for governance pressure levels."""
    # Approval fatigue: approvals per hour
    approval_fatigue_moderate: float = 10.0
    approval_fatigue_high: float = 20.0
    approval_fatigue_critical: float = 30.0
    # Interruptions per hour
    interruption_moderate: float = 15.0
    interruption_high: float = 30.0
    interruption_critical: float = 50.0
    # Cognitive load: events per minute
    cognitive_moderate: float = 5.0
    cognitive_high: float = 10.0
    cognitive_critical: float = 20.0
    # Hidden reveal rate (0-1)
    reveal_moderate: float = 0.3
    reveal_high: float = 0.5
    reveal_critical: float = 0.7
    # Override rate (0-1)
    override_moderate: float = 0.2
    override_high: float = 0.4
    override_critical: float = 0.6
    # Trust instability: changes per hour
    trust_moderate: float = 3.0
    trust_high: float = 6.0
    trust_critical: float = 10.0


class GovernancePressureMonitor:
    """
    Monitors governance pressure — ensures governance doesn't become bureaucracy.

    Usage:
        monitor = GovernancePressureMonitor()
        monitor.record_approval()
        monitor.record_interruption()
        pressure = monitor.get_current_pressure()
        recommendations = monitor.get_recommendations()
    """

    def __init__(self, thresholds: Optional[PressureThresholds] = None) -> None:
        self._thresholds = thresholds or PressureThresholds()
        self._readings: list[PressureReading] = []
        # Counters
        self._approval_timestamps: list[float] = []
        self._interruption_timestamps: list[float] = []
        self._event_timestamps: list[float] = []
        self._reveal_count = 0
        self._reveal_total = 0
        self._override_count = 0
        self._override_total = 0
        self._trust_change_timestamps: list[float] = []

    def record_approval(self) -> Optional[PressureReading]:
        """Record an approval. Returns pressure reading if threshold crossed."""
        now = time.time()
        self._approval_timestamps.append(now)
        self._cleanup_old(self._approval_timestamps, 3600)
        return self._check_approval_pressure()

    def record_interruption(self) -> Optional[PressureReading]:
        """Record an interruption. Returns pressure reading if threshold crossed."""
        now = time.time()
        self._interruption_timestamps.append(now)
        self._cleanup_old(self._interruption_timestamps, 3600)
        return self._check_interruption_pressure()

    def record_event(self) -> Optional[PressureReading]:
        """Record a surfaced event. Returns pressure reading if threshold crossed."""
        now = time.time()
        self._event_timestamps.append(now)
        self._cleanup_old(self._event_timestamps, 60)
        return self._check_cognitive_pressure()

    def record_reveal_hidden(self, total_hidden: int = 1) -> Optional[PressureReading]:
        """Record user revealing hidden items."""
        self._reveal_count += 1
        self._reveal_total += max(total_hidden, 1)
        return self._check_reveal_pressure()

    def record_override(self, total_decisions: int = 1) -> Optional[PressureReading]:
        """Record user overriding runtime decision."""
        self._override_count += 1
        self._override_total += max(total_decisions, 1)
        return self._check_override_pressure()

    def record_trust_change(self) -> Optional[PressureReading]:
        """Record a trust-related change."""
        now = time.time()
        self._trust_change_timestamps.append(now)
        self._cleanup_old(self._trust_change_timestamps, 3600)
        return self._check_trust_pressure()

    def get_current_pressure(self) -> dict[str, Any]:
        """Get current governance pressure levels."""
        now = time.time()
        one_hour_ago = now - 3600

        approvals_per_hour = len([t for t in self._approval_timestamps if t > one_hour_ago])
        interruptions_per_hour = len([t for t in self._interruption_timestamps if t > one_hour_ago])
        events_per_minute = len([t for t in self._event_timestamps if t > now - 60])
        reveal_rate = self._reveal_count / max(self._reveal_total, 1)
        override_rate = self._override_count / max(self._override_total, 1)
        trust_changes = len([t for t in self._trust_change_timestamps if t > one_hour_ago])

        return {
            "approvals_per_hour": approvals_per_hour,
            "interruptions_per_hour": interruptions_per_hour,
            "events_per_minute": events_per_minute,
            "reveal_rate": round(reveal_rate, 3),
            "override_rate": round(override_rate, 3),
            "trust_changes_per_hour": trust_changes,
            "overall_level": self._compute_overall_level(
                approvals_per_hour, interruptions_per_hour, events_per_minute,
                reveal_rate, override_rate, trust_changes
            ),
        }

    def get_recommendations(self) -> list[str]:
        """Get recommendations based on current pressure."""
        pressure = self.get_current_pressure()
        recs = []

        if pressure["approvals_per_hour"] > self._thresholds.approval_fatigue_high:
            recs.append("High approval rate — consider increasing auto-apply threshold or batching more aggressively")

        if pressure["interruptions_per_hour"] > self._thresholds.interruption_high:
            recs.append("High interruption rate — enable calm mode or increase batching window")

        if pressure["events_per_minute"] > self._thresholds.cognitive_high:
            recs.append("High event rate — increase compression level or reduce verbosity")

        if pressure["reveal_rate"] > self._thresholds.reveal_high:
            recs.append("High hidden-item reveal rate — user may not trust suppression, increase default visibility")

        if pressure["override_rate"] > self._thresholds.override_high:
            recs.append("High override rate — runtime decisions may not align with user expectations")

        if pressure["trust_changes_per_hour"] > self._thresholds.trust_high:
            recs.append("Trust instability detected — review recent personality or behavior changes")

        if not recs:
            recs.append("Governance pressure is healthy — no action needed")

        return recs

    def get_pressure_readings(self, limit: int = 20) -> list[PressureReading]:
        """Get recent pressure readings."""
        return sorted(self._readings, key=lambda r: r.timestamp, reverse=True)[:limit]

    def _compute_overall_level(self, approvals: int, interruptions: int,
                                events_per_min: float, reveal_rate: float,
                                override_rate: float, trust_changes: int) -> str:
        """Compute overall pressure level."""
        score = 0
        # Approval fatigue
        if approvals > self._thresholds.approval_fatigue_critical: score += 3
        elif approvals > self._thresholds.approval_fatigue_high: score += 2
        elif approvals > self._thresholds.approval_fatigue_moderate: score += 1
        # Interruptions
        if interruptions > self._thresholds.interruption_critical: score += 3
        elif interruptions > self._thresholds.interruption_high: score += 2
        elif interruptions > self._thresholds.interruption_moderate: score += 1
        # Cognitive load
        if events_per_min > self._thresholds.cognitive_critical: score += 3
        elif events_per_min > self._thresholds.cognitive_high: score += 2
        elif events_per_min > self._thresholds.cognitive_moderate: score += 1
        # Reveal rate
        if reveal_rate > self._thresholds.reveal_critical: score += 2
        elif reveal_rate > self._thresholds.reveal_high: score += 1
        # Override rate
        if override_rate > self._thresholds.override_critical: score += 2
        elif override_rate > self._thresholds.override_high: score += 1
        # Trust
        if trust_changes > self._thresholds.trust_critical: score += 2
        elif trust_changes > self._thresholds.trust_high: score += 1

        if score >= 8: return PressureLevel.CRITICAL.value
        if score >= 5: return PressureLevel.HIGH.value
        if score >= 3: return PressureLevel.MODERATE.value
        return PressureLevel.LOW.value

    def _check_approval_pressure(self) -> Optional[PressureReading]:
        count = len(self._approval_timestamps)
        return self._reading_if_threshold(
            PressureType.APPROVAL_FATIGUE, count,
            self._thresholds.approval_fatigue_critical,
            self._thresholds.approval_fatigue_high,
            self._thresholds.approval_fatigue_moderate,
            f"{count} approvals in last hour"
        )

    def _check_interruption_pressure(self) -> Optional[PressureReading]:
        count = len(self._interruption_timestamps)
        return self._reading_if_threshold(
            PressureType.INTERRUPTION_FREQUENCY, count,
            self._thresholds.interruption_critical,
            self._thresholds.interruption_high,
            self._thresholds.interruption_moderate,
            f"{count} interruptions in last hour"
        )

    def _check_cognitive_pressure(self) -> Optional[PressureReading]:
        count = len(self._event_timestamps)
        return self._reading_if_threshold(
            PressureType.COGNITIVE_LOAD_SPIKE, count,
            self._thresholds.cognitive_critical,
            self._thresholds.cognitive_high,
            self._thresholds.cognitive_moderate,
            f"{count} events in last minute"
        )

    def _check_reveal_pressure(self) -> Optional[PressureReading]:
        rate = self._reveal_count / max(self._reveal_total, 1)
        return self._reading_if_threshold(
            PressureType.HIDDEN_REVEAL_RATE, rate,
            self._thresholds.reveal_critical,
            self._thresholds.reveal_high,
            self._thresholds.reveal_moderate,
            f"Reveal rate: {rate:.0%}"
        )

    def _check_override_pressure(self) -> Optional[PressureReading]:
        rate = self._override_count / max(self._override_total, 1)
        return self._reading_if_threshold(
            PressureType.OVERRIDE_FREQUENCY, rate,
            self._thresholds.override_critical,
            self._thresholds.override_high,
            self._thresholds.override_moderate,
            f"Override rate: {rate:.0%}"
        )

    def _check_trust_pressure(self) -> Optional[PressureReading]:
        count = len(self._trust_change_timestamps)
        return self._reading_if_threshold(
            PressureType.TRUST_INSTABILITY, count,
            self._thresholds.trust_critical,
            self._thresholds.trust_high,
            self._thresholds.trust_moderate,
            f"{count} trust changes in last hour"
        )

    def _reading_if_threshold(self, ptype: PressureType, value: float,
                               crit: float, high: float, mod: float,
                               desc: str) -> Optional[PressureReading]:
        if value >= crit:
            reading = PressureReading(ptype, PressureLevel.CRITICAL, value, crit, desc)
        elif value >= high:
            reading = PressureReading(ptype, PressureLevel.HIGH, value, high, desc)
        elif value >= mod:
            reading = PressureReading(ptype, PressureLevel.MODERATE, value, mod, desc)
        else:
            return None
        self._readings.append(reading)
        return reading

    def _cleanup_old(self, timestamps: list[float], window_seconds: float) -> None:
        cutoff = time.time() - window_seconds
        timestamps[:] = [t for t in timestamps if t > cutoff]
