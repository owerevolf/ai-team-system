"""
P20 — Long-Run Stability.

Tests for runtime decay over time:
- Memory leak detection
- Stale cache detection
- Event buildup detection
- Performance degradation tracking
- Long-session stability
"""

import time
import threading
from typing import Dict, List, Any, Optional
from collections import deque
from dataclasses import dataclass, field


@dataclass
class StabilitySnapshot:
    """A point-in-time stability measurement."""
    timestamp: float
    memory_items: int  # number of tracked items in memory
    cache_entries: int
    event_queue_depth: int
    active_tasks: int
    avg_task_duration_ms: float
    error_rate: float  # errors per minute


class LongRunStability:
    """
    Monitors long-run stability of the platform.
    Detects decay over time.
    """

    def __init__(self, max_snapshots: int = 1000):
        self._snapshots: deque = deque(maxlen=max_snapshots)
        self._start_time = time.time()
        self._error_count = 0
        self._operation_count = 0
        self._lock = threading.Lock()

    def take_snapshot(self, memory_items: int = 0, cache_entries: int = 0,
                      event_queue_depth: int = 0, active_tasks: int = 0,
                      avg_task_duration_ms: float = 0.0) -> StabilitySnapshot:
        """Take a stability snapshot."""
        with self._lock:
            elapsed = time.time() - self._start_time
            error_rate = (self._error_count / (elapsed / 60)) if elapsed > 0 else 0.0

            snapshot = StabilitySnapshot(
                timestamp=time.time(),
                memory_items=memory_items,
                cache_entries=cache_entries,
                event_queue_depth=event_queue_depth,
                active_tasks=active_tasks,
                avg_task_duration_ms=avg_task_duration_ms,
                error_rate=round(error_rate, 2),
            )
            self._snapshots.append(snapshot)
            return snapshot

    def record_operation(self, success: bool = True) -> None:
        """Record an operation for error rate tracking."""
        with self._lock:
            self._operation_count += 1
            if not success:
                self._error_count += 1

    def detect_memory_leak(self, window: int = 10) -> Optional[Dict[str, Any]]:
        """
        Detect potential memory leak by checking if memory_items
        is consistently growing.
        """
        if len(self._snapshots) < window * 2:
            return None

        recent = list(self._snapshots)[-window * 2:]
        first_half = recent[:window]
        second_half = recent[window:]

        avg_first = sum(s.memory_items for s in first_half) / window
        avg_second = sum(s.memory_items for s in second_half) / window

        if avg_second > avg_first * 1.2 and avg_second - avg_first > 10:
            return {
                'detected': True,
                'growth_rate': round((avg_second - avg_first) / window, 2),
                'first_half_avg': round(avg_first, 1),
                'second_half_avg': round(avg_second, 1),
                'message': f"Memory growing: {avg_first:.0f} -> {avg_second:.0f} items",
            }

        return {'detected': False}

    def detect_stale_cache(self, max_cache_age_seconds: float = 3600) -> Optional[Dict[str, Any]]:
        """Detect if cache has stale entries."""
        if not self._snapshots:
            return None

        latest = self._snapshots[-1]
        if latest.cache_entries > 0:
            # Check if cache has been growing without bound
            if len(self._snapshots) >= 5:
                recent = list(self._snapshots)[-5:]
                cache_growing = all(
                    recent[i].cache_entries <= recent[i + 1].cache_entries
                    for i in range(len(recent) - 1)
                )
                if cache_growing and latest.cache_entries > 100:
                    return {
                        'detected': True,
                        'cache_entries': latest.cache_entries,
                        'message': f"Cache monotonically growing: {latest.cache_entries} entries",
                    }

        return {'detected': False}

    def detect_event_buildup(self, window: int = 10) -> Optional[Dict[str, Any]]:
        """Detect if events are building up (not being processed)."""
        if len(self._snapshots) < window:
            return None

        recent = list(self._snapshots)[-window:]
        depths = [s.event_queue_depth for s in recent]

        if all(d > 0 for d in depths) and depths[-1] > depths[0] * 2:
            return {
                'detected': True,
                'initial_depth': depths[0],
                'current_depth': depths[-1],
                'message': f"Event queue building up: {depths[0]} -> {depths[-1]}",
            }

        return {'detected': False}

    def detect_performance_degradation(self, window: int = 10) -> Optional[Dict[str, Any]]:
        """Detect if performance is degrading over time."""
        if len(self._snapshots) < window * 2:
            return None

        recent = list(self._snapshots)[-window * 2:]
        first_half = recent[:window]
        second_half = recent[window:]

        avg_first = sum(s.avg_task_duration_ms for s in first_half) / window
        avg_second = sum(s.avg_task_duration_ms for s in second_half) / window

        if avg_second > avg_first * 2 and avg_second > 100:
            return {
                'detected': True,
                'first_half_avg_ms': round(avg_first, 1),
                'second_half_avg_ms': round(avg_second, 1),
                'degradation_factor': round(avg_second / avg_first, 1) if avg_first > 0 else float('inf'),
                'message': f"Performance degrading: {avg_first:.0f}ms -> {avg_second:.0f}ms",
            }

        return {'detected': False}

    def get_stability_report(self) -> Dict[str, Any]:
        """Get a full stability report."""
        if not self._snapshots:
            return {'status': 'no_data'}

        latest = self._snapshots[-1]
        uptime = time.time() - self._start_time

        leak = self.detect_memory_leak()
        stale = self.detect_stale_cache()
        buildup = self.detect_event_buildup()
        perf = self.detect_performance_degradation()

        issues = []
        for check in [leak, stale, buildup, perf]:
            if check and check.get('detected'):
                issues.append(check['message'])

        return {
            'uptime_seconds': round(uptime, 0),
            'total_snapshots': len(self._snapshots),
            'total_operations': self._operation_count,
            'total_errors': self._error_count,
            'error_rate_per_min': latest.error_rate,
            'current_memory_items': latest.memory_items,
            'current_cache_entries': latest.cache_entries,
            'current_event_depth': latest.event_queue_depth,
            'current_active_tasks': latest.active_tasks,
            'issues': issues,
            'is_stable': len(issues) == 0,
        }
