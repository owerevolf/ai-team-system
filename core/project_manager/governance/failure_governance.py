"""
P14 — Failure Governance.

Systematic failure management:
- Failure classification
- Retry policies
- Escalation rules
- Isolation boundaries
- Recovery policies
"""

import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class FailureType(Enum):
    TRANSIENT = "transient"      # temporary, retryable
    PERMANENT = "permanent"      # won't succeed on retry
    TIMEOUT = "timeout"          # operation timed out
    RESOURCE = "resource"        # resource unavailable
    VALIDATION = "validation"    # validation failed
    CONFLICT = "conflict"        # resource conflict
    UNKNOWN = "unknown"          # unclassified


class FailureSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FailureRecord:
    """A single failure record."""
    failure_id: str
    task_id: str
    subsystem: str
    failure_type: FailureType
    severity: FailureSeverity
    message: str
    timestamp: float
    retry_count: int = 0
    max_retries: int = 3
    resolved: bool = False
    resolution: str = ""
    escalated: bool = False


@dataclass
class RetryPolicy:
    """Retry policy for a failure type."""
    failure_type: FailureType
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_backoff: bool = True
    retryable: bool = True


class FailureGovernance:
    """
    Manages failures systematically.
    Classification, retry, escalation, isolation, recovery.
    """

    DEFAULT_POLICIES: Dict[FailureType, RetryPolicy] = {
        FailureType.TRANSIENT: RetryPolicy(FailureType.TRANSIENT, max_retries=3, base_delay_seconds=1.0),
        FailureType.TIMEOUT: RetryPolicy(FailureType.TIMEOUT, max_retries=2, base_delay_seconds=2.0),
        FailureType.RESOURCE: RetryPolicy(FailureType.RESOURCE, max_retries=3, base_delay_seconds=5.0),
        FailureType.CONFLICT: RetryPolicy(FailureType.CONFLICT, max_retries=5, base_delay_seconds=0.5),
        FailureType.PERMANENT: RetryPolicy(FailureType.PERMANENT, max_retries=0, retryable=False),
        FailureType.VALIDATION: RetryPolicy(FailureType.VALIDATION, max_retries=0, retryable=False),
        FailureType.UNKNOWN: RetryPolicy(FailureType.UNKNOWN, max_retries=1, base_delay_seconds=1.0),
    }

    def __init__(self):
        self._failures: List[FailureRecord] = []
        self._policies: Dict[FailureType, RetryPolicy] = dict(self.DEFAULT_POLICIES)
        self._subsystem_failures: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.Lock()
        self._escalation_callbacks: List[Callable] = []
        self._max_failures = 10000

    def record_failure(self, task_id: str, subsystem: str,
                       failure_type: FailureType, severity: FailureSeverity,
                       message: str) -> FailureRecord:
        """Record a failure."""
        import uuid
        failure = FailureRecord(
            failure_id=str(uuid.uuid4())[:8],
            task_id=task_id,
            subsystem=subsystem,
            failure_type=failure_type,
            severity=severity,
            message=message,
            timestamp=time.time(),
            max_retries=self._policies.get(failure_type, self.DEFAULT_POLICIES[FailureType.UNKNOWN]).max_retries,
        )

        with self._lock:
            self._failures.append(failure)
            self._subsystem_failures[subsystem].append(failure.failure_id)
            if len(self._failures) > self._max_failures:
                self._failures = self._failures[-self._max_failures:]

        # Auto-escalate critical failures
        if severity == FailureSeverity.CRITICAL:
            self._escalate(failure)

        return failure

    def should_retry(self, failure_id: str) -> tuple:
        """
        Check if a failure should be retried.
        Returns: (should_retry, delay_seconds)
        """
        failure = self._get_failure(failure_id)
        if not failure:
            return False, 0.0

        policy = self._policies.get(failure.failure_type)
        if not policy or not policy.retryable:
            return False, 0.0

        if failure.retry_count >= policy.max_retries:
            return False, 0.0

        delay = policy.base_delay_seconds
        if policy.exponential_backoff:
            delay = delay * (2 ** failure.retry_count)
        delay = min(delay, policy.max_delay_seconds)

        return True, delay

    def record_retry(self, failure_id: str) -> None:
        """Record a retry attempt."""
        failure = self._get_failure(failure_id)
        if failure:
            failure.retry_count += 1

    def resolve_failure(self, failure_id: str, resolution: str) -> bool:
        """Mark a failure as resolved."""
        failure = self._get_failure(failure_id)
        if failure:
            failure.resolved = True
            failure.resolution = resolution
            return True
        return False

    def _escalate(self, failure: FailureRecord) -> None:
        """Escalate a failure."""
        failure.escalated = True
        for callback in self._escalation_callbacks:
            try:
                callback(failure)
            except Exception:
                pass

    def register_escalation_callback(self, callback: Callable) -> None:
        """Register a callback for critical failure escalation."""
        self._escalation_callbacks.append(callback)

    def _get_failure(self, failure_id: str) -> Optional[FailureRecord]:
        """Get a failure by ID."""
        for f in self._failures:
            if f.failure_id == failure_id:
                return f
        return None

    def get_failures(self, subsystem: Optional[str] = None,
                     failure_type: Optional[FailureType] = None,
                     unresolved_only: bool = False,
                     limit: int = 100) -> List[FailureRecord]:
        """Get failures, optionally filtered."""
        failures = self._failures
        if subsystem:
            failure_ids = set(self._subsystem_failures.get(subsystem, []))
            failures = [f for f in failures if f.failure_id in failure_ids]
        if failure_type:
            failures = [f for f in failures if f.failure_type == failure_type]
        if unresolved_only:
            failures = [f for f in failures if not f.resolved]
        return failures[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get failure statistics."""
        total = len(self._failures)
        unresolved = sum(1 for f in self._failures if not f.resolved)
        escalated = sum(1 for f in self._failures if f.escalated)

        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        for f in self._failures:
            by_type[f.failure_type.value] += 1
            by_severity[f.severity.value] += 1

        return {
            'total_failures': total,
            'unresolved': unresolved,
            'escalated': escalated,
            'by_type': dict(by_type),
            'by_severity': dict(by_severity),
        }
