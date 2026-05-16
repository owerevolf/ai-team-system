"""
P2 — Attention Management (Phase 10)

Runtime understands what's important to the user right now.
Not everything has equal priority. Surfaces what matters,
defers what doesn't.

Key principle: signal over noise, urgency over volume.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class AttentionPriority(Enum):
    CRITICAL = 0    # Blocks progress, needs immediate action
    HIGH = 1        # Important, should address soon
    NORMAL = 2      # Standard information
    LOW = 3         # Background, can be deferred
    SILENT = 4      # Log only, don't surface


class AttentionCategory(Enum):
    ERROR = "error"
    WARNING = "warning"
    APPROVAL = "approval"
    PROGRESS = "progress"
    INFO = "info"
    SUCCESS = "success"


@dataclass
class AttentionItem:
    """A single item competing for user attention."""
    item_id: str
    category: AttentionCategory
    priority: AttentionPriority
    message: str
    source: str = ""
    timestamp: float = 0.0
    actionable: bool = False
    action_label: str = ""
    action_payload: dict[str, Any] = field(default_factory=dict)
    group_key: str = ""  # For grouping similar items
    dismissed: bool = False
    auto_dismiss_after: float = 0.0  # 0 = no auto-dismiss

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "category": self.category.value,
            "priority": self.priority.value,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp,
            "actionable": self.actionable,
            "action_label": self.action_label,
            "group_key": self.group_key,
            "dismissed": self.dismissed,
        }


@dataclass
class AttentionSnapshot:
    """Current attention state — what the user should see now."""
    items: list[AttentionItem]
    critical_count: int = 0
    high_count: int = 0
    actionable_count: int = 0
    generated_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = time.time()
        self.critical_count = sum(1 for i in self.items if i.priority == AttentionPriority.CRITICAL)
        self.high_count = sum(1 for i in self.items if i.priority == AttentionPriority.HIGH)
        self.actionable_count = sum(1 for i in self.items if i.actionable and not i.dismissed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "actionable_count": self.actionable_count,
            "generated_at": self.generated_at,
        }


class AttentionManager:
    """
    Manages what the user should pay attention to right now.

    Usage:
        manager = AttentionManager()
        manager.add(AttentionItem(item_id="err-1", category=AttentionCategory.ERROR, ...))
        snapshot = manager.get_snapshot(max_items=10)
        manager.dismiss("err-1")
    """

    def __init__(self, max_items: int = 100) -> None:
        self._items: dict[str, AttentionItem] = {}
        self._max_items = max_items

    def add(self, item: AttentionItem) -> None:
        """Add an attention item."""
        self._items[item.item_id] = item
        self._enforce_limit()

    def dismiss(self, item_id: str) -> bool:
        """Dismiss an attention item."""
        item = self._items.get(item_id)
        if item:
            item.dismissed = True
            return True
        return False

    def dismiss_group(self, group_key: str) -> int:
        """Dismiss all items in a group. Returns count dismissed."""
        count = 0
        for item in self._items.values():
            if item.group_key == group_key and not item.dismissed:
                item.dismissed = True
                count += 1
        return count

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()

    def clear_dismissed(self) -> int:
        """Remove dismissed items. Returns count removed."""
        to_remove = [k for k, v in self._items.items() if v.dismissed]
        for k in to_remove:
            del self._items[k]
        return len(to_remove)

    def get_snapshot(self, max_items: int = 10, include_dismissed: bool = False) -> AttentionSnapshot:
        """Get current attention snapshot — what user should see now."""
        items = list(self._items.values())

        if not include_dismissed:
            items = [i for i in items if not i.dismissed]

        # Auto-dismiss expired items
        now = time.time()
        for item in items:
            if item.auto_dismiss_after > 0 and (now - item.timestamp) > item.auto_dismiss_after:
                item.dismissed = True
        if not include_dismissed:
            items = [i for i in items if not i.dismissed]

        # Sort by priority (lowest number = highest priority), then by timestamp (newest first)
        items.sort(key=lambda i: (i.priority.value, -i.timestamp))

        # Group similar items if there are many
        if len(items) > max_items:
            items = self._group_and_truncate(items, max_items)

        return AttentionSnapshot(items=items)

    def get_critical(self) -> list[AttentionItem]:
        """Get only critical items."""
        return [
            i for i in self._items.values()
            if i.priority == AttentionPriority.CRITICAL and not i.dismissed
        ]

    def get_actionable(self) -> list[AttentionItem]:
        """Get items that require user action."""
        return [
            i for i in self._items.values()
            if i.actionable and not i.dismissed
        ]

    def _group_and_truncate(self, items: list[AttentionItem], max_items: int) -> list[AttentionItem]:
        """Group similar items and truncate to max_items."""
        # Keep critical and high priority items always visible
        must_show = [i for i in items if i.priority in (AttentionPriority.CRITICAL, AttentionPriority.HIGH)]
        rest = [i for i in items if i.priority not in (AttentionPriority.CRITICAL, AttentionPriority.HIGH)]

        remaining_slots = max(0, max_items - len(must_show))
        if remaining_slots <= 0:
            return must_show[:max_items]

        # Group remaining by group_key
        grouped: dict[str, list[AttentionItem]] = {}
        ungrouped: list[AttentionItem] = []
        for item in rest:
            if item.group_key:
                grouped.setdefault(item.group_key, []).append(item)
            else:
                ungrouped.append(item)

        result = must_show
        # Add grouped items as single representative
        for key, group in grouped.items():
            if len(result) >= max_items:
                break
            representative = group[0]
            representative.message = f"[{len(group)}] {representative.message}"
            result.append(representative)

        # Fill remaining slots with ungrouped
        for item in ungrouped:
            if len(result) >= max_items:
                break
            result.append(item)

        return result

    def _enforce_limit(self) -> None:
        """Keep total items under max_items."""
        if len(self._items) <= self._max_items:
            return
        # Remove oldest low-priority items first
        sorted_items = sorted(
            self._items.values(),
            key=lambda i: (i.priority.value, i.timestamp),
        )
        to_remove = len(self._items) - self._max_items
        for item in sorted_items[:to_remove]:
            if item.priority in (AttentionPriority.LOW, AttentionPriority.SILENT):
                del self._items[item.item_id]
            else:
                break

    def get_stats(self) -> dict[str, Any]:
        """Get attention stats."""
        total = len(self._items)
        by_priority: dict[str, int] = {}
        by_category: dict[str, int] = {}
        dismissed = 0
        actionable = 0
        for item in self._items.values():
            p = item.priority.name
            by_priority[p] = by_priority.get(p, 0) + 1
            c = item.category.value
            by_category[c] = by_category.get(c, 0) + 1
            if item.dismissed:
                dismissed += 1
            if item.actionable:
                actionable += 1
        return {
            "total": total,
            "active": total - dismissed,
            "dismissed": dismissed,
            "actionable": actionable,
            "by_priority": by_priority,
            "by_category": by_category,
        }
