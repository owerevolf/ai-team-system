"""
runtime_metrics.py — Engineering Observability.

Tracks operational metrics:
- task success rate
- patch approval rate
- rollback rate
- test pass rate
- execution latency
- tool usage
- failure hotspots

NOT telemetry spam. Only operationally useful metrics.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict

from loguru import logger


@dataclass
class MetricSnapshot:
    """A point-in-time snapshot of metrics."""
    timestamp: str = ""
    task_success_rate: float = 0.0
    patch_approval_rate: float = 0.0
    rollback_rate: float = 0.0
    test_pass_rate: float = 0.0
    avg_execution_ms: float = 0.0
    tool_usage: Dict[str, int] = field(default_factory=dict)
    failure_hotspots: List[Dict[str, Any]] = field(default_factory=list)
    total_tasks: int = 0
    total_patches: int = 0
    total_tests: int = 0
    total_rollbacks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "task_success_rate": self.task_success_rate,
            "patch_approval_rate": self.patch_approval_rate,
            "rollback_rate": self.rollback_rate,
            "test_pass_rate": self.test_pass_rate,
            "avg_execution_ms": round(self.avg_execution_ms, 2),
            "tool_usage": self.tool_usage,
            "failure_hotspots": self.failure_hotspots,
            "total_tasks": self.total_tasks,
            "total_patches": self.total_patches,
            "total_tests": self.total_tests,
            "total_rollbacks": self.total_rollbacks,
        }


@dataclass
class TaskMetric:
    """Metrics for a single task."""
    task_id: str = ""
    agent_id: str = ""
    status: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_ms: float = 0.0
    patches_created: int = 0
    patches_approved: int = 0
    tests_run: int = 0
    tests_passed: int = 0
    was_rolled_back: bool = False
    failure_reason: str = ""


@dataclass
class ToolMetric:
    """Metrics for tool usage."""
    tool_type: str = ""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    blocked_runs: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    last_run: str = ""


class RuntimeMetrics:
    """
    Engineering observability.
    Collects and aggregates operational metrics.
    """

    def __init__(self, max_history: int = 10000):
        self._task_metrics: List[TaskMetric] = []
        self._tool_metrics: Dict[str, ToolMetric] = {}
        self._failure_log: List[Dict[str, Any]] = []
        self._max_history = max_history
        self._lock = threading.Lock()

    # ── Recording ──

    def record_task(self, metric: TaskMetric) -> None:
        """Record task metrics."""
        with self._lock:
            self._task_metrics.append(metric)
            if len(self._task_metrics) > self._max_history:
                self._task_metrics = self._task_metrics[-self._max_history:]

    def record_tool_run(
        self,
        tool_type: str,
        success: bool,
        blocked: bool,
        duration_ms: float,
    ) -> None:
        """Record a tool execution."""
        with self._lock:
            tm = self._tool_metrics.get(tool_type)
            if not tm:
                tm = ToolMetric(tool_type=tool_type)
                self._tool_metrics[tool_type] = tm

            tm.total_runs += 1
            if blocked:
                tm.blocked_runs += 1
            elif success:
                tm.successful_runs += 1
            else:
                tm.failed_runs += 1

            tm.total_duration_ms += duration_ms
            tm.avg_duration_ms = tm.total_duration_ms / tm.total_runs
            tm.last_run = datetime.utcnow().isoformat() + "Z"

    def record_failure(
        self,
        task_id: str,
        agent_id: str,
        failure_type: str,
        reason: str,
        tool_type: str = "",
    ) -> None:
        """Record a failure for hotspot analysis."""
        with self._lock:
            self._failure_log.append({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "task_id": task_id,
                "agent_id": agent_id,
                "failure_type": failure_type,
                "reason": reason[:300],
                "tool_type": tool_type,
            })
            if len(self._failure_log) > self._max_history:
                self._failure_log = self._failure_log[-self._max_history:]

    def record_rollback(self, task_id: str, reason: str) -> None:
        """Record a rollback."""
        with self._lock:
            self._failure_log.append({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "task_id": task_id,
                "failure_type": "rollback",
                "reason": reason[:300],
            })

    # ── Aggregation ──

    def get_snapshot(self) -> MetricSnapshot:
        """Get a current metrics snapshot."""
        with self._lock:
            tasks = list(self._task_metrics)
            tools = dict(self._tool_metrics)
            failures = list(self._failure_log)

        snapshot = MetricSnapshot(
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        # Task metrics
        if tasks:
            completed = [t for t in tasks if t.status == "completed"]
            failed = [t for t in tasks if t.status == "failed"]
            snapshot.total_tasks = len(tasks)
            snapshot.task_success_rate = round(
                len(completed) / len(tasks) * 100, 1
            ) if tasks else 0

            # Execution latency
            durations = [t.duration_ms for t in tasks if t.duration_ms > 0]
            snapshot.avg_execution_ms = (
                sum(durations) / len(durations) if durations else 0
            )

        # Patch metrics
        total_patches = sum(t.patches_created for t in tasks)
        approved_patches = sum(t.patches_approved for t in tasks)
        snapshot.total_patches = total_patches
        snapshot.patch_approval_rate = round(
            approved_patches / total_patches * 100, 1
        ) if total_patches > 0 else 0

        # Rollback rate
        rollbacks = sum(1 for t in tasks if t.was_rolled_back)
        snapshot.total_rollbacks = rollbacks
        snapshot.rollback_rate = round(
            rollbacks / len(tasks) * 100, 1
        ) if tasks else 0

        # Test metrics
        total_tests = sum(t.tests_run for t in tasks)
        passed_tests = sum(t.tests_passed for t in tasks)
        snapshot.total_tests = total_tests
        snapshot.test_pass_rate = round(
            passed_tests / total_tests * 100, 1
        ) if total_tests > 0 else 0

        # Tool usage
        for tool_type, tm in tools.items():
            snapshot.tool_usage[tool_type] = tm.total_runs

        # Failure hotspots
        failure_counts: Dict[str, int] = defaultdict(int)
        for f in failures:
            key = f.get("tool_type") or f.get("failure_type") or "unknown"
            failure_counts[key] += 1

        sorted_hotspots = sorted(
            failure_counts.items(), key=lambda x: x[1], reverse=True
        )
        snapshot.failure_hotspots = [
            {"source": k, "count": v} for k, v in sorted_hotspots[:10]
        ]

        return snapshot

    def get_tool_metrics(self) -> Dict[str, ToolMetric]:
        """Get all tool metrics."""
        with self._lock:
            return dict(self._tool_metrics)

    def get_failure_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent failures."""
        with self._lock:
            return self._failure_log[-limit:]

    def get_task_history(self, limit: int = 100) -> List[TaskMetric]:
        """Get recent task metrics."""
        with self._lock:
            return self._task_metrics[-limit:]

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._task_metrics.clear()
            self._tool_metrics.clear()
            self._failure_log.clear()
