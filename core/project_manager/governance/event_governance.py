"""
P10 — Event Governance.

Governs the event system to prevent chaos.

Policies:
- Event budgets (max events per type per second)
- Recursion detection (already in EventBus, extended here)
- Event chain tracing (track event chains)
- Event throttling policies (per-subsystem limits)
- Subsystem event isolation (events don't leak across boundaries)
"""

import time
import threading
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum


class EventPolicy(Enum):
    ALLOW = "allow"
    THROTTLE = "throttle"
    BLOCK = "block"
    ISOLATE = "isolate"  # don't propagate to other subsystems


@dataclass
class EventBudget:
    """Budget for a specific event type."""
    event_type: str
    max_per_second: int = 50
    max_per_minute: int = 1000
    burst_limit: int = 100
    current_second_count: int = 0
    current_minute_count: int = 0
    last_second_reset: float = 0.0
    last_minute_reset: float = 0.0


@dataclass
class EventChain:
    """Tracks a chain of related events."""
    chain_id: str
    root_event: str
    events: List[Dict[str, Any]] = field(default_factory=list)
    started_at: float = 0.0
    max_depth: int = 10
    current_depth: int = 0
    is_circular: bool = False


class EventGovernance:
    """
    Governs event system behavior.
    Prevents event storms, recursion, and cross-subsystem leakage.
    """

    DEFAULT_MAX_PER_SECOND = 50
    DEFAULT_MAX_PER_MINUTE = 1000
    DEFAULT_BURST_LIMIT = 100
    DEFAULT_MAX_CHAIN_DEPTH = 10

    def __init__(self):
        self._budgets: Dict[str, EventBudget] = {}
        self._active_chains: Dict[str, EventChain] = {}
        self._subsystem_events: Dict[str, Set[str]] = defaultdict(set)  # subsystem -> event types
        self._event_subscribers: Dict[str, Set[str]] = defaultdict(set)  # event_type -> subsystems
        self._lock = threading.Lock()
        self._event_counts: Dict[str, deque] = defaultdict(deque)  # event_type -> timestamps
        self._recursion_detection: Dict[str, int] = {}  # event_type -> depth
        self._max_recursion_depth = 5

    def set_budget(self, event_type: str, max_per_second: int = DEFAULT_MAX_PER_SECOND,
                   max_per_minute: int = DEFAULT_MAX_PER_MINUTE,
                   burst_limit: int = DEFAULT_BURST_LIMIT) -> None:
        """Set an event budget."""
        self._budgets[event_type] = EventBudget(
            event_type=event_type,
            max_per_second=max_per_second,
            max_per_minute=max_per_minute,
            burst_limit=burst_limit,
        )

    def register_subsystem_events(self, subsystem: str, event_types: Set[str]) -> None:
        """Register which event types a subsystem is allowed to receive."""
        with self._lock:
            self._subsystem_events[subsystem] = event_types.copy()
            for et in event_types:
                self._event_subscribers[et].add(subsystem)

    def check_event_allowed(self, event_type: str, source_subsystem: str = "",
                            target_subsystem: str = "") -> tuple:
        """
        Check if an event is allowed.

        Returns: (allowed, reason)
        """
        now = time.time()

        # Check budget
        budget = self._budgets.get(event_type)
        if budget:
            # Reset counters if needed
            if now - budget.last_second_reset >= 1.0:
                budget.current_second_count = 0
                budget.last_second_reset = now
            if now - budget.last_minute_reset >= 60.0:
                budget.current_minute_count = 0
                budget.last_minute_reset = now

            budget.current_second_count += 1
            budget.current_minute_count += 1

            if budget.current_second_count > budget.max_per_second:
                return False, f"Event '{event_type}' exceeded per-second budget ({budget.max_per_second}/s)"
            if budget.current_minute_count > budget.max_per_minute:
                return False, f"Event '{event_type}' exceeded per-minute budget ({budget.max_per_minute}/min)"

        # Check recursion
        depth = self._recursion_detection.get(event_type, 0)
        if depth >= self._max_recursion_depth:
            return False, f"Event '{event_type}' recursion depth exceeded ({depth})"

        # Check subsystem isolation
        if target_subsystem and source_subsystem:
            allowed_events = self._subsystem_events.get(target_subsystem, set())
            if allowed_events and event_type not in allowed_events:
                return False, f"Event '{event_type}' not allowed in subsystem '{target_subsystem}'"

        return True, "OK"

    def start_event_chain(self, chain_id: str, root_event: str,
                          max_depth: int = DEFAULT_MAX_CHAIN_DEPTH) -> EventChain:
        """Start tracking an event chain."""
        chain = EventChain(
            chain_id=chain_id,
            root_event=root_event,
            started_at=time.time(),
            max_depth=max_depth,
        )
        self._active_chains[chain_id] = chain
        return chain

    def record_chain_event(self, chain_id: str, event_type: str,
                           data: Any = None) -> tuple:
        """
        Record an event in a chain.
        Returns: (allowed, reason)
        """
        chain = self._active_chains.get(chain_id)
        if not chain:
            return True, "No active chain"

        chain.current_depth += 1

        if chain.current_depth > chain.max_depth:
            chain.is_circular = True
            return False, f"Event chain depth exceeded ({chain.current_depth}/{chain.max_depth})"

        chain.events.append({
            'event_type': event_type,
            'data': str(data)[:200] if data else None,
            'timestamp': time.time(),
            'depth': chain.current_depth,
        })

        return True, "OK"

    def end_event_chain(self, chain_id: str) -> Optional[EventChain]:
        """End an event chain and return the result."""
        chain = self._active_chains.pop(chain_id, None)
        return chain

    def get_chain(self, chain_id: str) -> Optional[EventChain]:
        """Get an active chain."""
        return self._active_chains.get(chain_id)

    def get_event_stats(self) -> Dict[str, Any]:
        """Get event governance statistics."""
        now = time.time()
        stats = {}
        for event_type, timestamps in self._event_counts.items():
            # Count events in last second and minute
            recent_1s = sum(1 for t in timestamps if now - t < 1.0)
            recent_1m = sum(1 for t in timestamps if now - t < 60.0)
            stats[event_type] = {
                'per_second': recent_1s,
                'per_minute': recent_1m,
                'budget': self._budgets[event_type].max_per_second if event_type in self._budgets else 'unlimited',
            }
        return stats

    def get_active_chains(self) -> List[Dict[str, Any]]:
        """Get all active event chains."""
        return [
            {
                'chain_id': c.chain_id,
                'root_event': c.root_event,
                'depth': c.current_depth,
                'max_depth': c.max_depth,
                'event_count': len(c.events),
                'is_circular': c.is_circular,
                'duration_s': round(time.time() - c.started_at, 2),
            }
            for c in self._active_chains.values()
        ]
