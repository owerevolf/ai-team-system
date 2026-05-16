"""
P5 — Runtime Explainability Layer (Phase 9)

Unified explanation protocol for ALL runtime actions.
Every action explains: WHY, SOURCE, CONSTRAINTS, IMPACT, CONFIDENCE, RECOVERY.

Integrates with existing runtime/explainability.py — extends it with
a unified protocol that covers all runtime operations.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class ExplanationField(Enum):
    WHY = "why"              # Why this action happened
    SOURCE = "source"        # What data was used
    CONSTRAINTS = "constraints"  # What governance rules applied
    IMPACT = "impact"        # What was affected
    CONFIDENCE = "confidence"  # How confident (0-1)
    RECOVERY = "recovery"    # How to rollback


@dataclass
class UnifiedExplanation:
    """A complete explanation for any runtime action."""
    action_id: str
    action_type: str
    timestamp: float = 0.0
    why: str = ""
    source: str = ""
    constraints: list[str] = field(default_factory=list)
    impact: list[str] = field(default_factory=list)
    confidence: float = 1.0
    recovery: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "timestamp": self.timestamp,
            "why": self.why,
            "source": self.source,
            "constraints": self.constraints,
            "impact": self.impact,
            "confidence": self.confidence,
            "recovery": self.recovery,
            "metadata": self.metadata,
        }

    def format_display(self) -> str:
        """Format for human reading."""
        lines = [
            f"Action: {self.action_type} ({self.action_id})",
            f"  WHY: {self.why}",
            f"  SOURCE: {self.source}",
        ]
        if self.constraints:
            lines.append(f"  CONSTRAINTS: {', '.join(self.constraints)}")
        if self.impact:
            lines.append(f"  IMPACT: {', '.join(self.impact)}")
        lines.append(f"  CONFIDENCE: {self.confidence:.0%}")
        if self.recovery:
            lines.append(f"  RECOVERY: {self.recovery}")
        return "\n".join(lines)


class ExplainabilityLayer:
    """
    Unified explainability for all runtime operations.

    Usage:
        layer = ExplainabilityLayer()

        # Explain any action with the unified protocol
        explanation = layer.explain(
            action_type="file_modify",
            action_id="mod-001",
            why="Fix broken import in auth module",
            source="repo_repair scan found 'nonexistent_module' at line 5",
            constraints=["beginner_mode", "require_approval_for_modify"],
            impact=["src/auth.py: import fixed"],
            confidence=0.95,
            recovery="git reset --hard abc123",
        )

        # Query explanations
        recent = layer.get_explanations(limit=10)
    """

    def __init__(self) -> None:
        self._explanations: list[UnifiedExplanation] = []

    def explain(
        self,
        action_type: str,
        action_id: str = "",
        why: str = "",
        source: str = "",
        constraints: Optional[list[str]] = None,
        impact: Optional[list[str]] = None,
        confidence: float = 1.0,
        recovery: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> UnifiedExplanation:
        """Create and store a unified explanation."""
        import uuid
        if not action_id:
            action_id = f"exp-{uuid.uuid4().hex[:8]}"

        exp = UnifiedExplanation(
            action_id=action_id,
            action_type=action_type,
            why=why,
            source=source,
            constraints=constraints or [],
            impact=impact or [],
            confidence=confidence,
            recovery=recovery,
            metadata=metadata or {},
        )
        self._explanations.append(exp)
        # Keep manageable
        if len(self._explanations) > 1000:
            self._explanations = self._explanations[-1000:]
        return exp

    def get_explanations(
        self,
        action_type: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get explanations with optional filtering."""
        results = self._explanations
        if action_type:
            results = [e for e in results if e.action_type == action_type]
        if min_confidence > 0:
            results = [e for e in results if e.confidence >= min_confidence]
        return [e.to_dict() for e in results[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        """Get explainability stats."""
        total = len(self._explanations)
        by_type: dict[str, int] = {}
        avg_confidence = 0.0
        for e in self._explanations:
            by_type[e.action_type] = by_type.get(e.action_type, 0) + 1
            avg_confidence += e.confidence
        if total > 0:
            avg_confidence /= total
        return {
            "total_explanations": total,
            "by_type": by_type,
            "avg_confidence": round(avg_confidence, 3),
        }
