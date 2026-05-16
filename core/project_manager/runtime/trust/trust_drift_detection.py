"""
P5 — Trust Drift Detection (Phase 11)

Monitors signs that user is losing trust in runtime:
- Blind approvals (clicking through without reading)
- Constantly revealing hidden items
- Ignoring explanations
- Avoiding runtime recovery
- Escalating manual bypass

Key principle: trust degradation is a silent failure. Detect it early.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class TrustDriftType(Enum):
    BLIND_APPROVAL = "blind_approval"
    SUPPRESSION_DISTRUST = "suppression_distrust"
    EXPLANATION_REJECTION = "explanation_rejection"
    RECOVERY_AVOIDANCE = "recovery_avoidance"
    MANUAL_BYPASS_ESCALATION = "manual_bypass_escalation"
    GOVERNANCE_FATIGUE = "governance_fatigue"


class TrustDriftSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TrustDriftEvent:
    """A single trust drift indicator."""
    drift_type: TrustDriftType
    severity: TrustDriftSeverity
    description: str
    timestamp: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass
class TrustDriftThreshold:
    """Thresholds for detecting trust drift."""
    # Blind approval: approval time < threshold seconds
    blind_approval_seconds: float = 2.0
    # Suppression distrust: reveal rate > threshold
    reveal_rate_threshold: float = 0.7
    # Explanation rejection: skip rate > threshold
    explanation_skip_threshold: float = 0.8
    # Recovery avoidance: manual fix rate > threshold
    manual_fix_threshold: float = 0.6
    # Manual bypass: bypass count in window
    bypass_count_threshold: int = 5
    bypass_window_seconds: float = 300.0
    # Governance fatigue: approval count with avg time < threshold
    fatigue_approval_count: int = 10
    fatigue_avg_time_seconds: float = 1.5


class TrustDriftDetector:
    """
    Detects trust drift — when user starts losing confidence in runtime.

    Usage:
        detector = TrustDriftDetector()
        detector.record_approval(decision_time_seconds=0.5)
        detector.record_reveal_hidden()
        events = detector.get_drift_events()
        summary = detector.get_trust_summary()
    """

    def __init__(self, thresholds: Optional[TrustDriftThreshold] = None) -> None:
        self._thresholds = thresholds or TrustDriftThreshold()
        self._drift_events: list[TrustDriftEvent] = []
        # Tracking counters
        self._approval_count = 0
        self._approval_times: list[float] = []
        self._reveal_count = 0
        self._reveal_total = 0
        self._explanation_skip_count = 0
        self._explanation_total = 0
        self._manual_fix_count = 0
        self._recovery_total = 0
        self._bypass_timestamps: list[float] = []

    def record_approval(self, decision_time_seconds: float) -> None:
        """Record an approval decision."""
        self._approval_count += 1
        self._approval_times.append(decision_time_seconds)

        if decision_time_seconds < self._thresholds.blind_approval_seconds:
            self._add_drift(TrustDriftType.BLIND_APPROVAL, TrustDriftSeverity.LOW,
                            f"Approval in {decision_time_seconds:.1f}s (threshold: {self._thresholds.blind_approval_seconds}s)",
                            context={"decision_time": decision_time_seconds})

        # Check governance fatigue
        if self._approval_count >= self._thresholds.fatigue_approval_count:
            recent = self._approval_times[-self._thresholds.fatigue_approval_count:]
            avg_time = sum(recent) / len(recent)
            if avg_time < self._thresholds.fatigue_avg_time_seconds:
                self._add_drift(TrustDriftType.GOVERNANCE_FATIGUE, TrustDriftSeverity.MEDIUM,
                                f"Governance fatigue: {self._approval_count} approvals, avg {avg_time:.1f}s",
                                context={"avg_time": avg_time, "count": self._approval_count})

    def record_reveal_hidden(self, total_hidden: int = 1) -> None:
        """Record user revealing a hidden/suppressed item."""
        self._reveal_count += 1
        self._reveal_total += max(total_hidden, 1)

        if self._reveal_total > 0:
            rate = self._reveal_count / self._reveal_total
            if rate > self._thresholds.reveal_rate_threshold:
                self._add_drift(TrustDriftType.SUPPRESSION_DISTRUST, TrustDriftSeverity.MEDIUM,
                                f"Reveal rate {rate:.0%} (threshold: {self._thresholds.reveal_rate_threshold:.0%})",
                                context={"reveal_rate": rate})

    def record_explanation_skip(self, total_explanations: int = 1) -> None:
        """Record user skipping/ignoring an explanation."""
        self._explanation_skip_count += 1
        self._explanation_total += max(total_explanations, 1)

        if self._explanation_total > 0:
            rate = self._explanation_skip_count / self._explanation_total
            if rate > self._thresholds.explanation_skip_threshold:
                self._add_drift(TrustDriftType.EXPLANATION_REJECTION, TrustDriftSeverity.MEDIUM,
                                f"Explanation skip rate {rate:.0%}",
                                context={"skip_rate": rate})

    def record_manual_fix(self, total_recovery_opportunities: int = 1) -> None:
        """Record user manually fixing something runtime could have recovered."""
        self._manual_fix_count += 1
        self._recovery_total += max(total_recovery_opportunities, 1)

        if self._recovery_total > 0:
            rate = self._manual_fix_count / self._recovery_total
            if rate > self._thresholds.manual_fix_threshold:
                self._add_drift(TrustDriftType.RECOVERY_AVOIDANCE, TrustDriftSeverity.HIGH,
                                f"Manual fix rate {rate:.0%} — user avoiding runtime recovery",
                                context={"manual_fix_rate": rate})

    def record_manual_bypass(self) -> None:
        """Record user manually bypassing runtime."""
        now = time.time()
        self._bypass_timestamps.append(now)
        # Clean old timestamps
        cutoff = now - self._thresholds.bypass_window_seconds
        self._bypass_timestamps = [t for t in self._bypass_timestamps if t > cutoff]

        if len(self._bypass_timestamps) >= self._thresholds.bypass_count_threshold:
            self._add_drift(TrustDriftType.MANUAL_BYPASS_ESCALATION, TrustDriftSeverity.HIGH,
                            f"{len(self._bypass_timestamps)} manual bypasses in {self._thresholds.bypass_window_seconds:.0f}s",
                            context={"bypass_count": len(self._bypass_timestamps)})

    def get_drift_events(self, min_severity: Optional[TrustDriftSeverity] = None) -> list[TrustDriftEvent]:
        """Get drift events, optionally filtered by minimum severity."""
        if not min_severity:
            return list(self._drift_events)
        severity_order = {s: i for i, s in enumerate(TrustDriftSeverity)}
        min_val = severity_order[min_severity]
        return [e for e in self._drift_events if severity_order[e.severity] >= min_val]

    def get_trust_summary(self) -> dict[str, Any]:
        """Get trust health summary."""
        total_events = len(self._drift_events)
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for e in self._drift_events:
            by_type[e.drift_type.value] = by_type.get(e.drift_type.value, 0) + 1
            by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1

        # Compute trust score (0-100, higher = more trust)
        trust_score = 100
        trust_score -= by_severity.get("low", 0) * 5
        trust_score -= by_severity.get("medium", 0) * 15
        trust_score -= by_severity.get("high", 0) * 25
        trust_score -= by_severity.get("critical", 0) * 40
        trust_score = max(0, trust_score)

        return {
            "trust_score": trust_score,
            "total_drift_events": total_events,
            "by_type": by_type,
            "by_severity": by_severity,
            "approval_count": self._approval_count,
            "reveal_count": self._reveal_count,
            "explanation_skip_count": self._explanation_skip_count,
            "manual_fix_count": self._manual_fix_count,
            "recent_bypass_count": len(self._bypass_timestamps),
            "is_healthy": trust_score >= 70,
            "needs_attention": trust_score < 50,
        }

    def _add_drift(self, drift_type: TrustDriftType, severity: TrustDriftSeverity,
                   description: str, context: Optional[dict[str, Any]] = None) -> None:
        """Add a drift event, avoiding duplicates within short time."""
        # Check for recent duplicate
        now = time.time()
        for event in reversed(self._drift_events):
            if event.drift_type == drift_type and (now - event.timestamp) < 60:
                return  # Skip duplicate within 60 seconds
        self._drift_events.append(TrustDriftEvent(
            drift_type=drift_type,
            severity=severity,
            description=description,
            context=context or {},
        ))
