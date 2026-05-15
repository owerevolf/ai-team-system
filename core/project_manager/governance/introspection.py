"""
P6 — Runtime Introspection System.

Provides runtime transparency: what's running, what's blocked,
what's degraded, where are the bottlenecks.

PM must be able to answer:
- What is currently executing?
- Where is the bottleneck?
- What is blocked?
- What is degrading?
- Which subsystems are unstable?
- Which workflows are overloaded?
"""

import time
import threading
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


class TaskStatus(Enum):
    RUNNING = "running"
    BLOCKED = "blocked"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RuntimeTask:
    """Snapshot of a running task."""
    task_id: str
    agent: str
    status: TaskStatus
    started_at: float
    resources: List[str]
    workflow: str
    progress_pct: float = 0.0
    last_activity: float = 0.0
    error: str = ""


@dataclass
class Bottleneck:
    """A detected bottleneck."""
    resource: str
    task_id: str
    wait_time_seconds: float
    blocked_tasks: List[str]
    severity: str = "warning"  # warning, critical


@dataclass
class SubsystemStatus:
    """Status of a single subsystem."""
    name: str
    is_healthy: bool
    active_operations: int
    error_count: int
    last_error: str = ""
    avg_response_ms: float = 0.0


class RuntimeIntrospection:
    """
    Runtime introspection layer.
    Provides real-time visibility into platform state.
    """

    def __init__(self):
        self._tasks: Dict[str, RuntimeTask] = {}
        self._subsystems: Dict[str, SubsystemStatus] = {}
        self._lock = threading.RLock()
        self._operation_log: List[Dict[str, Any]] = []
        self._max_log_size = 10000

    # ── Task Tracking ──

    def register_task(self, task_id: str, agent: str, workflow: str,
                      resources: List[str]) -> None:
        """Register a new running task."""
        with self._lock:
            self._tasks[task_id] = RuntimeTask(
                task_id=task_id,
                agent=agent,
                status=TaskStatus.RUNNING,
                started_at=time.time(),
                resources=resources,
                workflow=workflow,
                last_activity=time.time(),
            )

    def update_task(self, task_id: str, status: Optional[TaskStatus] = None,
                    progress: Optional[float] = None, error: str = "") -> None:
        """Update task status."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                if status:
                    task.status = status
                if progress is not None:
                    task.progress_pct = progress
                if error:
                    task.error = error
                task.last_activity = time.time()

    def complete_task(self, task_id: str, success: bool = True) -> None:
        """Mark a task as completed or failed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.progress_pct = 100.0 if success else task.progress_pct
                task.last_activity = time.time()

    def get_running_tasks(self) -> List[RuntimeTask]:
        """Get all currently running tasks."""
        with self._lock:
            return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]

    def get_blocked_tasks(self) -> List[RuntimeTask]:
        """Get all blocked tasks."""
        with self._lock:
            return [t for t in self._tasks.values() if t.status == TaskStatus.BLOCKED]

    # ── Bottleneck Detection ──

    def detect_bottlenecks(self, threshold_seconds: float = 5.0) -> List[Bottleneck]:
        """
        Detect resource bottlenecks.
        A bottleneck is a resource where tasks are waiting too long.
        """
        bottlenecks = []
        with self._lock:
            # Group tasks by resource
            resource_tasks: Dict[str, List[RuntimeTask]] = defaultdict(list)
            for task in self._tasks.values():
                if task.status in (TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.WAITING):
                    for resource in task.resources:
                        resource_tasks[resource].append(task)

            for resource, tasks in resource_tasks.items():
                if len(tasks) > 1:
                    # Multiple tasks competing for same resource
                    now = time.time()
                    oldest = min(tasks, key=lambda t: t.started_at)
                    wait_time = now - oldest.started_at
                    if wait_time > threshold_seconds:
                        blocked = [t.task_id for t in tasks if t.status == TaskStatus.BLOCKED]
                        bottlenecks.append(Bottleneck(
                            resource=resource,
                            task_id=oldest.task_id,
                            wait_time_seconds=round(wait_time, 1),
                            blocked_tasks=blocked,
                            severity="critical" if wait_time > threshold_seconds * 3 else "warning"
                        ))

        return bottlenecks

    # ── Subsystem Status ──

    def register_subsystem(self, name: str) -> None:
        """Register a subsystem for monitoring."""
        with self._lock:
            self._subsystems[name] = SubsystemStatus(
                name=name,
                is_healthy=True,
                active_operations=0,
                error_count=0,
            )

    def record_subsystem_operation(self, name: str, success: bool = True,
                                    response_ms: float = 0.0, error: str = "") -> None:
        """Record a subsystem operation."""
        with self._lock:
            ss = self._subsystems.get(name)
            if ss:
                ss.active_operations += 1
                if not success:
                    ss.error_count += 1
                    ss.is_healthy = False
                    ss.last_error = error
                # Update rolling average response time
                if response_ms > 0:
                    ss.avg_response_ms = (ss.avg_response_ms + response_ms) / 2

    def get_subsystem_status(self, name: str) -> Optional[SubsystemStatus]:
        """Get status of a subsystem."""
        return self._subsystems.get(name)

    def get_all_subsystem_statuses(self) -> Dict[str, SubsystemStatus]:
        """Get all subsystem statuses."""
        return dict(self._subsystems)

    def get_unstable_subsystems(self) -> List[SubsystemStatus]:
        """Get subsystems that are not healthy."""
        return [s for s in self._subsystems.values() if not s.is_healthy]

    # ── Operation Log ──

    def log_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """Log an operation for debugging."""
        entry = {
            'timestamp': time.time(),
            'operation': operation,
            'details': details,
        }
        self._operation_log.append(entry)
        if len(self._operation_log) > self._max_log_size:
            self._operation_log = self._operation_log[-self._max_log_size:]

    def get_operation_log(self, limit: int = 100,
                          operation_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent operations."""
        log = self._operation_log
        if operation_filter:
            log = [e for e in log if e['operation'] == operation_filter]
        return log[-limit:]

    # ── Full Snapshot ──

    def get_snapshot(self) -> Dict[str, Any]:
        """Get a full runtime snapshot."""
        now = time.time()
        with self._lock:
            running = [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]
            blocked = [t for t in self._tasks.values() if t.status == TaskStatus.BLOCKED]
            waiting = [t for t in self._tasks.values() if t.status == TaskStatus.WAITING]

            total_tasks = len(self._tasks)
            active_tasks = len(running) + len(blocked) + len(waiting)

            # Find long-running tasks (>60s)
            long_running = [
                {'task_id': t.task_id, 'agent': t.agent,
                 'duration_s': round(now - t.started_at, 1)}
                for t in running
                if now - t.started_at > 60
            ]

            return {
                'timestamp': now,
                'total_tasks': total_tasks,
                'active_tasks': active_tasks,
                'running': len(running),
                'blocked': len(blocked),
                'waiting': len(waiting),
                'long_running': long_running,
                'bottlenecks': [
                    {'resource': b.resource, 'wait_s': b.wait_time_seconds,
                     'severity': b.severity}
                    for b in self.detect_bottlenecks()
                ],
                'unstable_subsystems': [
                    {'name': s.name, 'errors': s.error_count,
                     'last_error': s.last_error}
                    for s in self.get_unstable_subsystems()
                ],
            }
