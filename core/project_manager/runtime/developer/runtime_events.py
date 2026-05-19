"""
Runtime Events — structured event system for orchestration.

No print chaos. Only structured events.
All orchestration actions produce events that can be:
- logged
- replayed
- displayed in UI
- used for debugging
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EventType(Enum):
    # Orchestration lifecycle
    ORCHESTRATION_STARTED = "orchestration.started"
    ORCHESTRATION_COMPLETED = "orchestration.completed"
    ORCHESTRATION_FAILED = "orchestration.failed"
    ORCHESTRATION_BLOCKED = "orchestration.blocked"

    # Plan lifecycle
    PLAN_CREATED = "plan.created"
    PLAN_UPDATED = "plan.updated"
    PLAN_APPROVED = "plan.approved"
    PLAN_REJECTED = "plan.rejected"

    # Task lifecycle
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_BLOCKED = "task.blocked"
    TASK_RETRY = "task.retry"

    # Review lifecycle
    REVIEW_STARTED = "review.started"
    REVIEW_PASSED = "review.passed"
    REVIEW_BLOCKED = "review.blocked"
    REVIEW_VIOLATION = "review.violation"

    # Agent lifecycle
    AGENT_ASSIGNED = "agent.assigned"
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"

    # Understanding
    UNDERSTANDING_COMPLETED = "understanding.completed"
    CLARIFICATION_NEEDED = "clarification.needed"

    # System
    WARNING = "system.warning"
    ERROR = "system.error"
    INFO = "system.info"


class EventSeverity(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class RuntimeEvent:
    """A single structured event in the orchestration timeline."""
    event_type: str = ""
    message: str = ""
    severity: str = EventSeverity.INFO.value
    timestamp: str = ""
    event_id: str = ""
    source: str = ""  # which component produced the event
    task_id: str = ""
    agent_id: str = ""
    plan_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())[:8]
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "message": self.message,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "source": self.source,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "plan_id": self.plan_id,
            "data": self.data,
        }


class EventBus:
    """
    Central event bus for orchestration.

    Components produce events. Consumers subscribe to event types.
    All events are stored in timeline for replay/debugging.
    """

    def __init__(self):
        self._timeline: List[RuntimeEvent] = []
        self._subscribers: Dict[str, List[Callable]] = {}
        self._all_subscribers: List[Callable] = []

    def emit(self, event: RuntimeEvent) -> None:
        """Emit an event to all subscribers and store in timeline."""
        self._timeline.append(event)

        # Notify type-specific subscribers
        for callback in self._subscribers.get(event.event_type, []):
            try:
                callback(event)
            except Exception:
                pass

        # Notify global subscribers
        for callback in self._all_subscribers:
            try:
                callback(event)
            except Exception:
                pass

    def emit_simple(self, event_type: EventType, message: str,
                    source: str = "", severity: str = EventSeverity.INFO.value,
                    **kwargs) -> RuntimeEvent:
        """Convenience method to create and emit an event."""
        event = RuntimeEvent(
            event_type=event_type.value,
            message=message,
            severity=severity,
            source=source,
            **kwargs,
        )
        self.emit(event)
        return event

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """Subscribe to a specific event type."""
        key = event_type.value
        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(callback)

    def subscribe_all(self, callback: Callable) -> None:
        """Subscribe to all events."""
        self._all_subscribers.append(callback)

    def get_timeline(self, limit: int = 0) -> List[RuntimeEvent]:
        """Get all events in chronological order."""
        if limit > 0:
            return self._timeline[-limit:]
        return list(self._timeline)

    def get_events_by_type(self, event_type: EventType) -> List[RuntimeEvent]:
        """Get all events of a specific type."""
        return [e for e in self._timeline if e.event_type == event_type.value]

    def get_events_by_severity(self, severity: str) -> List[RuntimeEvent]:
        """Get all events with severity >= given level."""
        levels = ["debug", "info", "warning", "error", "critical"]
        if severity not in levels:
            return []
        min_idx = levels.index(severity)
        return [e for e in self._timeline
                if levels.index(e.severity) >= min_idx]

    def get_last_event(self) -> Optional[RuntimeEvent]:
        return self._timeline[-1] if self._timeline else None

    def clear(self) -> None:
        self._timeline.clear()

    @property
    def event_count(self) -> int:
        return len(self._timeline)
