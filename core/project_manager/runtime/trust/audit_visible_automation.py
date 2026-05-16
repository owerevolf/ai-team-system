"""
P8 — Audit-Visible Automation (Phase 11)

Any automation (auto-apply, batching, suppression, prioritization) must be:
visible, replayable, attributable, reversible.

Key principle: runtime must never "quietly handle" something.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class AutomationType(Enum):
    AUTO_APPLY = "auto_apply"
    BATCHING = "batching"
    SUPPRESSION = "suppression"
    PRIORITIZATION = "prioritization"
    COMPRESSION = "compression"
    DELAY = "delay"


class AutomationStatus(Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    REVERSED = "reversed"
    FAILED = "failed"


@dataclass
class AutomationRecord:
    """A record of an automation action — fully auditable."""
    record_id: str
    automation_type: AutomationType
    status: AutomationStatus
    action_description: str
    affected_items: list[str]
    reason: str
    timestamp: float = 0.0
    reversed_at: float = 0.0
    reverse_reason: str = ""
    reverse_available: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.record_id:
            self.record_id = f"auto-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "automation_type": self.automation_type.value,
            "status": self.status.value,
            "action_description": self.action_description,
            "affected_items": self.affected_items,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "reversed_at": self.reversed_at,
            "reverse_reason": self.reverse_reason,
            "reverse_available": self.reverse_available,
            "metadata": self.metadata,
        }


class AuditVisibleAutomation:
    """
    Ensures all automation is visible, replayable, attributable, reversible.

    Usage:
        audit = AuditVisibleAutomation()
        record = audit.record_automation(
            AutomationType.AUTO_APPLY,
            "Auto-applied low-risk formatting changes",
            affected_items=["src/auth.py", "src/models.py"],
            reason="Low-risk auto-apply policy"
        )
        audit.reverse(record.record_id, "User requested rollback")
        history = audit.get_history()
    """

    def __init__(self, max_records: int = 500) -> None:
        self._records: dict[str, AutomationRecord] = {}
        self._max_records = max_records

    def record_automation(self, automation_type: AutomationType,
                          action_description: str,
                          affected_items: list[str],
                          reason: str,
                          reverse_available: bool = True,
                          metadata: Optional[dict[str, Any]] = None) -> AutomationRecord:
        """Record an automation action."""
        record = AutomationRecord(
            record_id=f"auto-{uuid.uuid4().hex[:8]}",
            automation_type=automation_type,
            status=AutomationStatus.EXECUTED,
            action_description=action_description,
            affected_items=affected_items,
            reason=reason,
            reverse_available=reverse_available,
            metadata=metadata or {},
        )
        self._records[record.record_id] = record
        self._enforce_limit()
        return record

    def reverse(self, record_id: str, reason: str) -> bool:
        """Reverse an automation action. Returns True if successful."""
        record = self._records.get(record_id)
        if not record:
            return False
        if not record.reverse_available:
            return False
        if record.status == AutomationStatus.REVERSED:
            return False

        record.status = AutomationStatus.REVERSED
        record.reversed_at = time.time()
        record.reverse_reason = reason
        return True

    def get_record(self, record_id: str) -> Optional[AutomationRecord]:
        """Get a specific automation record."""
        return self._records.get(record_id)

    def get_history(self, automation_type: Optional[AutomationType] = None,
                    status: Optional[AutomationStatus] = None,
                    limit: int = 50) -> list[AutomationRecord]:
        """Get automation history with optional filtering."""
        results = list(self._records.values())
        if automation_type:
            results = [r for r in results if r.automation_type == automation_type]
        if status:
            results = [r for r in results if r.status == status]
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:limit]

    def get_reversible(self) -> list[AutomationRecord]:
        """Get all reversible automation records."""
        return [
            r for r in self._records.values()
            if r.reverse_available and r.status == AutomationStatus.EXECUTED
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get automation audit stats."""
        total = len(self._records)
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        reversible = 0
        reversed_count = 0
        for r in self._records.values():
            t = r.automation_type.value
            by_type[t] = by_type.get(t, 0) + 1
            s = r.status.value
            by_status[s] = by_status.get(s, 0) + 1
            if r.reverse_available:
                reversible += 1
            if r.status == AutomationStatus.REVERSED:
                reversed_count += 1

        return {
            "total_records": total,
            "by_type": by_type,
            "by_status": by_status,
            "reversible_count": reversible,
            "reversed_count": reversed_count,
            "reversal_rate": round(reversed_count / total, 3) if total > 0 else 0.0,
        }

    def _enforce_limit(self) -> None:
        """Keep records under max limit."""
        if len(self._records) <= self._max_records:
            return
        sorted_records = sorted(self._records.values(), key=lambda r: r.timestamp)
        to_remove = len(self._records) - self._max_records
        for r in sorted_records[:to_remove]:
            del self._records[r.record_id]
