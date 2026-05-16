"""
Phase 12, P6: Interaction Minimalism Layer

Eliminates unnecessary interaction surface:
- no duplicate confirmations
- no repeated explanations
- no redundant warnings
- no unnecessary state exposure

Principle: Silence is acceptable.
Runtime is not obligated to constantly interact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class InteractionType(Enum):
    CONFIRMATION = "confirmation"
    EXPLANATION = "explanation"
    WARNING = "warning"
    NOTIFICATION = "notification"
    STATE_EXPOSURE = "state_exposure"
    PROMPT = "prompt"


class InteractionPriority(Enum):
    CRITICAL = 0      # Must show — safety or data loss risk
    IMPORTANT = 1     # Should show — significant operational event
    NORMAL = 2        # Can show — routine information
    LOW = 3           # Suppress by default — minor detail
    SILENT = 4        # Never show unless explicitly requested


@dataclass
class InteractionEvent:
    """A single interaction event that runtime wants to present."""
    name: str
    interaction_type: InteractionType
    priority: InteractionPriority
    message: str = ""
    dedup_key: str = ""  # For deduplication
    timestamp: float = field(default_factory=time.time)
    shown: bool = False
    suppressed: bool = False
    suppress_reason: str = ""


@dataclass
class MinimalInteractionPolicy:
    """Policy for minimal interaction."""
    max_confirmations_per_workflow: int = 1
    max_explanations_per_decision: int = 1
    max_warnings_per_session: int = 5
    dedup_window_seconds: float = 30.0
    suppress_low_priority: bool = True
    batch_notifications: bool = True


@dataclass
class InteractionBatch:
    """A batch of interactions that can be shown together."""
    events: list[InteractionEvent] = field(default_factory=list)
    batch_key: str = ""

    @property
    def summary(self) -> str:
        if not self.events:
            return ""
        by_type: dict[str, int] = {}
        for e in self.events:
            by_type[e.interaction_type.value] = by_type.get(e.interaction_type.value, 0) + 1
        parts = [f"{count} {typ}" for typ, count in by_type.items()]
        return f"Batch: {', '.join(parts)}"


class InteractionMinimalismLayer:
    """
    Filters and minimizes runtime-to-user interactions.
    Enforces deduplication, batching, and priority-based suppression.
    """

    def __init__(self, policy: Optional[MinimalInteractionPolicy] = None) -> None:
        self.policy = policy or MinimalInteractionPolicy()
        self._history: list[InteractionEvent] = []
        self._dedup_cache: dict[str, float] = {}  # dedup_key -> last_shown_timestamp
        self._confirmation_count: int = 0
        self._explanation_count: int = 0
        self._warning_count: int = 0

    def request_interaction(self, event: InteractionEvent) -> Optional[InteractionEvent]:
        """
        Request permission to show an interaction.
        Returns the event if it should be shown, None if suppressed.
        """
        # Always allow CRITICAL
        if event.priority == InteractionPriority.CRITICAL:
            return self._approve(event)

        # Suppress SILENT unless explicitly requested
        if event.priority == InteractionPriority.SILENT:
            event.suppressed = True
            event.suppress_reason = "SILENT priority — suppressed by policy"
            self._history.append(event)
            return None

        # Suppress LOW if policy says so
        if event.priority == InteractionPriority.LOW and self.policy.suppress_low_priority:
            event.suppressed = True
            event.suppress_reason = "LOW priority — suppressed by policy"
            self._history.append(event)
            return None

        # Deduplication check
        if event.dedup_key and self._is_duplicate(event):
            event.suppressed = True
            event.suppress_reason = f"Duplicate of recent event (key: {event.dedup_key})"
            self._history.append(event)
            return None

        # Confirmation limit
        if event.interaction_type == InteractionType.CONFIRMATION:
            if self._confirmation_count >= self.policy.max_confirmations_per_workflow:
                event.suppressed = True
                event.suppress_reason = "Confirmation limit reached for this workflow"
                self._history.append(event)
                return None
            self._confirmation_count += 1

        # Explanation limit
        if event.interaction_type == InteractionType.EXPLANATION:
            if self._explanation_count >= self.policy.max_explanations_per_decision:
                event.suppressed = True
                event.suppress_reason = "Explanation limit reached for this decision"
                self._history.append(event)
                return None
            self._explanation_count += 1

        # Warning limit
        if event.interaction_type == InteractionType.WARNING:
            if self._warning_count >= self.policy.max_warnings_per_session:
                event.suppressed = True
                event.suppress_reason = "Warning limit reached for this session"
                self._history.append(event)
                return None
            self._warning_count += 1

        return self._approve(event)

    def _approve(self, event: InteractionEvent) -> InteractionEvent:
        event.shown = True
        if event.dedup_key:
            self._dedup_cache[event.dedup_key] = event.timestamp
        self._history.append(event)
        return event

    def _is_duplicate(self, event: InteractionEvent) -> bool:
        last_shown = self._dedup_cache.get(event.dedup_key)
        if last_shown is None:
            return False
        return (event.timestamp - last_shown) < self.policy.dedup_window_seconds

    def batch_events(self, events: list[InteractionEvent]) -> list[InteractionBatch]:
        """Batch compatible events together."""
        if not self.policy.batch_notifications:
            return [InteractionBatch(events=[e], batch_key=e.name) for e in events]

        batches: dict[str, InteractionBatch] = {}
        for event in events:
            if event.interaction_type in (InteractionType.NOTIFICATION, InteractionType.STATE_EXPOSURE):
                key = event.interaction_type.value
                if key not in batches:
                    batches[key] = InteractionBatch(batch_key=key)
                batches[key].events.append(event)
            else:
                # Non-batchable events get their own batch
                batches[event.name] = InteractionBatch(events=[event], batch_key=event.name)

        return list(batches.values())

    def reset_workflow_counters(self) -> None:
        """Reset per-workflow counters."""
        self._confirmation_count = 0
        self._explanation_count = 0

    def reset_session_counters(self) -> None:
        """Reset per-session counters."""
        self.reset_workflow_counters()
        self._warning_count = 0

    @property
    def suppression_stats(self) -> dict[str, int]:
        stats: dict[str, int] = {"shown": 0, "suppressed": 0}
        for event in self._history:
            if event.shown:
                stats["shown"] += 1
            if event.suppressed:
                stats["suppressed"] += 1
        return stats
