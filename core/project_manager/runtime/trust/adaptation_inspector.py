"""
P3 — Runtime Adaptation Inspector (Phase 11)

Answers "Why am I seeing this?", "Why was this hidden?", "Why was this delayed?"
for every adaptive decision runtime makes.

Key principle: every adaptation decision must be explainable on demand.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class AdaptationType(Enum):
    SURFACED = "surfaces"       # Event was shown
    SUPPRESSED = "suppressed"   # Event was hidden
    DELAYED = "delayed"         # Event was batched/deferred
    COMPRESSED = "compressed"   # Event was summarized
    PRIORITIZED = "prioritized" # Event priority was changed
    AUTO_APPLIED = "auto_applied" # Action was auto-executed
    BATCHED = "batched"         # Action was grouped with others


class AdaptationReason(Enum):
    CALM_MODE = "calm_mode"
    NOISE_REDUCTION = "noise_reduction"
    TRANSPARENCY_CONTRACT = "transparency_contract"
    VISIBILITY_GUARANTEE = "visibility_guarantee"
    ATTENTION_PRIORITY = "attention_priority"
    FOCUS_BLOCK = "focus_block"
    USER_PREFERENCE = "user_preference"
    RISK_TIER = "risk_tier"
    DEDUPLICATION = "deduplication"
    COMPRESSION_LEVEL = "compression_level"
    TRUST_DRIFT = "trust_drift"


@dataclass
class AdaptationDecision:
    """A record of a single adaptation decision."""
    decision_id: str
    adaptation_type: AdaptationType
    reason: AdaptationReason
    event_id: str
    event_category: str
    timestamp: float = 0.0
    detail: str = ""
    reversible: bool = True
    user_visible: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.decision_id:
            self.decision_id = f"dec-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "adaptation_type": self.adaptation_type.value,
            "reason": self.reason.value,
            "event_id": self.event_id,
            "event_category": self.event_category,
            "timestamp": self.timestamp,
            "detail": self.detail,
            "reversible": self.reversible,
            "user_visible": self.user_visible,
            "metadata": self.metadata,
        }

    def explain(self) -> str:
        """Generate human-readable explanation."""
        explanations = {
            AdaptationType.SURFACED: f"Shown because: {self.detail}",
            AdaptationType.SUPPRESSED: f"Hidden because: {self.detail}. Reversible: {self.reversible}",
            AdaptationType.DELAYED: f"Delayed because: {self.detail}. Will be shown at next batch.",
            AdaptationType.COMPRESSED: f"Summarized because: {self.detail}. Full detail available on demand.",
            AdaptationType.PRIORITIZED: f"Priority changed because: {self.detail}",
            AdaptationType.AUTO_APPLIED: f"Auto-applied because: {self.detail}. Reversible: {self.reversible}",
            AdaptationType.BATCHED: f"Batched because: {self.detail}. Part of a grouped action.",
        }
        return explanations.get(self.adaptation_type, f"Decision: {self.adaptation_type.value} — {self.detail}")


class RuntimeAdaptationInspector:
    """
    Records and explains all adaptive decisions runtime makes.

    Usage:
        inspector = RuntimeAdaptationInspector()
        inspector.record(AdaptationType.SUPPRESSED, AdaptationReason.CALM_MODE,
                         event_id="evt-1", event_category="progress",
                         detail="Calm mode suppresses progress updates")
        explanation = inspector.why_hidden("evt-1")
        all_decisions = inspector.get_decisions()
    """

    def __init__(self, max_decisions: int = 1000) -> None:
        self._decisions: dict[str, AdaptationDecision] = {}
        self._event_index: dict[str, list[str]] = {}  # event_id -> [decision_ids]
        self._max_decisions = max_decisions

    def record(self, adaptation_type: AdaptationType, reason: AdaptationReason,
               event_id: str, event_category: str = "", detail: str = "",
               reversible: bool = True, metadata: Optional[dict[str, Any]] = None) -> AdaptationDecision:
        """Record an adaptation decision."""
        decision = AdaptationDecision(
            decision_id=f"dec-{uuid.uuid4().hex[:8]}",
            adaptation_type=adaptation_type,
            reason=reason,
            event_id=event_id,
            event_category=event_category,
            detail=detail,
            reversible=reversible,
            metadata=metadata or {},
        )
        self._decisions[decision.decision_id] = decision
        self._event_index.setdefault(event_id, []).append(decision.decision_id)
        self._enforce_limit()
        return decision

    def why_surfaced(self, event_id: str) -> Optional[str]:
        """Explain why an event was surfaced."""
        decisions = self._get_event_decisions(event_id)
        for d in decisions:
            if d.adaptation_type == AdaptationType.SURFACED:
                return d.explain()
        return None

    def why_hidden(self, event_id: str) -> Optional[str]:
        """Explain why an event was hidden/suppressed."""
        decisions = self._get_event_decisions(event_id)
        for d in decisions:
            if d.adaptation_type == AdaptationType.SUPPRESSED:
                return d.explain()
        return None

    def why_delayed(self, event_id: str) -> Optional[str]:
        """Explain why an event was delayed/batched."""
        decisions = self._get_event_decisions(event_id)
        for d in decisions:
            if d.adaptation_type == AdaptationType.DELAYED:
                return d.explain()
        return None

    def why_compressed(self, event_id: str) -> Optional[str]:
        """Explain why an event was compressed."""
        decisions = self._get_event_decisions(event_id)
        for d in decisions:
            if d.adaptation_type == AdaptationType.COMPRESSED:
                return d.explain()
        return None

    def get_decisions(self, adaptation_type: Optional[AdaptationType] = None,
                      reason: Optional[AdaptationReason] = None,
                      limit: int = 50) -> list[AdaptationDecision]:
        """Get adaptation decisions with optional filtering."""
        results = list(self._decisions.values())
        if adaptation_type:
            results = [d for d in results if d.adaptation_type == adaptation_type]
        if reason:
            results = [d for d in results if d.reason == reason]
        # Sort by timestamp, newest first
        results.sort(key=lambda d: d.timestamp, reverse=True)
        return results[:limit]

    def get_event_history(self, event_id: str) -> list[AdaptationDecision]:
        """Get all adaptation decisions for an event."""
        return self._get_event_decisions(event_id)

    def get_stats(self) -> dict[str, Any]:
        """Get adaptation decision stats."""
        total = len(self._decisions)
        by_type: dict[str, int] = {}
        by_reason: dict[str, int] = {}
        reversible_count = 0
        for d in self._decisions.values():
            t = d.adaptation_type.value
            by_type[t] = by_type.get(t, 0) + 1
            r = d.reason.value
            by_reason[r] = by_reason.get(r, 0) + 1
            if d.reversible:
                reversible_count += 1

        return {
            "total_decisions": total,
            "by_type": by_type,
            "by_reason": by_reason,
            "reversible_count": reversible_count,
            "irreversible_count": total - reversible_count,
        }

    def _get_event_decisions(self, event_id: str) -> list[AdaptationDecision]:
        """Get all decisions for an event."""
        decision_ids = self._event_index.get(event_id, [])
        return [self._decisions[did] for did in decision_ids if did in self._decisions]

    def _enforce_limit(self) -> None:
        """Keep decisions under max limit."""
        if len(self._decisions) <= self._max_decisions:
            return
        # Remove oldest
        sorted_decisions = sorted(self._decisions.values(), key=lambda d: d.timestamp)
        to_remove = len(self._decisions) - self._max_decisions
        for d in sorted_decisions[:to_remove]:
            del self._decisions[d.decision_id]
            # Clean up index
            if d.event_id in self._event_index:
                self._event_index[d.event_id] = [
                    did for did in self._event_index[d.event_id]
                    if did != d.decision_id
                ]
