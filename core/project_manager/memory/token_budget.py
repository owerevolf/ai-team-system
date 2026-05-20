"""
token_budget.py — Token Governance Runtime.

MAX ACTIVE CONTEXT: 150k tokens.

Priority order:
1. Current task
2. Safety/governance
3. Architectural constraints
4. Fragile systems
5. Recent history
6. General summaries

Principle: NOT "throw entire repo into LLM".
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


# Token estimation: ~4 chars per token
CHARS_PER_TOKEN = 4

# Default budget allocation
DEFAULT_MAX_TOKENS = 150_000

# Priority tiers (percentage of budget)
PRIORITY_BUDGET = {
    1: 0.30,  # Current task: 30%
    2: 0.15,  # Safety/governance: 15%
    3: 0.20,  # Architectural constraints: 20%
    4: 0.15,  # Fragile systems: 15%
    5: 0.10,  # Recent history: 10%
    6: 0.10,  # General summaries: 10%
}


@dataclass
class ContextItem:
    """A single piece of context with metadata."""
    content: str = ""
    priority: int = 5  # 1 = highest, 6 = lowest
    source: str = ""  # what generated this context
    token_cost: int = 0
    is_pinned: bool = False  # pinned items cannot be evicted
    timestamp: float = 0.0


@dataclass
class BudgetReport:
    """Token budget status report."""
    max_tokens: int = 0
    used_tokens: int = 0
    available_tokens: int = 0
    utilization_pct: float = 0.0
    items_count: int = 0
    by_priority: Dict[int, int] = field(default_factory=dict)
    evicted_count: int = 0
    warnings: List[str] = field(default_factory=list)


class TokenBudget:
    """
    Token governance runtime.

    Manages context within token budget.
    Prioritizes critical context, evicts low-value context.
    """

    def __init__(self, max_tokens: int = DEFAULT_MAX_TOKENS):
        self._max_tokens = max_tokens
        self._items: List[ContextItem] = []
        self._evicted_count = 0
        self._lock = threading.Lock()

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        return max(1, len(text) // CHARS_PER_TOKEN)

    def add_context(self, content: str, priority: int = 5,
                    source: str = "", pin: bool = False) -> Tuple[bool, str]:
        """
        Add context item within budget.

        Returns (added, reason).
        """
        with self._lock:
            token_cost = self.estimate_tokens(content)

            # Pinned items always fit
            if pin:
                self._items.append(ContextItem(
                    content=content, priority=priority, source=source,
                    token_cost=token_cost, is_pinned=True,
                    timestamp=__import__("time").time(),
                ))
                self._enforce_budget()
                return True, "Pinned"

            # Check if single item exceeds budget
            if token_cost > self._max_tokens:
                return False, f"Context item ({token_cost} tokens) exceeds budget ({self._max_tokens})"

            # Add item
            self._items.append(ContextItem(
                content=content, priority=priority, source=source,
                token_cost=token_cost, is_pinned=False,
                timestamp=__import__("time").time(),
            ))

            # Enforce budget (evict low-priority items if needed)
            evicted = self._enforce_budget()

            return True, f"Added (evicted {evicted} items)" if evicted > 0 else "Added"

    def remove_context(self, source: str) -> int:
        """Remove all context items from a source. Returns count removed."""
        with self._lock:
            original_len = len(self._items)
            self._items = [item for item in self._items if item.source != source]
            return original_len - len(self._items)

    def get_context(self, max_tokens: int = 0) -> str:
        """
        Get assembled context string within budget.

        Items are sorted by priority (1 first), then by timestamp (newest first).
        """
        max_tokens = max_tokens or self._max_tokens

        with self._lock:
            # Sort: priority asc, then timestamp desc
            sorted_items = sorted(
                self._items,
                key=lambda item: (item.priority, -item.timestamp),
            )

            lines = []
            current_tokens = 0

            for item in sorted_items:
                if current_tokens + item.token_cost > max_tokens:
                    if item.is_pinned:
                        # Pinned items must fit — skip non-pinned first
                        continue
                    break
                lines.append(item.content)
                current_tokens += item.token_cost

            return "\n\n".join(lines)

    def get_budget_report(self) -> BudgetReport:
        """Get current budget status."""
        with self._lock:
            used = sum(item.token_cost for item in self._items)
            by_priority: Dict[int, int] = {}
            for item in self._items:
                by_priority[item.priority] = by_priority.get(item.priority, 0) + item.token_cost

            warnings = []
            utilization = used / self._max_tokens * 100 if self._max_tokens > 0 else 0

            if utilization > 90:
                warnings.append(f"Critical: {utilization:.1f}% budget used")
            elif utilization > 75:
                warnings.append(f"Warning: {utilization:.1f}% budget used")

            if self._evicted_count > 10:
                warnings.append(f"High eviction count: {self._evicted_count}")

            return BudgetReport(
                max_tokens=self._max_tokens,
                used_tokens=used,
                available_tokens=self._max_tokens - used,
                utilization_pct=round(utilization, 1),
                items_count=len(self._items),
                by_priority=by_priority,
                evicted_count=self._evicted_count,
                warnings=warnings,
            )

    def _enforce_budget(self) -> int:
        """Evict items until within budget. Returns count evicted."""
        total = sum(item.token_cost for item in self._items)
        if total <= self._max_tokens:
            return 0

        evicted = 0
        # Sort by priority desc (evict lowest first), then timestamp asc (oldest first)
        self._items.sort(
            key=lambda item: (-item.priority, item.timestamp)
        )

        while total > self._max_tokens and self._items:
            # Find lowest-priority non-pinned item
            evict_idx = -1
            for i in range(len(self._items) - 1, -1, -1):
                if not self._items[i].is_pinned:
                    evict_idx = i
                    break

            if evict_idx == -1:
                # All items are pinned — can't evict
                logger.warning("All context items are pinned, cannot enforce budget")
                break

            evicted_item = self._items.pop(evict_idx)
            total -= evicted_item.token_cost
            evicted += 1
            self._evicted_count += 1

        return evicted

    def clear(self) -> None:
        """Clear all context items."""
        with self._lock:
            self._items.clear()

    def clear_by_priority(self, priority: int) -> int:
        """Clear all items of a specific priority. Returns count cleared."""
        with self._lock:
            original_len = len(self._items)
            self._items = [item for item in self._items if item.priority != priority]
            return original_len - len(self._items)

    def get_priority_budget(self, priority: int) -> int:
        """Get token budget for a specific priority tier."""
        pct = PRIORITY_BUDGET.get(priority, 0.1)
        return int(self._max_tokens * pct)
