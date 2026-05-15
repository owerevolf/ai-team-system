"""
P5 — Failure Analysis System.

Structured failure learning and taxonomy.
Tracks failures, classifies them, learns from patterns.

Failure categories:
- workflow_failure: workflow step failed
- validation_failure: validation check failed
- merge_failure: merge conflict or issue
- retrieval_failure: context retrieval missed
- patch_failure: patch application failed
- timeout_failure: operation timed out
- resource_failure: resource unavailable
- permission_failure: access denied
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class FailureCategory(Enum):
    WORKFLOW = "workflow_failure"
    VALIDATION = "validation_failure"
    MERGE = "merge_failure"
    RETRIEVAL = "retrieval_failure"
    PATCH = "patch_failure"
    TIMEOUT = "timeout_failure"
    RESOURCE = "resource_failure"
    PERMISSION = "permission_failure"
    UNKNOWN = "unknown"


class FailureSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FailureRecord:
    """A single failure record."""
    id: str
    category: FailureCategory
    severity: FailureSeverity
    task_id: str
    workflow: str
    step: str
    message: str
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution: str = ""
    retry_count: int = 0


@dataclass
class FailurePattern:
    """A detected failure pattern."""
    pattern_id: str
    category: FailureCategory
    step: str
    frequency: int
    first_seen: float
    last_seen: float
    common_message: str
    recommendation: str


class FailureAnalysisSystem:
    """
    Structured failure learning.
    Tracks, classifies, and learns from failures.
    """

    def __init__(self):
        self._failures: List[FailureRecord] = []
        self._patterns: Dict[str, FailurePattern] = {}
        self._lock = threading.Lock()
        self._max_failures = 50000

    def record_failure(self, category: FailureCategory,
                       severity: FailureSeverity,
                       task_id: str, workflow: str, step: str,
                       message: str,
                       context: Dict[str, Any] = None) -> FailureRecord:
        """Record a failure."""
        import uuid
        record = FailureRecord(
            id=str(uuid.uuid4())[:8],
            category=category,
            severity=severity,
            task_id=task_id,
            workflow=workflow,
            step=step,
            message=message,
            timestamp=time.time(),
            context=context or {},
        )

        with self._lock:
            self._failures.append(record)
            if len(self._failures) > self._max_failures:
                self._failures = self._failures[-self._max_failures:]

            # Update patterns
            self._update_patterns(record)

        return record

    def _update_patterns(self, record: FailureRecord) -> None:
        """Update failure patterns from a new record."""
        key = f"{record.category.value}:{record.step}"
        existing = self._patterns.get(key)
        if existing:
            existing.frequency += 1
            existing.last_seen = record.timestamp
        else:
            self._patterns[key] = FailurePattern(
                pattern_id=key,
                category=record.category,
                step=record.step,
                frequency=1,
                first_seen=record.timestamp,
                last_seen=record.timestamp,
                common_message=record.message[:100],
                recommendation=self._generate_recommendation(record),
            )

    def _generate_recommendation(self, record: FailureRecord) -> str:
        """Generate a recommendation based on failure type."""
        recommendations = {
            FailureCategory.WORKFLOW: "Review workflow definition and step dependencies",
            FailureCategory.VALIDATION: "Check validation rules and input data",
            FailureCategory.MERGE: "Resolve conflicts manually and re-run validation",
            FailureCategory.RETRIEVAL: "Expand retrieval scope or improve indexing",
            FailureCategory.PATCH: "Check patch format and target file state",
            FailureCategory.TIMEOUT: "Increase timeout or optimize operation",
            FailureCategory.RESOURCE: "Check resource availability and quotas",
            FailureCategory.PERMISSION: "Verify access permissions",
            FailureCategory.UNKNOWN: "Investigate root cause",
        }
        return recommendations.get(record.category, "Investigate")

    def get_patterns(self, min_frequency: int = 2) -> List[FailurePattern]:
        """Get detected failure patterns."""
        return sorted(
            [p for p in self._patterns.values() if p.frequency >= min_frequency],
            key=lambda p: -p.frequency,
        )

    def get_failures(self, category: FailureCategory = None,
                     task_id: str = None, limit: int = 100) -> List[FailureRecord]:
        """Get failures, optionally filtered."""
        failures = self._failures
        if category:
            failures = [f for f in failures if f.category == category]
        if task_id:
            failures = [f for f in failures if f.task_id == task_id]
        return failures[-limit:]

    def get_taxonomy(self) -> Dict[str, Any]:
        """Get failure taxonomy summary."""
        by_category = defaultdict(int)
        by_severity = defaultdict(int)
        by_step = defaultdict(int)

        for f in self._failures:
            by_category[f.category.value] += 1
            by_severity[f.severity.value] += 1
            by_step[f.step] += 1

        return {
            'total_failures': len(self._failures),
            'by_category': dict(by_category),
            'by_severity': dict(by_severity),
            'top_steps': dict(sorted(by_step.items(), key=lambda x: -x[1])[:10]),
            'patterns_detected': len(self._patterns),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get failure analysis statistics."""
        return {
            'total_failures': len(self._failures),
            'patterns': len(self._patterns),
            'unresolved': sum(1 for f in self._failures if not f.resolved),
        }
