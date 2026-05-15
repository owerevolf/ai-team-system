"""
Lightweight internal event bus for ProjectManager.

No external dependencies. No enterprise patterns.
Just a simple pub/sub for internal state change notifications.
"""

import threading
import time
from typing import Callable, Dict, List, Any
from collections import defaultdict


# Event types — minimal set
FILE_INDEXED = "file_indexed"
FILE_CHANGED = "file_changed"
SYMBOLS_UPDATED = "symbols_updated"
CONTEXT_REQUESTED = "context_requested"
AGENT_TASK_COMPLETED = "agent_task_completed"
INDEX_UPDATED = "index_updated"
SNAPSHOT_CREATED = "snapshot_created"


class EventBus:
    """Simple synchronous pub/sub event bus."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type."""
        with self._lock:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Remove a handler."""
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def emit(self, event_type: str, data: Any = None) -> None:
        """Emit an event synchronously."""
        handlers = []
        with self._lock:
            handlers = list(self._subscribers.get(event_type, []))

        for handler in handlers:
            try:
                handler(event_type, data)
            except Exception:
                # Event handlers must not crash the system
                pass

    def reset(self) -> None:
        """Clear all subscribers."""
        with self._lock:
            self._subscribers.clear()
