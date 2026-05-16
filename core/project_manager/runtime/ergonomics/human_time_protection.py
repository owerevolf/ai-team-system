"""
P7 — Human Time Protection (Phase 10)

Minimizes context switching, approval interruptions, and workflow
fragmentation. Batches interruptions, protects focus time.

Key principle: the user's time is the most expensive resource.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class InterruptionType(Enum):
    APPROVAL = "approval"
    ERROR = "error"
    NOTIFICATION = "notification"
    PROGRESS = "progress"
    SUGGESTION = "suggestion"


class InterruptionUrgency(Enum):
    NOW = "now"           # Must interrupt immediately
    BATCH = "batch"       # Can be batched with others
    DEFER = "defer"       # Can wait until natural break
    LOG_ONLY = "log_only" # Don't interrupt at all


@dataclass
class Interruption:
    """A potential interruption to the user."""
    interruption_id: str
    interruption_type: InterruptionType
    urgency: InterruptionUrgency
    message: str
    source: str = ""
    timestamp: float = 0.0
    delivered: bool = False
    batch_key: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "interruption_id": self.interruption_id,
            "interruption_type": self.interruption_type.value,
            "urgency": self.urgency.value,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp,
            "delivered": self.delivered,
        }


@dataclass
class FocusBlock:
    """A period of protected focus time."""
    block_id: str
    started_at: float
    label: str = ""
    allowed_interruptions: set[InterruptionUrgency] = field(
        default_factory=lambda: {InterruptionUrgency.NOW}
    )
    ended_at: float = 0.0

    @property
    def is_active(self) -> bool:
        return self.ended_at == 0

    @property
    def duration_seconds(self) -> float:
        end = self.ended_at if self.ended_at else time.time()
        return end - self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "label": self.label,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "is_active": self.is_active,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class InterruptionBatch:
    """A batch of interruptions to be delivered together."""
    batch_id: str
    interruptions: list[Interruption]
    created_at: float = 0.0
    delivered_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "count": len(self.interruptions),
            "interruptions": [i.to_dict() for i in self.interruptions],
            "created_at": self.created_at,
            "delivered_at": self.delivered_at,
        }


class HumanTimeProtection:
    """
    Protects user's time by batching and deferring interruptions.

    Usage:
        htp = HumanTimeProtection()
        htp.start_focus_block("Coding session")
        htp.add_interruption(Interruption(...))
        # Only critical interruptions break through
        ready = htp.get_ready_interruptions()
    """

    def __init__(
        self,
        batch_window_seconds: float = 30.0,
        max_batch_size: int = 10,
    ) -> None:
        self._interruptions: list[Interruption] = []
        self._batches: list[InterruptionBatch] = []
        self._focus_blocks: list[FocusBlock] = []
        self._batch_window = batch_window_seconds
        self._max_batch_size = max_batch_size
        self._total_interruptions_prevented = 0

    def start_focus_block(self, label: str = "", allowed: Optional[set[InterruptionUrgency]] = None) -> str:
        """Start a focus block. Returns block_id."""
        import uuid
        block = FocusBlock(
            block_id=f"focus-{uuid.uuid4().hex[:8]}",
            started_at=time.time(),
            label=label,
            allowed_interruptions=allowed or {InterruptionUrgency.NOW},
        )
        self._focus_blocks.append(block)
        return block.block_id

    def end_focus_block(self, block_id: str) -> Optional[FocusBlock]:
        """End a focus block. Returns the block info."""
        for block in self._focus_blocks:
            if block.block_id == block_id and block.is_active:
                block.ended_at = time.time()
                return block
        return None

    def get_active_focus_block(self) -> Optional[FocusBlock]:
        """Get the current active focus block, if any."""
        for block in reversed(self._focus_blocks):
            if block.is_active:
                return block
        return None

    def add_interruption(self, interruption: Interruption) -> bool:
        """
        Add a potential interruption. Returns True if it should be
        delivered immediately, False if batched/deferred.
        """
        focus = self.get_active_focus_block()

        # If in focus block, only allow urgent interruptions
        if focus:
            if interruption.urgency not in focus.allowed_interruptions:
                self._total_interruptions_prevented += 1
                # Still store for later delivery
                self._interruptions.append(interruption)
                return False

        # Critical interruptions always go through
        if interruption.urgency == InterruptionUrgency.NOW:
            interruption.delivered = True
            self._interruptions.append(interruption)
            return True

        # Log-only interruptions never go through
        if interruption.urgency == InterruptionUrgency.LOG_ONLY:
            self._total_interruptions_prevented += 1
            self._interruptions.append(interruption)
            return False

        # Batch and defer go to the queue
        self._interruptions.append(interruption)
        return False

    def get_ready_interruptions(self) -> list[Interruption]:
        """
        Get interruptions that are ready to be delivered.
        Only returns interruptions that should break through now.
        """
        now = time.time()
        ready = []
        remaining = []

        for interruption in self._interruptions:
            if interruption.delivered:
                continue

            if interruption.urgency == InterruptionUrgency.NOW:
                interruption.delivered = True
                ready.append(interruption)
            elif interruption.urgency == InterruptionUrgency.BATCH:
                # Deliver if batch window has passed
                if (now - interruption.timestamp) >= self._batch_window:
                    interruption.delivered = True
                    ready.append(interruption)
                else:
                    remaining.append(interruption)
            elif interruption.urgency == InterruptionUrgency.DEFER:
                # Only deliver if no active focus block
                focus = self.get_active_focus_block()
                if not focus:
                    interruption.delivered = True
                    ready.append(interruption)
                else:
                    remaining.append(interruption)
            else:
                remaining.append(interruption)

        self._interruptions = remaining
        return ready

    def create_batch(self, interruptions: Optional[list[Interruption]] = None) -> InterruptionBatch:
        """Create a batch from pending interruptions."""
        import uuid
        if interruptions is None:
            pending = [i for i in self._interruptions if not i.delivered]
            interruptions = pending[:self._max_batch_size]

        batch = InterruptionBatch(
            batch_id=f"batch-{uuid.uuid4().hex[:8]}",
            interruptions=interruptions,
        )
        self._batches.append(batch)
        return batch

    def deliver_batch(self, batch_id: str) -> list[Interruption]:
        """Mark a batch as delivered. Returns the interruptions."""
        for batch in self._batches:
            if batch.batch_id == batch_id and not batch.delivered_at:
                batch.delivered_at = time.time()
                for interruption in batch.interruptions:
                    interruption.delivered = True
                # Remove from pending
                delivered_ids = {i.interruption_id for i in batch.interruptions}
                self._interruptions = [
                    i for i in self._interruptions
                    if i.interruption_id not in delivered_ids
                ]
                return batch.interruptions
        return []

    def get_pending_count(self) -> int:
        """Get count of pending (undelivered) interruptions."""
        return sum(1 for i in self._interruptions if not i.delivered)

    def get_stats(self) -> dict[str, Any]:
        """Get human time protection stats."""
        total = len(self._interruptions) + self._total_interruptions_prevented
        delivered = sum(1 for i in self._interruptions if i.delivered)
        pending = self.get_pending_count()
        by_urgency: dict[str, int] = {}
        for i in self._interruptions:
            u = i.urgency.value
            by_urgency[u] = by_urgency.get(u, 0) + 1

        active_focus = self.get_active_focus_block()
        return {
            "total_interruptions": total,
            "delivered": delivered,
            "pending": pending,
            "prevented": self._total_interruptions_prevented,
            "prevention_rate": (
                round(self._total_interruptions_prevented / total, 3)
                if total > 0 else 0.0
            ),
            "by_urgency": by_urgency,
            "active_focus_block": active_focus.to_dict() if active_focus else None,
            "total_focus_blocks": len(self._focus_blocks),
            "total_batches": len(self._batches),
        }
