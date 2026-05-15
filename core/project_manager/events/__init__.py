"""
Lightweight internal event bus for ProjectManager.

Features:
- Synchronous pub/sub
- Event deduplication
- Event throttling
- Max depth protection (prevents recursive events)
- Event queue protection
"""

import threading
import time
from typing import Callable, Dict, List, Any, Optional
from collections import defaultdict, deque

from loguru import logger


# Event types
FILE_INDEXED = "file_indexed"
FILE_CHANGED = "file_changed"
FILE_DELETED = "file_deleted"
SYMBOLS_UPDATED = "symbols_updated"
CONTEXT_REQUESTED = "context_requested"
AGENT_TASK_COMPLETED = "agent_task_completed"
INDEX_UPDATED = "index_updated"
INDEX_INCREMENTAL = "index_incremental"
SNAPSHOT_CREATED = "snapshot_created"
GIT_STATE_CHANGED = "git_state_changed"
IMPACT_ANALYSIS = "impact_analysis"


class EventBus:
    """
    Simple synchronous pub/sub event bus with safety features.

    Safety:
    - Max recursion depth (prevents infinite loops)
    - Event deduplication (same event type + data within window)
    - Event throttling (max events per type per second)
    - Handler isolation (one handler crash doesn't affect others)
    """

    DEFAULT_MAX_DEPTH = 5
    DEFAULT_DEDUP_WINDOW = 1.0  # seconds
    DEFAULT_MAX_PER_SECOND = 50  # per event type

    def __init__(
        self,
        max_depth: int = DEFAULT_MAX_DEPTH,
        dedup_window: float = DEFAULT_DEDUP_WINDOW,
        max_per_second: int = DEFAULT_MAX_PER_SECOND,
    ):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
        self._depth = 0
        self._max_depth = max_depth
        self._dedup_window = dedup_window
        self._max_per_second = max_per_second

        # Deduplication cache: event_type -> {(data_hash): timestamp}
        self._recent_events: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Throttle counters: event_type -> deque of timestamps
        self._event_timestamps: Dict[str, deque] = defaultdict(deque)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type."""
        with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Remove a handler."""
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def emit(self, event_type: str, data: Any = None) -> bool:
        """
        Emit an event synchronously.

        Returns True if event was delivered, False if suppressed.
        """
        # Check recursion depth
        if self._depth >= self._max_depth:
            logger.warning(f"EventBus: max depth ({self._max_depth}) reached, suppressing {event_type}")
            return False

        # Check deduplication
        if self._is_duplicate(event_type, data):
            logger.debug(f"EventBus: dedup {event_type}")
            return False

        # Check throttling
        if self._is_throttled(event_type):
            logger.warning(f"EventBus: throttled {event_type}")
            return False

        # Record event
        self._record_event(event_type, data)

        # Deliver
        handlers = []
        with self._lock:
            handlers = list(self._subscribers.get(event_type, []))

        self._depth += 1
        try:
            for handler in handlers:
                try:
                    handler(event_type, data)
                except Exception as e:
                    # Handler crash must not affect other handlers
                    logger.error(f"EventBus handler error for {event_type}: {e}")
        finally:
            self._depth -= 1

        return True

    def reset(self) -> None:
        """Clear all subscribers."""
        with self._lock:
            self._subscribers.clear()
            self._recent_events.clear()
            self._event_timestamps.clear()

    def _is_duplicate(self, event_type: str, data: Any) -> bool:
        """Check if this event is a duplicate within the dedup window."""
        try:
            data_hash = str(hash(str(data)))
        except Exception:
            data_hash = str(data)

        now = time.time()
        recent = self._recent_events[event_type]

        # Clean old entries
        for key in list(recent.keys()):
            if now - recent[key] > self._dedup_window:
                del recent[key]

        if data_hash in recent:
            return True

        return False

    def _is_throttled(self, event_type: str) -> bool:
        """Check if event type is being emitted too fast."""
        now = time.time()
        timestamps = self._event_timestamps[event_type]

        # Remove timestamps older than 1 second
        while timestamps and now - timestamps[0] > 1.0:
            timestamps.popleft()

        if len(timestamps) >= self._max_per_second:
            return True

        return False

    def _record_event(self, event_type: str, data: Any) -> None:
        """Record event for dedup and throttle tracking."""
        try:
            data_hash = str(hash(str(data)))
        except Exception:
            data_hash = str(data)

        now = time.time()
        self._recent_events[event_type][data_hash] = now
        self._event_timestamps[event_type].append(now)
