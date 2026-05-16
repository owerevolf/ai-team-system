"""
P8 — Operational Observability (Phase 9)

Developer-grade observability. NOT enterprise telemetry monster.

Provides:
  - Runtime timeline (what happened)
  - Decision trace (why runtime chose an action)
  - Validation graph (what checks influenced the outcome)
  - Context trace (where context came from)

Key principle: observability helps debugging, not business analytics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class EntryType(Enum):
    RUNTIME_EVENT = "runtime_event"
    DECISION = "decision"
    VALIDATION = "validation"
    CONTEXT = "context"
    ERROR = "error"
    RECOVERY = "recovery"


@dataclass
class TimelineEntry:
    """An entry in the runtime timeline."""
    entry_id: str
    timestamp: float
    entry_type: EntryType
    title: str
    description: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "entry_type": self.entry_type.value,
            "title": self.title,
            "description": self.description,
            "data": self.data,
            "duration_ms": self.duration_ms,
            "success": self.success,
        }


@dataclass
class DecisionTrace:
    """A decision trace: why runtime chose an action."""
    trace_id: str
    timestamp: float
    decision: str
    reason: str
    alternatives_considered: list[str] = field(default_factory=list)
    constraints_applied: list[str] = field(default_factory=list)
    confidence: float = 1.0
    outcome: str = ""          # What actually happened

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "decision": self.decision,
            "reason": self.reason,
            "alternatives_considered": self.alternatives_considered,
            "constraints_applied": self.constraints_applied,
            "confidence": self.confidence,
            "outcome": self.outcome,
        }


class OperationalObservability:
    """
    Developer-grade observability.

    Usage:
        obs = OperationalObservability()

        # Record events
        obs.record_event(EntryType.RUNTIME_EVENT, "Import started", {"files": 150})
        obs.record_decision("Use incremental index", "Only 3 files changed", confidence=0.95)

        # Query
        timeline = obs.get_timeline(limit=20)
        decisions = obs.get_decisions(limit=10)
    """

    def __init__(self, max_entries: int = 5000) -> None:
        self._timeline: list[TimelineEntry] = []
        self._decisions: list[DecisionTrace] = []
        self._max_entries = max_entries

    def record_event(
        self,
        entry_type: EntryType,
        title: str,
        description: str = "",
        data: Optional[dict[str, Any]] = None,
        duration_ms: float = 0.0,
        success: bool = True,
    ) -> TimelineEntry:
        """Record a timeline event."""
        import uuid
        entry = TimelineEntry(
            entry_id=f"tl-{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            entry_type=entry_type,
            title=title,
            description=description,
            data=data or {},
            duration_ms=duration_ms,
            success=success,
        )
        self._timeline.append(entry)
        if len(self._timeline) > self._max_entries:
            self._timeline = self._timeline[-self._max_entries:]
        return entry

    def record_decision(
        self,
        decision: str,
        reason: str,
        alternatives: Optional[list[str]] = None,
        constraints: Optional[list[str]] = None,
        confidence: float = 1.0,
        outcome: str = "",
    ) -> DecisionTrace:
        """Record a decision trace."""
        import uuid
        trace = DecisionTrace(
            trace_id=f"dt-{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            decision=decision,
            reason=reason,
            alternatives_considered=alternatives or [],
            constraints_applied=constraints or [],
            confidence=confidence,
            outcome=outcome,
        )
        self._decisions.append(trace)
        if len(self._decisions) > self._max_entries:
            self._decisions = self._decisions[-self._max_entries:]
        return trace

    def get_timeline(
        self,
        entry_type: Optional[EntryType] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get timeline entries."""
        entries = self._timeline
        if entry_type:
            entries = [e for e in entries if e.entry_type == entry_type]
        return [e.to_dict() for e in entries[-limit:]]

    def get_decisions(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get decision traces."""
        return [d.to_dict() for d in self._decisions[-limit:]]

    def get_summary(self) -> dict[str, Any]:
        """Get observability summary."""
        errors = [e for e in self._timeline if not e.success]
        avg_confidence = (
            sum(d.confidence for d in self._decisions) / len(self._decisions)
            if self._decisions else 0.0
        )
        by_type: dict[str, int] = {}
        for e in self._timeline:
            t = e.entry_type.value
            by_type[t] = by_type.get(t, 0) + 1

        return {
            "total_events": len(self._timeline),
            "total_decisions": len(self._decisions),
            "errors": len(errors),
            "avg_decision_confidence": round(avg_confidence, 3),
            "events_by_type": by_type,
        }
