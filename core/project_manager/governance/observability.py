"""
P16 — Observability Simplification.

Prevents telemetry overload:
- Signal prioritization
- Anomaly thresholds
- Alert deduplication
- Subsystem dashboards
- Actionable metrics only
"""

import time
import threading
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class SignalPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    NOISE = 4


@dataclass
class Signal:
    """A single telemetry signal."""
    name: str
    value: float
    priority: SignalPriority
    subsystem: str
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    message: str = ""


@dataclass
class AnomalyThreshold:
    """Threshold for anomaly detection."""
    signal_name: str
    warning_threshold: float = 0.0
    critical_threshold: float = 0.0
    direction: str = "above"  # above or below
    cooldown_seconds: float = 60.0
    last_triggered: float = 0.0


@dataclass
class Alert:
    """A deduplicated alert."""
    alert_id: str
    signal_name: str
    severity: str  # warning, critical
    message: str
    first_seen: float
    last_seen: float
    count: int = 1
    acknowledged: bool = False


class ObservabilitySimplification:
    """
    Simplifies observability by prioritizing signals,
    deduplicating alerts, and focusing on actionable metrics.
    """

    def __init__(self):
        self._signals: List[Signal] = []
        self._thresholds: Dict[str, AnomalyThreshold] = {}
        self._alerts: Dict[str, Alert] = {}  # signal_name -> Alert
        self._suppressed_signals: Set[str] = set()
        self._lock = threading.Lock()
        self._max_signals = 50000
        self._dedup_window = 300.0  # 5 minutes

    def record_signal(self, name: str, value: float, priority: SignalPriority,
                      subsystem: str, message: str = "",
                      tags: Optional[Dict[str, str]] = None) -> Optional[Alert]:
        """
        Record a telemetry signal.
        Returns an Alert if the signal triggers an anomaly threshold.
        """
        if name in self._suppressed_signals:
            return None

        signal = Signal(
            name=name, value=value, priority=priority,
            subsystem=subsystem, timestamp=time.time(),
            tags=tags or {}, message=message,
        )

        with self._lock:
            self._signals.append(signal)
            if len(self._signals) > self._max_signals:
                self._signals = self._signals[-self._max_signals:]

        # Check anomaly threshold
        threshold = self._thresholds.get(name)
        if threshold:
            return self._check_threshold(signal, threshold)

        return None

    def set_threshold(self, signal_name: str, warning: float, critical: float,
                      direction: str = "above", cooldown_seconds: float = 60.0) -> None:
        """Set an anomaly threshold for a signal."""
        self._thresholds[signal_name] = AnomalyThreshold(
            signal_name=signal_name,
            warning_threshold=warning,
            critical_threshold=critical,
            direction=direction,
            cooldown_seconds=cooldown_seconds,
        )

    def suppress_signal(self, name: str) -> None:
        """Suppress a signal (mark as noise)."""
        self._suppressed_signals.add(name)

    def unsuppress_signal(self, name: str) -> None:
        """Unsuppress a signal."""
        self._suppressed_signals.discard(name)

    def _check_threshold(self, signal: Signal, threshold: AnomalyThreshold) -> Optional[Alert]:
        """Check if a signal exceeds its threshold."""
        now = time.time()

        # Check cooldown
        if now - threshold.last_triggered < threshold.cooldown_seconds:
            return None

        triggered = False
        severity = "warning"

        if threshold.direction == "above":
            if signal.value >= threshold.critical_threshold:
                triggered = True
                severity = "critical"
            elif signal.value >= threshold.warning_threshold:
                triggered = True
                severity = "warning"
        else:  # below
            if signal.value <= threshold.critical_threshold:
                triggered = True
                severity = "critical"
            elif signal.value <= threshold.warning_threshold:
                triggered = True
                severity = "warning"

        if triggered:
            threshold.last_triggered = now

            # Deduplicate alerts
            existing = self._alerts.get(signal.name)
            if existing and (now - existing.last_seen) < self._dedup_window:
                existing.last_seen = now
                existing.count += 1
                return None  # Suppressed as duplicate

            import uuid
            alert = Alert(
                alert_id=str(uuid.uuid4())[:8],
                signal_name=signal.name,
                severity=severity,
                message=f"{signal.name}={signal.value:.2f} ({severity})",
                first_seen=now,
                last_seen=now,
            )
            self._alerts[signal.name] = alert
            return alert

        return None

    def get_active_alerts(self, severity: Optional[str] = None) -> List[Alert]:
        """Get active (unacknowledged) alerts."""
        alerts = [a for a in self._alerts.values() if not a.acknowledged]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return sorted(alerts, key=lambda a: a.first_seen, reverse=True)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts.values():
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_subsystem_dashboard(self, subsystem: str) -> Dict[str, Any]:
        """Get a dashboard for a specific subsystem."""
        signals = [s for s in self._signals if s.subsystem == subsystem]
        recent = [s for s in signals if time.time() - s.timestamp < 300]  # last 5 min

        by_priority = defaultdict(int)
        for s in recent:
            by_priority[s.priority.name] += 1

        return {
            'subsystem': subsystem,
            'total_signals': len(signals),
            'recent_signals': len(recent),
            'by_priority': dict(by_priority),
            'active_alerts': [
                {'name': a.signal_name, 'severity': a.severity, 'count': a.count}
                for a in self.get_active_alerts()
            ],
        }

    def get_actionable_metrics(self) -> List[Dict[str, Any]]:
        """Get only actionable metrics (CRITICAL and HIGH priority)."""
        now = time.time()
        actionable = []
        for signal in reversed(self._signals[-1000:]):
            if signal.priority in (SignalPriority.CRITICAL, SignalPriority.HIGH):
                if now - signal.timestamp < 3600:  # last hour
                    actionable.append({
                        'name': signal.name,
                        'value': signal.value,
                        'priority': signal.priority.name,
                        'subsystem': signal.subsystem,
                        'message': signal.message,
                        'age_s': round(now - signal.timestamp, 0),
                    })
        return actionable

    def get_stats(self) -> Dict[str, Any]:
        """Get observability statistics."""
        return {
            'total_signals': len(self._signals),
            'suppressed_signals': len(self._suppressed_signals),
            'active_alerts': len([a for a in self._alerts.values() if not a.acknowledged]),
            'thresholds_defined': len(self._thresholds),
        }
