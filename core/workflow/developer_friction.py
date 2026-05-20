"""
developer_friction.py — Developer Friction Observatory.

Purpose: Find what annoys the developer.
Main threat is NOT AI failure — it's developer exhaustion.

Tracks:
- excessive clicks
- repeated approvals
- repeated context loading
- noisy explanations
- confusing workflows
- excessive orchestration depth
- unnecessary agent switching
- dead-end UX flows
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class FrictionEvent:
    """A single friction event."""
    event_type: str = ""  # click, approval, context_load, explanation, orchestration, agent_switch, dead_end
    description: str = ""
    severity: str = "low"  # low, medium, high, critical
    timestamp: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FrictionReport:
    """Aggregated friction report."""
    session_id: str = ""
    total_events: int = 0
    friction_score: float = 0.0  # 0.0 to 10.0, higher = more friction
    interruption_rate: float = 0.0  # interruptions per minute
    orchestration_overhead: float = 0.0  # percentage of time in orchestration
    cognitive_switch_count: int = 0
    unnecessary_operations: int = 0
    top_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class DeveloperFriction:
    """
    Tracks and analyzes developer friction.
    Goal: minimize friction, maximize flow.
    """

    # Friction weights per event type
    FRICTION_WEIGHTS = {
        "click": 0.1,
        "approval": 0.3,
        "context_load": 0.2,
        "explanation": 0.15,
        "orchestration": 0.25,
        "agent_switch": 0.4,
        "dead_end": 0.5,
    }

    # Thresholds
    HIGH_FRICTION_THRESHOLD = 5.0
    APPROVAL_FATIGUE_THRESHOLD = 5  # approvals per session
    CONTEXT_RELOAD_THRESHOLD = 3  # reloads per task

    def __init__(self):
        self._events: List[FrictionEvent] = []
        self._session_start: float = 0.0
        self._lock = threading.Lock()

    def start_session(self, session_id: str = "") -> None:
        """Start tracking a session."""
        with self._lock:
            self._events.clear()
            self._session_start = time.time()

    def record_event(self, event_type: str, description: str = "",
                     severity: str = "low", context: Optional[Dict] = None) -> None:
        """Record a friction event."""
        event = FrictionEvent(
            event_type=event_type,
            description=description,
            severity=severity,
            timestamp=time.time(),
            context=context or {},
        )
        with self._lock:
            self._events.append(event)

        if severity in ("high", "critical"):
            logger.warning(f"Friction: [{severity}] {event_type} — {description}")

    def record_click(self, description: str = "") -> None:
        """Record an unnecessary click."""
        self.record_event("click", description, "low")

    def record_approval(self, description: str = "") -> None:
        """Record an approval request."""
        self.record_event("approval", description, "medium")

    def record_context_load(self, description: str = "") -> None:
        """Record a context reload."""
        self.record_event("context_load", description, "low")

    def record_explanation(self, description: str = "", verbose: bool = False) -> None:
        """Record a noisy explanation."""
        severity = "medium" if verbose else "low"
        self.record_event("explanation", description, severity)

    def record_orchestration(self, description: str = "", depth: int = 1) -> None:
        """Record orchestration overhead."""
        severity = "high" if depth > 3 else "medium" if depth > 1 else "low"
        self.record_event("orchestration", description, severity, {"depth": depth})

    def record_agent_switch(self, description: str = "") -> None:
        """Record an agent switch."""
        self.record_event("agent_switch", description, "medium")

    def record_dead_end(self, description: str = "") -> None:
        """Record a dead-end UX flow."""
        self.record_event("dead_end", description, "high")

    def get_report(self, session_id: str = "") -> FrictionReport:
        """Generate a friction report for the current session."""
        with self._lock:
            events = list(self._events)

        if not events:
            return FrictionReport(session_id=session_id)

        # Calculate metrics
        duration = max(1.0, time.time() - self._session_start)
        friction_score = sum(
            self.FRICTION_WEIGHTS.get(e.event_type, 0.1) * (1 if e.severity == "low" else 2 if e.severity == "medium" else 3)
            for e in events
        )

        interruption_rate = len([e for e in events if e.severity in ("high", "critical")]) / (duration / 60)
        orchestration_events = [e for e in events if e.event_type == "orchestration"]
        orchestration_overhead = len(orchestration_events) / max(1, len(events))
        cognitive_switch_count = len([e for e in events if e.event_type == "agent_switch"])
        unnecessary_operations = len([e for e in events if e.event_type in ("click", "dead_end")])

        # Top issues
        issue_counts: Dict[str, int] = {}
        for e in events:
            if e.severity in ("high", "critical"):
                issue_counts[e.event_type] = issue_counts.get(e.event_type, 0) + 1

        top_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_issues = [f"{k}: {v} occurrences" for k, v in top_issues]

        # Recommendations
        recommendations = []
        approval_count = len([e for e in events if e.event_type == "approval"])
        if approval_count > self.APPROVAL_FATIGUE_THRESHOLD:
            recommendations.append(f"Reduce approvals: {approval_count} in one session (threshold: {self.APPROVAL_FATIGUE_THRESHOLD})")

        context_reloads = len([e for e in events if e.event_type == "context_load"])
        if context_reloads > self.CONTEXT_RELOAD_THRESHOLD:
            recommendations.append(f"Reduce context reloads: {context_reloads} (threshold: {self.CONTEXT_RELOAD_THRESHOLD})")

        if cognitive_switch_count > 3:
            recommendations.append(f"Reduce agent switching: {cognitive_switch_count} switches")

        if friction_score > self.HIGH_FRICTION_THRESHOLD:
            recommendations.append(f"High friction detected: {friction_score:.1f}/10 — review workflow")

        return FrictionReport(
            session_id=session_id,
            total_events=len(events),
            friction_score=round(friction_score, 2),
            interruption_rate=round(interruption_rate, 2),
            orchestration_overhead=round(orchestration_overhead, 2),
            cognitive_switch_count=cognitive_switch_count,
            unnecessary_operations=unnecessary_operations,
            top_issues=top_issues,
            recommendations=recommendations,
        )

    def is_approval_fatigued(self) -> bool:
        """Check if the developer is suffering from approval fatigue."""
        with self._lock:
            approval_count = sum(1 for e in self._events if e.event_type == "approval")
        return approval_count > self.APPROVAL_FATIGUE_THRESHOLD

    def get_stats(self) -> Dict[str, Any]:
        """Get friction statistics."""
        with self._lock:
            events = list(self._events)

        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for e in events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
            by_severity[e.severity] = by_severity.get(e.severity, 0) + 1

        return {
            "total_events": len(events),
            "by_type": by_type,
            "by_severity": by_severity,
            "session_duration": time.time() - self._session_start if self._session_start > 0 else 0,
        }
