"""
engineering_metrics.py — Real Engineering Metrics.

Purpose: Measure real utility of the system.
NOT: AI "intelligence", token flex, orchestration complexity.
YES: task completion, rollback frequency, review rejection, trust stability.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class MetricSnapshot:
    """A snapshot of engineering metrics."""
    timestamp: float = 0.0
    task_completion_rate: float = 0.0
    rollback_frequency: float = 0.0
    review_rejection_rate: float = 0.0
    context_recovery_success: float = 0.0
    onboarding_speed: float = 0.0  # minutes to first useful output
    architecture_understanding_accuracy: float = 0.0
    developer_fatigue: float = 0.0  # 0.0 to 1.0
    trust_stability: float = 1.0  # 0.0 to 1.0


class EngineeringMetrics:
    """
    Measures real engineering utility.
    NOT: AI intelligence, token counts, orchestration complexity.
    YES: task completion, rollbacks, trust, fatigue.
    """

    def __init__(self):
        self._tasks_total = 0
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._rollbacks = 0
        self._reviews_total = 0
        self._reviews_rejected = 0
        self._context_recoveries = 0
        self._context_recovery_successes = 0
        self._onboarding_times: List[float] = []
        self._architecture_checks = 0
        self._architecture_correct = 0
        self._fatigue_events = 0
        self._trust_events = 0
        self._trust_violations = 0
        self._lock = threading.Lock()
        self._snapshots: List[MetricSnapshot] = []

    def record_task_completion(self, success: bool) -> None:
        """Record a task completion."""
        with self._lock:
            self._tasks_total += 1
            if success:
                self._tasks_completed += 1
            else:
                self._tasks_failed += 1

    def record_rollback(self) -> None:
        """Record a rollback."""
        with self._lock:
            self._rollbacks += 1

    def record_review(self, approved: bool) -> None:
        """Record a review decision."""
        with self._lock:
            self._reviews_total += 1
            if not approved:
                self._reviews_rejected += 1

    def record_context_recovery(self, success: bool) -> None:
        """Record a context recovery attempt."""
        with self._lock:
            self._context_recoveries += 1
            if success:
                self._context_recovery_successes += 1

    def record_onboarding_time(self, minutes: float) -> None:
        """Record onboarding time in minutes."""
        with self._lock:
            self._onboarding_times.append(minutes)

    def record_architecture_check(self, correct: bool) -> None:
        """Record an architecture understanding check."""
        with self._lock:
            self._architecture_checks += 1
            if correct:
                self._architecture_correct += 1

    def record_fatigue_event(self) -> None:
        """Record a developer fatigue event."""
        with self._lock:
            self._fatigue_events += 1

    def record_trust_event(self, violation: bool = False) -> None:
        """Record a trust event."""
        with self._lock:
            self._trust_events += 1
            if violation:
                self._trust_violations += 1

    def get_snapshot(self) -> MetricSnapshot:
        """Get current metrics snapshot."""
        with self._lock:
            task_rate = (self._tasks_completed / max(1, self._tasks_total))
            rollback_freq = (self._rollbacks / max(1, self._tasks_total))
            rejection_rate = (self._reviews_rejected / max(1, self._reviews_total))
            recovery_success = (self._context_recovery_successes / max(1, self._context_recoveries))
            avg_onboarding = (sum(self._onboarding_times) / max(1, len(self._onboarding_times))) if self._onboarding_times else 0.0
            arch_accuracy = (self._architecture_correct / max(1, self._architecture_checks))
            fatigue = min(1.0, self._fatigue_events / 10.0)
            trust = 1.0 - (self._trust_violations / max(1, self._trust_events))

        snapshot = MetricSnapshot(
            timestamp=time.time(),
            task_completion_rate=round(task_rate, 3),
            rollback_frequency=round(rollback_freq, 3),
            review_rejection_rate=round(rejection_rate, 3),
            context_recovery_success=round(recovery_success, 3),
            onboarding_speed=round(avg_onboarding, 1),
            architecture_understanding_accuracy=round(arch_accuracy, 3),
            developer_fatigue=round(fatigue, 3),
            trust_stability=round(trust, 3),
        )
        self._snapshots.append(snapshot)
        return snapshot

    def get_trend(self, metric_name: str, last_n: int = 10) -> List[float]:
        """Get trend for a specific metric."""
        with self._lock:
            snapshots = self._snapshots[-last_n:]
        return [getattr(s, metric_name, 0.0) for s in snapshots]

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        snapshot = self.get_snapshot()
        return {
            "task_completion_rate": snapshot.task_completion_rate,
            "rollback_frequency": snapshot.rollback_frequency,
            "review_rejection_rate": snapshot.review_rejection_rate,
            "context_recovery_success": snapshot.context_recovery_success,
            "onboarding_speed_min": snapshot.onboarding_speed,
            "architecture_accuracy": snapshot.architecture_understanding_accuracy,
            "developer_fatigue": snapshot.developer_fatigue,
            "trust_stability": snapshot.trust_stability,
            "total_tasks": self._tasks_total,
            "total_rollbacks": self._rollbacks,
            "total_reviews": self._reviews_total,
        }
