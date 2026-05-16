"""
P3 — Approval Intelligence (Phase 10)

Not autonomous approvals. Smart batching, grouping, risk-tiering,
and meaningful review surfaces.

Key principle: approvals should be meaningful, not mechanical.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class ApprovalRisk(Enum):
    LOW = "low"          # Safe auto-apply (formatting, comments)
    MEDIUM = "medium"    # Review suggested (config changes, new deps)
    HIGH = "high"        # Review required (core logic, migrations)
    CRITICAL = "critical"  # Explicit approval + confirmation (deletions, security)


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPLIED = "auto_applied"
    BATCHED = "batched"
    SKIPPED = "skipped"


@dataclass
class ApprovalItem:
    """A single approval request."""
    title: str
    approval_id: str = ""
    description: str = ""
    risk: ApprovalRisk = ApprovalRisk.MEDIUM
    status: ApprovalStatus = ApprovalStatus.PENDING
    category: str = ""  # For grouping: "files", "deps", "config", "security"
    changes_summary: list[str] = field(default_factory=list)
    impact_score: float = 0.0  # 0-1, computed from affected files/symbols
    created_at: float = 0.0
    decided_at: float = 0.0
    group_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()
        if not self.approval_id:
            self.approval_id = f"apr-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "title": self.title,
            "description": self.description,
            "risk": self.risk.value,
            "status": self.status.value,
            "category": self.category,
            "changes_summary": self.changes_summary,
            "impact_score": self.impact_score,
            "created_at": self.created_at,
            "decided_at": self.decided_at,
            "group_key": self.group_key,
        }


@dataclass
class ApprovalBatch:
    """A batch of related approvals presented together."""
    batch_id: str
    title: str
    items: list[ApprovalItem]
    max_risk: ApprovalRisk = ApprovalRisk.LOW
    created_at: float = 0.0
    status: ApprovalStatus = ApprovalStatus.PENDING

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()
        if not self.batch_id:
            self.batch_id = f"batch-{uuid.uuid4().hex[:8]}"
        # Compute max risk
        risk_values = {r: i for i, r in enumerate(ApprovalRisk)}
        self.max_risk = max(self.items, key=lambda i: risk_values[i.risk]).risk if self.items else ApprovalRisk.LOW

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "title": self.title,
            "item_count": len(self.items),
            "max_risk": self.max_risk.value,
            "status": self.status.value,
            "items": [i.to_dict() for i in self.items],
        }


class ApprovalIntelligence:
    """
    Smart approval management: batching, grouping, risk-tiering.

    Usage:
        ai = ApprovalIntelligence()
        ai.add(ApprovalItem(title="Add requests dep", risk=ApprovalRisk.LOW, category="deps"))
        ai.add(ApprovalItem(title="Add httpx dep", risk=ApprovalRisk.LOW, category="deps"))
        batches = ai.create_batches()
        ai.approve_batch(batches[0].batch_id)
    """

    # Risk thresholds for auto-apply
    AUTO_APPLY_RISKS = {ApprovalRisk.LOW}
    # Risks that require explicit confirmation
    REQUIRE_CONFIRMATION = {ApprovalRisk.HIGH, ApprovalRisk.CRITICAL}

    def __init__(self) -> None:
        self._items: dict[str, ApprovalItem] = {}
        self._batches: dict[str, ApprovalBatch] = {}

    def add(self, item: ApprovalItem) -> str:
        """Add an approval item. Returns approval_id."""
        self._items[item.approval_id] = item
        return item.approval_id

    def decide(self, approval_id: str, approved: bool) -> bool:
        """Approve or reject a single item."""
        item = self._items.get(approval_id)
        if not item or item.status != ApprovalStatus.PENDING:
            return False
        item.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        item.decided_at = time.time()
        return True

    def auto_decide(self, approval_id: str) -> bool:
        """Auto-decide based on risk level. Returns True if decided."""
        item = self._items.get(approval_id)
        if not item or item.status != ApprovalStatus.PENDING:
            return False
        if item.risk in self.AUTO_APPLY_RISKS:
            item.status = ApprovalStatus.AUTO_APPLIED
            item.decided_at = time.time()
            return True
        return False

    def create_batches(self, max_batch_size: int = 10) -> list[ApprovalBatch]:
        """
        Group pending approvals into meaningful batches.
        Groups by category, then by risk level within category.
        """
        pending = [i for i in self._items.values() if i.status == ApprovalStatus.PENDING]

        # Auto-apply low-risk items
        for item in pending:
            if item.risk in self.AUTO_APPLY_RISKS:
                item.status = ApprovalStatus.AUTO_APPLIED
                item.decided_at = time.time()

        # Remaining items that need review
        remaining = [i for i in pending if i.status == ApprovalStatus.PENDING]
        if not remaining:
            return []

        # Group by category
        by_category: dict[str, list[ApprovalItem]] = {}
        for item in remaining:
            cat = item.category or "general"
            by_category.setdefault(cat, []).append(item)

        batches = []
        for category, items in by_category.items():
            # Sort by risk (highest first) so high-risk items are prominent
            risk_order = {r: i for i, r in enumerate(ApprovalRisk)}
            items.sort(key=lambda i: risk_order[i.risk], reverse=True)

            # Split into batches if too many
            for i in range(0, len(items), max_batch_size):
                chunk = items[i:i + max_batch_size]
                batch = ApprovalBatch(
                    batch_id=f"batch-{uuid.uuid4().hex[:8]}",
                    title=f"{category} ({len(chunk)} items)",
                    items=chunk,
                )
                self._batches[batch.batch_id] = batch
                # Mark items as batched
                for item in chunk:
                    item.status = ApprovalStatus.BATCHED
                    item.group_key = batch.batch_id
                batches.append(batch)

        return batches

    def approve_batch(self, batch_id: str) -> int:
        """Approve all items in a batch. Returns count approved."""
        batch = self._batches.get(batch_id)
        if not batch:
            return 0
        count = 0
        for item in batch.items:
            if item.status == ApprovalStatus.BATCHED:
                item.status = ApprovalStatus.APPROVED
                item.decided_at = time.time()
                count += 1
        batch.status = ApprovalStatus.APPROVED
        return count

    def reject_batch(self, batch_id: str) -> int:
        """Reject all items in a batch. Returns count rejected."""
        batch = self._batches.get(batch_id)
        if not batch:
            return 0
        count = 0
        for item in batch.items:
            if item.status == ApprovalStatus.BATCHED:
                item.status = ApprovalStatus.REJECTED
                item.decided_at = time.time()
                count += 1
        batch.status = ApprovalStatus.REJECTED
        return count

    def get_pending(self) -> list[ApprovalItem]:
        """Get all pending items."""
        return [i for i in self._items.values() if i.status == ApprovalStatus.PENDING]

    def get_batches(self) -> list[ApprovalBatch]:
        """Get all batches."""
        return list(self._batches.values())

    def get_approval_surface(self) -> dict[str, Any]:
        """
        Get the current approval surface — what user needs to review.
        Returns a structured view optimized for minimal cognitive load.
        """
        pending = self.get_pending()
        batches = self.get_batches()

        # Count by risk
        risk_counts: dict[str, int] = {}
        for item in pending:
            r = item.risk.value
            risk_counts[r] = risk_counts.get(r, 0) + 1

        # Check if there are critical items
        has_critical = any(i.risk == ApprovalRisk.CRITICAL for i in pending)

        return {
            "total_pending": len(pending),
            "total_batches": len(batches),
            "risk_counts": risk_counts,
            "has_critical": has_critical,
            "needs_attention": has_critical or risk_counts.get("high", 0) > 0,
            "auto_applied_count": sum(
                1 for i in self._items.values()
                if i.status == ApprovalStatus.AUTO_APPLIED
            ),
            "batches": [b.to_dict() for b in batches],
        }

    def get_stats(self) -> dict[str, Any]:
        """Get approval stats."""
        total = len(self._items)
        by_status: dict[str, int] = {}
        by_risk: dict[str, int] = {}
        for item in self._items.values():
            s = item.status.value
            by_status[s] = by_status.get(s, 0) + 1
            r = item.risk.value
            by_risk[r] = by_risk.get(r, 0) + 1
        return {
            "total": total,
            "by_status": by_status,
            "by_risk": by_risk,
            "batches": len(self._batches),
        }
