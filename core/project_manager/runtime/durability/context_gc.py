"""
P2 — Context Garbage Collection (Phase 9)

Detects and removes stale context:
  - Outdated assumptions
  - Dead workflows
  - Abandoned tasks
  - Obsolete checkpoints
  - Invalidated summaries

Key principle: GC must not break replay/recovery.
Immutable audit log is NEVER pruned. Only mutable operational cache is GC'd.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class ContextType(Enum):
    ASSUMPTION = "assumption"
    WORKFLOW_STATE = "workflow_state"
    TASK_STATE = "task_state"
    CHECKPOINT_REF = "checkpoint_ref"
    SUMMARY = "summary"
    RETRIEVAL_CACHE = "retrieval_cache"
    VALIDATION_CACHE = "validation_cache"


class ContextStatus(Enum):
    ACTIVE = "active"
    STALE = "stale"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


@dataclass
class ContextEntry:
    """A tracked context item."""
    key: str
    context_type: ContextType
    status: ContextStatus = ContextStatus.ACTIVE
    created_at: float = 0.0
    last_validated: float = 0.0
    ttl_seconds: float = 0.0
    source: str = ""              # What created this context
    invalidated_by: str = ""      # What invalidated it
    is_audit: bool = False        # If True, NEVER prune (immutable audit log)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()
        if not self.last_validated:
            self.last_validated = self.created_at

    @property
    def is_prunable(self) -> bool:
        if self.is_audit:
            return False
        if self.status in (ContextStatus.STALE, ContextStatus.EXPIRED, ContextStatus.INVALIDATED):
            return True
        if self.ttl_seconds > 0:
            return (time.time() - self.last_validated) > self.ttl_seconds
        return False

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


@dataclass
class GCReport:
    """Report from a garbage collection run."""
    timestamp: float = 0.0
    scanned: int = 0
    pruned: int = 0
    kept: int = 0
    audit_protected: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "scanned": self.scanned,
            "pruned": self.pruned,
            "kept": self.kept,
            "audit_protected": self.audit_protected,
            "by_type": self.by_type,
            "errors": self.errors,
        }


class ContextGC:
    """
    Garbage collector for runtime context.

    Usage:
        gc = ContextGC()
        gc.track("assumption_1", ContextType.ASSUMPTION, ttl=3600)
        gc.track("audit_log", ContextType.ASSUMPTION, is_audit=True)  # never pruned

        # Mark context as invalidated
        gc.invalidate("assumption_1", source="new_scan")

        # Run GC
        report = gc.collect()
    """

    # Default TTLs per context type
    DEFAULT_TTLS: dict[ContextType, float] = {
        ContextType.ASSUMPTION: 3600,         # 1 hour
        ContextType.WORKFLOW_STATE: 86400,    # 1 day
        ContextType.TASK_STATE: 604800,       # 7 days
        ContextType.CHECKPOINT_REF: 2592000,  # 30 days
        ContextType.SUMMARY: 3600,            # 1 hour
        ContextType.RETRIEVAL_CACHE: 1800,    # 30 minutes
        ContextType.VALIDATION_CACHE: 3600,   # 1 hour
    }

    def __init__(self) -> None:
        self._contexts: dict[str, ContextEntry] = {}
        self._last_gc_report: Optional[GCReport] = None

    def track(
        self,
        key: str,
        context_type: ContextType,
        ttl: float = 0,
        source: str = "",
        is_audit: bool = False,
    ) -> ContextEntry:
        """Track a new context item."""
        entry = ContextEntry(
            key=key,
            context_type=context_type,
            ttl_seconds=ttl or self.DEFAULT_TTLS.get(context_type, 3600),
            source=source,
            is_audit=is_audit,
        )
        self._contexts[key] = entry
        return entry

    def invalidate(self, key: str, source: str = "") -> bool:
        """Mark a context as invalidated."""
        entry = self._contexts.get(key)
        if entry:
            entry.status = ContextStatus.INVALIDATED
            entry.invalidated_by = source
            return True
        return False

    def mark_stale(self, key: str) -> bool:
        """Mark a context as stale."""
        entry = self._contexts.get(key)
        if entry:
            entry.status = ContextStatus.STALE
            return True
        return False

    def validate(self, key: str) -> bool:
        """Re-validate a context (reset TTL)."""
        entry = self._contexts.get(key)
        if entry and not entry.is_audit:
            entry.last_validated = time.time()
            entry.status = ContextStatus.ACTIVE
            return True
        return False

    def collect(self, dry_run: bool = False) -> GCReport:
        """
        Run garbage collection.

        Args:
            dry_run: If True, report what would be pruned without actually removing.

        Returns:
            GCReport with results.
        """
        report = GCReport()
        to_prune = []

        for key, entry in self._contexts.items():
            report.scanned += 1

            if entry.is_audit:
                report.audit_protected += 1
                report.kept += 1
                continue

            if entry.is_prunable:
                to_prune.append(key)
                report.pruned += 1
                type_name = entry.context_type.value
                report.by_type[type_name] = report.by_type.get(type_name, 0) + 1
            else:
                report.kept += 1

        if not dry_run:
            for key in to_prune:
                del self._contexts[key]

        self._last_gc_report = report
        return report

    def get_status(self, key: str) -> Optional[dict[str, Any]]:
        """Get status of a specific context entry."""
        entry = self._contexts.get(key)
        if not entry:
            return None
        return {
            "key": entry.key,
            "type": entry.context_type.value,
            "status": entry.status.value,
            "age_seconds": round(entry.age_seconds, 1),
            "prunable": entry.is_prunable,
            "is_audit": entry.is_audit,
        }

    def get_all_statuses(self) -> list[dict[str, Any]]:
        """Get status of all tracked contexts."""
        return [self.get_status(k) for k in self._contexts]

    def get_stats(self) -> dict[str, Any]:
        """Get overall GC stats."""
        total = len(self._contexts)
        prunable = sum(1 for e in self._contexts.values() if e.is_prunable)
        audit = sum(1 for e in self._contexts.values() if e.is_audit)
        by_status = {}
        for e in self._contexts.values():
            s = e.status.value
            by_status[s] = by_status.get(s, 0) + 1
        return {
            "total_tracked": total,
            "prunable": prunable,
            "audit_protected": audit,
            "active": total - prunable,
            "by_status": by_status,
            "last_gc": self._last_gc_report.to_dict() if self._last_gc_report else None,
        }
