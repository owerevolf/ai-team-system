"""
P7 — Debuggability Layer.

Provides execution traces for every failure.
Every failure must be traceable.

Trace types:
- Execution traces (task execution steps)
- Workflow traces (workflow step execution)
- Validation traces (validation check results)
- Dependency traces (dependency resolution)
- Lock traces (lock acquire/release)
- Retrieval traces (retrieval pipeline stages)
"""

import time
import threading
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class TraceType(Enum):
    EXECUTION = "execution"
    WORKFLOW = "workflow"
    VALIDATION = "validation"
    DEPENDENCY = "dependency"
    LOCK = "lock"
    RETRIEVAL = "retrieval"


class TraceStatus(Enum):
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TraceEntry:
    """A single trace entry."""
    trace_id: str
    trace_type: TraceType
    task_id: str
    operation: str
    status: TraceStatus
    started_at: float
    ended_at: float = 0.0
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    children: List[str] = field(default_factory=list)  # child trace IDs


class DebuggabilityLayer:
    """
    Execution tracing system.
    Every operation can be traced for debugging.
    """

    def __init__(self, max_traces: int = 50000):
        self._traces: Dict[str, TraceEntry] = {}
        self._task_traces: Dict[str, List[str]] = defaultdict(list)  # task_id -> trace_ids
        self._max_traces = max_traces
        self._lock = threading.Lock()
        self._enabled: Dict[TraceType, bool] = {t: True for t in TraceType}

    def set_trace_enabled(self, trace_type: TraceType, enabled: bool) -> None:
        """Enable or disable tracing for a specific type."""
        self._enabled[trace_type] = enabled

    def start_trace(self, trace_type: TraceType, task_id: str, operation: str,
                    details: Optional[Dict[str, Any]] = None,
                    parent_trace_id: str = "") -> str:
        """
        Start a new trace. Returns trace ID.
        """
        if not self._enabled.get(trace_type, True):
            return ""

        trace_id = str(uuid.uuid4())[:12]
        entry = TraceEntry(
            trace_id=trace_id,
            trace_type=trace_type,
            task_id=task_id,
            operation=operation,
            status=TraceStatus.STARTED,
            started_at=time.time(),
            details=details or {},
        )

        with self._lock:
            self._traces[trace_id] = entry
            self._task_traces[task_id].append(trace_id)

            # Link to parent
            if parent_trace_id and parent_trace_id in self._traces:
                self._traces[parent_trace_id].children.append(trace_id)

            # Evict old traces if over limit
            if len(self._traces) > self._max_traces:
                self._evict_oldest()

        return trace_id

    def end_trace(self, trace_id: str, status: TraceStatus = TraceStatus.SUCCESS,
                  error: str = "", details: Optional[Dict[str, Any]] = None) -> None:
        """End a trace."""
        if not trace_id:
            return

        with self._lock:
            entry = self._traces.get(trace_id)
            if entry:
                entry.ended_at = time.time()
                entry.duration_ms = round((entry.ended_at - entry.started_at) * 1000, 2)
                entry.status = status
                if error:
                    entry.error = error
                if details:
                    entry.details.update(details)

    def get_trace(self, trace_id: str) -> Optional[TraceEntry]:
        """Get a trace by ID."""
        return self._traces.get(trace_id)

    def get_task_traces(self, task_id: str,
                        trace_type: Optional[TraceType] = None) -> List[TraceEntry]:
        """Get all traces for a task."""
        trace_ids = self._task_traces.get(task_id, [])
        traces = [self._traces[tid] for tid in trace_ids if tid in self._traces]
        if trace_type:
            traces = [t for t in traces if t.trace_type == trace_type]
        return sorted(traces, key=lambda t: t.started_at)

    def get_failed_traces(self, task_id: Optional[str] = None,
                          limit: int = 50) -> List[TraceEntry]:
        """Get failed traces, optionally filtered by task."""
        traces = [
            t for t in self._traces.values()
            if t.status == TraceStatus.FAILED
        ]
        if task_id:
            traces = [t for t in traces if t.task_id == task_id]
        return sorted(traces, key=lambda t: t.started_at, reverse=True)[:limit]

    def get_trace_tree(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a trace with all its children as a tree.
        Useful for debugging nested operations.
        """
        entry = self._traces.get(trace_id)
        if not entry:
            return None

        return {
            'trace_id': entry.trace_id,
            'type': entry.trace_type.value,
            'operation': entry.operation,
            'status': entry.status.value,
            'duration_ms': entry.duration_ms,
            'error': entry.error,
            'details': entry.details,
            'children': [
                self.get_trace_tree(child_id)
                for child_id in entry.children
                if child_id in self._traces
            ],
        }

    def get_execution_summary(self, task_id: str) -> Dict[str, Any]:
        """Get a summary of all traces for a task."""
        traces = self.get_task_traces(task_id)
        if not traces:
            return {'task_id': task_id, 'traces': 0}

        by_type: Dict[str, List[TraceEntry]] = defaultdict(list)
        for t in traces:
            by_type[t.trace_type.value].append(t)

        total_duration = sum(t.duration_ms for t in traces if t.duration_ms > 0)
        failed = [t for t in traces if t.status == TraceStatus.FAILED]

        return {
            'task_id': task_id,
            'total_traces': len(traces),
            'total_duration_ms': round(total_duration, 2),
            'failed_count': len(failed),
            'by_type': {
                ttype: {
                    'count': len(tlist),
                    'total_ms': round(sum(t.duration_ms for t in tlist), 2),
                    'failed': len([t for t in tlist if t.status == TraceStatus.FAILED]),
                }
                for ttype, tlist in by_type.items()
            },
            'failures': [
                {'operation': t.operation, 'error': t.error, 'duration_ms': t.duration_ms}
                for t in failed
            ],
        }

    def clear_traces(self, task_id: Optional[str] = None) -> int:
        """Clear traces. If task_id given, clear only that task's traces."""
        with self._lock:
            if task_id:
                trace_ids = self._task_traces.pop(task_id, [])
                for tid in trace_ids:
                    self._traces.pop(tid, None)
                return len(trace_ids)
            else:
                count = len(self._traces)
                self._traces.clear()
                self._task_traces.clear()
                return count

    def _evict_oldest(self) -> None:
        """Evict oldest traces when over limit."""
        # Remove oldest 25%
        sorted_traces = sorted(self._traces.items(), key=lambda x: x[1].started_at)
        to_remove = sorted_traces[:max(1, len(sorted_traces) // 4)]
        for tid, _ in to_remove:
            entry = self._traces.pop(tid, None)
            if entry:
                task_traces = self._task_traces.get(entry.task_id)
                if task_traces and tid in task_traces:
                    task_traces.remove(tid)

    def get_stats(self) -> Dict[str, Any]:
        """Get tracing system statistics."""
        with self._lock:
            by_type = defaultdict(int)
            by_status = defaultdict(int)
            for t in self._traces.values():
                by_type[t.trace_type.value] += 1
                by_status[t.status.value] += 1

            return {
                'total_traces': len(self._traces),
                'max_traces': self._max_traces,
                'by_type': dict(by_type),
                'by_status': dict(by_status),
                'enabled': {t.value: v for t, v in self._enabled.items()},
            }
